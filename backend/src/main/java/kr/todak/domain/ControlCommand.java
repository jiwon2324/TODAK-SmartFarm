package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_CONTROL_COMMAND — 제어 명령 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_CONTROL_COMMAND")
@Getter
@Setter
@NoArgsConstructor
public class ControlCommand {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "command_id", nullable = false)
    private Long commandId;

    @Column(name = "device_id", nullable = false)
    private Integer deviceId;

    @Column(name = "action", nullable = false)
    private String action;

    @Column(name = "duration_sec")
    private Integer durationSec;

    @Column(name = "source", nullable = false)
    private String source;

    @Column(name = "rule_id")
    private Integer ruleId;

    @Column(name = "requested_by")
    private Integer requestedBy;

    @Column(name = "idempotency_key", nullable = false)
    private String idempotencyKey;

    @Column(name = "status", nullable = false)
    private String status = "REQUESTED";

    @Column(name = "retry_count", nullable = false)
    private Byte retryCount = (byte) 0;

    @Column(name = "reason")
    private String reason;

    @Column(name = "requested_at", nullable = false)
    private LocalDateTime requestedAt = LocalDateTime.now();

    @Column(name = "sent_at")
    private LocalDateTime sentAt;

    @Column(name = "acked_at")
    private LocalDateTime ackedAt;

}
