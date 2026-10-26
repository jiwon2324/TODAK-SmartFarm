package kr.todak.auth;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import kr.todak.common.ApiException;
import kr.todak.common.CurrentUser;
import kr.todak.common.FarmAccess;
import kr.todak.config.TodakProperties;
import kr.todak.repo.UserRepository;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseCookie;
import org.springframework.web.bind.annotation.*;

import java.time.Duration;
import java.util.Map;

@Tag(name = "인증", description = "로그인·토큰 갱신·로그아웃 [REQ-F-12, REQ-N-04] [TB_USER, TB_REFRESH_TOKEN]")
@RestController
@RequestMapping("/api/auth")
public class AuthController {
    static final String COOKIE = "todak_rt";
    private final AuthService auth;
    private final JwtService jwt;
    private final FarmAccess access;
    private final UserRepository users;
    private final boolean secureCookie;

    public AuthController(AuthService auth, JwtService jwt, FarmAccess access, UserRepository users, TodakProperties props) {
        this.auth = auth;
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

    @Operation(summary = "내 정보", description = "역할과 접근 가능한 농장 ID 목록")
    @GetMapping("/me")
    public Map<String, Object> me() {
        CurrentUser u = access.user();
        String name = users.findById(u.userId()).map(x -> x.getName()).orElse("");
        return Map.of("userId", u.userId(), "loginId", u.loginId(), "name", name, "role", u.role(), "farmIds", access.allowedFarmIds());
    }

    private Map<String, Object> body(AuthService.Tokens t) {
        String name = users.findById(t.user().userId()).map(x -> x.getName()).orElse("");
        return Map.of("accessToken", t.accessToken(), "tokenType", "Bearer", "expiresIn", jwt.accessTtlSeconds(),
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
