package kr.todak.web;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import kr.todak.common.FarmAccess;
import kr.todak.config.TodakProperties;
import kr.todak.control.RuleEngine;
import kr.todak.domain.*;
import kr.todak.repo.*;
import org.springframework.data.domain.PageRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 통합 관제 API (SCR-M1). 센서마다 '지금 괜찮은가'를 서버가 한 기준으로 판정하고, 경보·명령·상태 변경을 한 줄 타임라인으로 합친다.
 * 판정 단계 (낮은 것부터):
 *   OK      재배 기준값 범위 안
 *   WARN    재배 기준값 이탈 (ThresholdEvaluator 경보와 같은 기준)
 *   ALARM   안전 한계 규칙(is_safety) 조건 도달, 또는 측정값 품질 이상(OUT_RANGE·SPIKE)
 *   STALE   수신 끊김(stale_seconds 초과) 또는 센서 FAULT
 *   NODATA  측정값 없음
 * 화면(관제)은 판정을 다시 계산하지 않고 이 결과를 그대로 그린다.
 */
@Tag(name = "관제", description = "통합 관제 상황판 [REQ-F-01, F-06, F-08, F-09, F-18]")
@RestController
@RequestMapping("/api")
public class MonitorController {
    private final FarmAccess access;
    private final SensorRepository sensors;
    private final SensorDataRepository data;
    private final DeviceRepository devices;
    private final AlertRepository alerts;
    private final ControlCommandRepository commands;
    private final ControlLogRepository logs;
    private final ControlRuleRepository rules;
    private final CropCycleRepository cycles;
    private final RuleEngine ruleEngine;
    private final int staleSeconds;

    public MonitorController(FarmAccess access, SensorRepository sensors, SensorDataRepository data, DeviceRepository devices,
                             AlertRepository alerts, ControlCommandRepository commands, ControlLogRepository logs, ControlRuleRepository rules,
                             CropCycleRepository cycles, RuleEngine ruleEngine, TodakProperties props) {
        this.access = access;
        this.sensors = sensors;
        this.data = data;
        this.devices = devices;
        this.alerts = alerts;
        this.commands = commands;
        this.logs = logs;
        this.rules = rules;
        this.cycles = cycles;
        this.ruleEngine = ruleEngine;
        this.staleSeconds = props.control() == null ? 180 : props.control().staleSeconds();
    }

    /** 센서 한 개의 기준 범위 (주간·야간 온도 구분). 기준이 없는 지표는 null */
    record Band(Double lo, Double hi, String label) {
    }

    static Band band(String metric, CropStd std, boolean day) {
        if (std == null) {
            return new Band(null, null, null);
        }
        return switch (metric) {
            case "TEMP" -> new Band(day ? std.getDayTempMin() : std.getNightTempMin(), day ? std.getDayTempMax() : std.getNightTempMax(),
                    day ? "주간 온도" : "야간 온도");
            case "HUMI" -> new Band(std.getHumidityMin(), std.getHumidityMax(), "습도");
            // ThresholdEvaluator와 같은 여유폭 (EC ±0.3, 배지 수분 -10%p)
            case "EC" -> new Band(std.getEcMin() == null ? null : std.getEcMin() - 0.3, std.getEcMax() == null ? null : std.getEcMax() + 0.3, "양액 EC");
            case "PH" -> new Band(std.getPhMin(), std.getPhMax(), "양액 pH");
            case "SUBSTRATE" -> new Band(std.getSubstrateMoistureMin() == null ? null : std.getSubstrateMoistureMin() - 10, null, "배지 수분");
            default -> new Band(null, null, null);
        };
    }

    /** 안전 한계 규칙 조건 도달 여부. 구역 규칙은 같은 구역 센서에만, 동 전체 규칙은 모든 센서에 적용 */
    static Optional<ControlRule> safetyHit(Sensor s, double v, List<ControlRule> safety) {
        return safety.stream()
                .filter(r -> r.getMetric().equals(s.getMetric()) && r.getOnThreshold() != null)
                .filter(r -> r.getZoneId() == null || Objects.equals(r.getZoneId(), s.getZoneId()))
                .filter(r -> "GE".equals(r.getCompareOp()) ? v >= r.getOnThreshold() : v <= r.getOnThreshold())
                .findFirst();
    }

    @Operation(summary = "통합 관제 스냅샷",
            description = "센서별 판정(OK·WARN·ALARM·STALE·NODATA)과 기준 범위, 판정 요약, 최근 경보·명령·상태 변경 30건 타임라인, 현재 주간/야간·생육 단계")
    @GetMapping("/farms/{farmId}/monitor")
    public Map<String, Object> monitor(@PathVariable Integer farmId) {
        access.check(farmId);
        LocalDateTime now = LocalDateTime.now();
        CropStd std = ruleEngine.currentStd(farmId);
        boolean day = RuleEngine.isDay(std, now.toLocalTime());
        List<ControlRule> safety = rules.findByFarmIdAndIsEnabledTrueOrderByPriority(farmId).stream()
                .filter(r -> Boolean.TRUE.equals(r.getIsSafety())).toList();

        List<Map<String, Object>> out = new ArrayList<>();
        Map<String, Integer> summary = new LinkedHashMap<>();
        for (String k : List.of("OK", "WARN", "ALARM", "STALE", "NODATA")) {
            summary.put(k, 0);
        }
        for (Sensor s : sensors.findByFarmIdOrderBySensorId(farmId)) {
            if ("RETIRED".equals(s.getStatus())) {
                continue;
            }
            Optional<SensorData> last = data.findFirstBySensorIdOrderByMeasuredAtDesc(s.getSensorId());
            Band b = band(s.getMetric(), std, day);
            String level;
            String note;
            if (last.isEmpty()) {
                level = "NODATA";
                note = "측정값 없음";
            } else {
                SensorData d = last.get();
                long age = Duration.between(d.getMeasuredAt(), now).getSeconds();
                Optional<ControlRule> hit = safetyHit(s, d.getValue(), safety);
                if ("FAULT".equals(s.getStatus()) || age > staleSeconds) {
                    level = "STALE";
                    note = "수신 끊김 " + age + "초";
                } else if (hit.isPresent()) {
                    level = "ALARM";
                    note = "안전 한계 " + hit.get().getRuleCode() + " (" + ("GE".equals(hit.get().getCompareOp()) ? "≥ " : "≤ ") + hit.get().getOnThreshold() + ")";
                } else if (!"OK".equals(d.getQuality())) {
                    level = "ALARM";
                    note = "품질 이상 " + d.getQuality();
                } else if (b.hi() != null && d.getValue() > b.hi()) {
                    level = "WARN";
                    note = b.label() + " 높음 (기준 ≤ " + b.hi() + ")";
                } else if (b.lo() != null && d.getValue() < b.lo()) {
                    level = "WARN";
                    note = b.label() + " 낮음 (기준 ≥ " + b.lo() + ")";
                } else {
                    level = "OK";
                    note = b.label() == null ? "기준 없음 (참고 지표)" : "기준 안";
                }
            }
            summary.merge(level, 1, Integer::sum);
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("sensorId", s.getSensorId());
            m.put("sensorCode", s.getSensorCode());
            m.put("metric", s.getMetric());
            m.put("unit", s.getUnit());
            m.put("zoneId", s.getZoneId());
            m.put("value", last.map(SensorData::getValue).orElse(null));
            m.put("measuredAt", last.map(SensorData::getMeasuredAt).orElse(null));
            m.put("quality", last.map(SensorData::getQuality).orElse(null));
            m.put("level", level);
            m.put("note", note);
            m.put("lo", b.lo());
            m.put("hi", b.hi());
            out.add(m);
        }

        CropCycle cycle = cycles.findFirstByFarmIdAndStatusOrderByCycleIdDesc(farmId, "ACTIVE").orElse(null);
        Map<String, Object> res = new LinkedHashMap<>();
        res.put("serverTime", now);
        res.put("day", day);
        res.put("stage", cycle == null ? (std == null ? null : std.getStage()) : cycle.getCurrentStage());
        res.put("stdVersion", std == null ? null : std.getVersionNo());
        res.put("overall", summary.get("ALARM") > 0 || summary.get("STALE") > 0 ? "ALARM" : summary.get("WARN") > 0 ? "WARN" : "OK");
        res.put("summary", summary);
        res.put("sensors", out);
        res.put("events", events(farmId));
        return res;
    }

    /** 경보·제어 명령·실제 상태 변경을 시각순으로 합친 최근 30건 */
    List<Map<String, Object>> events(Integer farmId) {
        Map<Integer, Device> ds = devices.findByFarmIdOrderByDeviceId(farmId).stream().collect(Collectors.toMap(Device::getDeviceId, Function.identity()));
        PageRequest p = PageRequest.of(0, 30);
        List<Map<String, Object>> ev = new ArrayList<>();
        alerts.findByFarmIdInOrderByAlertIdDesc(List.of(farmId), p).forEach(a -> ev.add(event(a.getLastAt(), "ALERT",
                a.getSeverity(), a.getMessage(), a.getStatus(), a.getAlertType())));
        if (!ds.isEmpty()) {
            commands.findByDeviceIdInOrderByCommandIdDesc(ds.keySet(), p).forEach(c -> ev.add(event(c.getRequestedAt(), "COMMAND",
                    "TIMEOUT".equals(c.getStatus()) || "FAILED".equals(c.getStatus()) ? "WARN" : "INFO",
                    ds.get(c.getDeviceId()).getDeviceName() + " " + c.getAction() + " 명령 (" + c.getSource() + ")", c.getStatus(),
                    ds.get(c.getDeviceId()).getDeviceCode())));
            logs.findByDeviceIdInOrderByLogIdDesc(ds.keySet(), p).forEach(l -> ev.add(event(l.getChangedAt(), "STATE", "INFO",
                    ds.get(l.getDeviceId()).getDeviceName() + " " + Objects.toString(l.getPrevState(), "-") + " → " + l.getNewState(),
                    l.getChangedBy(), ds.get(l.getDeviceId()).getDeviceCode())));
        }
        ev.sort(Comparator.comparing((Map<String, Object> m) -> (LocalDateTime) m.get("at"), Comparator.nullsLast(Comparator.reverseOrder())));
        return ev.size() > 30 ? new ArrayList<>(ev.subList(0, 30)) : ev;
    }

    private static Map<String, Object> event(LocalDateTime at, String kind, String severity, String text, String status, String ref) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("at", at);
        m.put("kind", kind);
        m.put("severity", severity);
        m.put("text", text);
        m.put("status", status);
        m.put("ref", ref);
        return m;
    }
}
