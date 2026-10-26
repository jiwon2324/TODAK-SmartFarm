package kr.todak.it;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** 인수 기준 5·6: 역할 분리와 농가 간 데이터 격리 (화면이 아니라 API에서 막는지) */
class AuthorizationIntegrationTest extends IntegrationTestBase {

    @Test
    @DisplayName("농가는 관리자 API 403")
    void farmerCannotUseAdminApi() throws Exception {
        String t = login("farmer01", FARMER_PW);
        mvc.perform(get("/api/admin/users").header("Authorization", bearer(t))).andExpect(status().isForbidden());
        mvc.perform(get("/api/admin/summary").header("Authorization", bearer(t))).andExpect(status().isForbidden());
        mvc.perform(post("/api/admin/simulator/scenario").header("Authorization", bearer(t)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"farmId\":1,\"scenario\":\"heat\"}")).andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("farmer01은 농장 2의 대시보드·센서·장치·알림에 접근 불가")
    void farmIsolation() throws Exception {
        String t = login("farmer01", FARMER_PW);
        mvc.perform(get("/api/farms/2/dashboard").header("Authorization", bearer(t))).andExpect(status().isForbidden());
        mvc.perform(get("/api/sensors?farmId=2").header("Authorization", bearer(t))).andExpect(status().isForbidden());
        mvc.perform(get("/api/sensor-data/series?sensorId=12&from=2026-01-01T00:00:00&to=2026-01-02T00:00:00").header("Authorization", bearer(t)))
                .andExpect(status().isForbidden());
        mvc.perform(post("/api/devices/12/commands").header("Authorization", bearer(t)).header("Idempotency-Key", "x1")
                .contentType(MediaType.APPLICATION_JSON).content("{\"action\":\"ON\",\"confirm\":true}")).andExpect(status().isForbidden());
        mvc.perform(get("/api/alerts?farmId=2").header("Authorization", bearer(t))).andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("농가 농장 목록에는 자기 농장만 나온다")
    void farmListScoped() throws Exception {
        String t = login("farmer01", FARMER_PW);
        mvc.perform(get("/api/farms").header("Authorization", bearer(t))).andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1)).andExpect(jsonPath("$[0].farmId").value(1));
    }

    @Test
    @DisplayName("관리자는 모든 농장 조회 가능")
    void adminSeesAll() throws Exception {
        String t = login("admin", ADMIN_PW);
        mvc.perform(get("/api/farms").header("Authorization", bearer(t))).andExpect(jsonPath("$.length()").value(2));
        mvc.perform(get("/api/farms/2/dashboard").header("Authorization", bearer(t))).andExpect(status().isOk());
    }

    @Test
    @DisplayName("관리자 권한을 회수하면 농장 접근도 즉시 막힌다")
    void revokeFarmAccess() throws Exception {
        String admin = login("admin", ADMIN_PW);
        String farmer = login("farmer01", FARMER_PW);
        mvc.perform(put("/api/admin/users/2/farms").header("Authorization", bearer(admin)).contentType(MediaType.APPLICATION_JSON).content("[]"))
                .andExpect(status().isOk());
        mvc.perform(get("/api/farms/1/dashboard").header("Authorization", bearer(farmer))).andExpect(status().isForbidden());
        mvc.perform(put("/api/admin/users/2/farms").header("Authorization", bearer(admin)).contentType(MediaType.APPLICATION_JSON).content("[1]"))
                .andExpect(status().isOk());
        mvc.perform(get("/api/farms/1/dashboard").header("Authorization", bearer(farmer))).andExpect(status().isOk());
    }
}
