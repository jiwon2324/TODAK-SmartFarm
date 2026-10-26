package kr.todak.auth;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import kr.todak.common.CurrentUser;
import kr.todak.config.TodakProperties;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;

/** Access Token(HS256) 발급·검증. Refresh Token은 서명 토큰이 아닌 난수이며 AuthService가 관리한다. */
@Service
public class JwtService {
    private final SecretKey key;
    private final long accessTtl;

    public JwtService(TodakProperties props) {
        String secret = props.jwt().secret();
        if (secret == null || secret.getBytes(StandardCharsets.UTF_8).length < 32) {
            throw new IllegalStateException("JWT_SECRET 환경 변수는 32바이트 이상이어야 합니다");
        }
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.accessTtl = props.jwt().accessTtlSeconds();
    }

    public String issue(CurrentUser u) {
        Instant now = Instant.now();
        return Jwts.builder()
                .subject(String.valueOf(u.userId()))
                .claim("login", u.loginId())
                .claim("role", u.role())
                .issuer("todak")
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(accessTtl)))
                .signWith(key)
                .compact();
    }

    /** 서명·만료·발급자 검증. 실패하면 JwtException. */
    public CurrentUser parse(String token) throws JwtException {
        Claims c = Jwts.parser().verifyWith(key).requireIssuer("todak").build().parseSignedClaims(token).getPayload();
        return new CurrentUser(Integer.valueOf(c.getSubject()), c.get("login", String.class), c.get("role", String.class));
    }

    public long accessTtlSeconds() {
        return accessTtl;
    }
}
