package kr.todak.unit;

import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import kr.todak.auth.JwtService;
import kr.todak.common.CurrentUser;
import kr.todak.config.TodakProperties;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** TC-012 보조: Access Token 발급·검증·위조·만료 */
class JwtServiceTest {
    private static final String SECRET = "unit-test-secret-0123456789abcdef-0123456789";

    private JwtService service(long ttl, String secret) {
        return new JwtService(new TodakProperties(new TodakProperties.Jwt(secret, ttl, 100), new TodakProperties.Cookie(false),
                new TodakProperties.Cors(List.of()), new TodakProperties.Mqtt(false, "", "", "", ""), new TodakProperties.Control(1, 1, 1, 1, 1), new TodakProperties.Retention(1095)));
    }

    @Test
    void issueAndParse() {
        JwtService s = service(60, SECRET);
        CurrentUser u = s.parse(s.issue(new CurrentUser(7, "farmer01", "FARMER")));
        assertThat(u.userId()).isEqualTo(7);
        assertThat(u.role()).isEqualTo("FARMER");
    }

    @Test
    void tamperedTokenRejected() {
        JwtService s = service(60, SECRET);
        String t = s.issue(new CurrentUser(1, "admin", "ADMIN"));
        String tampered = t.substring(0, t.length() - 3) + (t.endsWith("AAA") ? "BBB" : "AAA");
        assertThatThrownBy(() -> s.parse(tampered)).isInstanceOf(JwtException.class);
    }

    @Test
    void otherKeyRejected() {
        String t = service(60, SECRET).issue(new CurrentUser(1, "admin", "ADMIN"));
        assertThatThrownBy(() -> service(60, SECRET + "-other").parse(t)).isInstanceOf(JwtException.class);
    }

    @Test
    void expiredRejected() throws InterruptedException {
        JwtService s = service(1, SECRET);
        String t = s.issue(new CurrentUser(1, "admin", "ADMIN"));
        Thread.sleep(1500);
        assertThatThrownBy(() -> s.parse(t)).isInstanceOf(ExpiredJwtException.class);
    }

    @Test
    void shortSecretRefused() {
        assertThatThrownBy(() -> service(60, "short")).isInstanceOf(IllegalStateException.class);
    }
}
