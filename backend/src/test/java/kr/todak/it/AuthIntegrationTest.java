package kr.todak.it;

import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** TC-012 · REQ-F-12 · REQ-N-04: 로그인, 잠금, Refresh Token 회전·재사용 탐지, 로그아웃, CSRF 헤더 */
class AuthIntegrationTest extends IntegrationTestBase {

    private MvcResult doLogin(String id, String pw) throws Exception {
        return mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                .content("{\"loginId\":\"" + id + "\",\"password\":\"" + pw + "\"}")).andReturn();
    }

    @Test
    @DisplayName("로그인 성공: Access Token + HttpOnly·SameSite=Strict Refresh 쿠키")
    void loginOk() throws Exception {
        MvcResult r = doLogin("farmer01", FARMER_PW);
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(json(r).get("accessToken").asText()).isNotBlank();
        String setCookie = r.getResponse().getHeader("Set-Cookie");
        assertThat(setCookie).contains("todak_rt=").contains("HttpOnly").contains("SameSite=Strict").contains("Path=/api/auth");
        Integer stored = jdbc.queryForObject("SELECT COUNT(*) FROM TB_REFRESH_TOKEN WHERE user_id = 2", Integer.class);
        assertThat(stored).isEqualTo(1);
    }

    @Test
    @DisplayName("비밀번호 해시는 BCrypt로 저장된다")
    void passwordHashed() {
        String hash = jdbc.queryForObject("SELECT password_hash FROM TB_USER WHERE login_id='farmer01'", String.class);
        assertThat(hash).startsWith("$2a$10$").doesNotContain(FARMER_PW);
    }

    @Test
    @DisplayName("틀린 비밀번호 401(없는 아이디와 같은 메시지), 5번째 실패에 423 잠금, 잠금 중엔 맞는 비밀번호도 423")
    void lockAfterFiveFailures() throws Exception {
        String unknown = json(doLogin("no_such_user", "wrong-pw")).get("message").asText();
        for (int i = 0; i < 4; i++) {
            MvcResult f = doLogin("farmer02", "wrong-pw");
            assertThat(f.getResponse().getStatus()).isEqualTo(401);
            assertThat(json(f).get("message").asText()).isEqualTo(unknown);
        }
        assertThat(doLogin("farmer02", "wrong-pw").getResponse().getStatus()).isEqualTo(423);
        MvcResult r = doLogin("farmer02", FARMER_PW);
        assertThat(r.getResponse().getStatus()).isEqualTo(423);
        assertThat(json(r).get("code").asText()).isEqualTo("ACCOUNT_LOCKED");
    }

    @Test
    @DisplayName("Refresh: CSRF 헤더 없으면 403, 회전 후 이전 토큰 재사용 시 401 REFRESH_REUSED + 계열 폐기")
    void refreshRotationAndReuse() throws Exception {
        MvcResult login = doLogin("admin", ADMIN_PW);
        Cookie rt1 = login.getResponse().getCookie("todak_rt");

        mvc.perform(post("/api/auth/refresh").cookie(rt1)).andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("CSRF_HEADER_REQUIRED"));

        MvcResult r2 = mvc.perform(post("/api/auth/refresh").cookie(rt1).header("X-TODAK-CSRF", "1")).andExpect(status().isOk()).andReturn();
        Cookie rt2 = r2.getResponse().getCookie("todak_rt");
        assertThat(rt2.getValue()).isNotEqualTo(rt1.getValue());

        mvc.perform(post("/api/auth/refresh").cookie(rt1).header("X-TODAK-CSRF", "1")).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("REFRESH_REUSED"));
        // 재사용 탐지로 같은 계열의 최신 토큰도 폐기됨
        mvc.perform(post("/api/auth/refresh").cookie(rt2).header("X-TODAK-CSRF", "1")).andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("로그아웃하면 Refresh Token이 무효화된다")
    void logoutRevokes() throws Exception {
        Cookie rt = doLogin("farmer01", FARMER_PW).getResponse().getCookie("todak_rt");
        mvc.perform(post("/api/auth/logout").cookie(rt).header("X-TODAK-CSRF", "1")).andExpect(status().isOk());
        mvc.perform(post("/api/auth/refresh").cookie(rt).header("X-TODAK-CSRF", "1")).andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("토큰 없음 401 UNAUTHORIZED, 위조 토큰 401 TOKEN_INVALID")
    void missingAndInvalidToken() throws Exception {
        mvc.perform(get("/api/farms")).andExpect(status().isUnauthorized()).andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
        mvc.perform(get("/api/farms").header("Authorization", "Bearer abc.def.ghi")).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("TOKEN_INVALID"));
    }

    @Test
    @DisplayName("비활성 계정은 로그인 불가: 비밀번호가 맞으면 403 ACCOUNT_DISABLED, 틀리면 일반 401")
    void inactiveUser() throws Exception {
        jdbc.update("UPDATE TB_USER SET is_active=0 WHERE login_id='farmer02'");
        MvcResult r = doLogin("farmer02", FARMER_PW);
        assertThat(r.getResponse().getStatus()).isEqualTo(403);
        assertThat(json(r).get("code").asText()).isEqualTo("ACCOUNT_DISABLED");
        assertThat(doLogin("farmer02", "wrong-pw").getResponse().getStatus()).isEqualTo(401);
    }
}
