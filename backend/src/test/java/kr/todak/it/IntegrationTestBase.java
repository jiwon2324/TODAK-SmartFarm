package kr.todak.it;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import kr.todak.mqtt.RecordingMqttGateway;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.autoconfigure.flyway.FlywayMigrationStrategy;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.LocalDateTime;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * 실제 MySQL(todak_test)에 붙는 통합 테스트 공통 설정.
 * 컨텍스트가 뜰 때 Flyway clean + migrate로 스키마·시드를 새로 만들고, 각 테스트 전에는 동적 데이터만 비운다.
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Import(IntegrationTestBase.CleanMigrate.class)
public abstract class IntegrationTestBase {
    protected static final String ADMIN_PW = "Admin!2026";
    protected static final String FARMER_PW = "Farmer!2026";

    @Autowired
    protected MockMvc mvc;
    @Autowired
    protected JdbcTemplate jdbc;
    @Autowired
    protected RecordingMqttGateway mqtt;
    protected final ObjectMapper om = new ObjectMapper();

    @TestConfiguration
    static class CleanMigrate {
        @Bean
        FlywayMigrationStrategy cleanMigrate() {
            return (Flyway f) -> {
                f.clean();
                f.migrate();
            };
        }
    }

    @BeforeEach
    void resetDynamicData() {
        for (String t : new String[]{"TB_CONTROL_LOG", "TB_CONTROL_COMMAND", "TB_ALERT_DELIVERY", "TB_ALERT", "TB_SENSOR_DATA_HOURLY",
                "TB_SENSOR_DATA", "TB_GDD_DAILY", "TB_WEATHER_DAILY", "TB_REFRESH_TOKEN", "TB_SETTING_HISTORY"}) {
            jdbc.update("DELETE FROM " + t);
        }
        jdbc.update("UPDATE TB_DEVICE SET mode='AUTO', manual_until=NULL, state_changed_at=NULL, "
                + "current_state = CASE device_type WHEN 'VENT' THEN 'CLOSE' WHEN 'SHADE' THEN 'OPEN' ELSE 'OFF' END");
        jdbc.update("UPDATE TB_GATEWAY SET status='ONLINE', last_heartbeat_at=NOW()");
        jdbc.update("UPDATE TB_SENSOR SET status='ACTIVE', last_received_at=NULL");
        jdbc.update("DELETE FROM TB_USER_FARM");
        jdbc.update("DELETE FROM TB_USER WHERE user_id > 4");
        jdbc.update("UPDATE TB_USER SET failed_count=0, locked_until=NULL, is_active=1, approval_status='APPROVED', must_change_pw=0, pw_reset_requested_at=NULL");
        jdbc.update("INSERT INTO TB_USER_FARM (user_id, farm_id) VALUES (2, 1), (3, 2), (4, 1)");
        jdbc.update("DELETE FROM TB_ZONE WHERE zone_id > 3");
        jdbc.update("UPDATE TB_GATEWAY SET device_token_hash=NULL");
        mqtt.clear();
    }

    protected String login(String id, String pw) throws Exception {
        MvcResult r = mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                .content("{\"loginId\":\"" + id + "\",\"password\":\"" + pw + "\"}")).andReturn();
        return om.readTree(r.getResponse().getContentAsString()).get("accessToken").asText();
    }

    protected static final String VIEWER_PW = "Viewer!2026";

    protected String bearer(String token) {
        return "Bearer " + token;
    }

    protected JsonNode json(MvcResult r) throws Exception {
        return om.readTree(r.getResponse().getContentAsString());
    }

    /** 시뮬레이터와 같은 형식의 센서 payload */
    protected static String payload(String msgId, String code, double value, LocalDateTime at) {
        String ts = OffsetDateTime.of(at, ZoneId.of("Asia/Seoul").getRules().getOffset(at)).toString();
        return "{\"msgId\":\"" + msgId + "\",\"sensor\":\"" + code + "\",\"value\":" + value + ",\"ts\":\"" + ts + "\",\"samples\":6}";
    }
}
