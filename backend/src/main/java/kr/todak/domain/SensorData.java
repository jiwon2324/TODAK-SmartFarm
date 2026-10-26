package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_SENSOR_DATA — 센서 원시 데이터 (1분) (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_SENSOR_DATA")
@Getter
@Setter
@NoArgsConstructor
public class SensorData {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "data_id", nullable = false)
    private Long dataId;

    @Column(name = "sensor_id", nullable = false)
    private Integer sensorId;

    @Column(name = "measured_at", nullable = false)
    private LocalDateTime measuredAt;

    @Column(name = "value", nullable = false)
    private Double value;

    @Column(name = "value_min")
    private Double valueMin;

    @Column(name = "value_max")
    private Double valueMax;

    @Column(name = "sample_count")
    private Short sampleCount;

    @Column(name = "quality", nullable = false)
    private String quality = "OK";

    @Column(name = "msg_id", nullable = false)
    private String msgId;

    @Column(name = "is_buffered", nullable = false)
    private Boolean isBuffered = false;

    @Column(name = "received_at", nullable = false)
    private LocalDateTime receivedAt = LocalDateTime.now();

}
