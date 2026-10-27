package kr.todak.it;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MvcResult;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** 로그인 없이 둘러보기: 조회 전용(VIEWER) 계정으로만 들어가고, 제어·관리자 기능은 막힌다 [REQ-F-12, REQ-N-04] */
@TestPropertySource(properties = "DEMO_LOGIN_ID=viewer01")
class DemoLoginIntegrationTest extends IntegrationTestBase {

    @Test
    @DisplayName("둘러보기: 사용 여부 공개 → VIEWER 토큰 발급 → 조회 200, 장치 제어·관리자 API 403")
    void demoIsReadOnly() throws Exception {
        mvc.perform(get("/api/auth/demo")).andExpect(status().isOk()).andExpect(jsonPath("$.enabled").value(true));
        MvcResult r = mvc.perform(post("/api/auth/demo")).andExpect(status().isOk()).andReturn();
        assertThat(r.getResponse().getHeader("Set-Cookie")).contains("todak_rt=");
        String t = json(r).get("accessToken").asText();
        assertThat(json(r).get("user").get("role").asText()).isEqualTo("VIEWER");

        mvc.perform(get("/api/farms/1/dashboard").header("Authorization", bearer(t))).andExpect(status().isOk());
        mvc.perform(post("/api/devices/1/commands").header("Authorization", bearer(t)).header("Idempotency-Key", "demo-1").contentType(MediaType.APPLICATION_JSON)
                .content("{\"action\":\"ON\",\"confirm\":true,\"manualMinutes\":10,\"reason\":\"둘러보기\"}")).andExpect(status().isForbidden());
        mvc.perform(get("/api/admin/users").header("Authorization", bearer(t))).andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("둘러보기 계정이 VIEWER가 아니면(설정 실수) 거부한다")
    void demoRefusesNonViewer() throws Exception {
        jdbc.update("UPDATE TB_USER SET role='FARMER' WHERE login_id='viewer01'");
        try {
            MvcResult r = mvc.perform(post("/api/auth/demo")).andReturn();
            assertThat(r.getResponse().getStatus()).isEqualTo(403);
            assertThat(json(r).get("code").asText()).isEqualTo("DEMO_DISABLED");
        } finally {
            jdbc.update("UPDATE TB_USER SET role='VIEWER' WHERE login_id='viewer01'");
        }
    }
}
