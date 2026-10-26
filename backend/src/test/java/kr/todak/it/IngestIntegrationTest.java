package kr.todak.it;

import kr.todak.analytics.HourlyAggregator;
import kr.todak.ingest.SensorIngestService;
import kr.todak.ingest.SensorIngestService.Result;
import kr.todak.mqtt.MqttMessageRouter;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;

import static org.assertj.core.api.Assertions.assertThat;

/** TC-001 · REQ-F-01: 수신 → 검증 → 중복 제거 → 품질 플래그 → MySQL 저장 */
class IngestIntegrationTest extends IntegrationTestBase {
    @Autowired
    SensorIngestService ingest;
    @Autowired
    MqttMessageRouter router;
    @Autowired
    HourlyAggregator aggregator;

    private final LocalDateTime t0 = LocalDateTime.now().truncatedTo(ChronoUnit.MINUTES);

    @org.junit.jupiter.api.BeforeEach
    void clear() {
        ingest.clearMemory();
    }

    @Test
    @DisplayName("MQTT 토픽으로 받은 값이 TB_SENSOR_DATA에 저장된다")
    void storesViaTopic() {
        router.route("todak/1/Z1/sensor/S-T01", payload("it-1", "S-T01", 22.5, t0));
        Double v = jdbc.queryForObject("SELECT value FROM TB_SENSOR_DATA WHERE msg_id='it-1'", Double.class);
        assertThat(v).isEqualTo(22.5);
        assertThat(jdbc.queryForObject("SELECT quality FROM TB_SENSOR_DATA WHERE msg_id='it-1'", String.class)).isEqualTo("OK");
    }

    @Test
    @DisplayName("같은 msgId·같은 분 재전송 100건 → 추가 저장 0건")
    void duplicatesIgnored() {
        assertThat(ingest.ingest(1, "S-T01", payload("dup-0", "S-T01", 20.0, t0))).isEqualTo(Result.SAVED);
        int dups = 0;
        for (int i = 0; i < 100; i++) {
            String id = i % 2 == 0 ? "dup-0" : "dup-x" + i;   // 같은 msgId 또는 같은 (센서, 분)
            if (ingest.ingest(1, "S-T01", payload(id, "S-T01", 20.0, t0)) == Result.DUPLICATE) {
                dups++;
            }
        }
        assertThat(dups).isEqualTo(100);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_SENSOR_DATA", Integer.class)).isEqualTo(1);
    }

    @Test
    @DisplayName("범위 밖 값은 OUT_RANGE로 저장되고 OUTLIER 경보가 열린다")
    void outOfRange() {
        ingest.ingest(1, "S-H01", payload("oor-1", "S-H01", 140.0, t0));
        assertThat(jdbc.queryForObject("SELECT quality FROM TB_SENSOR_DATA WHERE msg_id='oor-1'", String.class)).isEqualTo("OUT_RANGE");
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_ALERT WHERE alert_type='OUTLIER' AND status='OPEN'", Integer.class)).isEqualTo(1);
    }

    @Test
    @DisplayName("1분 사이 급변(spike_limit 초과)은 SPIKE")
    void spike() {
        ingest.ingest(1, "S-T02", payload("sp-1", "S-T02", 20.0, t0.minusMinutes(1)));
        ingest.ingest(1, "S-T02", payload("sp-2", "S-T02", 29.0, t0));
        assertThat(jdbc.queryForObject("SELECT quality FROM TB_SENSOR_DATA WHERE msg_id='sp-2'", String.class)).isEqualTo("SPIKE");
    }

    @Test
    @DisplayName("형식 오류·미등록 센서는 거부")
    void rejects() {
        assertThat(ingest.ingest(1, "S-T01", "{not json")).isEqualTo(Result.REJECTED);
        assertThat(ingest.ingest(1, "S-T01", "{\"msgId\":\"a\"}")).isEqualTo(Result.REJECTED);
        assertThat(ingest.ingest(1, "S-NOPE", payload("nope", "S-NOPE", 1, t0))).isEqualTo(Result.REJECTED);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_SENSOR_DATA", Integer.class)).isZero();
    }

    @Test
    @DisplayName("통신 복구 재전송(buffered)도 저장되고 시간 집계에 반영된다")
    void bufferedAndHourly() {
        LocalDateTime h = t0.minusHours(3).withMinute(0);
        for (int m = 0; m < 60; m++) {
            String p = payload("buf-" + m, "S-T01", 18.0 + (m % 2), h.plusMinutes(m)).replace("\"samples\":6", "\"samples\":6,\"buffered\":true");
            ingest.ingest(1, "S-T01", p);
        }
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_SENSOR_DATA WHERE is_buffered=1", Integer.class)).isEqualTo(60);
        aggregator.aggregateReceivedSince(LocalDateTime.now().minusMinutes(5));
        Double avg = jdbc.queryForObject("SELECT avg_value FROM TB_SENSOR_DATA_HOURLY WHERE sensor_id=1 AND hour_at=?", Double.class, h);
        Integer ok = jdbc.queryForObject("SELECT ok_count FROM TB_SENSOR_DATA_HOURLY WHERE sensor_id=1 AND hour_at=?", Integer.class, h);
        assertThat(avg).isEqualTo(18.5);
        assertThat(ok).isEqualTo(60);
    }
}
