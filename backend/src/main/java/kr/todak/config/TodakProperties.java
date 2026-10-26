package kr.todak.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.List;

@ConfigurationProperties(prefix = "todak")
public record TodakProperties(Jwt jwt, Cookie cookie, Cors cors, Mqtt mqtt, Control control, Retention retention) {

    public record Jwt(String secret, long accessTtlSeconds, long refreshTtlSeconds) {
    }

    public record Cookie(boolean secure) {
    }

    public record Cors(List<String> allowedOrigins) {
    }

    public record Mqtt(boolean enabled, String url, String username, String password, String clientId) {
    }

    /** 원시 1분 데이터 보존 일수 (계획서 표 68: 3년) */
    public record Retention(int rawDays) {
        public Retention {
            if (rawDays <= 0) {
                rawDays = 1095;
            }
        }
    }

    public record Control(long ruleIntervalMs, int ackTimeoutSeconds, int staleSeconds, int alertDedupeMinutes, int manualDefaultMinutes) {
    }
}
