package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_ALERT_DELIVERY — 알림 발송 내역 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_ALERT_DELIVERY")
@Getter
@Setter
@NoArgsConstructor
public class AlertDelivery {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "delivery_id", nullable = false)
    private Long deliveryId;

    @Column(name = "alert_id", nullable = false)
    private Long alertId;

    @Column(name = "user_id", nullable = false)
    private Integer userId;

    @Column(name = "channel", nullable = false)
    private String channel;

    @Column(name = "result", nullable = false)
    private String result;

    @Column(name = "try_count", nullable = false)
    private Byte tryCount = (byte) 1;

    @Column(name = "sent_at", nullable = false)
    private LocalDateTime sentAt = LocalDateTime.now();

}
