package kr.todak.auth;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import kr.todak.domain.User;
import org.springframework.transaction.annotation.Transactional;
import java.util.LinkedHashMap;
import kr.todak.common.ApiException;
import kr.todak.common.CurrentUser;
import kr.todak.common.FarmAccess;
import kr.todak.config.TodakProperties;
import kr.todak.repo.UserRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseCookie;
import org.springframework.web.bind.annotation.*;

import java.time.Duration;
import java.util.Map;

@Tag(name = "인증", description = "로그인·회원가입·토큰 갱신·로그아웃·내 정보·비밀번호 [REQ-F-12, REQ-N-04] [TB_USER, TB_REFRESH_TOKEN]")
@RestController
@RequestMapping("/api/auth")
public class AuthController {
    static final String COOKIE = "todak_rt";
    private final AuthService auth;
    private final JwtService jwt;
    private final FarmAccess access;
    private final UserRepository users;
    private final boolean secureCookie;
    /** 로그인 없이 둘러보기에 쓸 조회 전용(VIEWER) 계정. 비어 있으면 기능을 끈다 */
    private final String demoLoginId;

    public AuthController(AuthService auth, JwtService jwt, FarmAccess access, UserRepository users, TodakProperties props,
                          @Value("${DEMO_LOGIN_ID:}") String demoLoginId) {
        this.auth = auth;
        this.demoLoginId = demoLoginId == null ? "" : demoLoginId.trim();
        this.jwt = jwt;
        this.access = access;
        this.users = users;
        this.secureCookie = props.cookie().secure();
    }

    public record LoginRequest(@NotBlank String loginId, @NotBlank String password) {
    }

    @Operation(summary = "로그인", description = "200: accessToken(본문, 15분) + Refresh Token(HttpOnly 쿠키 todak_rt, 14일). 401 UNAUTHORIZED, 423 ACCOUNT_LOCKED")
    @PostMapping("/login")
    public Map<String, Object> login(@Valid @RequestBody LoginRequest req, HttpServletResponse res) {
        AuthService.Tokens t = auth.login(req.loginId(), req.password());
        setCookie(res, t.refreshToken(), auth.refreshTtlSeconds());
        return body(t);
    }

    @Operation(summary = "로그인 없이 둘러보기 사용 여부", description = "DEMO_LOGIN_ID 환경변수가 있으면 enabled=true")
    @GetMapping("/demo")
    public Map<String, Object> demoEnabled() {
        return Map.of("enabled", !demoLoginId.isEmpty());
    }

    @Operation(summary = "로그인 없이 둘러보기", description = "조회 전용(VIEWER) 계정으로 바로 로그인한다. 장치 제어·기준값 변경·관리자 화면은 막혀 있다. DEMO_LOGIN_ID가 없으면 404")
    @PostMapping("/demo")
    public Map<String, Object> demo(HttpServletResponse res) {
        if (demoLoginId.isEmpty()) {
            throw new ApiException(HttpStatus.NOT_FOUND, "DEMO_DISABLED", "둘러보기 기능이 꺼져 있습니다.");
        }
        AuthService.Tokens t = auth.demoLogin(demoLoginId);
        setCookie(res, t.refreshToken(), auth.refreshTtlSeconds());
        return body(t);
    }

    @Operation(summary = "Access Token 갱신", description = "쿠키 todak_rt와 헤더 X-TODAK-CSRF: 1 필요. Refresh Token을 회전해 새 쿠키를 내려준다. 재사용된 토큰이면 401 REFRESH_REUSED")
    @PostMapping("/refresh")
    public Map<String, Object> refresh(@CookieValue(name = COOKIE, required = false) String rt,
                                       @RequestHeader(name = "X-TODAK-CSRF", required = false) String csrf, HttpServletResponse res) {
        requireCsrf(csrf);
        AuthService.Tokens t = auth.refresh(rt);
        setCookie(res, t.refreshToken(), auth.refreshTtlSeconds());
        return body(t);
    }

    @Operation(summary = "로그아웃", description = "Refresh Token 계열 전체 폐기 + 쿠키 삭제. 헤더 X-TODAK-CSRF: 1 필요")
    @PostMapping("/logout")
    public Map<String, Object> logout(@CookieValue(name = COOKIE, required = false) String rt,
                                      @RequestHeader(name = "X-TODAK-CSRF", required = false) String csrf, HttpServletResponse res) {
        requireCsrf(csrf);
        auth.logout(rt);
        setCookie(res, "", 0);
        return Map.of("result", "OK");
    }

    @Operation(summary = "내 정보", description = "역할, 접근 가능한 농장 ID, 연락처, 최근 로그인, 비밀번호 변경 필요 여부")
    @GetMapping("/me")
    public Map<String, Object> me() {
        CurrentUser cu = access.user();
        User u = users.findById(cu.userId()).orElseThrow(() -> ApiException.notFound("사용자"));
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("userId", u.getUserId());
        m.put("loginId", u.getLoginId());
        m.put("name", u.getName());
        m.put("role", u.getRole());
        m.put("farmIds", access.allowedFarmIds());
        m.put("phone", u.getPhone());
        m.put("email", u.getEmail());
        m.put("notifyAgreed", u.getNotifyAgreed());
        m.put("mustChangePassword", u.getMustChangePw());
        m.put("lastLoginAt", u.getLastLoginAt());
        m.put("pwChangedAt", u.getPwChangedAt());
        m.put("createdAt", u.getCreatedAt());
        return m;
    }

    public record ProfileUpdate(@NotBlank @Size(max = 30) String name, @Pattern(regexp = "01[016789]-?\\d{3,4}-?\\d{4}") String phone,
                                @Email @Size(max = 100) String email, Boolean notifyAgreed) {
    }

    @Operation(summary = "내 정보 수정", description = "이름·휴대폰·이메일·알림 수신 동의. 역할·농장 권한은 관리자만 바꾼다")
    @PatchMapping("/me")
    @Transactional
    public Map<String, Object> updateMe(@Valid @RequestBody ProfileUpdate r) {
        User u = users.findById(access.user().userId()).orElseThrow(() -> ApiException.notFound("사용자"));
        u.setName(r.name().trim());
        u.setPhone(r.phone());
        u.setEmail(r.email() == null || r.email().isBlank() ? null : r.email());
        if (r.notifyAgreed() != null) {
            u.setNotifyAgreed(r.notifyAgreed());
        }
        users.save(u);
        return me();
    }

    public record PasswordChange(@NotBlank String currentPassword, @NotBlank String newPassword) {
    }

    @Operation(summary = "비밀번호 변경", description = "현재 비밀번호 확인 → 규칙 검사(8~64자, 영문·숫자·특수문자) → 저장. 다른 기기의 로그인은 모두 끊기고 이 기기에는 새 토큰을 준다. 400 WRONG_PASSWORD·WEAK_PASSWORD·SAME_PASSWORD")
    @PostMapping("/password")
    public Map<String, Object> changePassword(@Valid @RequestBody PasswordChange r, HttpServletResponse res) {
        AuthService.Tokens t = auth.changePassword(access.user().userId(), r.currentPassword(), r.newPassword());
        setCookie(res, t.refreshToken(), auth.refreshTtlSeconds());
        return body(t);
    }

    @Operation(summary = "모든 기기에서 로그아웃", description = "이 계정의 Refresh Token을 전부 폐기한다. 헤더 X-TODAK-CSRF: 1 필요")
    @PostMapping("/logout-all")
    public Map<String, Object> logoutAll(@RequestHeader(name = "X-TODAK-CSRF", required = false) String csrf, HttpServletResponse res) {
        requireCsrf(csrf);
        auth.revokeAll(access.user().userId());
        setCookie(res, "", 0);
        return Map.of("result", "OK");
    }

    public record SignupBody(@NotBlank String loginId, @NotBlank String password, @NotBlank String passwordConfirm, @NotBlank String name,
                             @NotBlank String phone, String email, @Pattern(regexp = "FARMER|VIEWER") String requestedRole,
                             @Size(max = 300) String signupNote, boolean agreeTerms, boolean agreePrivacy, boolean agreeNotify) {
    }

    @Operation(summary = "회원가입 신청", description = """
            공개 API. 가입 즉시 사용할 수 없고 관리자 승인(역할·농장 권한 지정) 후 로그인할 수 있다.
            201 {loginId, approvalStatus: PENDING}. 400 VALIDATION_ERROR·WEAK_PASSWORD, 409 DUPLICATE_LOGIN [REQ-F-12] [TB_USER]""")
    @PostMapping("/signup")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> signup(@Valid @RequestBody SignupBody r) {
        if (!r.password().equals(r.passwordConfirm())) {
            throw ApiException.badRequest("비밀번호 확인이 일치하지 않습니다");
        }
        User u = auth.signup(new AuthService.SignupRequest(r.loginId(), r.password(), r.name(), r.phone(), r.email(),
                r.requestedRole(), r.signupNote(), r.agreeTerms(), r.agreePrivacy(), r.agreeNotify()));
        return Map.of("loginId", u.getLoginId(), "approvalStatus", u.getApprovalStatus());
    }

    @Operation(summary = "아이디 사용 가능 여부", description = "공개 API. {available, message}")
    @GetMapping("/check-id")
    public Map<String, Object> checkId(@RequestParam String loginId) {
        return auth.checkLoginId(loginId);
    }

    public record ResetBody(@NotBlank String loginId, @NotBlank String name, @NotBlank String phone) {
    }

    @Operation(summary = "비밀번호 초기화 요청", description = "공개 API. 아이디·이름·휴대폰이 일치하면 관리자 화면에 요청이 표시된다. 계정 존재 여부를 숨기려고 결과와 상관없이 같은 응답을 준다")
    @PostMapping("/password-reset-request")
    public Map<String, Object> resetRequest(@Valid @RequestBody ResetBody r) {
        auth.requestPasswordReset(r.loginId(), r.name(), r.phone());
        return Map.of("message", AuthService.RESET_ACCEPTED);
    }

    private Map<String, Object> body(AuthService.Tokens t) {
        String name = users.findById(t.user().userId()).map(x -> x.getName()).orElse("");
        return Map.of("accessToken", t.accessToken(), "tokenType", "Bearer", "expiresIn", jwt.accessTtlSeconds(), "mustChangePassword", t.mustChangePassword(),
                "user", Map.of("userId", t.user().userId(), "loginId", t.user().loginId(), "name", name, "role", t.user().role()));
    }

    private void requireCsrf(String csrf) {
        if (!"1".equals(csrf)) {
            throw new ApiException(HttpStatus.FORBIDDEN, "CSRF_HEADER_REQUIRED", "X-TODAK-CSRF 헤더가 필요합니다");
        }
    }

    private void setCookie(HttpServletResponse res, String value, long maxAge) {
        ResponseCookie c = ResponseCookie.from(COOKIE, value).httpOnly(true).secure(secureCookie).sameSite("Strict")
                .path("/api/auth").maxAge(Duration.ofSeconds(maxAge)).build();
        res.addHeader(HttpHeaders.SET_COOKIE, c.toString());
    }
}
