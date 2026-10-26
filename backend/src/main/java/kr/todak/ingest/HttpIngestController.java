package kr.todak.ingest;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import kr.todak.common.ApiException;
import kr.todak.domain.Gateway;
import kr.todak.repo.GatewayRepository;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * API-26 HTTP 대체 수집. MQTT 브로커 장애 때 게이트웨이가 같은 JSON을 HTTP로 올린다. [REQ-F-01]
 * 사용자 JWT가 아니라 게이트웨이 기기 토큰(X-Device-Token)으로 인증하며, 토큰의 게이트웨이가 속한 농장 센서만 받는다.
 * 저장 로직(검증·중복 제거·품질 플래그)은 MQTT 경로와 같은 SensorIngestService를 쓴다.
 */
@Tag(name = "수집 (게이트웨이)", description = "MQTT 장애 시 HTTP 대체 수집 [REQ-F-01, API-26] [TB_SENSOR_DATA]")
@RestController
@RequestMapping("/api/ingest")
public class HttpIngestController {
    private static final int MAX_BATCH = 2000;
    private final GatewayRepository gateways;
    private final SensorIngestService ingest;
    private final ObjectMapper om = new ObjectMapper();

    public HttpIngestController(GatewayRepository gateways, SensorIngestService ingest) {
        this.gateways = gateways;
        this.ingest = ingest;
    }

    @Operation(summary = "센서 측정값 일괄 업로드", description = """
            헤더 X-Device-Token (관리자 → 게이트웨이 기기 토큰 발급). 본문 {"gatewayCode":"GW-01","readings":[{"sensorCode":"S-T01","msgId":"...","ts":"2026-10-27T10:00:00+09:00","value":21.3}]}
            200 {saved, duplicates, rejected}. 401 DEVICE_UNAUTHORIZED, 400 VALIDATION_ERROR (최대 2000건)""")
    @PostMapping("/sensor-data")
    public Map<String, Object> upload(@RequestHeader(name = "X-Device-Token", required = false) String token, @RequestBody JsonNode body) {
        String code = body.path("gatewayCode").asText("");
        Gateway g = gateways.findByGatewayCode(code).orElse(null);
        if (g == null || g.getDeviceTokenHash() == null || token == null
                || !MessageDigest.isEqual(g.getDeviceTokenHash().getBytes(StandardCharsets.UTF_8), sha256(token).getBytes(StandardCharsets.UTF_8))) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "DEVICE_UNAUTHORIZED", "게이트웨이 기기 토큰이 올바르지 않습니다");
        }
        JsonNode rs = body.path("readings");
        if (!rs.isArray() || rs.isEmpty() || rs.size() > MAX_BATCH) {
            throw ApiException.badRequest("readings는 1~" + MAX_BATCH + "건 배열이어야 합니다");
        }
        int saved = 0, dup = 0, rejected = 0;
        for (JsonNode r : rs) {
            SensorIngestService.Result res;
            try {
                res = ingest.ingest(g.getFarmId(), r.path("sensorCode").asText(""), om.writeValueAsString(r));
            } catch (Exception e) {
                res = SensorIngestService.Result.REJECTED;
            }
            switch (res) {
                case SAVED -> saved++;
                case DUPLICATE -> dup++;
                default -> rejected++;
            }
        }
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("gatewayCode", code);
        m.put("saved", saved);
        m.put("duplicates", dup);
        m.put("rejected", rejected);
        return m;
    }

    public static String sha256(String s) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }
}
