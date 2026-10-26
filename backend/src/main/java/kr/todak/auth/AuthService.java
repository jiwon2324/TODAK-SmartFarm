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
import java.util.Map;
import java.util.UUID;

/**
 * 로그인·토큰 갱신·로그아웃. [REQ-F-12, REQ-N-04]
 * Refresh Token은 32바이트 난수이고 DB에는 SHA-256 해시만 저장한다.
 * 갱신할 때마다 새 토큰으로 회전하며, 이미 회전된(폐기된) 토큰이 다시 오면 탈취로 보고 같은 계열 전체를 폐기한다.
 */
@Service
public class AuthService {
    public record Tokens(String accessToken, String refreshToken, CurrentUser user, boolean mustChangePassword) {
    }

    public record SignupRequest(String loginId, String password, String name, String phone, String email,
                                String requestedRole, String signupNote, boolean agreeTerms, boolean agreePrivacy, boolean agreeNotify) {
    }

    /** 공통 응답으로 계정 존재 여부를 숨기는 비밀번호 재설정 요청 결과 */
    public static final String RESET_ACCEPTED = "입력한 정보가 등록된 계정과 일치하면 관리자에게 비밀번호 초기화 요청이 전달됩니다. 관리자가 임시 비밀번호를 알려 드립니다.";

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

    /**
     * 로그인. 계정 존재 여부가 드러나지 않도록 비밀번호를 확인한 뒤에만 승인 대기·거절·비활성 상태를 알려 준다.
     * 실패할 때마다 남은 시도 횟수를 알려 주고 5회째에 10분 잠근다.
     */
    @Transactional(noRollbackFor = ApiException.class)
    public Tokens login(String loginId, String password) {
        User u = users.findByLoginId(loginId == null ? "" : loginId.trim()).orElse(null);
        LocalDateTime now = LocalDateTime.now();
        if (u == null) {
            throw invalid(null);
        }
        if (u.getLockedUntil() != null && u.getLockedUntil().isAfter(now)) {
            long min = Math.max(1, java.time.Duration.between(now, u.getLockedUntil()).toMinutes() + 1);
            throw new ApiException(HttpStatus.LOCKED, "ACCOUNT_LOCKED", "로그인에 5번 실패해 계정이 잠겼습니다. 약 " + min + "분 뒤에 다시 시도하세요.");
        }
        if (!encoder.matches(password, u.getPasswordHash())) {
            int fails = u.getFailedCount() + 1;
            u.setFailedCount((byte) Math.min(fails, 100));
            if (fails >= MAX_FAIL) {
                u.setLockedUntil(now.plusMinutes(LOCK_MINUTES));
                u.setFailedCount((byte) 0);
                throw new ApiException(HttpStatus.LOCKED, "ACCOUNT_LOCKED", "로그인에 5번 실패해 계정이 10분 동안 잠겼습니다.");
            }
            throw invalid(null);
        }
        if ("PENDING".equals(u.getApprovalStatus())) {
            throw new ApiException(HttpStatus.FORBIDDEN, "ACCOUNT_PENDING", "가입 신청이 접수되어 관리자 승인을 기다리고 있습니다. 승인 후 로그인할 수 있습니다.");
        }
        if ("REJECTED".equals(u.getApprovalStatus())) {
            throw new ApiException(HttpStatus.FORBIDDEN, "ACCOUNT_REJECTED", "가입 신청이 승인되지 않았습니다. 관리자에게 문의하세요.");
        }
        if (!Boolean.TRUE.equals(u.getIsActive())) {
            throw new ApiException(HttpStatus.FORBIDDEN, "ACCOUNT_DISABLED", "사용이 중지된 계정입니다. 관리자에게 문의하세요.");
        }
        u.setFailedCount((byte) 0);
        u.setLockedUntil(null);
        u.setLastLoginAt(now);
        CurrentUser cu = new CurrentUser(u.getUserId(), u.getLoginId(), u.getRole());
        return new Tokens(jwt.issue(cu), newRefresh(u.getUserId(), UUID.randomUUID().toString()), cu, Boolean.TRUE.equals(u.getMustChangePw()));
    }

    /** 회원가입 신청. 바로 쓸 수 없고 관리자가 승인하며 농장 접근 권한을 줘야 한다. */
    @Transactional
    public User signup(SignupRequest r) {
        String idErr = PasswordPolicy.loginIdViolation(r.loginId());
        if (idErr != null) {
            throw ApiException.badRequest(idErr);
        }
        if (users.findByLoginId(r.loginId()).isPresent()) {
            throw new ApiException(HttpStatus.CONFLICT, "DUPLICATE_LOGIN", "이미 사용 중인 아이디입니다");
        }
        PasswordPolicy.check(r.loginId(), r.password());
        if (!r.agreeTerms() || !r.agreePrivacy()) {
            throw ApiException.badRequest("필수 약관(이용약관, 개인정보 수집·이용)에 동의해야 가입할 수 있습니다");
        }
        if (r.name() == null || r.name().isBlank() || r.name().length() > 30) {
            throw ApiException.badRequest("이름을 1~30자로 입력하세요");
        }
        if (r.phone() == null || !r.phone().matches("01[016789]-?\\d{3,4}-?\\d{4}")) {
            throw ApiException.badRequest("휴대폰 번호 형식이 올바르지 않습니다 (예: 010-1234-5678)");
        }
        if (r.email() != null && !r.email().isBlank() && !r.email().matches("[^@\\s]+@[^@\\s]+\\.[^@\\s]+")) {
            throw ApiException.badRequest("이메일 형식이 올바르지 않습니다");
        }
        String role = "VIEWER".equals(r.requestedRole()) ? "VIEWER" : "FARMER";
        LocalDateTime now = LocalDateTime.now();
        User u = new User();
        u.setLoginId(r.loginId());
        u.setPasswordHash(encoder.encode(r.password()));
        u.setName(r.name().trim());
        u.setPhone(r.phone().replaceAll("(\\d{3})-?(\\d{3,4})-?(\\d{4})", "$1-$2-$3"));
        u.setEmail(r.email() == null || r.email().isBlank() ? null : r.email().trim());
        u.setRole(role);
        u.setRequestedRole(role);
        u.setApprovalStatus("PENDING");
        u.setSignupNote(r.signupNote() == null ? null : r.signupNote().substring(0, Math.min(300, r.signupNote().length())));
        u.setTermsAgreedAt(now);
        u.setPrivacyAgreedAt(now);
        u.setNotifyAgreed(r.agreeNotify());
        u.setPwChangedAt(now);
        return users.save(u);
    }

    public Map<String, Object> checkLoginId(String loginId) {
        String err = PasswordPolicy.loginIdViolation(loginId);
        if (err != null) {
            return Map.of("available", false, "message", err);
        }
        boolean taken = users.findByLoginId(loginId).isPresent();
        return Map.of("available", !taken, "message", taken ? "이미 사용 중인 아이디입니다" : "사용할 수 있는 아이디입니다");
    }

    /** 이메일·문자 발송 수단이 없으므로 관리자에게 초기화 요청을 남긴다. 응답은 항상 같다. */
    @Transactional
    public void requestPasswordReset(String loginId, String name, String phone) {
        users.findByLoginId(loginId == null ? "" : loginId.trim())
                .filter(u -> u.getName().equals(name == null ? "" : name.trim()))
                .filter(u -> u.getPhone() != null && digits(u.getPhone()).equals(digits(phone)))
                .ifPresent(u -> u.setPwResetRequestedAt(LocalDateTime.now()));
    }

    /** 본인 비밀번호 변경. 다른 기기 세션은 모두 끊고 현재 기기에는 새 토큰을 준다. */
    @Transactional(noRollbackFor = ApiException.class)
    public Tokens changePassword(Integer userId, String current, String next) {
        User u = users.findById(userId).orElseThrow(() -> ApiException.notFound("사용자"));
        if (!encoder.matches(current == null ? "" : current, u.getPasswordHash())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "WRONG_PASSWORD", "현재 비밀번호가 맞지 않습니다");
        }
        if (encoder.matches(next == null ? "" : next, u.getPasswordHash())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "SAME_PASSWORD", "새 비밀번호가 지금 비밀번호와 같습니다");
        }
        PasswordPolicy.check(u.getLoginId(), next);
        u.setPasswordHash(encoder.encode(next));
        u.setMustChangePw(false);
        u.setPwChangedAt(LocalDateTime.now());
        u.setPwResetRequestedAt(null);
        revokeAll(userId);
        CurrentUser cu = new CurrentUser(u.getUserId(), u.getLoginId(), u.getRole());
        return new Tokens(jwt.issue(cu), newRefresh(u.getUserId(), UUID.randomUUID().toString()), cu, false);
    }

    private static String digits(String s) {
        return s == null ? "" : s.replaceAll("\\D", "");
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
        if (!Boolean.TRUE.equals(u.getIsActive()) || !"APPROVED".equals(u.getApprovalStatus())) {
            revokeFamily(rt.getFamilyId(), now);
            throw new ApiException(HttpStatus.UNAUTHORIZED, "ACCOUNT_DISABLED", "비활성 계정");
        }
        String next = newRefresh(u.getUserId(), rt.getFamilyId());
        rt.setRevokedAt(now);
        rt.setReplacedBy(refreshTokens.findByTokenHash(sha256(next)).map(RefreshToken::getTokenId).orElse(null));
        CurrentUser cu = new CurrentUser(u.getUserId(), u.getLoginId(), u.getRole());
        return new Tokens(jwt.issue(cu), next, cu, Boolean.TRUE.equals(u.getMustChangePw()));
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

    private ApiException invalid(Integer remaining) {
        // 남은 횟수를 알려 주면 없는 아이디와 구분돼 계정 존재가 드러나므로 일반 안내만 한다
        return new ApiException(HttpStatus.UNAUTHORIZED, "UNAUTHORIZED", "아이디 또는 비밀번호가 올바르지 않습니다. 5번 연속 틀리면 10분 동안 잠깁니다.");
    }

    public long refreshTtlSeconds() {
        return refreshTtl;
    }
}
