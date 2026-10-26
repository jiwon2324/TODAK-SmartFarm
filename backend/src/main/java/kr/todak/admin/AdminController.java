package kr.todak.admin;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import kr.todak.analytics.WeatherImportService;
import kr.todak.auth.AuthService;
import kr.todak.common.ApiException;
import kr.todak.common.ErrorLog;
import kr.todak.common.FarmAccess;
import kr.todak.control.CommandService;
import kr.todak.control.GatewayService;
import kr.todak.domain.*;
import kr.todak.ingest.SensorIngestService;
import kr.todak.mqtt.MqttGateway;
import kr.todak.repo.*;
import kr.todak.stream.SseHub;
import org.springframework.data.domain.PageRequest;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

/** 관리자 전용 API. URL(/api/admin/**)과 @PreAuthorize 두 곳에서 ADMIN을 검사한다. */
@Tag(name = "관리자", description = "시스템 현황·사용자·권한·센서·장치·규칙·로그·기상 자료 [REQ-F-12, REQ-F-13, REQ-F-15, REQ-F-17]")
@RestController
@RequestMapping("/api/admin")
@PreAuthorize("hasRole('ADMIN')")
public class AdminController {
    private static final Set<String> SCENARIOS = Set.of("normal", "heat", "cold", "humid", "dry", "sensor_silent", "disconnect", "device_fail", "recover");
    private final ObjectMapper om = new ObjectMapper();
    private final FarmAccess access;
    private final UserRepository users;
    private final UserFarmRepository userFarms;
    private final FarmRepository farms;
    private final SensorRepository sensors;
    private final SensorDataRepository data;
    private final DeviceRepository devices;
    private final GatewayRepository gateways;
    private final ControlRuleRepository rules;
    private final ControlCommandRepository commands;
    private final AlertRepository alerts;
    private final AlertDeliveryRepository deliveries;
    private final SettingHistoryRepository history;
    private final WeatherDailyRepository weather;
    private final PasswordEncoder encoder;
    private final AuthService auth;
    private final SensorIngestService ingest;
    private final GatewayService gatewayService;
    private final WeatherImportService weatherImport;
    private final MqttGateway mqtt;
    private final ErrorLog errorLog;
    private final SseHub sse;

    public AdminController(FarmAccess access, UserRepository users, UserFarmRepository userFarms, FarmRepository farms, SensorRepository sensors,
                           SensorDataRepository data, DeviceRepository devices, GatewayRepository gateways, ControlRuleRepository rules,
                           ControlCommandRepository commands, AlertRepository alerts, AlertDeliveryRepository deliveries, SettingHistoryRepository history,
                           WeatherDailyRepository weather, PasswordEncoder encoder, AuthService auth, SensorIngestService ingest,
                           GatewayService gatewayService, WeatherImportService weatherImport, MqttGateway mqtt, ErrorLog errorLog, SseHub sse) {
        this.access = access;
        this.users = users;
        this.userFarms = userFarms;
        this.farms = farms;
        this.sensors = sensors;
        this.data = data;
        this.devices = devices;
        this.gateways = gateways;
        this.rules = rules;
        this.commands = commands;
        this.alerts = alerts;
        this.deliveries = deliveries;
        this.history = history;
        this.weather = weather;
        this.encoder = encoder;
        this.auth = auth;
        this.ingest = ingest;
        this.gatewayService = gatewayService;
        this.weatherImport = weatherImport;
        this.mqtt = mqtt;
        this.errorLog = errorLog;
        this.sse = sse;
    }

    // ---------------- 현황 ----------------
    @Operation(summary = "관리자 대시보드 요약", description = "농장·센서(정상/오류)·장치·게이트웨이·최근 수집·미해결 경보·24시간 명령 결과")
    @GetMapping("/summary")
    public Map<String, Object> summary() {
        LocalDateTime now = LocalDateTime.now();
        List<Sensor> ss = sensors.findAll();
        List<Device> ds = devices.findAll();
        Map<String, Long> deviceStates = new TreeMap<>();
        ds.forEach(d -> deviceStates.merge(d.getCurrentState(), 1L, Long::sum));
        Map<String, Long> cmd24 = new LinkedHashMap<>();
        for (String s : List.of("ACKED", "FAILED", "TIMEOUT", "SENT", "REQUESTED")) {
            cmd24.put(s, commands.countByRequestedAtAfterAndStatus(now.minusHours(24), s));
        }
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("farms", farms.count());
        m.put("users", users.count());
        m.put("sensors", Map.of("total", ss.size(), "active", ss.stream().filter(s -> "ACTIVE".equals(s.getStatus())).count(),
                "fault", ss.stream().filter(s -> "FAULT".equals(s.getStatus())).count()));
        m.put("devices", Map.of("total", ds.size(), "byState", deviceStates,
                "manual", ds.stream().filter(d -> "MANUAL".equals(d.getMode())).count()));
        m.put("gateways", gateways.findAll());
        m.put("lastReceivedAt", data.lastReceivedAt());
        m.put("receivedLastHour", data.countByReceivedAtAfter(now.minusHours(1)));
        m.put("ingestCounters", ingest.stats());
        m.put("openAlerts", alerts.countByFarmIdInAndStatusNot(farms.findAll().stream().map(Farm::getFarmId).toList(), "RESOLVED"));
        m.put("commands24h", cmd24);
        m.put("mqttConnected", mqtt.isConnected());
        m.put("sseSubscribers", sse.subscriberCount());
        m.put("serverTime", now);
        return m;
    }

    @Operation(summary = "전체 농장")
    @GetMapping("/farms")
    public List<Farm> farms() {
        return farms.findAll();
    }

    // ---------------- 사용자 ----------------
    @Operation(summary = "사용자 목록 (농장 권한 포함)")
    @GetMapping("/users")
    public List<Map<String, Object>> users() {
        return users.findAll().stream().map(this::userView).toList();
    }

    public record UserCreate(@NotBlank @Size(min = 4, max = 30) @Pattern(regexp = "[a-zA-Z0-9_]+") String loginId,
                             @NotBlank @Size(min = 8, max = 64) String password, @NotBlank @Size(max = 30) String name,
                             @Size(max = 20) String phone, @Pattern(regexp = "ADMIN|FARMER") String role, List<Integer> farmIds) {
    }

    @Operation(summary = "사용자 등록", description = "비밀번호는 BCrypt 해시로 저장. 409 DUPLICATE_LOGIN")
    @PostMapping("/users")
    @Transactional
    public Map<String, Object> createUser(@Valid @RequestBody UserCreate r) {
        if (users.findByLoginId(r.loginId()).isPresent()) {
            throw new ApiException(HttpStatus.CONFLICT, "DUPLICATE_LOGIN", "이미 있는 아이디입니다");
        }
        User u = new User();
        u.setLoginId(r.loginId());
        u.setPasswordHash(encoder.encode(r.password()));
        u.setName(r.name());
        u.setPhone(r.phone());
        u.setRole(r.role() == null ? "FARMER" : r.role());
        u = users.save(u);
        setFarms(u.getUserId(), r.farmIds() == null ? List.of() : r.farmIds());
        return userView(u);
    }

    public record UserUpdate(@Size(max = 30) String name, @Size(max = 20) String phone, @Pattern(regexp = "ADMIN|FARMER") String role,
                             Boolean isActive, @Size(min = 8, max = 64) String newPassword) {
    }

    @Operation(summary = "사용자 수정·활성/비활성·비밀번호 초기화", description = "비활성화·비밀번호 변경 시 해당 사용자의 Refresh Token 전부 폐기. 자기 자신은 비활성화 불가")
    @PatchMapping("/users/{userId}")
    @Transactional
    public Map<String, Object> updateUser(@PathVariable Integer userId, @Valid @RequestBody UserUpdate r) {
        User u = users.findById(userId).orElseThrow(() -> ApiException.notFound("사용자"));
        if (r.name() != null) {
            u.setName(r.name());
        }
        if (r.phone() != null) {
            u.setPhone(r.phone());
        }
        if (r.role() != null) {
            u.setRole(r.role());
        }
        if (r.isActive() != null) {
            if (!r.isActive() && userId.equals(access.user().userId())) {
                throw ApiException.badRequest("자기 계정은 비활성화할 수 없습니다");
            }
            u.setIsActive(r.isActive());
            if (!r.isActive()) {
                auth.revokeAll(userId);
            }
        }
        if (r.newPassword() != null) {
            u.setPasswordHash(encoder.encode(r.newPassword()));
            u.setLockedUntil(null);
            u.setFailedCount((byte) 0);
            auth.revokeAll(userId);
        }
        return userView(users.save(u));
    }

    @Operation(summary = "사용자별 농장 접근 권한 설정", description = "목록 전체를 교체한다")
    @PutMapping("/users/{userId}/farms")
    @Transactional
    public Map<String, Object> setUserFarms(@PathVariable Integer userId, @RequestBody List<Integer> farmIds) {
        User u = users.findById(userId).orElseThrow(() -> ApiException.notFound("사용자"));
        setFarms(userId, farmIds);
        return userView(u);
    }

    private void setFarms(Integer userId, List<Integer> farmIds) {
        userFarms.deleteByUserId(userId);
        userFarms.flush();
        for (Integer f : new LinkedHashSet<>(farmIds)) {
            if (!farms.existsById(f)) {
                throw ApiException.badRequest("없는 농장 ID: " + f);
            }
            UserFarm uf = new UserFarm();
            uf.setUserId(userId);
            uf.setFarmId(f);
            userFarms.save(uf);
        }
    }

    private Map<String, Object> userView(User u) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("userId", u.getUserId());
        m.put("loginId", u.getLoginId());
        m.put("name", u.getName());
        m.put("phone", u.getPhone());
        m.put("role", u.getRole());
        m.put("isActive", u.getIsActive());
        m.put("lockedUntil", u.getLockedUntil());
        m.put("createdAt", u.getCreatedAt());
        m.put("farmIds", userFarms.findByUserId(u.getUserId()).stream().map(UserFarm::getFarmId).toList());
        return m;
    }

    // ---------------- 센서·장치 ----------------
    public record SensorReq(Integer farmId, Integer zoneId, Integer gatewayId, @Size(max = 20) String sensorCode,
                            @Pattern(regexp = "TEMP|HUMI|CO2|SOLAR|SUBSTRATE|EC|PH|TEMP_OUT") String metric, @Size(max = 10) String unit,
                            Double validMin, Double validMax, Double spikeLimit, @Size(max = 100) String installNote,
                            @Pattern(regexp = "ACTIVE|FAULT|RETIRED") String status) {
    }

    @Operation(summary = "센서 등록")
    @PostMapping("/sensors")
    public Sensor createSensor(@Valid @RequestBody SensorReq r) {
        if (r.farmId() == null || r.gatewayId() == null || r.sensorCode() == null || r.metric() == null || r.unit() == null
                || r.validMin() == null || r.validMax() == null) {
            throw ApiException.badRequest("farmId, gatewayId, sensorCode, metric, unit, validMin, validMax 필수");
        }
        if (sensors.findByFarmIdAndSensorCode(r.farmId(), r.sensorCode()).isPresent()) {
            throw new ApiException(HttpStatus.CONFLICT, "DUPLICATE_CODE", "같은 농장에 같은 센서 코드가 있습니다");
        }
        Sensor s = new Sensor();
        s.setFarmId(r.farmId());
        s.setGatewayId(r.gatewayId());
        s.setSensorCode(r.sensorCode());
        s.setMetric(r.metric());
        applySensor(s, r);
        Sensor saved = sensors.save(s);
        ingest.evictCache();
        return saved;
    }

    @Operation(summary = "센서 수정 (구역·설치 위치·유효 범위·상태)")
    @PatchMapping("/sensors/{sensorId}")
    public Sensor updateSensor(@PathVariable Integer sensorId, @Valid @RequestBody SensorReq r) {
        Sensor s = sensors.findById(sensorId).orElseThrow(() -> ApiException.notFound("센서"));
        applySensor(s, r);
        Sensor saved = sensors.save(s);
        ingest.evictCache();
        return saved;
    }

    private void applySensor(Sensor s, SensorReq r) {
        if (r.zoneId() != null) {
            s.setZoneId(r.zoneId() == 0 ? null : r.zoneId());
        }
        if (r.unit() != null) {
            s.setUnit(r.unit());
        }
        if (r.validMin() != null) {
            s.setValidMin(r.validMin());
        }
        if (r.validMax() != null) {
            s.setValidMax(r.validMax());
        }
        if (r.spikeLimit() != null) {
            s.setSpikeLimit(r.spikeLimit());
        }
        if (r.installNote() != null) {
            s.setInstallNote(r.installNote());
        }
        if (r.status() != null) {
            s.setStatus(r.status());
        }
        if (s.getValidMin() >= s.getValidMax()) {
            throw ApiException.badRequest("validMin < validMax 이어야 합니다");
        }
    }

    public record DeviceReq(Integer farmId, Integer zoneId, Integer gatewayId, @Size(max = 20) String deviceCode,
                            @Pattern(regexp = "VENT|FAN|HEATER|SHADE|LIGHT|VALVE|NUTRIENT") String deviceType, @Size(max = 30) String deviceName) {
    }

    @Operation(summary = "장치 등록")
    @PostMapping("/devices")
    public Device createDevice(@Valid @RequestBody DeviceReq r) {
        if (r.farmId() == null || r.gatewayId() == null || r.deviceCode() == null || r.deviceType() == null || r.deviceName() == null) {
            throw ApiException.badRequest("farmId, gatewayId, deviceCode, deviceType, deviceName 필수");
        }
        if (devices.findByFarmIdAndDeviceCode(r.farmId(), r.deviceCode()).isPresent()) {
            throw new ApiException(HttpStatus.CONFLICT, "DUPLICATE_CODE", "같은 농장에 같은 장치 코드가 있습니다");
        }
        Device d = new Device();
        d.setFarmId(r.farmId());
        d.setZoneId(r.zoneId());
        d.setGatewayId(r.gatewayId());
        d.setDeviceCode(r.deviceCode());
        d.setDeviceType(r.deviceType());
        d.setDeviceName(r.deviceName());
        d.setCurrentState(kr.todak.control.DeviceStates.inactive(r.deviceType()));
        return devices.save(d);
    }

    @Operation(summary = "장치 수정 (이름·구역)")
    @PatchMapping("/devices/{deviceId}")
    public Device updateDevice(@PathVariable Integer deviceId, @Valid @RequestBody DeviceReq r) {
        Device d = devices.findById(deviceId).orElseThrow(() -> ApiException.notFound("장치"));
        if (r.deviceName() != null) {
            d.setDeviceName(r.deviceName());
        }
        if (r.zoneId() != null) {
            d.setZoneId(r.zoneId() == 0 ? null : r.zoneId());
        }
        return devices.save(d);
    }

    // ---------------- 제어 규칙 ----------------
    @Operation(summary = "자동 제어 규칙 목록")
    @GetMapping("/rules")
    public List<ControlRule> rules(@RequestParam Integer farmId) {
        return rules.findByFarmIdOrderByPriority(farmId);
    }

    public record RuleUpdate(Double onThreshold, Double offThreshold, @Min(0) @Max(3600) Integer minRunSec, @Min(1) @Max(3600) Integer maxRunSec,
                             @Min(1) @Max(100) Integer maxDailyCount, Boolean isEnabled) {
    }

    @Operation(summary = "자동 제어 규칙 수정", description = "히스테리시스 방향 검사: GE는 off < on, LE는 off > on. 변경 이력 저장 + 게이트웨이 config 재발행")
    @PatchMapping("/rules/{ruleId}")
    @Transactional
    public ControlRule updateRule(@PathVariable Integer ruleId, @Valid @RequestBody RuleUpdate r) {
        ControlRule x = rules.findById(ruleId).orElseThrow(() -> ApiException.notFound("규칙"));
        Map<String, Object[]> changes = new LinkedHashMap<>();
        if (r.onThreshold() != null) {
            changes.put("on_threshold", new Object[]{x.getOnThreshold(), r.onThreshold()});
            x.setOnThreshold(r.onThreshold());
        }
        if (r.offThreshold() != null) {
            changes.put("off_threshold", new Object[]{x.getOffThreshold(), r.offThreshold()});
            x.setOffThreshold(r.offThreshold());
        }
        if (r.minRunSec() != null) {
            changes.put("min_run_sec", new Object[]{x.getMinRunSec(), r.minRunSec()});
            x.setMinRunSec(r.minRunSec());
        }
        if (r.maxRunSec() != null) {
            changes.put("max_run_sec", new Object[]{x.getMaxRunSec(), r.maxRunSec()});
            x.setMaxRunSec(r.maxRunSec());
        }
        if (r.maxDailyCount() != null) {
            changes.put("max_daily_count", new Object[]{x.getMaxDailyCount(), r.maxDailyCount()});
            x.setMaxDailyCount(r.maxDailyCount());
        }
        if (r.isEnabled() != null) {
            changes.put("is_enabled", new Object[]{x.getIsEnabled(), r.isEnabled()});
            x.setIsEnabled(r.isEnabled());
        }
        boolean ok = "GE".equals(x.getCompareOp()) ? x.getOffThreshold() < x.getOnThreshold() : x.getOffThreshold() > x.getOnThreshold();
        if (!ok) {
            throw ApiException.badRequest("히스테리시스 방향 오류: GE는 해제값 < 작동값, LE는 해제값 > 작동값");
        }
        rules.save(x);
        Integer uid = access.user().userId();
        changes.forEach((k, v) -> {
            SettingHistory h = new SettingHistory();
            h.setEntityType("CONTROL_RULE");
            h.setEntityId(ruleId.longValue());
            h.setFieldName(k);
            h.setOldValue(String.valueOf(v[0]));
            h.setNewValue(String.valueOf(v[1]));
            h.setChangedBy(uid);
            history.save(h);
        });
        gatewayService.publishConfig(x.getFarmId());
        return x;
    }

    // ---------------- 로그 ----------------
    @Operation(summary = "센서 수집 로그", description = "센서별 최근 1시간 수신 건수·마지막 수신 시각·상태 + 수신 카운터(서버 기동 이후)")
    @GetMapping("/logs/ingest")
    public Map<String, Object> ingestLog() {
        LocalDateTime hourAgo = LocalDateTime.now().minusHours(1);
        List<Map<String, Object>> rows = new ArrayList<>();
        for (Sensor s : sensors.findAll()) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("sensorId", s.getSensorId());
            m.put("farmId", s.getFarmId());
            m.put("sensorCode", s.getSensorCode());
            m.put("metric", s.getMetric());
            m.put("status", s.getStatus());
            m.put("installNote", s.getInstallNote());
            m.put("lastReceivedAt", s.getLastReceivedAt());
            m.put("receivedLastHour", data.countBySensorIdAndReceivedAtAfter(s.getSensorId(), hourAgo));
            m.put("expectedPerHour", 60);
            rows.add(m);
        }
        return Map.of("counters", ingest.stats(), "sensors", rows);
    }

    @Operation(summary = "제어 명령 로그 (전체 농장)")
    @GetMapping("/logs/commands")
    public List<Map<String, Object>> commandLog(@RequestParam(defaultValue = "100") int size) {
        Map<Integer, Device> ds = new HashMap<>();
        devices.findAll().forEach(d -> ds.put(d.getDeviceId(), d));
        return commands.findByDeviceIdInOrderByCommandIdDesc(ds.keySet(), PageRequest.of(0, Math.min(size, 300)))
                .map(c -> CommandService.view(c, ds.get(c.getDeviceId()))).getContent();
    }

    @Operation(summary = "알림 발송 내역")
    @GetMapping("/logs/deliveries")
    public List<AlertDelivery> deliveryLog(@RequestParam(defaultValue = "100") int size) {
        return deliveries.findAllByOrderByDeliveryIdDesc(PageRequest.of(0, Math.min(size, 300))).getContent();
    }

    @Operation(summary = "오류·예외 로그 (메모리, 최근 200건)")
    @GetMapping("/logs/errors")
    public List<ErrorLog.Entry> errors() {
        return errorLog.recent();
    }

    @Operation(summary = "설정 변경 이력", description = "기준값·규칙·작기·장치 모드 변경")
    @GetMapping("/logs/settings")
    public List<SettingHistory> settings(@RequestParam(defaultValue = "100") int size) {
        return history.findAllByOrderByHistoryIdDesc(PageRequest.of(0, Math.min(size, 300))).getContent();
    }

    // ---------------- 기상 자료 ----------------
    @Operation(summary = "기상자료개방포털 ASOS 일자료 CSV 가져오기", description = "multipart file. 같은 날짜는 덮어쓴다")
    @PostMapping(value = "/weather/import", consumes = "multipart/form-data")
    public WeatherImportService.Result importWeather(@RequestParam("file") MultipartFile file) throws java.io.IOException {
        if (file.isEmpty()) {
            throw ApiException.badRequest("빈 파일");
        }
        return weatherImport.importCsv(file.getBytes(), file.getOriginalFilename());
    }

    @Operation(summary = "외부 기상 일자료 조회")
    @GetMapping("/weather")
    public List<WeatherDaily> weather(@RequestParam(defaultValue = "202") String station,
                                      @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                      @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        return weather.findByStationIdAndObsDateBetweenOrderByObsDate(station, from, to);
    }

    // ---------------- 시뮬레이터 ----------------
    public record ScenarioReq(@NotNull Integer farmId, @NotBlank String scenario, Integer durationSec, String target) {
    }

    @Operation(summary = "시뮬레이터 시나리오 실행 (B안)", description = """
            todak/{farmId}/sim/scenario 토픽으로 발행. scenario: normal, heat, cold, humid, dry, sensor_silent, disconnect, device_fail, recover.
            target: sensor_silent의 센서 코드(기본 S-T02), device_fail의 장치 코드(기본 D-FAN01). 실제 장비(A안)에는 영향 없음""")
    @PostMapping("/simulator/scenario")
    public Map<String, Object> scenario(@Valid @RequestBody ScenarioReq r) throws Exception {
        if (!SCENARIOS.contains(r.scenario())) {
            throw ApiException.badRequest("알 수 없는 시나리오: " + r.scenario());
        }
        if (!farms.existsById(r.farmId())) {
            throw ApiException.notFound("농장");
        }
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("scenario", r.scenario());
        p.put("durationSec", r.durationSec());
        p.put("target", r.target());
        p.put("requestedBy", access.user().loginId());
        p.put("at", LocalDateTime.now().toString());
        mqtt.publish(MqttGateway.scenarioTopic(r.farmId()), om.writeValueAsString(p), false);
        return Map.of("published", true, "topic", MqttGateway.scenarioTopic(r.farmId()), "payload", p);
    }
}
