package kr.todak.ingest;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import kr.todak.alert.AlertService;
import kr.todak.common.ErrorLog;
import kr.todak.domain.Sensor;
import kr.todak.domain.SensorData;
import kr.todak.repo.SensorDataRepository;
import kr.todak.repo.SensorRepository;
import kr.todak.stream.SseHub;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 센서 측정값 수신 → 형식 검증 → 중복 제거 → 범위·급변 검사 → 품질 플래그 → 저장 → SSE. [REQ-F-01, REQ-F-18]
 * 범위를 벗어난 값도 저장하되 quality로 표시하고, 제어 판단에는 quality=OK만 쓴다.
 */
@Service
public class SensorIngestService {
    private static final ZoneId SEOUL = ZoneId.of("Asia/Seoul");
    private final ObjectMapper om = new ObjectMapper();
    private final SensorRepository sensors;
    private final SensorDataRepository data;
    private final AlertService alerts;
    private final SseHub sse;
    private final ErrorLog errorLog;
    private final AtomicLong received = new AtomicLong();
    private final AtomicLong saved = new AtomicLong();
    private final AtomicLong duplicates = new AtomicLong();
    private final AtomicLong rejected = new AtomicLong();

    public SensorIngestService(SensorRepository sensors, SensorDataRepository data, AlertService alerts, SseHub sse, ErrorLog errorLog) {
        this.sensors = sensors;
        this.data = data;
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
        Sensor s = sensors.findByFarmIdAndSensorCode(farmId, sensorCode).orElse(null);
        if (s == null) {
            return reject("등록되지 않은 센서 farm=" + farmId + " " + sensorCode);
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
        if (data.existsByMsgId(msgId) || data.existsBySensorIdAndMeasuredAt(s.getSensorId(), measuredAt)) {
            duplicates.incrementAndGet();
            return Result.DUPLICATE;
        }
        double v = j.get("value").asDouble();
        String quality = quality(s, v, measuredAt);
        SensorData d = new SensorData();
        d.setSensorId(s.getSensorId());
        d.setMeasuredAt(measuredAt);
        d.setValue(v);
        d.setValueMin(j.hasNonNull("min") ? j.get("min").asDouble() : null);
        d.setValueMax(j.hasNonNull("max") ? j.get("max").asDouble() : null);
        d.setSampleCount(j.hasNonNull("samples") ? (short) j.get("samples").asInt() : null);
        d.setQuality(quality);
        d.setMsgId(msgId);
        d.setIsBuffered(j.path("buffered").asBoolean(false));
        d.setReceivedAt(LocalDateTime.now());
        try {
            data.save(d);
        } catch (DataIntegrityViolationException e) {
            duplicates.incrementAndGet();
            return Result.DUPLICATE;
        }
        saved.incrementAndGet();
        s.setLastReceivedAt(LocalDateTime.now());
        if ("FAULT".equals(s.getStatus()) && "OK".equals(quality)) {
            s.setStatus("ACTIVE");
            alerts.resolve("SENSOR_FAIL:" + farmId + ":" + s.getSensorCode());
        }
        sensors.save(s);
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
        ev.put("buffered", d.getIsBuffered());
        sse.publish(farmId, "reading", ev);
        return Result.SAVED;
    }

    /** 범위(valid_min~max) 밖이면 OUT_RANGE, 직전 2분 이내 값과 차이가 spike_limit 초과면 SPIKE */
    String quality(Sensor s, double v, LocalDateTime t) {
        if (v < s.getValidMin() || v > s.getValidMax()) {
            return "OUT_RANGE";
        }
        if (s.getSpikeLimit() != null) {
            var prev = data.findFirstBySensorIdOrderByMeasuredAtDesc(s.getSensorId()).orElse(null);
            if (prev != null && "OK".equals(prev.getQuality()) && !prev.getMeasuredAt().isAfter(t)
                    && ChronoUnit.MINUTES.between(prev.getMeasuredAt(), t) <= 2
                    && Math.abs(v - prev.getValue()) > s.getSpikeLimit()) {
                return "SPIKE";
            }
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
