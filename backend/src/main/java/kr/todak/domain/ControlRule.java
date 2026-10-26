package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_CONTROL_RULE — 자동 제어 규칙 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_CONTROL_RULE")
@Getter
@Setter
@NoArgsConstructor
public class ControlRule {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "rule_id", nullable = false)
    private Integer ruleId;

    @Column(name = "farm_id", nullable = false)
    private Integer farmId;

    @Column(name = "rule_code", nullable = false)
    private String ruleCode;

    @Column(name = "rule_name", nullable = false)
    private String ruleName;

    @Column(name = "zone_id")
    private Integer zoneId;

    @Column(name = "metric", nullable = false)
    private String metric;

    @Column(name = "period", nullable = false)
    private String period = "ALL";

    @Column(name = "compare_op", nullable = false)
    private String compareOp;

    @Column(name = "on_threshold", nullable = false)
    private Double onThreshold;

    @Column(name = "off_threshold", nullable = false)
    private Double offThreshold;

    @Column(name = "target_device_type", nullable = false)
    private String targetDeviceType;

    @Column(name = "action_on", nullable = false)
    private String actionOn;

    @Column(name = "action_off", nullable = false)
    private String actionOff;

    @Column(name = "min_run_sec", nullable = false)
    private Integer minRunSec = 180;

    @Column(name = "max_run_sec")
    private Integer maxRunSec;

    @Column(name = "max_daily_count")
    private Integer maxDailyCount;

    @Column(name = "is_safety", nullable = false)
    private Boolean isSafety = false;

    @Column(name = "priority", nullable = false)
    private Byte priority = (byte) 5;

    @Column(name = "is_enabled", nullable = false)
    private Boolean isEnabled = true;

}
