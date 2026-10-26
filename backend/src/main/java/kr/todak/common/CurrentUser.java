package kr.todak.common;

/** JWT에서 꺼낸 인증 사용자. SecurityContext의 principal로 들어간다. */
public record CurrentUser(Integer userId, String loginId, String role) {
    public boolean isAdmin() {
        return "ADMIN".equals(role);
    }
}
