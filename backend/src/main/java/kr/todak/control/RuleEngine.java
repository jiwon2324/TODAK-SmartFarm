package kr.todak.control;

import kr.todak.alert.AlertService;
import kr.todak.config.TodakProperties;
import kr.todak.domain.*;
import kr.todak.repo.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.temporal.ChronoUnit;
import java.util.*;

/**
 * 자동 제어 규칙 엔진 (서버 판단). 개발 계획서 14장 액티비티와 같은 순서로 평가한다. [REQ-F-02~04, REQ-F-08]
 * 1) 유효 센서값(quality OK, stale_seconds 이내)으로 대표값 계산 — 없으면 건너뜀(무응답 경보는 SensorHealthJob)
 * 2) 우선순위 순서로 규칙 평가, 안전 규칙(is_safety)이 잡은 장치는 하위 규칙이 건드리지 않음
 * 3) 수동 모드(manual_until 이전)는 안전 규칙만 개입
 * 4) 히스테리시스(on/off 임계값) + 최소 작동시간 + 대기 중 명령 중복 방지 + 관수 1회·일 상한
 */
@Service
public class RuleEngine {
    private static final Logger log = LoggerFactory.getLogger(RuleEngine.class);
    private final ControlRuleRepository rules;
    private final DeviceRepository devices;
    private final SensorRepository sensors;
    private final SensorDataRepository data;
    private final CropStdRepository stds;
    private final CropCycleRepository cycles;
    private final ControlCommandRepository commands;
    private final CommandService commandService;
    private final AlertService alerts;
    private final ThresholdEvaluator thresholds;
    private final int staleSeconds;

    public RuleEngine(ControlRuleRepository rules, DeviceRepository devices, SensorRepository sensors, SensorDataRepository data,
                      CropStdRepository stds, CropCycleRepository cycles, ControlCommandRepository commands, CommandService commandService,
                      AlertService alerts, ThresholdEvaluator thresholds, TodakProperties props) {
        this.rules = rules;
        this.devices = devices;
        this.sensors = sensors;
        this.data = data;
        this.stds = stds;
        this.cycles = cycles;
        this.commands = commands;
        this.commandService = commandService;
        this.alerts = alerts;
        this.thresholds = thresholds;
        this.staleSeconds = props.control().staleSeconds();
    }

    @Scheduled(fixedDelayString = "${todak.control.rule-interval-ms}", initialDelay = 20000)
    public void tick() {
        Set<Integer> farmIds = new TreeSet<>();
        devices.findAll().forEach(d -> farmIds.add(d.getFarmId()));
        for (Integer farmId : farmIds) {
            try {
                evaluateFarm(farmId, LocalDateTime.now());
            } catch (Exception e) {
                log.warn("규칙 평가 실패 farm={}", farmId, e);
            }
        }
    }

    /** 농장 하나의 규칙을 평가하고 만든 명령 수를 돌려준다 (테스트에서 직접 호출) */
    public int evaluateFarm(Integer farmId, LocalDateTime now) {
        Map<Integer, Double> fresh = freshValues(farmId, now);
        CropStd std = currentStd(farmId);
        boolean day = isDay(std, now.toLocalTime());
        thresholds.evaluate(farmId, std, day, fresh);

        List<Device> ds = devices.findByFarmIdOrderByDeviceId(farmId);
        List<Sensor> ss = sensors.findByFarmIdOrderBySensorId(farmId);
        Set<Integer> claimed = new HashSet<>();
        int created = 0;
        for (ControlRule r : rules.findByFarmIdAndIsEnabledTrueOrderByPriority(farmId)) {
            boolean safety = Boolean.TRUE.equals(r.getIsSafety());
            boolean periodOk = "ALL".equals(r.getPeriod()) || ("DAY".equals(r.getPeriod()) == day);
            Set<String> types = new HashSet<>(Arrays.asList(r.getTargetDeviceType().split(",")));
            for (Device d : ds) {
                if (!types.contains(d.getDeviceType()) || claimed.contains(d.getDeviceId())) {
                    continue;
                }
                boolean active = DeviceStates.isActive(d.getDeviceType(), d.getCurrentState());
                if (!periodOk) {
                    // 시간대가 끝난 규칙이 켜 둔 장치는 끈다 (예: 야간 난방 → 주간)
                    if (active && lastAutoRule(d) == r.getRuleId().intValue()) {
                        created += issue(d, r, false, now, "시간대 종료 (" + r.getPeriod() + ")") ? 1 : 0;
                        claimed.add(d.getDeviceId());
                    }
                    continue;
                }
                List<Double> vals = valuesFor(d, r.getMetric(), ss, fresh);
                if (vals.isEmpty()) {
                    continue;
                }
                double v = RuleDecision.representative(r.getCompareOp(), vals);
                RuleDecision.Want want = RuleDecision.decide(r.getCompareOp(), v, r.getOnThreshold(), r.getOffThreshold());
                if (r.getMaxRunSec() != null && active && d.getStateChangedAt() != null
                        && ChronoUnit.SECONDS.between(d.getStateChangedAt(), now) >= r.getMaxRunSec()) {
                    want = RuleDecision.Want.DEACTIVATE;
                }
                if (safety && want == RuleDecision.Want.ACTIVATE && active) {
                    claimed.add(d.getDeviceId());
                    continue;
                }
                if (want == RuleDecision.Want.HOLD || (want == RuleDecision.Want.ACTIVATE) == active) {
                    continue;
                }
                if (want == RuleDecision.Want.DEACTIVATE && safety) {
                    // 안전 규칙은 자기가 켠 장치만 해제하고, 일반 규칙이 맡는 장치면 해제하지 않고 넘겨준다
                    if (lastAutoRule(d) != r.getRuleId() || coveredByNormalRule(d, farmId, day)) {
                        continue;
                    }
                }
                if (!safety && manualHold(d, now)) {
                    continue;
                }
                if (!safety && d.getStateChangedAt() != null && ChronoUnit.SECONDS.between(d.getStateChangedAt(), now) < r.getMinRunSec()) {
                    continue;
                }
                if (commands.existsByDeviceIdAndStatusIn(d.getDeviceId(), CommandService.PENDING)) {
                    continue;
                }
                if (want == RuleDecision.Want.ACTIVATE && r.getMaxDailyCount() != null) {
                    long today = commands.countByDeviceIdAndSourceAndActionAndRequestedAtAfter(d.getDeviceId(), "AUTO",
                            DeviceStates.active(d.getDeviceType()), LocalDate.now().atStartOfDay());
                    if (today >= r.getMaxDailyCount()) {
                        alerts.raise(farmId, d.getZoneId(), "THRESHOLD", "WARN", "IRRIGATION_LIMIT:" + farmId + ":" + d.getDeviceCode(),
                                d.getDeviceName() + " 일 최대 관수 " + r.getMaxDailyCount() + "회 도달 — 자동 관수 중지");
                        continue;
                    }
                }
                String why = r.getRuleCode() + " " + r.getRuleName() + ": " + r.getMetric() + "=" + round(v)
                        + (want == RuleDecision.Want.ACTIVATE ? (" " + op(r.getCompareOp()) + " " + r.getOnThreshold()) : " → 해제 " + r.getOffThreshold());
                if (issue(d, r, want == RuleDecision.Want.ACTIVATE, now, why)) {
                    created++;
                    claimed.add(d.getDeviceId());
                }
            }
        }
        return created;
    }

    private boolean issue(Device d, ControlRule r, boolean activate, LocalDateTime now, String reason) {
        String action = activate ? DeviceStates.active(d.getDeviceType()) : DeviceStates.inactive(d.getDeviceType());
        String source = Boolean.TRUE.equals(r.getIsSafety()) ? "SAFETY" : "AUTO";
        String key = source + "-" + r.getRuleCode() + "-" + d.getDeviceId() + "-" + action + "-" + now.truncatedTo(ChronoUnit.MINUTES);
        var c = commandService.create(d, action, source, r.getRuleId(), null, key, reason, r.getMaxRunSec());
        return c != null;
    }

    private boolean manualHold(Device d, LocalDateTime now) {
        if (!"MANUAL".equals(d.getMode())) {
            return false;
        }
        if (d.getManualUntil() != null && d.getManualUntil().isBefore(now)) {
            d.setMode("AUTO");
            d.setManualUntil(null);
            devices.save(d);
            return false;
        }
        return true;
    }

    private int lastAutoRule(Device d) {
        return commands.findFirstByDeviceIdAndStatusOrderByCommandIdDesc(d.getDeviceId(), "ACKED")
                .filter(c -> c.getRuleId() != null).map(ControlCommand::getRuleId).orElse(-1);
    }

    /**
     * 구역이 있는 장치는 같은 구역 센서만 쓴다(다른 구역 값으로 관수·난방하지 않도록). 그 구역에 그 지표 센서가 아예 없으면 농장 전체 센서.
     * 구역이 없는 장치(측창·차광막 등 동 전체)는 농장 전체 센서.
     */
    private List<Double> valuesFor(Device d, String metric, List<Sensor> ss, Map<Integer, Double> fresh) {
        List<Double> zone = new ArrayList<>();
        List<Double> all = new ArrayList<>();
        boolean zoneHasSensor = false;
        for (Sensor s : ss) {
            if (!metric.equals(s.getMetric())) {
                continue;
            }
            boolean inZone = d.getZoneId() != null && d.getZoneId().equals(s.getZoneId());
            zoneHasSensor |= inZone;
            if (!fresh.containsKey(s.getSensorId())) {
                continue;
            }
            all.add(fresh.get(s.getSensorId()));
            if (inZone) {
                zone.add(fresh.get(s.getSensorId()));
            }
        }
        return zoneHasSensor ? zone : all;
    }

    private boolean coveredByNormalRule(Device d, Integer farmId, boolean day) {
        for (ControlRule x : rules.findByFarmIdAndIsEnabledTrueOrderByPriority(farmId)) {
            boolean periodOk = "ALL".equals(x.getPeriod()) || ("DAY".equals(x.getPeriod()) == day);
            if (!Boolean.TRUE.equals(x.getIsSafety()) && periodOk && Arrays.asList(x.getTargetDeviceType().split(",")).contains(d.getDeviceType())) {
                return true;
            }
        }
        return false;
    }

    Map<Integer, Double> freshValues(Integer farmId, LocalDateTime now) {
        Map<Integer, Double> m = new HashMap<>();
        LocalDateTime limit = now.minusSeconds(staleSeconds);
        for (Sensor s : sensors.findByFarmIdOrderBySensorId(farmId)) {
            data.findFirstBySensorIdOrderByMeasuredAtDesc(s.getSensorId())
                    .filter(x -> "OK".equals(x.getQuality()) && !x.getMeasuredAt().isBefore(limit))
                    .ifPresent(x -> m.put(s.getSensorId(), x.getValue()));
        }
        return m;
    }

    CropStd currentStd(Integer farmId) {
        CropCycle c = cycles.findFirstByFarmIdAndStatusOrderByCycleIdDesc(farmId, "ACTIVE").orElse(null);
        String stage = c == null ? "GROWTH" : c.getCurrentStage();
        return stds.findFirstByFarmIdAndStageAndIsCurrentTrue(farmId, stage)
                .or(() -> stds.findFirstByFarmIdAndStageAndIsCurrentTrue(farmId, "GROWTH")).orElse(null);
    }

    static boolean isDay(CropStd std, LocalTime t) {
        LocalTime ds = std == null ? LocalTime.of(7, 0) : std.getDayStartTime();
        LocalTime ns = std == null ? LocalTime.of(19, 0) : std.getNightStartTime();
        return !t.isBefore(ds) && t.isBefore(ns);
    }

    private static String op(String o) {
        return "GE".equals(o) ? "≥" : "≤";
    }

    private static double round(double v) {
        return Math.round(v * 10) / 10.0;
    }
}
