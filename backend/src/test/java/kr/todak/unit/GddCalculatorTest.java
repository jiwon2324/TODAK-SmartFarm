package kr.todak.unit;

import kr.todak.analytics.GddCalculator;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/** TC-014: GDD 계산이 손 계산과 0.1 이내로 일치하는지 */
class GddCalculatorTest {

    @Test
    @DisplayName("기준온도 이상: Tavg − Tbase")
    void basic() {
        assertThat(GddCalculator.gdd(18.4, 10, 30)).isCloseTo(8.4, within(1e-9));
    }

    @Test
    @DisplayName("기준온도 미만은 0")
    void belowBase() {
        assertThat(GddCalculator.gdd(7.5, 10, 30)).isZero();
    }

    @Test
    @DisplayName("상한온도 초과분은 잘라낸다")
    void upperCap() {
        assertThat(GddCalculator.gdd(33.0, 10, 30)).isEqualTo(20.0);
    }

    @Test
    @DisplayName("시간 평균 24개 → 일평균, 결측 없으면 complete")
    void hourlyComplete() {
        GddCalculator.Day d = GddCalculator.fromHourly(Collections.nCopies(24, 20.0), 10, 30);
        assertThat(d.tavg()).isEqualTo(20.0);
        assertThat(d.gdd()).isEqualTo(10.0);
        assertThat(d.coveragePct()).isEqualTo(100.0);
        assertThat(d.complete()).isTrue();
    }

    @Test
    @DisplayName("유효 시간 80% 미만은 불완전, 0시간은 GDD 없음")
    void coverage() {
        assertThat(GddCalculator.fromHourly(Collections.nCopies(19, 20.0), 10, 30).complete()).isFalse();
        assertThat(GddCalculator.fromHourly(Collections.nCopies(20, 20.0), 10, 30).complete()).isTrue();
        assertThat(GddCalculator.fromHourly(List.of(), 10, 30).gdd()).isNull();
    }

    @Test
    @DisplayName("외부(최고+최저)/2")
    void maxMin() {
        GddCalculator.Day d = GddCalculator.fromMaxMin(25.0, 15.0, null, 10, 30);
        assertThat(d.tavg()).isEqualTo(20.0);
        assertThat(d.gdd()).isEqualTo(10.0);
    }

    @Test
    @DisplayName("7일 누적이 손 계산과 일치 (오차 ≤ 0.1)")
    void sevenDaysHandCalculation() {
        double[] tavg = {12.3, 15.8, 18.4, 9.6, 21.0, 31.5, 16.2};
        // 손 계산: 2.3 + 5.8 + 8.4 + 0 + 11.0 + 20.0(상한) + 6.2 = 53.7
        double cum = 0;
        for (double t : tavg) {
            cum += GddCalculator.gdd(t, 10, 30);
        }
        assertThat(cum).isCloseTo(53.7, within(0.1));
    }
}
