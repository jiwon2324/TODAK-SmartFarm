package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_DEVICE — 제어 장치 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_DEVICE")
@Getter
@Setter
@NoArgsConstructor
public class Device {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "device_id", nullable = false)
    private Integer deviceId;

    @Column(name = "farm_id", nullable = false)
    private Integer farmId;

    @Column(name = "zone_id")
    private Integer zoneId;

    @Column(name = "gateway_id", nullable = false)
    private Integer gatewayId;

    @Column(name = "device_code", nullable = false)
    private String deviceCode;

    @Column(name = "device_type", nullable = false)
    private String deviceType;

    @Column(name = "device_name", nullable = false)
    private String deviceName;

    @Column(name = "mode", nullable = false)
    private String mode = "AUTO";

    @Column(name = "manual_until")
    private LocalDateTime manualUntil;

    @Column(name = "current_state", nullable = false)
    private String currentState = "OFF";

    @Column(name = "state_changed_at")
    private LocalDateTime stateChangedAt;

    @Column(name = "is_simulated", nullable = false)
    private Boolean isSimulated = true;

}
