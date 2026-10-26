package kr.todak.web;

import kr.todak.analytics.AnalyticsService;
import kr.todak.domain.CropCycle;
import java.time.LocalDate;
import java.util.Comparator;
import java.util.Objects;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import kr.todak.common.FarmAccess;
import kr.todak.domain.*;
import kr.todak.repo.*;
import kr.todak.stream.SseHub;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.time.LocalDateTime;
import java.util.*;

@Tag(name = "농장·대시보드", description = "[REQ-F-13, REQ-F-18] [TB_FARM, TB_ZONE, TB_SENSOR_DATA, TB_DEVICE, TB_ALERT]")
@RestController
@RequestMapping("/api")
public class FarmController {
    private final FarmAccess access;
    private final FarmRepository farms;
    private final ZoneRepository zones;
    private final SensorRepository sensors;
    private final SensorDataRepository data;
    private final DeviceRepository devices;
    private final AlertRepository alerts;
    private final GatewayRepository gateways;
    private final CropCycleRepository cycles;
    private final SseHub sse;
    private final kr.todak.analytics.AnalyticsService analytics;

    public FarmController(FarmAccess access, FarmRepository farms, ZoneRepository zones, SensorRepository sensors, SensorDataRepository data,
                          DeviceRepository devices, AlertRepository alerts, GatewayRepository gateways, CropCycleRepository cycles, SseHub sse,
                          kr.todak.analytics.AnalyticsService analytics) {
        this.access = access;
        this.farms = farms;
        this.zones = zones;
        this.sensors = sensors;
        this.data = data;
        this.devices = devices;
        this.alerts = alerts;
        this.gateways = gateways;
        this.cycles = cycles;
        this.sse = sse;
        this.analytics = analytics;
    }

    @Operation(summary = "내 농장 목록", description = "관리자는 전체, 농가는 TB_USER_FARM에 등록된 농장만")
    @GetMapping("/farms")
    public List<Farm> myFarms() {
        return farms.findAllById(access.allowedFarmIds());
    }

    @Operation(summary = "농장 구역 목록")
    @GetMapping("/farms/{farmId}/zones")
    public List<Zone> zones(@PathVariable Integer farmId) {
        access.check(farmId);
        return zones.findByFarmIdOrderByZoneCode(farmId);
    }

    @Operation(summary = "농가 메인 대시보드", description = "센서별 최신값·최종 수집 시각·품질, 장치 상태, 게이트웨이 상태, 미해결 경보 수, 작기 정보. 모든 센서값은 출처(simulated)를 함께 표시")
    @GetMapping("/farms/{farmId}/dashboard")
    public Map<String, Object> dashboard(@PathVariable Integer farmId) {
        access.check(farmId);
        List<Map<String, Object>> readings = new ArrayList<>();
        for (Sensor s : sensors.findByFarmIdOrderBySensorId(farmId)) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("sensorId", s.getSensorId());
            m.put("sensorCode", s.getSensorCode());
            m.put("metric", s.getMetric());
            m.put("unit", s.getUnit());
            m.put("zoneId", s.getZoneId());
            m.put("status", s.getStatus());
            m.put("simulated", s.getIsSimulated());
            data.findFirstBySensorIdOrderByMeasuredAtDesc(s.getSensorId()).ifPresent(d -> {
                m.put("value", d.getValue());
                m.put("measuredAt", d.getMeasuredAt());
                m.put("quality", d.getQuality());
            });
            m.put("lastReceivedAt", s.getLastReceivedAt());
            readings.add(m);
        }
        List<Map<String, Object>> ds = devices.findByFarmIdOrderByDeviceId(farmId).stream().map(FarmController::deviceView).toList();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("farm", farms.findById(farmId).orElseThrow());
        out.put("zones", zones.findByFarmIdOrderByZoneCode(farmId));
        out.put("readings", readings);
        out.put("devices", ds);
        out.put("gateways", gateways.findByFarmId(farmId));
        out.put("openAlerts", alerts.countByFarmIdInAndStatusNot(List.of(farmId), "RESOLVED"));
        CropCycle cycle = cycles.findFirstByFarmIdAndStatusOrderByCycleIdDesc(farmId, "ACTIVE").orElse(null);
        out.put("cropCycle", cycle);
        // API-06: 오늘 DLI 추정치(진행 중)와 정식 후 내부 누적 GDD
        LocalDate today = LocalDate.now();
        out.put("dliToday", analytics.daily(farmId, today, today).stream().findFirst().map(x -> x.get("dliEstimate")).orElse(null));
        out.put("cumGddInternal", cycle == null ? null : analytics.gdd(cycle, "INTERNAL", today, today).stream()
                .reduce((a, b) -> b).map(AnalyticsService.GddRow::cumGdd).orElse(null));
        out.put("lastReceivedAt", readings.stream().map(r -> (LocalDateTime) r.get("lastReceivedAt")).filter(Objects::nonNull)
                .max(Comparator.naturalOrder()).orElse(null));
        out.put("serverTime", LocalDateTime.now());
        return out;
    }

    @Operation(summary = "실시간 이벤트 구독 (SSE)", description = "이벤트: reading, device, command, alert. EventSource는 헤더를 못 보내므로 ?access_token= 사용")
    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream(@RequestParam Integer farmId) {
        access.check(farmId);
        return sse.subscribe(farmId);
    }

    static Map<String, Object> deviceView(Device d) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("deviceId", d.getDeviceId());
        m.put("deviceCode", d.getDeviceCode());
        m.put("deviceType", d.getDeviceType());
        m.put("deviceName", d.getDeviceName());
        m.put("zoneId", d.getZoneId());
        m.put("mode", d.getMode());
        m.put("manualUntil", d.getManualUntil());
        m.put("state", d.getCurrentState());
        m.put("stateChangedAt", d.getStateChangedAt());
        m.put("simulated", d.getIsSimulated());
        return m;
    }
}
