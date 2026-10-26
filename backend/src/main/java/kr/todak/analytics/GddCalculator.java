package kr.todak.analytics;

import java.util.List;

/**
 * 유효적산온도 계산 (순수 함수, 단위 테스트 대상). 개발 계획서 알고리즘 5-1. [REQ-F-14]
 * GDD = max(0, min(Tavg, Tupper) − Tbase)
 * 내부(HOURLY): 유효 시간 평균들의 평균, 외부(MAXMIN): (최고+최저)/2
 * 결측: 유효 시간 < 20시간(80%)이면 불완전 표시, 0시간이면 GDD 없음
 */
public final class GddCalculator {
    public record Day(Double tavg, Double gdd, double coveragePct, boolean complete) {
    }

    private GddCalculator() {
    }

    public static double gdd(double tavg, double base, double upper) {
        return Math.max(0.0, Math.min(tavg, upper) - base);
    }

    public static Day fromHourly(List<Double> hourlyAverages, double base, double upper) {
        int n = hourlyAverages.size();
        double coverage = Math.min(100.0, n / 24.0 * 100.0);
        if (n == 0) {
            return new Day(null, null, 0.0, false);
        }
        double tavg = hourlyAverages.stream().mapToDouble(Double::doubleValue).average().orElseThrow();
        return new Day(round(tavg, 1), round(gdd(tavg, base, upper), 2), round(coverage, 1), coverage >= 80.0);
    }

    public static Day fromMaxMin(Double tmax, Double tmin, Double tavgReported, double base, double upper) {
        if (tmax != null && tmin != null) {
            double tavg = (tmax + tmin) / 2.0;
            return new Day(round(tavg, 1), round(gdd(tavg, base, upper), 2), 100.0, true);
        }
        if (tavgReported != null) {
            return new Day(tavgReported, round(gdd(tavgReported, base, upper), 2), 50.0, false);
        }
        return new Day(null, null, 0.0, false);
    }

    static double round(double v, int digits) {
        double p = Math.pow(10, digits);
        return Math.round(v * p) / p;
    }
}
