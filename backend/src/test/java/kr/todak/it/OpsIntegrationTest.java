package kr.todak.it;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** 운영 점검 API (SCR-A7): 관리자만, 일일 점검 9개 항목을 판정해 돌려준다 */
class OpsIntegrationTest extends IntegrationTestBase {

    @Test
    @DisplayName("농가·조회 전용은 운영 점검 API 403")
    void onlyAdmin() throws Exception {
        mvc.perform(get("/api/admin/ops").header("Authorization", bearer(login("farmer01", FARMER_PW)))).andExpect(status().isForbidden());
        mvc.perform(get("/api/admin/ops")).andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("관리자: 9개 점검 항목과 서버·DB·백업 정보")
    void adminGetsChecks() throws Exception {
        mvc.perform(get("/api/admin/ops").header("Authorization", bearer(login("admin", ADMIN_PW))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.checks.length()").value(9))
                .andExpect(jsonPath("$.checks[*].key", hasItems("mqtt", "gateway", "ingest", "sensor", "alert", "command", "errors", "backup", "disk")))
                .andExpect(jsonPath("$.checks[*].status", everyItem(isOneOf("OK", "WARN", "FAIL"))))
                .andExpect(jsonPath("$.overall", isOneOf("OK", "WARN", "FAIL")))
                .andExpect(jsonPath("$.database.tables.length()", greaterThanOrEqualTo(22)))
                .andExpect(jsonPath("$.database.migration", startsWith("V")))
                .andExpect(jsonPath("$.retention.rawDays").value(1095))
                .andExpect(jsonPath("$.server.version", notNullValue()));
    }

    @Test
    @DisplayName("수집 데이터가 없으면 '센서 데이터 수집'은 FAIL, 오프라인 게이트웨이는 FAIL로 판정")
    void judgesFailures() throws Exception {
        jdbc.update("UPDATE TB_GATEWAY SET status='OFFLINE'");
        mvc.perform(get("/api/admin/ops").header("Authorization", bearer(login("admin", ADMIN_PW))))
                .andExpect(jsonPath("$.checks[?(@.key=='ingest')].status").value(contains("FAIL")))
                .andExpect(jsonPath("$.checks[?(@.key=='gateway')].status").value(contains("FAIL")))
                .andExpect(jsonPath("$.overall").value("FAIL"));
    }

    @Test
    @DisplayName("한 번도 연결되지 않은 게이트웨이는 장애가 아니라 '미개통'으로 표시")
    void neverConnectedGatewayIsNotFailure() throws Exception {
        jdbc.update("UPDATE TB_GATEWAY SET status='OFFLINE', last_heartbeat_at=NULL WHERE gateway_id=2");
        mvc.perform(get("/api/admin/ops").header("Authorization", bearer(login("admin", ADMIN_PW))))
                .andExpect(jsonPath("$.checks[?(@.key=='gateway')].status").value(contains("OK")))
                .andExpect(jsonPath("$.checks[?(@.key=='gateway')].detail").value(contains(containsString("미개통"))));
    }
}
