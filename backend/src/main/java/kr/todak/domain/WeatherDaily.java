package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_WEATHER_DAILY — 외부 기상 일자료 (ASOS) (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_WEATHER_DAILY")
@IdClass(WeatherDaily.Key.class)
@Getter
@Setter
@NoArgsConstructor
public class WeatherDaily {

    @Id
    @Column(name = "station_id", nullable = false)
    private String stationId;

    @Id
    @Column(name = "obs_date", nullable = false)
    private LocalDate obsDate;

    @Column(name = "tavg_c")
    private Double tavgC;

    @Column(name = "tmax_c")
    private Double tmaxC;

    @Column(name = "tmin_c")
    private Double tminC;

    @Column(name = "rain_mm")
    private Double rainMm;

    @Column(name = "rh_pct")
    private Double rhPct;

    @Column(name = "sunshine_hr")
    private Double sunshineHr;

    @Column(name = "solar_mj_m2")
    private Double solarMjM2;

    @Column(name = "missing_flags")
    private String missingFlags;

    @Column(name = "source_file", nullable = false)
    private String sourceFile;

    @Column(name = "imported_at", nullable = false)
    private LocalDateTime importedAt = LocalDateTime.now();

    /** 복합 기본키 */
    @Getter
    @Setter
    @NoArgsConstructor
    public static class Key implements Serializable {
        private String stationId;
        private LocalDate obsDate;

        public Key(String stationId, LocalDate obsDate) {
            this.stationId = stationId;
            this.obsDate = obsDate;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) {
                return true;
            }
            if (!(o instanceof Key k)) {
                return false;
            }
            return Objects.equals(stationId, k.stationId) && Objects.equals(obsDate, k.obsDate);
        }

        @Override
        public int hashCode() {
            return Objects.hash(stationId, obsDate);
        }
    }
}
