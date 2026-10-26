package kr.todak.auth;

import kr.todak.common.ApiException;

import java.util.regex.Pattern;

/**
 * 비밀번호·아이디 규칙 (회원가입·비밀번호 변경·관리자 등록 공통). [REQ-F-12, REQ-N-04]
 * 8~64자, 영문·숫자·특수문자를 모두 포함, 아이디를 포함하지 않음, 같은 문자 4번 연속 금지.
 */
public final class PasswordPolicy {
    public static final Pattern LOGIN_ID = Pattern.compile("^[a-z][a-z0-9_]{3,19}$");
    private static final Pattern LETTER = Pattern.compile("[A-Za-z]");
    private static final Pattern DIGIT = Pattern.compile("[0-9]");
    private static final Pattern SPECIAL = Pattern.compile("[^A-Za-z0-9\\s]");
    private static final Pattern REPEAT = Pattern.compile("(.)\\1{3,}");

    private PasswordPolicy() {
    }

    /** 규칙 위반 사유, 통과하면 null */
    public static String violation(String loginId, String pw) {
        if (pw == null || pw.length() < 8 || pw.length() > 64) {
            return "비밀번호는 8~64자여야 합니다";
        }
        if (pw.chars().anyMatch(Character::isWhitespace)) {
            return "비밀번호에 공백을 쓸 수 없습니다";
        }
        if (!LETTER.matcher(pw).find() || !DIGIT.matcher(pw).find() || !SPECIAL.matcher(pw).find()) {
            return "비밀번호는 영문, 숫자, 특수문자를 모두 포함해야 합니다";
        }
        if (loginId != null && !loginId.isBlank() && pw.toLowerCase().contains(loginId.toLowerCase())) {
            return "비밀번호에 아이디를 포함할 수 없습니다";
        }
        if (REPEAT.matcher(pw).find()) {
            return "같은 문자를 4번 이상 연속해서 쓸 수 없습니다";
        }
        return null;
    }

    public static void check(String loginId, String pw) {
        String v = violation(loginId, pw);
        if (v != null) {
            throw new ApiException(org.springframework.http.HttpStatus.BAD_REQUEST, "WEAK_PASSWORD", v);
        }
    }

    public static String loginIdViolation(String loginId) {
        if (loginId == null || !LOGIN_ID.matcher(loginId).matches()) {
            return "아이디는 영문 소문자로 시작하는 4~20자(영문 소문자·숫자·밑줄)여야 합니다";
        }
        return null;
    }
}
