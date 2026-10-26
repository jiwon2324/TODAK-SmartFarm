package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_GDD_DAILY — 유효적산온도 일별 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_GDD_DAILY")
@IdClass(GddDaily.Key.class)
@Getter
@Setter
@NoArgsConstructor
public class GddDaily {

    @Id
    @Column(name = "cycle_id", nullable = false)
    private Integer cycleId;

    @Id
    @Column(name = "calc_date", nullable = false)
    private LocalDate calcDate;

    @Id
    @Column(name = "source", nullable = false)
    private String source;

    @Column(name = "method", nullable = false)
    private String method;

    @Column(name = "tavg_c")
    private Double tavgC;

    @Column(name = "base_c", nullable = false)
    private Double baseC;

    @Column(name = "upper_c", nullable = false)
    private Double upperC;

    @Column(name = "gdd")
    private Double gdd;

    @Column(name = "cum_gdd")
    private Double cumGdd;

    @Column(name = "coverage_pct", nullable = false)
    private Double coveragePct;

    @Column(name = "is_complete", nullable = false)
    private Boolean isComplete;

    @Column(name = "calculated_at", nullable = false)
    private LocalDateTime calculatedAt = LocalDateTime.now();

    /** 복합 기본키 */
    @Getter
    @Setter
    @NoArgsConstructor
    public static class Key implements Serializable {
        private Integer cycleId;
        private LocalDate calcDate;
        private String source;

        public Key(Integer cycleId, LocalDate calcDate, String source) {
            this.cycleId = cycleId;
            this.calcDate = calcDate;
            this.source = source;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) {
                return true;
            }
            if (!(o instanceof Key k)) {
                return false;
            }
            return Objects.equals(cycleId, k.cycleId) && Objects.equals(calcDate, k.calcDate) && Objects.equals(source, k.source);
        }

        @Override
        public int hashCode() {
            return Objects.hash(cycleId, calcDate, source);
        }
    }
}
