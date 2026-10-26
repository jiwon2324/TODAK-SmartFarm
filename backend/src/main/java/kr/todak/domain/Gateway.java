package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_GATEWAY — 현장 게이트웨이 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_GATEWAY")
@Getter
@Setter
@NoArgsConstructor
public class Gateway {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "gateway_id", nullable = false)
    private Integer gatewayId;

    @Column(name = "farm_id", nullable = false)
    private Integer farmId;

    @Column(name = "gateway_code", nullable = false)
    private String gatewayCode;

    @Column(name = "is_simulated", nullable = false)
    private Boolean isSimulated = true;

    @Column(name = "status", nullable = false)
    private String status = "OFFLINE";

    @Column(name = "last_heartbeat_at")
    private LocalDateTime lastHeartbeatAt;

    @Column(name = "synced_std_version")
    private Integer syncedStdVersion;

    @com.fasterxml.jackson.annotation.JsonIgnore
    @Column(name = "device_token_hash")
    private String deviceTokenHash;

}
