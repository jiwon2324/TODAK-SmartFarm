package kr.todak.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {
    @Bean
    public OpenAPI todakOpenApi() {
        return new OpenAPI()
                .info(new Info().title("TODAK 스마트 농업 정보시스템 API").version("1.0.0")
                        .description("양평 100평 방울토마토 비닐하우스 웹 시스템. 각 API 설명의 [REQ-…]는 개발 계획서 요구사항 ID, [TB_…]는 관련 테이블이다. "
                                + "/api/auth/login으로 받은 accessToken을 오른쪽 위 Authorize에 입력하면 인증 API를 실행할 수 있다."))
                .components(new Components().addSecuritySchemes("bearer",
                        new SecurityScheme().type(SecurityScheme.Type.HTTP).scheme("bearer").bearerFormat("JWT")))
                .addSecurityItem(new SecurityRequirement().addList("bearer"));
    }
}
