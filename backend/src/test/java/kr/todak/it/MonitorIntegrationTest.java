package kr.todak.it;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** 통합 관제 API (SCR-M1): 센서 판정 단계와 타임라인, 농장 접근 제한 */
class MonitorIntegrationTest extends IntegrationTestBase {

    private void reading(int sensorId, double v, LocalDateTime at, String quality) {
        jdbc.update("INSERT INTO TB_SENSOR_DATA (sensor_id, measured_at, value, quality, msg_id) VALUES (?,?,?,?,?)",
                sensorId, at, v, quality, "m-" + sensorId + "-" + at);
    }

    @Test
    @DisplayName("판정: 안전 한계 ALARM, 기준 이탈 WARN, 기준 안 OK, 수신 끊김 STALE, 값 없음 NODATA")
    void levels() throws Exception {
        LocalDateTime now = LocalDateTime.now().truncatedTo(ChronoUnit.MINUTES);
        reading(1, 36.0, now, "OK");                    // S-T01 36℃ ≥ CR-05 고온 안전 35℃ (주야 무관)
        reading(2, 95.0, now, "OK");                    // S-H01 습도 95% > 기준 90%
        reading(7, 60.0, now, "OK");                    // S-SM01 배지 수분 60% ≥ 기준 45%
        reading(4, 70.0, now.minusMinutes(10), "OK");   // S-H02 10분 전 값 → 수신 끊김
        reading(9, 1.8, now, "SPIKE");                  // S-EC01 급변 플래그 → 품질 이상
        jdbc.update("INSERT INTO TB_ALERT (farm_id, alert_type, severity, dedupe_key, message) VALUES (1,'THRESHOLD','WARN','t-1','시험 경보')");

        mvc.perform(get("/api/farms/1/monitor").header("Authorization", bearer(login("farmer01", FARMER_PW))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sensors[?(@.sensorCode=='S-T01')].level").value(contains("ALARM")))
                .andExpect(jsonPath("$.sensors[?(@.sensorCode=='S-T01')].note").value(contains(containsString("CR-05"))))
                .andExpect(jsonPath("$.sensors[?(@.sensorCode=='S-H01')].level").value(contains("WARN")))
                .andExpect(jsonPath("$.sensors[?(@.sensorCode=='S-SM01')].level").value(contains("OK")))
                .andExpect(jsonPath("$.sensors[?(@.sensorCode=='S-H02')].level").value(contains("STALE")))
                .andExpect(jsonPath("$.sensors[?(@.sensorCode=='S-EC01')].level").value(contains("ALARM")))
                .andExpect(jsonPath("$.sensors[?(@.sensorCode=='S-T02')].level").value(contains("NODATA")))
                .andExpect(jsonPath("$.overall").value("ALARM"))
                .andExpect(jsonPath("$.summary.ALARM").value(2))
                .andExpect(jsonPath("$.day", isA(Boolean.class)))
                .andExpect(jsonPath("$.events[?(@.kind=='ALERT')].text").value(hasItem("시험 경보")));
    }

    @Test
    @DisplayName("다른 농장의 관제 화면은 403")
    void farmIsolation() throws Exception {
        mvc.perform(get("/api/farms/2/monitor").header("Authorization", bearer(login("farmer01", FARMER_PW)))).andExpect(status().isForbidden());
        mvc.perform(get("/api/farms/2/monitor").header("Authorization", bearer(login("admin", ADMIN_PW)))).andExpect(status().isOk());
    }
}
