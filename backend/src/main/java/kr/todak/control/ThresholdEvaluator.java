package kr.todak.control;

import kr.todak.alert.AlertService;
import kr.todak.domain.CropStd;
import kr.todak.domain.Sensor;
import kr.todak.repo.SensorRepository;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * 재배 기준값 이탈 경보 [REQ-F-09]. 기준 범위를 벗어나면 경보, 돌아오면 자동 해결.
 * 온도는 주간·야간 기준을 따로 적용한다.
 */
@Component
public class ThresholdEvaluator {
    private final SensorRepository sensors;
    private final AlertService alerts;

    public ThresholdEvaluator(SensorRepository sensors, AlertService alerts) {
        this.sensors = sensors;
        this.alerts = alerts;
    }

    public void evaluate(Integer farmId, CropStd std, boolean day, Map<Integer, Double> fresh) {
        if (std == null) {
            return;
        }
        for (Sensor s : sensors.findByFarmIdOrderBySensorId(farmId)) {
            Double v = fresh.get(s.getSensorId());
            if (v == null) {
                continue;
            }
            Double lo = null;
            Double hi = null;
            String label;
            switch (s.getMetric()) {
                case "TEMP" -> {
                    lo = day ? std.getDayTempMin() : std.getNightTempMin();
                    hi = day ? std.getDayTempMax() : std.getNightTempMax();
                    label = (day ? "주간" : "야간") + " 온도";
                }
                case "HUMI" -> {
                    lo = std.getHumidityMin();
                    hi = std.getHumidityMax();
                    label = "습도";
                }
                case "EC" -> {
                    lo = std.getEcMin() - 0.3;
                    hi = std.getEcMax() + 0.3;
                    label = "양액 EC";
                }
                case "PH" -> {
                    lo = std.getPhMin();
                    hi = std.getPhMax();
                    label = "양액 pH";
                }
                case "SUBSTRATE" -> {
                    lo = std.getSubstrateMoistureMin() == null ? null : std.getSubstrateMoistureMin() - 10;
                    label = "배지 수분";
                }
                default -> {
                    continue;
                }
            }
            String base = "THRESHOLD:" + farmId + ":" + s.getSensorCode();
            if (hi != null && v > hi) {
                alerts.raise(farmId, s.getZoneId(), "THRESHOLD", "WARN", base + ":HIGH",
                        s.getSensorCode() + " " + label + " 높음: " + v + " " + s.getUnit() + " (기준 ≤ " + hi + ")");
            } else {
                alerts.resolve(base + ":HIGH");
            }
            if (lo != null && v < lo) {
                alerts.raise(farmId, s.getZoneId(), "THRESHOLD", "WARN", base + ":LOW",
                        s.getSensorCode() + " " + label + " 낮음: " + v + " " + s.getUnit() + " (기준 ≥ " + lo + ")");
            } else {
                alerts.resolve(base + ":LOW");
            }
        }
    }
}
