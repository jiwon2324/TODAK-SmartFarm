package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_BEEHIVE — 벌통 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_BEEHIVE")
@Getter
@Setter
@NoArgsConstructor
public class Beehive {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "hive_id", nullable = false)
    private Integer hiveId;

    @Column(name = "cycle_id", nullable = false)
    private Integer cycleId;

    @Column(name = "zone_id")
    private Integer zoneId;

    @Column(name = "placed_date", nullable = false)
    private LocalDate placedDate;

    @Column(name = "replace_days", nullable = false)
    private Integer replaceDays;

    @Column(name = "removed_date")
    private LocalDate removedDate;

}
