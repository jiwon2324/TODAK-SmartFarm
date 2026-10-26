package kr.todak.it;

import kr.todak.control.CommandService;
import kr.todak.control.RuleEngine;
import kr.todak.ingest.SensorIngestService;
import kr.todak.mqtt.MqttMessageRouter;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;

import java.time.LocalDateTime;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** TC-002·004·008·016 · REQ-F-02~04, F-08, F-16: 자동 제어(히스테리시스·안전·수동 우선·관수 상한), 명령 수명주기 */
class ControlIntegrationTest extends IntegrationTestBase {
    @Autowired
    SensorIngestService ingest;
    @Autowired
    RuleEngine engine;
    @Autowired
    CommandService commands;
    @Autowired
    MqttMessageRouter router;

    /** 실제 현재 시각 기준 (state_changed_at·manual_until이 실제 시각으로 기록되므로). 주야 판정은 @BeforeEach에서 종일 주간으로 고정 */
    private final LocalDateTime noon = LocalDateTime.now().truncatedTo(java.time.temporal.ChronoUnit.MINUTES);
    private int seq;

    @org.junit.jupiter.api.BeforeEach
    void dayAllDay() {
        ingest.clearMemory();
        jdbc.update("UPDATE TB_CROP_STD SET day_start_time='00:00:00', night_start_time='23:59:59'");
    }

    private void temps(LocalDateTime at, double z1, double z2) {
        ingest.ingest(1, "S-T01", payload("t1-" + (++seq), "S-T01", z1, at));
        ingest.ingest(1, "S-T02", payload("t2-" + (++seq), "S-T02", z2, at));
    }

    private void ackAll() {
        for (var p : mqtt.published()) {
            if (!p.topic().endsWith("/cmd")) {
                continue;
            }
            String code = p.topic().split("/")[3];
            try {
                var j = om.readTree(p.payload());
                router.route("todak/1/device/" + code + "/ack",
                        "{\"commandId\":" + j.get("commandId").asLong() + ",\"result\":\"OK\",\"state\":\"" + j.get("action").asText() + "\"}");
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        }
        mqtt.clear();
    }

    private String state(String code) {
        return jdbc.queryForObject("SELECT current_state FROM TB_DEVICE WHERE farm_id=1 AND device_code=?", String.class, code);
    }

    private void backdateStateChange(int minutes) {
        jdbc.update("UPDATE TB_DEVICE SET state_changed_at = state_changed_at - INTERVAL ? MINUTE WHERE state_changed_at IS NOT NULL", minutes);
    }

    @Test
    @DisplayName("TC-002 고온 28℃ 이상 → 측창 OPEN 1회, 27℃(히스테리시스 구간) 유지, 26℃ 이하 → CLOSE")
    void ventHysteresis() {
        temps(noon, 28.6, 29.1);
        assertThat(engine.evaluateFarm(1, noon)).isEqualTo(2);           // D-VENT01, D-VENT02
        ackAll();
        assertThat(state("D-VENT01")).isEqualTo("OPEN");
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_CONTROL_LOG", Integer.class)).isEqualTo(2);

        backdateStateChange(10);
        temps(noon.plusMinutes(1), 27.0, 27.2);
        assertThat(engine.evaluateFarm(1, noon.plusMinutes(1))).isZero();  // 유지 (채터링 없음)

        temps(noon.plusMinutes(2), 25.8, 25.9);
        assertThat(engine.evaluateFarm(1, noon.plusMinutes(2))).isEqualTo(2);
        ackAll();
        assertThat(state("D-VENT02")).isEqualTo("CLOSE");
    }

    @Test
    @DisplayName("최소 작동시간 안에는 반대 명령을 내지 않는다")
    void minRunTime() {
        temps(noon, 29.0, 29.0);
        engine.evaluateFarm(1, noon);
        ackAll();
        temps(noon.plusMinutes(1), 25.0, 25.0);   // 바로 OFF 조건이지만 180초 안
        assertThat(engine.evaluateFarm(1, noon.plusMinutes(1))).isZero();
    }

    @Test
    @DisplayName("수동 모드 장치는 자동 규칙이 건드리지 않지만 안전 한계(35℃)는 개입한다")
    void manualAndSafety() throws Exception {
        String t = login("farmer01", FARMER_PW);
        mvc.perform(patch("/api/devices/1/mode").header("Authorization", bearer(t)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"mode\":\"MANUAL\",\"manualMinutes\":30}")).andExpect(status().isOk());
        temps(noon, 29.0, 29.0);
        engine.evaluateFarm(1, noon);
        assertThat(mqtt.published().stream().anyMatch(p -> p.topic().contains("D-VENT01"))).isFalse();
        assertThat(mqtt.published().stream().anyMatch(p -> p.topic().contains("D-VENT02"))).isTrue();
        ackAll();

        temps(noon.plusMinutes(1), 32.0, 32.5);
        engine.evaluateFarm(1, noon.plusMinutes(1));
        ackAll();
        temps(noon.plusMinutes(2), 35.5, 36.0);
        engine.evaluateFarm(1, noon.plusMinutes(2));
        ackAll();
        assertThat(state("D-VENT01")).isEqualTo("OPEN");                    // 수동이어도 안전 규칙
        assertThat(state("D-FAN01")).isEqualTo("ON");
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_CONTROL_COMMAND WHERE source='SAFETY'", Integer.class)).isGreaterThanOrEqualTo(3);

        // 안전 한계 작동 중 수동 OFF 요청 → 423
        mvc.perform(post("/api/devices/3/commands").header("Authorization", bearer(t)).header("Idempotency-Key", "k-safe")
                        .contentType(MediaType.APPLICATION_JSON).content("{\"action\":\"OFF\",\"confirm\":true}"))
                .andExpect(status().isLocked()).andExpect(jsonPath("$.code").value("SAFETY_LOCKED"));
    }

    @Test
    @DisplayName("TC-008·016 수동 명령: 확인 없으면 400, 202 SENT → ACK 후 ACKED·상태 반영, 같은 멱등키는 같은 명령")
    void manualCommandLifecycle() throws Exception {
        String t = login("farmer01", FARMER_PW);
        mvc.perform(post("/api/devices/7/commands").header("Authorization", bearer(t)).header("Idempotency-Key", "k1")
                        .contentType(MediaType.APPLICATION_JSON).content("{\"action\":\"ON\"}"))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("CONFIRM_REQUIRED"));

        MvcResult r = mvc.perform(post("/api/devices/7/commands").header("Authorization", bearer(t)).header("Idempotency-Key", "k1")
                        .contentType(MediaType.APPLICATION_JSON).content("{\"action\":\"ON\",\"confirm\":true,\"manualMinutes\":10}"))
                .andExpect(status().isAccepted()).andExpect(jsonPath("$.status").value("SENT")).andReturn();
        long id = json(r).get("commandId").asLong();
        assertThat(mqtt.published()).hasSize(1);
        assertThat(mqtt.published().get(0).topic()).isEqualTo("todak/1/device/D-LIGHT01/cmd");
        assertThat(jdbc.queryForObject("SELECT mode FROM TB_DEVICE WHERE device_id=7", String.class)).isEqualTo("MANUAL");

        MvcResult again = mvc.perform(post("/api/devices/7/commands").header("Authorization", bearer(t)).header("Idempotency-Key", "k1")
                .contentType(MediaType.APPLICATION_JSON).content("{\"action\":\"ON\",\"confirm\":true}")).andReturn();
        assertThat(json(again).get("commandId").asLong()).isEqualTo(id);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_CONTROL_COMMAND", Integer.class)).isEqualTo(1);

        ackAll();
        assertThat(jdbc.queryForObject("SELECT status FROM TB_CONTROL_COMMAND WHERE command_id=?", String.class, id)).isEqualTo("ACKED");
        assertThat(state("D-LIGHT01")).isEqualTo("ON");
        assertThat(jdbc.queryForObject("SELECT changed_by FROM TB_CONTROL_LOG WHERE command_id=?", String.class, id)).isEqualTo("MANUAL");
    }

    @Test
    @DisplayName("TC-016 ACK 없음 → 1회 재전송 → TIMEOUT + DEVICE_NOACK 경보 (명령 전송 ≠ 장치 동작)")
    void timeout() throws Exception {
        String t = login("farmer01", FARMER_PW);
        MvcResult r = mvc.perform(post("/api/devices/3/commands").header("Authorization", bearer(t)).header("Idempotency-Key", "k-to")
                .contentType(MediaType.APPLICATION_JSON).content("{\"action\":\"ON\",\"confirm\":true}")).andReturn();
        long id = json(r).get("commandId").asLong();
        jdbc.update("UPDATE TB_CONTROL_COMMAND SET sent_at = sent_at - INTERVAL 30 SECOND WHERE command_id=?", id);
        commands.checkTimeouts();
        assertThat(jdbc.queryForObject("SELECT retry_count FROM TB_CONTROL_COMMAND WHERE command_id=?", Integer.class, id)).isEqualTo(1);
        assertThat(mqtt.published()).hasSize(2);
        jdbc.update("UPDATE TB_CONTROL_COMMAND SET sent_at = sent_at - INTERVAL 30 SECOND WHERE command_id=?", id);
        commands.checkTimeouts();
        assertThat(jdbc.queryForObject("SELECT status FROM TB_CONTROL_COMMAND WHERE command_id=?", String.class, id)).isEqualTo("TIMEOUT");
        assertThat(state("D-FAN01")).isEqualTo("OFF");
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_ALERT WHERE alert_type='DEVICE_NOACK' AND status='OPEN'", Integer.class)).isEqualTo(1);
    }

    @Test
    @DisplayName("게이트웨이 오프라인이면 수동 명령 503")
    void gatewayOffline() throws Exception {
        jdbc.update("UPDATE TB_GATEWAY SET status='OFFLINE' WHERE gateway_id=1");
        String t = login("farmer01", FARMER_PW);
        mvc.perform(post("/api/devices/3/commands").header("Authorization", bearer(t)).header("Idempotency-Key", "k-off")
                        .contentType(MediaType.APPLICATION_JSON).content("{\"action\":\"ON\",\"confirm\":true}"))
                .andExpect(status().isServiceUnavailable()).andExpect(jsonPath("$.code").value("GATEWAY_OFFLINE"));
    }

    @Test
    @DisplayName("TC-004 관수: 배지수분 ≤55% → 밸브 ON, 일 최대 횟수 도달 시 차단 + 경보")
    void irrigationDailyLimit() {
        jdbc.update("UPDATE TB_CONTROL_RULE SET max_daily_count=1 WHERE rule_code='CR-04'");
        try {
            ingest.ingest(1, "S-SM01", payload("sm-1", "S-SM01", 50.0, noon));
            engine.evaluateFarm(1, noon);
            ackAll();
            assertThat(state("D-VALVE01")).isEqualTo("ON");
            jdbc.update("UPDATE TB_DEVICE SET current_state='OFF', state_changed_at = NOW() - INTERVAL 1 HOUR WHERE device_code='D-VALVE01'");
            ingest.ingest(1, "S-SM01", payload("sm-2", "S-SM01", 50.0, noon.plusMinutes(5)));
            engine.evaluateFarm(1, noon.plusMinutes(5));
            assertThat(mqtt.published().stream().noneMatch(p -> p.topic().contains("D-VALVE01"))).isTrue();
            assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_ALERT WHERE dedupe_key LIKE 'IRRIGATION_LIMIT:%'", Integer.class)).isEqualTo(1);
        } finally {
            jdbc.update("UPDATE TB_CONTROL_RULE SET max_daily_count=12 WHERE rule_code='CR-04'");
        }
    }

    @Test
    @DisplayName("기준값 이탈 경보는 30분 안 재발생 시 횟수만 늘고, 범위로 돌아오면 해결")
    void thresholdAlertDedupe() {
        ingest.ingest(1, "S-H01", payload("h-1", "S-H01", 95.0, noon));
        engine.evaluateFarm(1, noon);
        ingest.ingest(1, "S-H01", payload("h-2", "S-H01", 96.0, noon.plusMinutes(1)));
        engine.evaluateFarm(1, noon.plusMinutes(1));
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_ALERT WHERE dedupe_key='THRESHOLD:1:S-H01:HIGH'", Integer.class)).isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT occur_count FROM TB_ALERT WHERE dedupe_key='THRESHOLD:1:S-H01:HIGH'", Integer.class)).isEqualTo(2);
        ingest.ingest(1, "S-H01", payload("h-3", "S-H01", 82.0, noon.plusMinutes(2)) /* 96→82: 급변 한계(20) 이내 */);
        engine.evaluateFarm(1, noon.plusMinutes(2));
        assertThat(jdbc.queryForObject("SELECT status FROM TB_ALERT WHERE dedupe_key='THRESHOLD:1:S-H01:HIGH'", String.class)).isEqualTo("RESOLVED");
    }
}
