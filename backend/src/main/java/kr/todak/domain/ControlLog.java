package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_CONTROL_LOG — 장치 상태 이력 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_CONTROL_LOG")
@Getter
@Setter
@NoArgsConstructor
public class ControlLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "log_id", nullable = false)
    private Long logId;

    @Column(name = "device_id", nullable = false)
    private Integer deviceId;

    @Column(name = "command_id")
    private Long commandId;

    @Column(name = "prev_state")
    private String prevState;

    @Column(name = "new_state", nullable = false)
    private String newState;

    @Column(name = "changed_by", nullable = false)
    private String changedBy;

    @Column(name = "changed_at", nullable = false)
    private LocalDateTime changedAt;

}
