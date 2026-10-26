package kr.todak.unit;

import kr.todak.control.DeviceStates;
import kr.todak.control.RuleDecision;
import org.junit.jupiter.api.Test;

import java.util.List;

import static kr.todak.control.RuleDecision.Want.*;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** TC-002 보조: 히스테리시스 판단과 장치 상태 매핑 */
class RuleDecisionTest {

    @Test
    void geHysteresis() {
        // CR-01 주간 환기: ON 28, OFF 26
        assertThat(RuleDecision.decide("GE", 28.0, 28, 26)).isEqualTo(ACTIVATE);
        assertThat(RuleDecision.decide("GE", 27.0, 28, 26)).isEqualTo(HOLD);
        assertThat(RuleDecision.decide("GE", 26.0, 28, 26)).isEqualTo(DEACTIVATE);
    }

    @Test
    void leHysteresis() {
        // CR-02 야간 난방: ON 14, OFF 16
        assertThat(RuleDecision.decide("LE", 13.9, 14, 16)).isEqualTo(ACTIVATE);
        assertThat(RuleDecision.decide("LE", 15.0, 14, 16)).isEqualTo(HOLD);
        assertThat(RuleDecision.decide("LE", 16.0, 14, 16)).isEqualTo(DEACTIVATE);
    }

    @Test
    void noChatterAroundThreshold() {
        // 27.9 ↔ 28.1 사이를 오가도 ON 1회 뒤 OFF 조건(≤26)이 오기 전까지 유지 → 채터링 0
        double[] series = {27.5, 28.1, 27.9, 28.0, 27.8, 27.0, 26.5, 26.0};
        boolean active = false;
        int changes = 0;
        for (double v : series) {
            RuleDecision.Want w = RuleDecision.decide("GE", v, 28, 26);
            boolean next = w == ACTIVATE || (w == HOLD && active);
            if (next != active) {
                changes++;
                active = next;
            }
        }
        assertThat(changes).isEqualTo(2);
    }

    @Test
    void representativeIsConservative() {
        assertThat(RuleDecision.representative("GE", List.of(27.0, 29.5))).isEqualTo(29.5);
        assertThat(RuleDecision.representative("LE", List.of(13.0, 15.5))).isEqualTo(13.0);
    }

    @Test
    void unknownOperator() {
        assertThatThrownBy(() -> RuleDecision.decide("EQ", 1, 1, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void deviceStates() {
        assertThat(DeviceStates.active("VENT")).isEqualTo("OPEN");
        assertThat(DeviceStates.active("SHADE")).isEqualTo("CLOSE");
        assertThat(DeviceStates.normalize("VENT", "ON")).isEqualTo("OPEN");
        assertThat(DeviceStates.normalize("FAN", "OFF")).isEqualTo("OFF");
        assertThatThrownBy(() -> DeviceStates.normalize("FAN", "OPEN")).isInstanceOf(IllegalArgumentException.class);
    }
}
