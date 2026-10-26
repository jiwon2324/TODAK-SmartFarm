package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_ZONE — 관리 구역 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_ZONE")
@Getter
@Setter
@NoArgsConstructor
public class Zone {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "zone_id", nullable = false)
    private Integer zoneId;

    @Column(name = "farm_id", nullable = false)
    private Integer farmId;

    @Column(name = "zone_code", nullable = false)
    private String zoneCode;

    @Column(name = "zone_name", nullable = false)
    private String zoneName;

    @Column(name = "area_m2", nullable = false)
    private Double areaM2;

    @Column(name = "x_from_m")
    private Double xFromM;

    @Column(name = "x_to_m")
    private Double xToM;

    @Column(name = "description")
    private String description;

}
