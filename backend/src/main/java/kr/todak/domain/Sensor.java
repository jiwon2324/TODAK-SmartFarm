package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_SENSOR — 센서 채널 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_SENSOR")
@Getter
@Setter
@NoArgsConstructor
public class Sensor {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "sensor_id", nullable = false)
    private Integer sensorId;

    @Column(name = "farm_id", nullable = false)
    private Integer farmId;

    @Column(name = "zone_id")
    private Integer zoneId;

    @Column(name = "gateway_id", nullable = false)
    private Integer gatewayId;

    @Column(name = "sensor_code", nullable = false)
    private String sensorCode;

    @Column(name = "metric", nullable = false)
    private String metric;

    @Column(name = "unit", nullable = false)
    private String unit;

    @Column(name = "valid_min", nullable = false)
    private Double validMin;

    @Column(name = "valid_max", nullable = false)
    private Double validMax;

    @Column(name = "spike_limit")
    private Double spikeLimit;

    @Column(name = "install_note")
    private String installNote;

    @Column(name = "is_simulated", nullable = false)
    private Boolean isSimulated = true;

    @Column(name = "status", nullable = false)
    private String status = "ACTIVE";

    @Column(name = "last_received_at")
    private LocalDateTime lastReceivedAt;

}
