package kr.todak.alert;

import kr.todak.config.TodakProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * 데이터 보존 배치 (계획서 19장 표 68, REQ-N-05). 매일 03:00 보존 기간(기본 3년)이 지난 원시 1분 데이터를 1만 건씩 지운다.
 * 시간 집계(TB_SENSOR_DATA_HOURLY)는 영구 보존하므로 건드리지 않는다.
 */
@Component
public class RetentionJob {
    private static final Logger log = LoggerFactory.getLogger(RetentionJob.class);
    private final JdbcTemplate jdbc;
    private final int rawDays;

    public RetentionJob(JdbcTemplate jdbc, TodakProperties props) {
        this.jdbc = jdbc;
        this.rawDays = props.retention() == null ? 1095 : props.retention().rawDays();
    }

    @Scheduled(cron = "0 0 3 * * *")
    public int purgeRaw() {
        LocalDateTime limit = LocalDateTime.now().minusDays(rawDays);
        int total = 0;
        int n;
        do {
            n = jdbc.update("DELETE FROM TB_SENSOR_DATA WHERE measured_at < ? LIMIT 10000", limit);
            total += n;
        } while (n == 10000);
        log.info("보존 배치: {}일 지난 원시 데이터 {}건 삭제 (기준 {})", rawDays, total, limit);
        return total;
    }
}
