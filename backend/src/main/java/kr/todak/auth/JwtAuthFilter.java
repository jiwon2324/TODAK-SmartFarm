package kr.todak.auth;

import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import kr.todak.common.CurrentUser;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * Authorization: Bearer 헤더의 Access Token을 검증한다.
 * 브라우저 EventSource는 헤더를 못 보내므로 SSE 경로(/api/stream)에서만 ?access_token= 을 허용한다.
 * 만료·위조 토큰은 요청 속성에 사유를 남기고 인증 없이 통과시켜 진입점에서 401로 응답한다.
 */
public class JwtAuthFilter extends OncePerRequestFilter {
    public static final String ATTR_REASON = "todak.auth.reason";
    private final JwtService jwt;

    public JwtAuthFilter(JwtService jwt) {
        this.jwt = jwt;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain) throws ServletException, IOException {
        String token = null;
        String h = req.getHeader("Authorization");
        if (h != null && h.startsWith("Bearer ")) {
            token = h.substring(7);
        } else if (req.getRequestURI().startsWith("/api/stream")) {
            token = req.getParameter("access_token");
        }
        if (token != null) {
            try {
                CurrentUser u = jwt.parse(token);
                var auth = new UsernamePasswordAuthenticationToken(u, null, List.of(new SimpleGrantedAuthority("ROLE_" + u.role())));
                SecurityContextHolder.getContext().setAuthentication(auth);
            } catch (ExpiredJwtException e) {
                req.setAttribute(ATTR_REASON, "TOKEN_EXPIRED");
            } catch (JwtException | IllegalArgumentException e) {
                req.setAttribute(ATTR_REASON, "TOKEN_INVALID");
            }
        }
        chain.doFilter(req, res);
    }
}
