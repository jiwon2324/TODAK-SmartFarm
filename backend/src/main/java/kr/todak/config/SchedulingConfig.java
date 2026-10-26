package kr.todak.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;

/** 주기 작업(규칙 평가·ACK 시간초과·무응답 감지·집계). 통합 테스트에서는 todak.scheduling.enabled=false로 끄고 직접 호출한다. */
@Configuration
@EnableScheduling
@ConditionalOnProperty(prefix = "todak.scheduling", name = "enabled", havingValue = "true", matchIfMissing = true)
public class SchedulingConfig {
}
