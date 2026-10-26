package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_IMAGE_RESULT — 수확 판별 결과 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_IMAGE_RESULT")
@Getter
@Setter
@NoArgsConstructor
public class ImageResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "image_id", nullable = false)
    private Long imageId;

    @Column(name = "zone_id", nullable = false)
    private Integer zoneId;

    @Column(name = "camera_code", nullable = false)
    private String cameraCode;

    @Column(name = "image_path", nullable = false)
    private String imagePath;

    @Column(name = "captured_at", nullable = false)
    private LocalDateTime capturedAt;

    @Column(name = "image_quality", nullable = false)
    private String imageQuality;

    @Column(name = "red_ratio_pct")
    private Double redRatioPct;

    @Column(name = "ripeness_stage")
    private String ripenessStage;

    @Column(name = "harvest_candidate", nullable = false)
    private Boolean harvestCandidate = false;

    @Column(name = "algorithm_ver", nullable = false)
    private String algorithmVer;

    @Column(name = "label_stage")
    private String labelStage;

}
