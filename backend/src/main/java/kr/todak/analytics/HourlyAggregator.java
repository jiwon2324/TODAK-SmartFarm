package kr.todak.analytics;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 1분 원시 데이터를 시간 집계(TB_SENSOR_DATA_HOURLY)로 올린다. [REQ-F-10]
 * 최근 10분 안에 받은 데이터가 속한 시간대만 다시 계산하므로, 통신 복구 후 재전송된 과거 데이터도 반영된다.
 * 품질 OK인 값만 집계한다.
 */
@Component
public class HourlyAggregator {
    private static final String UPSERT = """
            INSERT INTO TB_SENSOR_DATA_HOURLY (sensor_id, hour_at, avg_value, min_value, max_value, ok_count)
            SELECT d.sensor_id, DATE_FORMAT(d.measured_at, '%Y-%m-%d %H:00:00') AS h, AVG(d.value), MIN(d.value), MAX(d.value), COUNT(*)
            FROM TB_SENSOR_DATA d
            JOIN (SELECT DISTINCT sensor_id, DATE_FORMAT(measured_at, '%Y-%m-%d %H:00:00') AS h
                  FROM TB_SENSOR_DATA WHERE received_at >= ?) t
              ON t.sensor_id = d.sensor_id AND DATE_FORMAT(d.measured_at, '%Y-%m-%d %H:00:00') = t.h
            WHERE d.quality = 'OK'
            GROUP BY d.sensor_id, h
            ON DUPLICATE KEY UPDATE avg_value = VALUES(avg_value), min_value = VALUES(min_value),
              max_value = VALUES(max_value), ok_count = VALUES(ok_count)
            """;
    private final JdbcTemplate jdbc;

    public HourlyAggregator(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Scheduled(fixedDelay = 60000, initialDelay = 15000)
    public void aggregateRecent() {
        aggregateReceivedSince(java.time.LocalDateTime.now().minusMinutes(10));
    }

    public int aggregateReceivedSince(java.time.LocalDateTime since) {
        return jdbc.update(UPSERT, since);
    }
}
