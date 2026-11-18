package kr.todak.admin;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import kr.todak.common.ErrorLog;
import kr.todak.config.TodakProperties;
import kr.todak.domain.Farm;
import kr.todak.domain.Gateway;
import kr.todak.domain.Sensor;
import kr.todak.ingest.SensorIngestService;
import kr.todak.mqtt.MqttGateway;
import kr.todak.repo.*;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.info.BuildProperties;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.File;
import java.lang.management.ManagementFactory;
import java.time.*;
import java.util.*;

/**
 * 운영 점검 API (운영팀 이관용, SCR-A7). 운영 매뉴얼 4장 '일상 운영 — 일일 점검'의 항목을 서버가 직접 판정해 돌려준다.
 * 판정: OK(정상) · WARN(확인 필요) · FAIL(즉시 조치). 각 항목에 매뉴얼의 조치 절차 번호를 붙인다.
 */
@Tag(name = "관리자", description = "운영 점검")
@RestController
@RequestMapping("/api/admin/ops")
@PreAuthorize("hasRole('ADMIN')")
public class OpsController {
    /** 백업 판정 기준: 일 1회(04:00) 백업이므로 26시간이 지나면 경고 */
    static final long BACKUP_WARN_HOURS = 26;
    static final double DISK_WARN_FREE = 0.15;
    static final double DISK_FAIL_FREE = 0.05;

    private final JdbcTemplate jdbc;
    private final FarmRepository farms;
    private final SensorRepository sensors;
    private final SensorDataRepository data;
    private final GatewayRepository gateways;
    private final ControlCommandRepository commands;
    private final AlertRepository alerts;
    private final SensorIngestService ingest;
    private final MqttGateway mqtt;
    private final ErrorLog errorLog;
    private final ObjectProvider<BuildProperties> build;
    private final int staleSeconds;
    private final int rawDays;
    private final String backupDir;

    public OpsController(JdbcTemplate jdbc, FarmRepository farms, SensorRepository sensors, SensorDataRepository data, GatewayRepository gateways,
                         ControlCommandRepository commands, AlertRepository alerts, SensorIngestService ingest, MqttGateway mqtt, ErrorLog errorLog,
                         ObjectProvider<BuildProperties> build, TodakProperties props, @Value("${todak.ops.backup-dir:/backups}") String backupDir) {
        this.jdbc = jdbc;
        this.farms = farms;
        this.sensors = sensors;
        this.data = data;
        this.gateways = gateways;
        this.commands = commands;
        this.alerts = alerts;
        this.ingest = ingest;
        this.mqtt = mqtt;
        this.errorLog = errorLog;
        this.build = build;
        this.staleSeconds = props.control() == null ? 180 : props.control().staleSeconds();
        this.rawDays = props.retention() == null ? 1095 : props.retention().rawDays();
        this.backupDir = backupDir;
    }

    public record Check(String key, String label, String status, String detail, String action) {
    }

    @Operation(summary = "운영 점검", description = "일일 점검 항목 자동 판정, 서버·DB·백업·보존 정보")
    @GetMapping
    public Map<String, Object> ops() {
        LocalDateTime now = LocalDateTime.now();
        Map<String, Object> backup = backupInfo();
        Map<String, Object> server = serverInfo();
        Map<String, Object> db = dbInfo();

        List<Check> checks = new ArrayList<>();
        boolean mq = mqtt.isConnected();
        checks.add(new Check("mqtt", "MQTT 브로커 연결", mq ? "OK" : "FAIL", mq ? "연결됨" : "백엔드가 브로커에 연결되지 않음", "매뉴얼 6.2"));

        List<Gateway> gws = gateways.findAll();
        // 한 번도 하트비트가 없었던 게이트웨이는 아직 설치(개통) 전으로 보고 장애에서 뺀다
        List<String> off = gws.stream().filter(g -> !"ONLINE".equals(g.getStatus()) && g.getLastHeartbeatAt() != null).map(Gateway::getGatewayCode).toList();
        List<String> never = gws.stream().filter(g -> !"ONLINE".equals(g.getStatus()) && g.getLastHeartbeatAt() == null).map(Gateway::getGatewayCode).toList();
        long online = gws.stream().filter(g -> "ONLINE".equals(g.getStatus())).count();
        String gwDetail = (off.isEmpty() ? "온라인 " + online + "대" : "오프라인: " + String.join(", ", off))
                + (never.isEmpty() ? "" : " · 미개통(연결 기록 없음): " + String.join(", ", never));
        checks.add(new Check("gateway", "게이트웨이 온라인", off.isEmpty() ? "OK" : "FAIL", gwDetail, "매뉴얼 6.3"));

        LocalDateTime last = data.lastReceivedAt();
        long lag = last == null ? -1 : Duration.between(last, now).getSeconds();
        checks.add(new Check("ingest", "센서 데이터 수집", last == null ? "FAIL" : lag > staleSeconds * 3L ? "FAIL" : lag > staleSeconds ? "WARN" : "OK",
                last == null ? "수집된 데이터 없음" : "마지막 수신 " + lag + "초 전 (기준 " + staleSeconds + "초)", "매뉴얼 6.3"));

        List<String> fault = sensors.findAll().stream().filter(s -> "FAULT".equals(s.getStatus())).map(Sensor::getSensorCode).toList();
        checks.add(new Check("sensor", "센서 상태", fault.isEmpty() ? "OK" : "WARN",
                fault.isEmpty() ? "오류 센서 없음" : "오류: " + String.join(", ", fault), "매뉴얼 6.4"));

        long open = alerts.countByFarmIdInAndStatusNot(farms.findAll().stream().map(Farm::getFarmId).toList(), "RESOLVED");
        checks.add(new Check("alert", "미해결 경보", open == 0 ? "OK" : "WARN", open + "건", "매뉴얼 4.2"));

        long failed = commands.countByRequestedAtAfterAndStatus(now.minusHours(24), "FAILED")
                + commands.countByRequestedAtAfterAndStatus(now.minusHours(24), "TIMEOUT");
        checks.add(new Check("command", "24시간 제어 실패·응답 없음", failed == 0 ? "OK" : "WARN", failed + "건", "매뉴얼 6.5"));

        long errs = errorLog.recent().stream().filter(e -> e.at().isAfter(now.minusHours(24))).count();
        checks.add(new Check("errors", "24시간 서버 오류 로그", errs == 0 ? "OK" : "WARN", errs + "건 (관리자 > 로그 > 오류·예외)", "매뉴얼 6.6"));

        Object lastBackupAt = backup.get("lastAt");
        String bStatus;
        String bDetail;
        if (!Boolean.TRUE.equals(backup.get("dirMounted"))) {
            bStatus = "WARN";
            bDetail = "백업 폴더가 서버에 연결되지 않아 확인 불가 (" + backupDir + ")";
        } else if (lastBackupAt == null) {
            bStatus = "FAIL";
            bDetail = "백업 파일 없음";
        } else {
            long h = Duration.between((LocalDateTime) lastBackupAt, now).toHours();
            bStatus = h > BACKUP_WARN_HOURS * 2 ? "FAIL" : h > BACKUP_WARN_HOURS ? "WARN" : "OK";
            bDetail = "마지막 백업 " + h + "시간 전 · " + backup.get("lastFile");
        }
        checks.add(new Check("backup", "DB 백업 (일 1회)", bStatus, bDetail, "매뉴얼 5.1"));

        double free = (double) server.get("diskFreeRatio");
        checks.add(new Check("disk", "디스크 여유 공간", free < DISK_FAIL_FREE ? "FAIL" : free < DISK_WARN_FREE ? "WARN" : "OK",
                String.format("여유 %.1f%% (%s / %s)", free * 100, gb((long) server.get("diskFreeBytes")), gb((long) server.get("diskTotalBytes"))), "매뉴얼 5.3"));

        Map<String, Long> summary = new LinkedHashMap<>();
        for (String s : List.of("OK", "WARN", "FAIL")) {
            summary.put(s, checks.stream().filter(c -> c.status().equals(s)).count());
        }

        Map<String, Object> m = new LinkedHashMap<>();
        m.put("checkedAt", now);
        m.put("overall", summary.get("FAIL") > 0 ? "FAIL" : summary.get("WARN") > 0 ? "WARN" : "OK");
        m.put("summary", summary);
        m.put("checks", checks);
        m.put("server", server);
        m.put("database", db);
        m.put("backup", backup);
        m.put("retention", Map.of("rawDays", rawDays, "oldestRaw", Optional.ofNullable(
                jdbc.queryForObject("SELECT MIN(measured_at) FROM TB_SENSOR_DATA", LocalDateTime.class)).map(Object::toString).orElse("-")));
        m.put("ingestCounters", ingest.stats());
        return m;
    }

    private Map<String, Object> serverInfo() {
        Map<String, Object> s = new LinkedHashMap<>();
        BuildProperties b = build.getIfAvailable();
        s.put("version", b == null ? "dev" : b.getVersion());
        s.put("builtAt", b == null || b.getTime() == null ? null : LocalDateTime.ofInstant(b.getTime(), ZoneId.systemDefault()));
        long start = ManagementFactory.getRuntimeMXBean().getStartTime();
        s.put("startedAt", LocalDateTime.ofInstant(Instant.ofEpochMilli(start), ZoneId.systemDefault()));
        s.put("uptimeSec", ManagementFactory.getRuntimeMXBean().getUptime() / 1000);
        s.put("timeZone", ZoneId.systemDefault().getId());
        s.put("java", System.getProperty("java.version"));
        Runtime rt = Runtime.getRuntime();
        s.put("memUsedBytes", rt.totalMemory() - rt.freeMemory());
        s.put("memMaxBytes", rt.maxMemory());
        File root = new File("/");
        s.put("diskTotalBytes", root.getTotalSpace());
        s.put("diskFreeBytes", root.getUsableSpace());
        s.put("diskFreeRatio", root.getTotalSpace() == 0 ? 1.0 : (double) root.getUsableSpace() / root.getTotalSpace());
        return s;
    }

    private Map<String, Object> dbInfo() {
        Map<String, Object> d = new LinkedHashMap<>();
        d.put("version", jdbc.queryForObject("SELECT VERSION()", String.class));
        List<Map<String, Object>> tables = jdbc.queryForList(
                "SELECT TABLE_NAME AS name, TABLE_ROWS AS approxRows, DATA_LENGTH + INDEX_LENGTH AS bytes "
                        + "FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE' ORDER BY bytes DESC");
        d.put("tables", tables);
        d.put("totalBytes", tables.stream().mapToLong(t -> ((Number) t.get("bytes")).longValue()).sum());
        d.put("sensorDataRows", jdbc.queryForObject("SELECT COUNT(*) FROM TB_SENSOR_DATA", Long.class));
        try {
            d.put("migration", jdbc.queryForObject(
                    "SELECT CONCAT('V', version, ' ', description) FROM flyway_schema_history WHERE success = 1 ORDER BY installed_rank DESC LIMIT 1", String.class));
        } catch (Exception e) {
            d.put("migration", "-");
        }
        return d;
    }

    private Map<String, Object> backupInfo() {
        Map<String, Object> b = new LinkedHashMap<>();
        File dir = new File(backupDir);
        b.put("dir", backupDir);
        b.put("dirMounted", dir.isDirectory());
        File[] files = dir.isDirectory() ? dir.listFiles((x, n) -> n.startsWith("todak_") && n.endsWith(".sql.gz")) : null;
        List<Map<String, Object>> list = new ArrayList<>();
        if (files != null) {
            Arrays.sort(files, Comparator.comparingLong(File::lastModified).reversed());
            for (File f : files) {
                list.add(Map.of("file", f.getName(), "bytes", f.length(),
                        "at", LocalDateTime.ofInstant(Instant.ofEpochMilli(f.lastModified()), ZoneId.systemDefault())));
            }
        }
        b.put("files", list.size() > 10 ? list.subList(0, 10) : list);
        b.put("count", list.size());
        b.put("lastFile", list.isEmpty() ? null : list.get(0).get("file"));
        b.put("lastAt", list.isEmpty() ? null : list.get(0).get("at"));
        return b;
    }

    private static String gb(long bytes) {
        return String.format("%.1fGB", bytes / 1024.0 / 1024 / 1024);
    }
}
