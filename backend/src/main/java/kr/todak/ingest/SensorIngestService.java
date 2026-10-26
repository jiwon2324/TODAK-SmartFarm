package kr.todak.ingest;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import kr.todak.alert.AlertService;
import kr.todak.common.ErrorLog;
import kr.todak.domain.Sensor;
import kr.todak.repo.SensorRepository;
import kr.todak.stream.SseHub;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 센서 측정값 수신 → 형식 검증 → 중복 제거 → 범위·급변 검사 → 품질 플래그 → 저장 → SSE. [REQ-F-01, REQ-F-18]
 * 범위를 벗어난 값도 저장하되 quality로 표시하고, 제어 판단에는 quality=OK만 쓴다.
 * 처리량: 센서 정보는 60초 캐시, 저장은 INSERT IGNORE 한 번(msg_id·(sensor_id, measured_at) 유니크키가 중복을 막는다).
 */
@Service
public class SensorIngestService {
    private static final ZoneId SEOUL = ZoneId.of("Asia/Seoul");
    private static final long CACHE_MS = 60_000;
    private static final String INSERT = """
            INSERT IGNORE INTO TB_SENSOR_DATA (sensor_id, measured_at, value, value_min, value_max, sample_count, quality, msg_id, is_buffered, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""";

    private record Cached(Sensor sensor, long loadedAt) {
    }

    private record Last(LocalDateTime at, double value, String quality) {
    }

    private final ObjectMapper om = new ObjectMapper();
    private final SensorRepository sensors;
    private final JdbcTemplate jdbc;
    private final AlertService alerts;
    private final SseHub sse;
    private final ErrorLog errorLog;
    private final Map<String, Cached> cache = new ConcurrentHashMap<>();
    private final Map<Integer, Last> last = new ConcurrentHashMap<>();
    private final Map<Integer, Long> touched = new ConcurrentHashMap<>();
    private final AtomicLong received = new AtomicLong();
    private final AtomicLong saved = new AtomicLong();
    private final AtomicLong duplicates = new AtomicLong();
    private final AtomicLong rejected = new AtomicLong();

    public SensorIngestService(SensorRepository sensors, JdbcTemplate jdbc, AlertService alerts, SseHub sse, ErrorLog errorLog) {
        this.sensors = sensors;
        this.jdbc = jdbc;
        this.alerts = alerts;
        this.sse = sse;
        this.errorLog = errorLog;
    }

    public enum Result { SAVED, DUPLICATE, REJECTED }

    public Result ingest(Integer farmId, String sensorCode, String payload) {
        received.incrementAndGet();
        JsonNode j;
        try {
            j = om.readTree(payload);
        } catch (Exception e) {
            return reject("JSON 형식 오류 (" + sensorCode + ")");
        }
        if (!j.hasNonNull("msgId") || !j.hasNonNull("value") || !j.get("value").isNumber() || !j.hasNonNull("ts")) {
            return reject("필수 필드 누락 msgId/value/ts (" + sensorCode + ")");
        }
        Sensor s = sensor(farmId, sensorCode);
        if (s == null) {
            return reject("등록되지 않은 센서 farm=" + farmId + " " + sensorCode);
        }
        if ("RETIRED".equals(s.getStatus())) {
            return reject("폐기된 센서 " + sensorCode);
        }
        LocalDateTime measuredAt;
        try {
            measuredAt = OffsetDateTime.parse(j.get("ts").asText()).atZoneSameInstant(SEOUL).toLocalDateTime().truncatedTo(ChronoUnit.MINUTES);
        } catch (Exception e) {
            return reject("ts 형식 오류 (" + sensorCode + ")");
        }
        String msgId = j.get("msgId").asText();
        if (msgId.length() > 80) {
            return reject("msgId 길이 초과");
        }
        double v = j.get("value").asDouble();
        String quality = quality(s, v, measuredAt);
        boolean buffered = j.path("buffered").asBoolean(false);
        LocalDateTime now = LocalDateTime.now();
        int n = jdbc.update(INSERT, s.getSensorId(), measuredAt, v,
                j.hasNonNull("min") ? j.get("min").asDouble() : null, j.hasNonNull("max") ? j.get("max").asDouble() : null,
                j.hasNonNull("samples") ? j.get("samples").asInt() : null, quality, msgId, buffered, now);
        if (n == 0) {
            duplicates.incrementAndGet();
            return Result.DUPLICATE;
        }
        saved.incrementAndGet();
        Last prev = last.get(s.getSensorId());
        if (prev == null || !measuredAt.isBefore(prev.at())) {
            last.put(s.getSensorId(), new Last(measuredAt, v, quality));
        }
        touch(s, quality);
        if (!"OK".equals(quality)) {
            alerts.raise(farmId, s.getZoneId(), "OUTLIER", "WARN", "OUTLIER:" + farmId + ":" + s.getSensorCode(),
                    s.getSensorCode() + " 측정값 이상(" + quality + "): " + v + " " + s.getUnit() + " — 제어 판단에서 제외");
        }
        Map<String, Object> ev = new LinkedHashMap<>();
        ev.put("sensorId", s.getSensorId());
        ev.put("sensorCode", s.getSensorCode());
        ev.put("metric", s.getMetric());
        ev.put("zoneId", s.getZoneId());
        ev.put("value", v);
        ev.put("unit", s.getUnit());
        ev.put("measuredAt", measuredAt.toString());
        ev.put("quality", quality);
        ev.put("buffered", buffered);
        sse.publish(farmId, "reading", ev);
        return Result.SAVED;
    }

    /** 마지막 수신 시각은 센서마다 5초에 한 번만 갱신하고, 무응답(FAULT)이던 센서가 정상값을 보내면 복구 처리 */
    private void touch(Sensor s, String quality) {
        long nowMs = System.currentTimeMillis();
        Long prev = touched.get(s.getSensorId());
        if (prev != null && nowMs - prev < 5000) {
            return;
        }
        touched.put(s.getSensorId(), nowMs);
        int recovered = "OK".equals(quality)
                ? jdbc.update("UPDATE TB_SENSOR SET status = 'ACTIVE' WHERE sensor_id = ? AND status = 'FAULT'", s.getSensorId()) : 0;
        jdbc.update("UPDATE TB_SENSOR SET last_received_at = ? WHERE sensor_id = ?", LocalDateTime.now(), s.getSensorId());
        if (recovered > 0) {
            alerts.resolve("SENSOR_FAIL:" + s.getFarmId() + ":" + s.getSensorCode());
        }
    }

    private Sensor sensor(Integer farmId, String code) {
        String key = farmId + ":" + code;
        Cached c = cache.get(key);
        if (c == null || System.currentTimeMillis() - c.loadedAt() > CACHE_MS) {
            Sensor s = sensors.findByFarmIdAndSensorCode(farmId, code).orElse(null);
            if (s == null) {
                cache.remove(key);
                return null;
            }
            c = new Cached(s, System.currentTimeMillis());
            cache.put(key, c);
        }
        return c.sensor();
    }

    /** 관리자가 센서를 바꾸면 캐시를 비운다 */
    public void evictCache() {
        cache.clear();
    }

    /** 캐시와 직전 값 기억을 모두 비운다 (테스트 격리용) */
    public void clearMemory() {
        cache.clear();
        last.clear();
        touched.clear();
    }

    /** 범위(valid_min~max) 밖이면 OUT_RANGE, 직전 2분 이내 정상값과 차이가 spike_limit 초과면 SPIKE */
    String quality(Sensor s, double v, LocalDateTime t) {
        if (v < s.getValidMin() || v > s.getValidMax()) {
            return "OUT_RANGE";
        }
        Last prev = last.get(s.getSensorId());
        if (s.getSpikeLimit() != null && prev != null && "OK".equals(prev.quality()) && !prev.at().isAfter(t)
                && ChronoUnit.MINUTES.between(prev.at(), t) <= 2 && Math.abs(v - prev.value()) > s.getSpikeLimit()) {
            return "SPIKE";
        }
        return "OK";
    }

    public Result reject(String reason) {
        rejected.incrementAndGet();
        errorLog.add("INGEST", reason);
        return Result.REJECTED;
    }

    public Map<String, Long> stats() {
        return Map.of("received", received.get(), "saved", saved.get(), "duplicates", duplicates.get(), "rejected", rejected.get());
    }
}
