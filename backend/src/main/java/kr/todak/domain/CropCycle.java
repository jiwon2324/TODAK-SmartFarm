package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_CROP_CYCLE — 작기 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_CROP_CYCLE")
@Getter
@Setter
@NoArgsConstructor
public class CropCycle {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "cycle_id", nullable = false)
    private Integer cycleId;

    @Column(name = "farm_id", nullable = false)
    private Integer farmId;

    @Column(name = "variety")
    private String variety;

    @Column(name = "transplant_date", nullable = false)
    private LocalDate transplantDate;

    @Column(name = "end_date")
    private LocalDate endDate;

    @Column(name = "current_stage", nullable = false)
    private String currentStage = "GROWTH";

    @Column(name = "gdd_base_c", nullable = false)
    private Double gddBaseC = 10.0;

    @Column(name = "gdd_upper_c", nullable = false)
    private Double gddUpperC = 30.0;

    @Column(name = "status", nullable = false)
    private String status = "ACTIVE";

}
