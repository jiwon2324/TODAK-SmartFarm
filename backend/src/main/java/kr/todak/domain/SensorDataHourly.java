package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_SENSOR_DATA_HOURLY — 센서 시간 집계 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_SENSOR_DATA_HOURLY")
@IdClass(SensorDataHourly.Key.class)
@Getter
@Setter
@NoArgsConstructor
public class SensorDataHourly {

    @Id
    @Column(name = "sensor_id", nullable = false)
    private Integer sensorId;

    @Id
    @Column(name = "hour_at", nullable = false)
    private LocalDateTime hourAt;

    @Column(name = "avg_value", nullable = false)
    private Double avgValue;

    @Column(name = "min_value", nullable = false)
    private Double minValue;

    @Column(name = "max_value", nullable = false)
    private Double maxValue;

    @Column(name = "ok_count", nullable = false)
    private Short okCount;

    /** 복합 기본키 */
    @Getter
    @Setter
    @NoArgsConstructor
    public static class Key implements Serializable {
        private Integer sensorId;
        private LocalDateTime hourAt;

        public Key(Integer sensorId, LocalDateTime hourAt) {
            this.sensorId = sensorId;
            this.hourAt = hourAt;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) {
                return true;
            }
            if (!(o instanceof Key k)) {
                return false;
            }
            return Objects.equals(sensorId, k.sensorId) && Objects.equals(hourAt, k.hourAt);
        }

        @Override
        public int hashCode() {
            return Objects.hash(sensorId, hourAt);
        }
    }
}
