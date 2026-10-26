package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_CROP_STD — 재배 기준값 (버전 관리) (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_CROP_STD")
@Getter
@Setter
@NoArgsConstructor
public class CropStd {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "std_id", nullable = false)
    private Integer stdId;

    @Column(name = "farm_id", nullable = false)
    private Integer farmId;

    @Column(name = "zone_id")
    private Integer zoneId;

    @Column(name = "stage", nullable = false)
    private String stage;

    @Column(name = "version_no", nullable = false)
    private Integer versionNo = 1;

    @Column(name = "day_start_time", nullable = false)
    private LocalTime dayStartTime = LocalTime.parse("07:00:00");

    @Column(name = "night_start_time", nullable = false)
    private LocalTime nightStartTime = LocalTime.parse("19:00:00");

    @Column(name = "day_temp_min", nullable = false)
    private Double dayTempMin;

    @Column(name = "day_temp_max", nullable = false)
    private Double dayTempMax;

    @Column(name = "night_temp_min", nullable = false)
    private Double nightTempMin;

    @Column(name = "night_temp_max", nullable = false)
    private Double nightTempMax;

    @Column(name = "humidity_min", nullable = false)
    private Double humidityMin;

    @Column(name = "humidity_max", nullable = false)
    private Double humidityMax;

    @Column(name = "ec_min", nullable = false)
    private Double ecMin;

    @Column(name = "ec_max", nullable = false)
    private Double ecMax;

    @Column(name = "ph_min", nullable = false)
    private Double phMin;

    @Column(name = "ph_max", nullable = false)
    private Double phMax;

    @Column(name = "substrate_moisture_min")
    private Double substrateMoistureMin;

    @Column(name = "source_note")
    private String sourceNote;

    @Column(name = "effective_from", nullable = false)
    private LocalDateTime effectiveFrom = LocalDateTime.now();

    @Column(name = "is_current", nullable = false)
    private Boolean isCurrent = true;

    @Column(name = "created_by")
    private Integer createdBy;

}
