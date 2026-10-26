package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_FARM — 농장(재배동) (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_FARM")
@Getter
@Setter
@NoArgsConstructor
public class Farm {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "farm_id", nullable = false)
    private Integer farmId;

    @Column(name = "owner_user_id", nullable = false)
    private Integer ownerUserId;

    @Column(name = "farm_name", nullable = false)
    private String farmName;

    @Column(name = "region", nullable = false)
    private String region;

    @Column(name = "area_m2", nullable = false)
    private Double areaM2;

    @Column(name = "facility_type", nullable = false)
    private String facilityType;

    @Column(name = "culture_type")
    private String cultureType;

    @Column(name = "kma_station_id")
    private String kmaStationId;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

}
