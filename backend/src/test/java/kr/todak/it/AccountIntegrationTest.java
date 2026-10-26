package kr.todak.it;

import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** TC-012 계정: 회원가입 신청 → 승인 → 로그인, 비밀번호 규칙, 재설정 요청, 본인 비밀번호 변경, 내 정보 [REQ-F-12, REQ-N-04] */
class AccountIntegrationTest extends IntegrationTestBase {

    private MvcResult signup(String body) throws Exception {
        return mvc.perform(post("/api/auth/signup").contentType(MediaType.APPLICATION_JSON).content(body)).andReturn();
    }

    private static String body(String id, String pw, String confirm, boolean terms) {
        return "{\"loginId\":\"" + id + "\",\"password\":\"" + pw + "\",\"passwordConfirm\":\"" + confirm + "\",\"name\":\"김농부\","
                + "\"phone\":\"01012345678\",\"email\":\"farm@example.com\",\"requestedRole\":\"FARMER\",\"signupNote\":\"양평 2동\","
                + "\"agreeTerms\":" + terms + ",\"agreePrivacy\":true,\"agreeNotify\":false}";
    }

    private MvcResult doLogin(String id, String pw) throws Exception {
        return mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                .content("{\"loginId\":\"" + id + "\",\"password\":\"" + pw + "\"}")).andReturn();
    }

    @Test
    @DisplayName("가입 신청은 PENDING → 로그인 403 ACCOUNT_PENDING → 관리자 승인(농장 지정) 후 로그인, 지정 농장만 접근")
    void signupApproveLogin() throws Exception {
        MvcResult s = signup(body("kimfarm", "Tomato#2026a", "Tomato#2026a", true));
        assertThat(s.getResponse().getStatus()).isEqualTo(201);
        assertThat(json(s).get("approvalStatus").asText()).isEqualTo("PENDING");
        assertThat(jdbc.queryForObject("SELECT phone FROM TB_USER WHERE login_id='kimfarm'", String.class)).isEqualTo("010-1234-5678");
        assertThat(jdbc.queryForObject("SELECT terms_agreed_at IS NOT NULL FROM TB_USER WHERE login_id='kimfarm'", Integer.class)).isEqualTo(1);

        MvcResult pending = doLogin("kimfarm", "Tomato#2026a");
        assertThat(pending.getResponse().getStatus()).isEqualTo(403);
        assertThat(json(pending).get("code").asText()).isEqualTo("ACCOUNT_PENDING");

        String admin = login("admin", ADMIN_PW);
        int id = jdbc.queryForObject("SELECT user_id FROM TB_USER WHERE login_id='kimfarm'", Integer.class);
        mvc.perform(post("/api/admin/users/" + id + "/approve").header("Authorization", bearer(admin)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"role\":\"FARMER\",\"farmIds\":[]}")).andExpect(status().isBadRequest());
        mvc.perform(post("/api/admin/users/" + id + "/approve").header("Authorization", bearer(admin)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"role\":\"FARMER\",\"farmIds\":[1]}")).andExpect(status().isOk()).andExpect(jsonPath("$.approvalStatus").value("APPROVED"));

        String t = login("kimfarm", "Tomato#2026a");
        mvc.perform(get("/api/farms/1/dashboard").header("Authorization", bearer(t))).andExpect(status().isOk());
        mvc.perform(get("/api/farms/2/dashboard").header("Authorization", bearer(t))).andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("가입 검증: 약한 비밀번호·아이디 포함·확인 불일치·필수 약관 미동의·잘못된 아이디 400, 중복 409, 아이디 확인 API")
    void signupValidation() throws Exception {
        assertThat(json(signup(body("kimfarm", "abcdefgh", "abcdefgh", true))).get("code").asText()).isEqualTo("WEAK_PASSWORD");
        assertThat(json(signup(body("kimfarm", "kimfarm#2026", "kimfarm#2026", true))).get("code").asText()).isEqualTo("WEAK_PASSWORD");
        assertThat(signup(body("kimfarm", "Tomato#2026a", "Tomato#2026b", true)).getResponse().getStatus()).isEqualTo(400);
        assertThat(signup(body("kimfarm", "Tomato#2026a", "Tomato#2026a", false)).getResponse().getStatus()).isEqualTo(400);
        assertThat(signup(body("1bad", "Tomato#2026a", "Tomato#2026a", true)).getResponse().getStatus()).isEqualTo(400);
        assertThat(signup(body("farmer01", "Tomato#2026a", "Tomato#2026a", true)).getResponse().getStatus()).isEqualTo(409);

        mvc.perform(get("/api/auth/check-id?loginId=farmer01")).andExpect(jsonPath("$.available").value(false));
        mvc.perform(get("/api/auth/check-id?loginId=newid_01")).andExpect(jsonPath("$.available").value(true));
        mvc.perform(get("/api/auth/check-id?loginId=AB")).andExpect(jsonPath("$.available").value(false));
    }

    @Test
    @DisplayName("거절된 신청은 403 ACCOUNT_REJECTED")
    void rejected() throws Exception {
        signup(body("kimfarm", "Tomato#2026a", "Tomato#2026a", true));
        int id = jdbc.queryForObject("SELECT user_id FROM TB_USER WHERE login_id='kimfarm'", Integer.class);
        mvc.perform(post("/api/admin/users/" + id + "/reject").header("Authorization", bearer(login("admin", ADMIN_PW)))).andExpect(status().isOk());
        assertThat(json(doLogin("kimfarm", "Tomato#2026a")).get("code").asText()).isEqualTo("ACCOUNT_REJECTED");
    }

    @Test
    @DisplayName("비밀번호 재설정 요청: 일치/불일치/없는 계정 모두 같은 응답, 일치할 때만 관리자 화면에 요청 표시")
    void resetRequest() throws Exception {
        String ok = json(mvc.perform(post("/api/auth/password-reset-request").contentType(MediaType.APPLICATION_JSON)
                .content("{\"loginId\":\"farmer01\",\"name\":\"양평 농가(가상)\",\"phone\":\"01000000001\"}")).andReturn()).get("message").asText();
        String no = json(mvc.perform(post("/api/auth/password-reset-request").contentType(MediaType.APPLICATION_JSON)
                .content("{\"loginId\":\"ghost\",\"name\":\"x\",\"phone\":\"01099999999\"}")).andReturn()).get("message").asText();
        assertThat(ok).isEqualTo(no);
        assertThat(jdbc.queryForObject("SELECT pw_reset_requested_at IS NOT NULL FROM TB_USER WHERE login_id='farmer01'", Integer.class)).isEqualTo(1);
        mvc.perform(post("/api/auth/password-reset-request").contentType(MediaType.APPLICATION_JSON)
                .content("{\"loginId\":\"farmer02\",\"name\":\"틀린 이름\",\"phone\":\"01000000002\"}"));
        assertThat(jdbc.queryForObject("SELECT pw_reset_requested_at IS NULL FROM TB_USER WHERE login_id='farmer02'", Integer.class)).isEqualTo(1);
    }

    @Test
    @DisplayName("관리자 임시 비밀번호 → 로그인 응답 mustChangePassword=true → 본인 변경(현재 비번 확인·규칙·다른 세션 폐기) → 플래그 해제")
    void forcedChange() throws Exception {
        String admin = login("admin", ADMIN_PW);
        mvc.perform(patch("/api/admin/users/2").header("Authorization", bearer(admin)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"newPassword\":\"Temp#2026xy\"}")).andExpect(status().isOk());
        MvcResult l1 = doLogin("farmer01", "Temp#2026xy");
        assertThat(json(l1).get("mustChangePassword").asBoolean()).isTrue();
        String t = json(l1).get("accessToken").asText();
        Cookie other = doLogin("farmer01", "Temp#2026xy").getResponse().getCookie("todak_rt");

        mvc.perform(post("/api/auth/password").header("Authorization", bearer(t)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"currentPassword\":\"wrong\",\"newPassword\":\"Fresh#2026ab\"}")).andExpect(jsonPath("$.code").value("WRONG_PASSWORD"));
        mvc.perform(post("/api/auth/password").header("Authorization", bearer(t)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"currentPassword\":\"Temp#2026xy\",\"newPassword\":\"short\"}")).andExpect(jsonPath("$.code").value("WEAK_PASSWORD"));
        MvcResult ch = mvc.perform(post("/api/auth/password").header("Authorization", bearer(t)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"currentPassword\":\"Temp#2026xy\",\"newPassword\":\"Fresh#2026ab\"}")).andExpect(status().isOk()).andReturn();
        assertThat(json(ch).get("mustChangePassword").asBoolean()).isFalse();
        assertThat(ch.getResponse().getCookie("todak_rt")).isNotNull();
        // 다른 기기 세션은 폐기
        mvc.perform(post("/api/auth/refresh").cookie(other).header("X-TODAK-CSRF", "1")).andExpect(status().isUnauthorized());
        assertThat(json(doLogin("farmer01", "Fresh#2026ab")).get("mustChangePassword").asBoolean()).isFalse();
        // 시드 비밀번호로 되돌림 (다른 테스트용)
        jdbc.update("UPDATE TB_USER SET password_hash=(SELECT h FROM (SELECT password_hash h FROM TB_USER WHERE user_id=3) x) WHERE user_id=2");
    }

    @Test
    @DisplayName("내 정보 조회·수정, 모든 기기 로그아웃")
    void profile() throws Exception {
        MvcResult l = doLogin("farmer01", FARMER_PW);
        String t = json(l).get("accessToken").asText();
        mvc.perform(get("/api/auth/me").header("Authorization", bearer(t))).andExpect(jsonPath("$.lastLoginAt").exists())
                .andExpect(jsonPath("$.farmIds[0]").value(1));
        mvc.perform(patch("/api/auth/me").header("Authorization", bearer(t)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"양평 농가\",\"phone\":\"010-2222-3333\",\"email\":\"a@b.kr\",\"notifyAgreed\":true}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.email").value("a@b.kr"));
        mvc.perform(patch("/api/auth/me").header("Authorization", bearer(t)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"x\",\"phone\":\"12345\"}")).andExpect(status().isBadRequest());
        mvc.perform(post("/api/auth/logout-all").header("Authorization", bearer(t)).header("X-TODAK-CSRF", "1")).andExpect(status().isOk());
        mvc.perform(post("/api/auth/refresh").cookie(l.getResponse().getCookie("todak_rt")).header("X-TODAK-CSRF", "1"))
                .andExpect(status().isUnauthorized());
        jdbc.update("UPDATE TB_USER SET name='양평 농가(가상)', phone='010-0000-0001', email=NULL WHERE user_id=2");
    }
}
