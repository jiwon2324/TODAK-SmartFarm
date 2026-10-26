package kr.todak.it;

import kr.todak.alert.AlertService;
import kr.todak.control.RuleEngine;
import kr.todak.ingest.SensorIngestService;
import kr.todak.mqtt.MqttMessageRouter;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;

import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 개발 계획서 v2.0 대비 검토에서 보완한 항목 (docs/Development_Plan/계획서_대비_구현_검토.md).
 * 표 41 VIEWER, REQ-F-13 구역, API-26 HTTP 수집, 표 39 CR-01·03·04·06 세부 조건, REQ-F-02 예외, REQ-F-09 30분 억제, REQ-F-15 덮어쓰기 확인
 */
class PlanAlignmentIntegrationTest extends IntegrationTestBase {
    @Autowired
    SensorIngestService ingest;
    @Autowired
    RuleEngine engine;
    @Autowired
    MqttMessageRouter router;
    @Autowired
    AlertService alerts;

    private final LocalDateTime now = LocalDateTime.now().truncatedTo(ChronoUnit.MINUTES);
    private int seq;

    @BeforeEach
    void allDay() {
        ingest.clearMemory();
        jdbc.update("UPDATE TB_CROP_STD SET day_start_time='00:00:00', night_start_time='23:59:59'");
    }

    private void put(String code, double v, LocalDateTime at) {
        ingest.ingest(1, code, payload("p-" + code + "-" + (++seq), code, v, at));
    }

    private long cmds(String devicePrefix, String action, String source) {
        return jdbc.queryForObject("SELECT COUNT(*) FROM TB_CONTROL_COMMAND c JOIN TB_DEVICE d ON d.device_id=c.device_id "
                + "WHERE d.device_code LIKE ? AND c.action=? AND c.source=?", Long.class, devicePrefix + "%", action, source);
    }

    private void ackAll() throws Exception {
        for (var p : mqtt.published()) {
            if (p.topic().endsWith("/cmd")) {
                var j = om.readTree(p.payload());
                router.route("todak/1/device/" + p.topic().split("/")[3] + "/ack",
                        "{\"commandId\":" + j.get("commandId").asLong() + ",\"result\":\"OK\",\"state\":\"" + j.get("action").asText() + "\"}");
            }
        }
        mqtt.clear();
    }

    @Test
    @DisplayName("표 41 VIEWER: 조회 200, 제어·모드·기준값·작기·알림 처리 403, 다른 농장·관리자 API 403")
    void viewerReadOnly() throws Exception {
        String v = login("viewer01", VIEWER_PW);
        mvc.perform(get("/api/farms/1/dashboard").header("Authorization", bearer(v))).andExpect(status().isOk());
        mvc.perform(get("/api/farms/2/dashboard").header("Authorization", bearer(v))).andExpect(status().isForbidden());
        int dev = jdbc.queryForObject("SELECT device_id FROM TB_DEVICE WHERE device_code='D-FAN01' AND farm_id=1", Integer.class);
        mvc.perform(post("/api/devices/" + dev + "/commands").header("Authorization", bearer(v)).header("Idempotency-Key", "v-1")
                .contentType(MediaType.APPLICATION_JSON).content("{\"action\":\"ON\",\"confirm\":true}")).andExpect(status().isForbidden());
        mvc.perform(patch("/api/devices/" + dev + "/mode").header("Authorization", bearer(v)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"mode\":\"MANUAL\"}")).andExpect(status().isForbidden());
        mvc.perform(patch("/api/crop-cycles/1").header("Authorization", bearer(v)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"gddBaseC\":9}")).andExpect(status().isForbidden());
        mvc.perform(post("/api/beehives").header("Authorization", bearer(v)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"farmId\":1,\"placedDate\":\"" + LocalDate.now() + "\",\"replaceDays\":6}")).andExpect(status().isForbidden());
        mvc.perform(get("/api/admin/summary").header("Authorization", bearer(v))).andExpect(status().isForbidden());
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_CONTROL_COMMAND", Integer.class)).isZero();
    }

    @Test
    @DisplayName("REQ-F-13 구역: 등록, 중복 409, 센서·장치가 연결된 구역 삭제 409 ZONE_IN_USE, 빈 구역 삭제, 농가 403")
    void zones() throws Exception {
        String a = login("admin", ADMIN_PW);
        String body = "{\"farmId\":1,\"zoneCode\":\"Z3\",\"zoneName\":\"육묘 구역\",\"areaM2\":10}";
        String id = json(mvc.perform(post("/api/admin/zones").header("Authorization", bearer(a)).contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk()).andReturn()).get("zoneId").asText();
        mvc.perform(post("/api/admin/zones").header("Authorization", bearer(a)).contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isConflict());
        mvc.perform(delete("/api/admin/zones/1").header("Authorization", bearer(a))).andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("ZONE_IN_USE"));
        mvc.perform(delete("/api/admin/zones/" + id).header("Authorization", bearer(a))).andExpect(status().isOk());
        mvc.perform(post("/api/admin/zones").header("Authorization", bearer(login("farmer01", FARMER_PW)))
                .contentType(MediaType.APPLICATION_JSON).content(body)).andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("API-26 HTTP 대체 수집: 기기 토큰 없거나 틀리면 401, 정상 저장, 같은 msgId 재전송은 중복, 미등록 센서 거부")
    void httpIngest() throws Exception {
        String a = login("admin", ADMIN_PW);
        String token = json(mvc.perform(post("/api/admin/gateways/1/token").header("Authorization", bearer(a))).andReturn()).get("deviceToken").asText();
        assertThat(jdbc.queryForObject("SELECT device_token_hash FROM TB_GATEWAY WHERE gateway_id=1", String.class)).hasSize(64).doesNotContain(token);
        String ts = now.atZone(java.time.ZoneId.of("Asia/Seoul")).toOffsetDateTime().toString();
        String b = "{\"gatewayCode\":\"GW-01\",\"readings\":[{\"sensorCode\":\"S-T01\",\"msgId\":\"http-1\",\"ts\":\"" + ts + "\",\"value\":21.5},"
                + "{\"sensorCode\":\"S-H01\",\"msgId\":\"http-2\",\"ts\":\"" + ts + "\",\"value\":70},"
                + "{\"sensorCode\":\"S-NOPE\",\"msgId\":\"http-3\",\"ts\":\"" + ts + "\",\"value\":1}]}";
        mvc.perform(post("/api/ingest/sensor-data").contentType(MediaType.APPLICATION_JSON).content(b)).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/ingest/sensor-data").header("X-Device-Token", "gw_wrong").contentType(MediaType.APPLICATION_JSON).content(b))
                .andExpect(status().isUnauthorized());
        mvc.perform(post("/api/ingest/sensor-data").header("X-Device-Token", token).contentType(MediaType.APPLICATION_JSON).content(b))
                .andExpect(status().isOk()).andExpect(jsonPath("$.saved").value(2)).andExpect(jsonPath("$.rejected").value(1));
        mvc.perform(post("/api/ingest/sensor-data").header("X-Device-Token", token).contentType(MediaType.APPLICATION_JSON).content(b))
                .andExpect(jsonPath("$.saved").value(0)).andExpect(jsonPath("$.duplicates").value(2));
    }

    @Test
    @DisplayName("CR-01 2단계: 측창 개방 5분 뒤에도 30℃ 이상이면 환기팬 ON, 26℃ 이하면 이 규칙이 켠 환기팬 OFF")
    void cr01Stage2() throws Exception {
        put("S-T01", 31, now);
        put("S-T02", 31, now);
        engine.evaluateFarm(1, now);
        ackAll();
        assertThat(cmds("D-VENT", "OPEN", "AUTO")).isEqualTo(2);
        assertThat(cmds("D-FAN", "ON", "AUTO")).isZero();      // 아직 5분 안 됨
        jdbc.update("UPDATE TB_DEVICE SET state_changed_at = NOW() - INTERVAL 6 MINUTE WHERE device_type='VENT'");
        engine.evaluateFarm(1, now);
        ackAll();
        assertThat(cmds("D-FAN", "ON", "AUTO")).isEqualTo(2);
        jdbc.update("UPDATE TB_DEVICE SET state_changed_at = NOW() - INTERVAL 10 MINUTE WHERE farm_id=1");
        put("S-T01", 26.0, now.plusMinutes(1));   // 31→26: 급변 한계(5℃) 안에서 해제값(26) 도달
        put("S-T02", 26.0, now.plusMinutes(1));
        engine.evaluateFarm(1, now.plusMinutes(1));
        assertThat(cmds("D-FAN", "OFF", "AUTO")).isEqualTo(2);
    }

    @Test
    @DisplayName("CR-06 저온 안전: 5℃ 이하면 난방 ON과 함께 열린 측창을 닫는다 (수동 모드여도)")
    void cr06ClosesVents() {
        jdbc.update("UPDATE TB_DEVICE SET current_state='OPEN', mode='MANUAL', manual_until=NOW() + INTERVAL 1 HOUR WHERE device_type='VENT'");
        put("S-T01", 4, now);
        put("S-T02", 4.5, now);
        engine.evaluateFarm(1, now);
        assertThat(cmds("D-HEAT", "ON", "SAFETY")).isEqualTo(1);
        assertThat(cmds("D-VENT", "CLOSE", "SAFETY")).isEqualTo(2);
    }

    @Test
    @DisplayName("CR-03 차광: 일사 800 이상이 10분 계속돼야 닫는다 (순간값 1건으로는 작동하지 않음)")
    void cr03Sustain() {
        put("S-SOL01", 900, now);
        engine.evaluateFarm(1, now);
        assertThat(cmds("D-SHADE", "CLOSE", "AUTO")).isZero();
        for (int m = 10; m >= 1; m--) {
            put("S-SOL01", 900, now.minusMinutes(m));
        }
        engine.evaluateFarm(1, now);
        assertThat(cmds("D-SHADE", "CLOSE", "AUTO")).isEqualTo(1);
    }

    @Test
    @DisplayName("CR-04 관수 간격: 직전 자동 관수 후 30분 안에는 다시 열지 않는다")
    void cr04Interval() throws Exception {
        put("S-SM01", 50, now);
        engine.evaluateFarm(1, now);
        ackAll();
        assertThat(cmds("D-VALVE01", "ON", "AUTO")).isEqualTo(1);
        jdbc.update("UPDATE TB_DEVICE SET current_state='OFF', state_changed_at = NOW() - INTERVAL 1 HOUR WHERE device_code='D-VALVE01'");
        put("S-SM01", 50, now.plusMinutes(5));
        engine.evaluateFarm(1, now.plusMinutes(5));
        assertThat(cmds("D-VALVE01", "ON", "AUTO")).isEqualTo(1);
        jdbc.update("UPDATE TB_CONTROL_COMMAND SET requested_at = NOW() - INTERVAL 31 MINUTE");
        engine.evaluateFarm(1, now.plusMinutes(5));
        assertThat(cmds("D-VALVE01", "ON", "AUTO")).isEqualTo(2);
    }

    @Test
    @DisplayName("REQ-F-02 예외: 게이트웨이는 연결됐는데 온도 센서 값이 모두 없으면 CRITICAL 경보, 값이 오면 해결")
    void allTempSensorsFailed() {
        engine.evaluateFarm(1, now);
        assertThat(jdbc.queryForObject("SELECT severity FROM TB_ALERT WHERE dedupe_key='ALL_FAIL:1:TEMP'", String.class)).isEqualTo("CRITICAL");
        put("S-T01", 20, now);
        engine.evaluateFarm(1, now);
        assertThat(jdbc.queryForObject("SELECT status FROM TB_ALERT WHERE dedupe_key='ALL_FAIL:1:TEMP'", String.class)).isEqualTo("RESOLVED");
    }

    @Test
    @DisplayName("REQ-F-09: 해결된 지 30분 안에 같은 경보가 다시 생기면 새 행을 만들지 않고 다시 연다")
    void dedupeAfterResolve() {
        var a1 = alerts.raise(1, null, "THRESHOLD", "WARN", "TEST:1", "첫 발생");
        alerts.resolve("TEST:1");
        var a2 = alerts.raise(1, null, "THRESHOLD", "WARN", "TEST:1", "재발생");
        assertThat(a2.getAlertId()).isEqualTo(a1.getAlertId());
        assertThat(a2.getStatus()).isEqualTo("OPEN");
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_ALERT WHERE dedupe_key='TEST:1'", Integer.class)).isEqualTo(1);
        jdbc.update("UPDATE TB_ALERT SET status='RESOLVED', resolved_at = NOW() - INTERVAL 31 MINUTE WHERE dedupe_key='TEST:1'");
        alerts.raise(1, null, "THRESHOLD", "WARN", "TEST:1", "30분 지나 새 발생");
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_ALERT WHERE dedupe_key='TEST:1'", Integer.class)).isEqualTo(2);
    }

    @Test
    @DisplayName("REQ-F-15: 이미 있는 날짜는 409 DUPLICATE_DATES로 확인 요청, overwrite=true면 덮어쓴다")
    void weatherOverwriteConfirm() throws Exception {
        String csv = "지점,지점명,일시,평균기온(°C),최저기온(°C),최고기온(°C)\n202,양평," + LocalDate.now().minusDays(3) + ",10,5,15\n";
        String a = login("admin", ADMIN_PW);
        var f = new MockMultipartFile("file", "w.csv", "text/csv", csv.getBytes(StandardCharsets.UTF_8));
        mvc.perform(multipart("/api/admin/weather/import").file(f).header("Authorization", bearer(a))).andExpect(status().isOk());
        mvc.perform(multipart("/api/admin/weather/import").file(f).header("Authorization", bearer(a))).andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("DUPLICATE_DATES"));
        mvc.perform(multipart("/api/admin/weather/import").file(f).param("overwrite", "true").header("Authorization", bearer(a)))
                .andExpect(status().isOk()).andExpect(jsonPath("$.overwritten").value(1));
        // 농가도 자기 농장 기상 지점 자료는 조회 가능 (API-22)
        mvc.perform(get("/api/analytics/weather?farmId=1&from=" + LocalDate.now().minusDays(5) + "&to=" + LocalDate.now())
                .header("Authorization", bearer(login("farmer01", FARMER_PW)))).andExpect(jsonPath("$[0].stationId").value("202"));
    }

    @Test
    @DisplayName("API-06 대시보드에 오늘 DLI·누적 GDD·최근 수집 시각, GDD 응답에 요약(경과일·결측·35℃/5℃ 일수)")
    void dashboardAndGddSummary() throws Exception {
        put("S-T01", 20, now);
        String t = login("farmer01", FARMER_PW);
        mvc.perform(get("/api/farms/1/dashboard").header("Authorization", bearer(t)))
                .andExpect(jsonPath("$.lastReceivedAt").exists()).andExpect(jsonPath("$.cumGddInternal").hasJsonPath()).andExpect(jsonPath("$.dliToday").hasJsonPath());
        mvc.perform(get("/api/analytics/gdd?farmId=1").header("Authorization", bearer(t)))
                .andExpect(jsonPath("$.summary.elapsedDays").value(14)).andExpect(jsonPath("$.summary.hot35Days").exists());
    }

    @Test
    @DisplayName("13장 센서 고장 대응: Z1 배지수분 센서 값이 없으면 Z2 센서로 임시 대체해 관수, 둘 다 없으면 관수 안 함")
    void zoneSensorSubstitution() {
        engine.evaluateFarm(1, now);
        assertThat(cmds("D-VALVE", "ON", "AUTO")).isZero();
        put("S-SM02", 50, now);
        engine.evaluateFarm(1, now);
        assertThat(cmds("D-VALVE01", "ON", "AUTO")).isEqualTo(1);   // S-SM01 없음 → S-SM02로 대체
        assertThat(cmds("D-VALVE02", "ON", "AUTO")).isEqualTo(1);
    }

    @Test
    @DisplayName("표 39 CR-05: 안전 한계 작동 시 CRITICAL 경보 / 표 67: 같은 Idempotency-Key 재요청은 기존 명령, 다른 본문은 409")
    void safetyAlertAndDuplicateRequest() throws Exception {
        put("S-T01", 36, now);
        put("S-T02", 36, now);
        engine.evaluateFarm(1, now);
        assertThat(jdbc.queryForObject("SELECT severity FROM TB_ALERT WHERE dedupe_key='SAFETY:1:CR-05'", String.class)).isEqualTo("CRITICAL");

        String t = login("farmer01", FARMER_PW);
        int heat = jdbc.queryForObject("SELECT device_id FROM TB_DEVICE WHERE device_code='D-HEAT01' AND farm_id=1", Integer.class);
        int light = jdbc.queryForObject("SELECT device_id FROM TB_DEVICE WHERE device_code='D-LIGHT01' AND farm_id=1", Integer.class);
        String on = "{\"action\":\"ON\",\"confirm\":true}";
        mvc.perform(post("/api/devices/" + light + "/commands").header("Authorization", bearer(t)).header("Idempotency-Key", "dup-1")
                .contentType(MediaType.APPLICATION_JSON).content(on)).andExpect(status().isAccepted());
        mvc.perform(post("/api/devices/" + light + "/commands").header("Authorization", bearer(t)).header("Idempotency-Key", "dup-1")
                .contentType(MediaType.APPLICATION_JSON).content(on)).andExpect(status().isAccepted());
        mvc.perform(post("/api/devices/" + heat + "/commands").header("Authorization", bearer(t)).header("Idempotency-Key", "dup-1")
                .contentType(MediaType.APPLICATION_JSON).content(on)).andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("DUPLICATE_REQUEST"));
        assertThat(cmds("D-LIGHT01", "ON", "MANUAL")).isEqualTo(1);
    }
}
