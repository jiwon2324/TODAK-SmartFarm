package kr.todak.auth;

import kr.todak.common.ApiException;
import kr.todak.common.CurrentUser;
import kr.todak.config.TodakProperties;
import kr.todak.domain.RefreshToken;
import kr.todak.domain.User;
import kr.todak.repo.RefreshTokenRepository;
import kr.todak.repo.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.LocalDateTime;
import java.util.Base64;
import java.util.HexFormat;
import java.util.UUID;

/**
 * 로그인·토큰 갱신·로그아웃. [REQ-F-12, REQ-N-04]
 * Refresh Token은 32바이트 난수이고 DB에는 SHA-256 해시만 저장한다.
 * 갱신할 때마다 새 토큰으로 회전하며, 이미 회전된(폐기된) 토큰이 다시 오면 탈취로 보고 같은 계열 전체를 폐기한다.
 */
@Service
public class AuthService {
    public record Tokens(String accessToken, String refreshToken, CurrentUser user) {
    }

    private static final int MAX_FAIL = 5;
    private static final int LOCK_MINUTES = 10;
    private final SecureRandom random = new SecureRandom();
    private final UserRepository users;
    private final RefreshTokenRepository refreshTokens;
    private final PasswordEncoder encoder;
    private final JwtService jwt;
    private final long refreshTtl;

    public AuthService(UserRepository users, RefreshTokenRepository refreshTokens, PasswordEncoder encoder, JwtService jwt, TodakProperties props) {
        this.users = users;
        this.refreshTokens = refreshTokens;
        this.encoder = encoder;
        this.jwt = jwt;
        this.refreshTtl = props.jwt().refreshTtlSeconds();
    }

    @Transactional(noRollbackFor = ApiException.class)
    public Tokens login(String loginId, String password) {
        User u = users.findByLoginId(loginId).orElse(null);
        LocalDateTime now = LocalDateTime.now();
        if (u == null || !Boolean.TRUE.equals(u.getIsActive())) {
            throw invalid();
        }
        if (u.getLockedUntil() != null && u.getLockedUntil().isAfter(now)) {
            throw new ApiException(HttpStatus.LOCKED, "ACCOUNT_LOCKED", "로그인 5회 실패로 10분간 잠겼습니다");
        }
        if (!encoder.matches(password, u.getPasswordHash())) {
            int fails = u.getFailedCount() + 1;
            u.setFailedCount((byte) Math.min(fails, 100));
            if (fails >= MAX_FAIL) {
                u.setLockedUntil(now.plusMinutes(LOCK_MINUTES));
                u.setFailedCount((byte) 0);
            }
            throw invalid();
        }
        u.setFailedCount((byte) 0);
        u.setLockedUntil(null);
        CurrentUser cu = new CurrentUser(u.getUserId(), u.getLoginId(), u.getRole());
        return new Tokens(jwt.issue(cu), newRefresh(u.getUserId(), UUID.randomUUID().toString()), cu);
    }

    @Transactional(noRollbackFor = ApiException.class)
    public Tokens refresh(String rawRefresh) {
        if (rawRefresh == null || rawRefresh.isBlank()) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "REFRESH_MISSING", "Refresh Token이 없습니다");
        }
        RefreshToken rt = refreshTokens.findByTokenHash(sha256(rawRefresh))
                .orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "REFRESH_INVALID", "유효하지 않은 Refresh Token"));
        LocalDateTime now = LocalDateTime.now();
        if (rt.getRevokedAt() != null) {
            revokeFamily(rt.getFamilyId(), now);
            throw new ApiException(HttpStatus.UNAUTHORIZED, "REFRESH_REUSED", "재사용된 Refresh Token — 다시 로그인하세요");
        }
        if (rt.getExpiresAt().isBefore(now)) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "REFRESH_EXPIRED", "Refresh Token 만료");
        }
        User u = users.findById(rt.getUserId()).orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "REFRESH_INVALID", "사용자 없음"));
        if (!Boolean.TRUE.equals(u.getIsActive())) {
            revokeFamily(rt.getFamilyId(), now);
            throw new ApiException(HttpStatus.UNAUTHORIZED, "ACCOUNT_DISABLED", "비활성 계정");
        }
        String next = newRefresh(u.getUserId(), rt.getFamilyId());
        rt.setRevokedAt(now);
        rt.setReplacedBy(refreshTokens.findByTokenHash(sha256(next)).map(RefreshToken::getTokenId).orElse(null));
        CurrentUser cu = new CurrentUser(u.getUserId(), u.getLoginId(), u.getRole());
        return new Tokens(jwt.issue(cu), next, cu);
    }

    @Transactional
    public void logout(String rawRefresh) {
        if (rawRefresh == null) {
            return;
        }
        refreshTokens.findByTokenHash(sha256(rawRefresh)).ifPresent(rt -> revokeFamily(rt.getFamilyId(), LocalDateTime.now()));
    }

    /** 사용자 비활성화·비밀번호 변경 시 모든 세션 폐기 */
    @Transactional
    public void revokeAll(Integer userId) {
        LocalDateTime now = LocalDateTime.now();
        refreshTokens.findByUserIdAndRevokedAtIsNull(userId).forEach(t -> t.setRevokedAt(now));
    }

    private void revokeFamily(String familyId, LocalDateTime now) {
        refreshTokens.findByFamilyIdAndRevokedAtIsNull(familyId).forEach(t -> t.setRevokedAt(now));
    }

    private String newRefresh(Integer userId, String familyId) {
        byte[] b = new byte[32];
        random.nextBytes(b);
        String raw = Base64.getUrlEncoder().withoutPadding().encodeToString(b);
        RefreshToken rt = new RefreshToken();
        rt.setUserId(userId);
        rt.setTokenHash(sha256(raw));
        rt.setFamilyId(familyId);
        rt.setExpiresAt(LocalDateTime.now().plusSeconds(refreshTtl));
        refreshTokens.saveAndFlush(rt);
        return raw;
    }

    static String sha256(String s) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    private ApiException invalid() {
        return new ApiException(HttpStatus.UNAUTHORIZED, "UNAUTHORIZED", "아이디 또는 비밀번호가 올바르지 않습니다");
    }

    public long refreshTtlSeconds() {
        return refreshTtl;
    }
}
