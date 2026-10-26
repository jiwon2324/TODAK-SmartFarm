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
    private final GatewayRepository gateways;
    private final int staleSeconds;

    public RuleEngine(ControlRuleRepository rules, DeviceRepository devices, SensorRepository sensors, SensorDataRepository data,
                      CropStdRepository stds, CropCycleRepository cycles, ControlCommandRepository commands, CommandService commandService,
                      AlertService alerts, ThresholdEvaluator thresholds, GatewayRepository gateways, TodakProperties props) {
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
        this.gateways = gateways;
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
        boolean gwOnline = gateways.findAll().stream().anyMatch(g -> farmId.equals(g.getFarmId()) && "ONLINE".equals(g.getStatus()));
        checkAllFailed(farmId, ss, fresh, gwOnline, "TEMP", "온도", "자동 온도 제어(환기·난방)를 멈췄습니다. 현장을 확인하세요");
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
                // 안전 규칙은 동 전체 기준: 어느 구역이든 한계를 넘으면 '모든 환기 장치 강제 개방' (계획서 표 39 CR-05·06)
                List<Double> vals = safety ? farmValues(r.getMetric(), ss, fresh) : valuesFor(d, r.getMetric(), ss, fresh);
                RuleDecision.Want want;
                double v;
                if (vals.isEmpty()) {
                    // 일사 센서 이상 시 차광은 시간 스케줄로 전환 (REQ-F-03 예외). 그 밖의 규칙은 판단하지 않는다
                    if (!"SOLAR".equals(r.getMetric()) || !"SHADE".equals(d.getDeviceType()) || !gwOnline) {
                        continue;
                    }
                    alerts.raise(farmId, null, "SENSOR_FAIL", "INFO", "SOLAR_SCHEDULE:" + farmId,
                            "일사 센서 값이 없어 차광막을 시간 스케줄(4~9월 11:00~14:00 닫힘)로 운전합니다");
                    want = shadeSchedule(now) ? RuleDecision.Want.ACTIVATE : RuleDecision.Want.DEACTIVATE;
                    v = Double.NaN;
                } else {
                    if ("SOLAR".equals(r.getMetric())) {
                        alerts.resolve("SOLAR_SCHEDULE:" + farmId);
                    }
                    v = RuleDecision.representative(r.getCompareOp(), vals);
                    want = RuleDecision.decide(r.getCompareOp(), v, r.getOnThreshold(), r.getOffThreshold());
                    // CR-03처럼 조건이 정해진 시간 동안 계속돼야 하는 규칙
                    if (want != RuleDecision.Want.HOLD && r.getSustainSec() != null
                            && !sustained(d, r, ss, now, want == RuleDecision.Want.ACTIVATE)) {
                        want = RuleDecision.Want.HOLD;
                    }
                }
                if (r.getMaxRunSec() != null && active && d.getStateChangedAt() != null
                        && ChronoUnit.SECONDS.between(d.getStateChangedAt(), now) >= r.getMaxRunSec()) {
                    want = RuleDecision.Want.DEACTIVATE;
                }
                if (safety && want == RuleDecision.Want.ACTIVATE && r.getAlsoCloseType() != null) {
                    created += closeAlso(ds, r, claimed, now);
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
                if (want == RuleDecision.Want.ACTIVATE && !safety && blockedByFrequency(d, r, now)) {
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
                String why = Double.isNaN(v) ? r.getRuleCode() + " " + r.getRuleName() + ": 일사 센서 이상 → 시간 스케줄"
                        : r.getRuleCode() + " " + r.getRuleName() + ": " + r.getMetric() + "=" + round(v)
                        + (want == RuleDecision.Want.ACTIVATE ? (" " + op(r.getCompareOp()) + " " + r.getOnThreshold()) : " → 해제 " + r.getOffThreshold());
                if (issue(d, r, want == RuleDecision.Want.ACTIVATE, now, why)) {
                    created++;
                    claimed.add(d.getDeviceId());
                }
            }
            if (r.getStage2DeviceType() != null && periodOk) {
                created += stage2(farmId, r, ds, ss, fresh, claimed, now);
            }
        }
        return created;
    }

    /**
     * CR-01 2단계: 1단계 장치(측창)가 열린 지 stage2_delay_sec이 지나도 대표값이 stage2_threshold 이상이면 2단계 장치(환기팬)를 켜고,
     * 1단계 해제값 이하로 내려가면 이 규칙이 켠 2단계 장치를 끈다.
     */
    private int stage2(Integer farmId, ControlRule r, List<Device> ds, List<Sensor> ss, Map<Integer, Double> fresh, Set<Integer> claimed, LocalDateTime now) {
        Set<String> first = new HashSet<>(Arrays.asList(r.getTargetDeviceType().split(",")));
        LocalDateTime since = null;
        for (Device p : ds) {
            if (first.contains(p.getDeviceType()) && DeviceStates.isActive(p.getDeviceType(), p.getCurrentState()) && p.getStateChangedAt() != null) {
                since = since == null || p.getStateChangedAt().isBefore(since) ? p.getStateChangedAt() : since;
            }
        }
        int n = 0;
        for (Device d : ds) {
            if (!r.getStage2DeviceType().equals(d.getDeviceType()) || claimed.contains(d.getDeviceId()) || manualHold(d, now)
                    || commands.existsByDeviceIdAndStatusIn(d.getDeviceId(), CommandService.PENDING)) {
                continue;
            }
            List<Double> vals = valuesFor(d, r.getMetric(), ss, fresh);
            if (vals.isEmpty()) {
                continue;
            }
            double v = RuleDecision.representative(r.getCompareOp(), vals);
            boolean active = DeviceStates.isActive(d.getDeviceType(), d.getCurrentState());
            boolean minRunOk = d.getStateChangedAt() == null || ChronoUnit.SECONDS.between(d.getStateChangedAt(), now) >= r.getMinRunSec();
            if (!active && since != null && ChronoUnit.SECONDS.between(since, now) >= r.getStage2DelaySec() && v >= r.getStage2Threshold() && minRunOk) {
                if (issue(d, r, true, now, r.getRuleCode() + " 2단계: 측창 개방 " + r.getStage2DelaySec() / 60 + "분 후에도 " + round(v) + " ≥ " + r.getStage2Threshold())) {
                    n++;
                    claimed.add(d.getDeviceId());
                }
            } else if (active && v <= r.getOffThreshold() && lastAutoRule(d) == r.getRuleId() && minRunOk) {
                if (issue(d, r, false, now, r.getRuleCode() + " 2단계 해제: " + round(v) + " ≤ " + r.getOffThreshold())) {
                    n++;
                    claimed.add(d.getDeviceId());
                }
            }
        }
        return n;
    }

    /** CR-06 저온 안전: 난방과 함께 열린 측창을 닫는다 */
    private int closeAlso(List<Device> ds, ControlRule r, Set<Integer> claimed, LocalDateTime now) {
        int n = 0;
        for (Device d : ds) {
            if (!r.getAlsoCloseType().equals(d.getDeviceType()) || claimed.contains(d.getDeviceId())) {
                continue;
            }
            claimed.add(d.getDeviceId());
            if (DeviceStates.isActive(d.getDeviceType(), d.getCurrentState())
                    && !commands.existsByDeviceIdAndStatusIn(d.getDeviceId(), CommandService.PENDING)
                    && issue(d, r, false, now, r.getRuleCode() + " " + r.getRuleName() + ": 저온 안전 — 측창 닫기")) {
                n++;
            }
        }
        return n;
    }

    /** CR-03 시간당 최대 횟수, CR-04 작동 간격 */
    private boolean blockedByFrequency(Device d, ControlRule r, LocalDateTime now) {
        if (r.getMaxPerHour() != null
                && commands.countByDeviceIdAndSourceAndRequestedAtAfter(d.getDeviceId(), "AUTO", now.minusHours(1)) >= r.getMaxPerHour() * 2L) {
            return true; // 켜고 끄는 명령을 합쳐 셈: 1회 작동 = 2건
        }
        if (r.getMinIntervalSec() != null) {
            return commands.findFirstByDeviceIdAndSourceAndActionOrderByCommandIdDesc(d.getDeviceId(), "AUTO", DeviceStates.active(d.getDeviceType()))
                    .map(c -> ChronoUnit.SECONDS.between(c.getRequestedAt(), now) < r.getMinIntervalSec()).orElse(false);
        }
        return false;
    }

    /** 최근 sustain_sec 동안 유효 측정값이 모두 조건을 만족했는지 (구간의 80% 이상 측정이 있어야 인정) */
    private boolean sustained(Device d, ControlRule r, List<Sensor> ss, LocalDateTime now, boolean activate) {
        LocalDateTime from = now.minusSeconds(r.getSustainSec());
        int need = (int) Math.ceil(r.getSustainSec() / 60.0 * 0.8);
        boolean zoneHas = ss.stream().anyMatch(s -> r.getMetric().equals(s.getMetric()) && d.getZoneId() != null && d.getZoneId().equals(s.getZoneId()));
        for (Sensor s : ss) {
            if (!r.getMetric().equals(s.getMetric()) || (zoneHas && !d.getZoneId().equals(s.getZoneId())) || !"ACTIVE".equals(s.getStatus())) {
                continue;
            }
            List<kr.todak.domain.SensorData> pts = data.findBySensorIdAndMeasuredAtBetweenOrderByMeasuredAt(s.getSensorId(), from, now).stream()
                    .filter(x -> "OK".equals(x.getQuality())).toList();
            if (pts.size() < need) {
                return false;
            }
            for (var x : pts) {
                boolean meets = activate
                        ? ("GE".equals(r.getCompareOp()) ? x.getValue() >= r.getOnThreshold() : x.getValue() <= r.getOnThreshold())
                        : ("GE".equals(r.getCompareOp()) ? x.getValue() <= r.getOffThreshold() : x.getValue() >= r.getOffThreshold());
                if (!meets) {
                    return false;
                }
            }
        }
        return true;
    }

    static boolean shadeSchedule(LocalDateTime now) {
        int m = now.getMonthValue(), h = now.getHour();
        return m >= 4 && m <= 9 && h >= 11 && h < 14;
    }

    /** 같은 지표 센서가 모두 값이 없으면(게이트웨이는 연결) 자동 제어 중지 경보 (REQ-F-02 예외) */
    private void checkAllFailed(Integer farmId, List<Sensor> ss, Map<Integer, Double> fresh, boolean gwOnline, String metric, String label, String msg) {
        List<Sensor> m = ss.stream().filter(s -> metric.equals(s.getMetric()) && !"RETIRED".equals(s.getStatus())).toList();
        String key = "ALL_FAIL:" + farmId + ":" + metric;
        if (m.isEmpty()) {
            return;
        }
        if (gwOnline && m.stream().noneMatch(s -> fresh.containsKey(s.getSensorId()))) {
            alerts.raise(farmId, null, "SENSOR_FAIL", "CRITICAL", key, label + " 센서 " + m.size() + "개 모두 이상 — " + msg);
        } else {
            alerts.resolve(key);
        }
    }

    private boolean issue(Device d, ControlRule r, boolean activate, LocalDateTime now, String reason) {
        String action = activate ? DeviceStates.active(d.getDeviceType()) : DeviceStates.inactive(d.getDeviceType());
        String source = Boolean.TRUE.equals(r.getIsSafety()) ? "SAFETY" : "AUTO";
        String key = source + "-" + r.getRuleCode() + "-" + d.getDeviceId() + "-" + action + "-" + now.truncatedTo(ChronoUnit.MINUTES);
        var c = commandService.create(d, action, source, r.getRuleId(), null, key, reason, r.getMaxRunSec());
        if (c != null && Boolean.TRUE.equals(r.getIsSafety())) {
            // CR-05·06: 안전 한계 작동은 경보와 함께 (계획서 표 39 '강제 개방 + 경보'), 해제되면 경보도 해결
            String k = "SAFETY:" + d.getFarmId() + ":" + r.getRuleCode();
            if (activate) {
                alerts.raise(d.getFarmId(), null, "THRESHOLD", "CRITICAL", k, r.getRuleCode() + " " + r.getRuleName() + " 작동 — " + reason);
            } else {
                alerts.resolve(k);
            }
        }
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
     * 구역이 있는 장치는 같은 구역 센서를 쓴다. 그 구역 센서가 이상(값 없음)이면 같은 지표의 다른 구역 센서로 임시 대체하고,
     * 모두 이상이면 빈 목록 → 해당 자동 제어 중지 (계획서 13장 '센서 고장 대응', 표 33).
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
        return zoneHasSensor && !zone.isEmpty() ? zone : all;
    }

    private List<Double> farmValues(String metric, List<Sensor> ss, Map<Integer, Double> fresh) {
        List<Double> all = new ArrayList<>();
        for (Sensor s : ss) {
            if (metric.equals(s.getMetric()) && fresh.containsKey(s.getSensorId())) {
                all.add(fresh.get(s.getSensorId()));
            }
        }
        return all;
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
