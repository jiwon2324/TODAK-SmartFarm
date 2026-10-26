package kr.todak.control;

/**
 * 히스테리시스 판단 (순수 함수, 단위 테스트 대상). [REQ-F-02~04]
 * GE 규칙: 값 ≥ on → 활성, 값 ≤ off → 비활성, 그 사이 → 현 상태 유지
 * LE 규칙: 값 ≤ on → 활성, 값 ≥ off → 비활성, 그 사이 → 현 상태 유지
 */
public final class RuleDecision {
    public enum Want { ACTIVATE, DEACTIVATE, HOLD }

    private RuleDecision() {
    }

    public static Want decide(String op, double value, double on, double off) {
        if ("GE".equals(op)) {
            if (value >= on) {
                return Want.ACTIVATE;
            }
            if (value <= off) {
                return Want.DEACTIVATE;
            }
            return Want.HOLD;
        }
        if ("LE".equals(op)) {
            if (value <= on) {
                return Want.ACTIVATE;
            }
            if (value >= off) {
                return Want.DEACTIVATE;
            }
            return Want.HOLD;
        }
        throw new IllegalArgumentException("compare_op는 GE 또는 LE: " + op);
    }

    /** 여러 센서 중 보수적인 값: GE(고온 등)는 최댓값, LE(저온 등)는 최솟값 */
    public static double representative(String op, java.util.List<Double> values) {
        return "GE".equals(op) ? values.stream().mapToDouble(Double::doubleValue).max().orElseThrow()
                : values.stream().mapToDouble(Double::doubleValue).min().orElseThrow();
    }
}
