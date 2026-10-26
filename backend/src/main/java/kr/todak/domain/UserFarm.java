package kr.todak.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.*;
import java.util.Objects;

/** TB_USER_FARM — 사용자별 농장 접근 권한 (tools/gen_backend.py로 생성) */
@Entity
@Table(name = "TB_USER_FARM")
@IdClass(UserFarm.Key.class)
@Getter
@Setter
@NoArgsConstructor
public class UserFarm {

    @Id
    @Column(name = "user_id", nullable = false)
    private Integer userId;

    @Id
    @Column(name = "farm_id", nullable = false)
    private Integer farmId;

    @Column(name = "granted_at", nullable = false)
    private LocalDateTime grantedAt = LocalDateTime.now();

    /** 복합 기본키 */
    @Getter
    @Setter
    @NoArgsConstructor
    public static class Key implements Serializable {
        private Integer userId;
        private Integer farmId;

        public Key(Integer userId, Integer farmId) {
            this.userId = userId;
            this.farmId = farmId;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) {
                return true;
            }
            if (!(o instanceof Key k)) {
                return false;
            }
            return Objects.equals(userId, k.userId) && Objects.equals(farmId, k.farmId);
        }

        @Override
        public int hashCode() {
            return Objects.hash(userId, farmId);
        }
    }
}
