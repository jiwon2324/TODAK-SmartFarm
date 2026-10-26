package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_ALERT — 알림 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_ALERT")
@Getter
@Setter
@NoArgsConstructor
public class Alert {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "alert_id", nullable = false)
    private Long alertId;

    @Column(name = "farm_id", nullable = false)
    private Integer farmId;

    @Column(name = "zone_id")
    private Integer zoneId;

    @Column(name = "alert_type", nullable = false)
    private String alertType;

    @Column(name = "severity", nullable = false)
    private String severity;

    @Column(name = "dedupe_key", nullable = false)
    private String dedupeKey;

    @Column(name = "message", nullable = false)
    private String message;

    @Column(name = "status", nullable = false)
    private String status = "OPEN";

    @Column(name = "occur_count", nullable = false)
    private Integer occurCount = 1;

    @Column(name = "first_at", nullable = false)
    private LocalDateTime firstAt = LocalDateTime.now();

    @Column(name = "last_at", nullable = false)
    private LocalDateTime lastAt = LocalDateTime.now();

    @Column(name = "acked_by")
    private Integer ackedBy;

    @Column(name = "resolved_at")
    private LocalDateTime resolvedAt;

}
