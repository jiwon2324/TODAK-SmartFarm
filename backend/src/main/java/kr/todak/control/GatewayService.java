package kr.todak.control;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import kr.todak.alert.AlertService;
import kr.todak.common.ErrorLog;
import kr.todak.domain.ControlRule;
import kr.todak.domain.CropCycle;
import kr.todak.domain.CropStd;
import kr.todak.domain.Gateway;
import kr.todak.mqtt.MqttGateway;
import kr.todak.repo.ControlRuleRepository;
import kr.todak.repo.CropCycleRepository;
import kr.todak.repo.CropStdRepository;
import kr.todak.repo.GatewayRepository;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 게이트웨이 상태(하트비트·LWT)와 기준값 사본 동기화. [REQ-N-03]
 * 서버가 기준값·안전 규칙을 retained config 토픽으로 발행하면 게이트웨이는 그 사본으로 단절 시 안전 운전한다.
 */
@Service
public class GatewayService {
    private static final int OFFLINE_AFTER_SEC = 90;
    private final ObjectMapper om = new ObjectMapper();
    private final GatewayRepository gateways;
    private final ControlRuleRepository rules;
    private final CropStdRepository stds;
    private final CropCycleRepository cycles;
    private final MqttGateway mqtt;
    private final AlertService alerts;
    private final ErrorLog errorLog;

    public GatewayService(GatewayRepository gateways, ControlRuleRepository rules, CropStdRepository stds, CropCycleRepository cycles,
                          MqttGateway mqtt, AlertService alerts, ErrorLog errorLog) {
        this.gateways = gateways;
        this.rules = rules;
        this.stds = stds;
        this.cycles = cycles;
        this.mqtt = mqtt;
        this.alerts = alerts;
        this.errorLog = errorLog;
    }

    @Transactional
    public void handleStatus(Integer farmId, String gatewayCode, String payload) {
        Gateway g = gateways.findByGatewayCode(gatewayCode).orElse(null);
        if (g == null || !g.getFarmId().equals(farmId)) {
            errorLog.add("GATEWAY", "알 수 없는 게이트웨이 " + gatewayCode);
            return;
        }
        String status;
        int ver = -1;
        try {
            JsonNode j = om.readTree(payload);
            status = j.path("status").asText("online");
            ver = j.path("configVersion").asInt(-1);
        } catch (Exception e) {
            status = payload.trim().toLowerCase();
        }
        if ("offline".equalsIgnoreCase(status)) {
            markOffline(g, "LWT 수신 (연결 끊김)");
            return;
        }
        boolean wasOffline = !"ONLINE".equals(g.getStatus());
        g.setStatus("ONLINE");
        g.setLastHeartbeatAt(LocalDateTime.now());
        if (ver >= 0) {
            g.setSyncedStdVersion(ver);
        }
        gateways.save(g);
        if (wasOffline) {
            alerts.resolve("GW_OFFLINE:" + farmId + ":" + gatewayCode);
            publishConfig(farmId);
        }
    }

    private void markOffline(Gateway g, String why) {
        if ("OFFLINE".equals(g.getStatus())) {
            return;
        }
        g.setStatus("OFFLINE");
        gateways.save(g);
        alerts.raise(g.getFarmId(), null, "GW_OFFLINE", "CRITICAL", "GW_OFFLINE:" + g.getFarmId() + ":" + g.getGatewayCode(),
                "게이트웨이 " + g.getGatewayCode() + " 통신 단절 (" + why + ") — 현장은 마지막 기준값으로 안전 운전");
    }

    /** 하트비트 90초 없으면 오프라인 */
    @Scheduled(fixedDelay = 15000)
    @Transactional
    public void heartbeatCheck() {
        LocalDateTime limit = LocalDateTime.now().minusSeconds(OFFLINE_AFTER_SEC);
        for (Gateway g : gateways.findAll()) {
            if ("ONLINE".equals(g.getStatus()) && g.getLastHeartbeatAt() != null && g.getLastHeartbeatAt().isBefore(limit)) {
                markOffline(g, "하트비트 " + OFFLINE_AFTER_SEC + "초 없음");
            }
        }
    }

    @EventListener(ApplicationReadyEvent.class)
    public void publishAll() {
        gateways.findAll().stream().map(Gateway::getFarmId).distinct().forEach(this::publishConfig);
    }

    /** 기준값·안전 규칙 사본 (retained). 버전 = 현재 단계 기준값의 version_no */
    public void publishConfig(Integer farmId) {
        try {
            CropCycle cycle = cycles.findFirstByFarmIdAndStatusOrderByCycleIdDesc(farmId, "ACTIVE").orElse(null);
            String stage = cycle == null ? "GROWTH" : cycle.getCurrentStage();
            CropStd std = stds.findFirstByFarmIdAndStageAndIsCurrentTrue(farmId, stage).orElse(null);
            List<ControlRule> rs = rules.findByFarmIdAndIsEnabledTrueOrderByPriority(farmId);
            Map<String, Object> cfg = new LinkedHashMap<>();
            cfg.put("version", std == null ? 0 : std.getVersionNo());
            cfg.put("stage", stage);
            if (std != null) {
                cfg.put("std", Map.of("dayStart", std.getDayStartTime().toString(), "nightStart", std.getNightStartTime().toString(),
                        "dayTempMax", std.getDayTempMax(), "nightTempMin", std.getNightTempMin(), "substrateMin", std.getSubstrateMoistureMin()));
            }
            cfg.put("rules", rs.stream().map(r -> Map.of("code", r.getRuleCode(), "metric", r.getMetric(), "op", r.getCompareOp(),
                    "on", r.getOnThreshold(), "off", r.getOffThreshold(), "targets", r.getTargetDeviceType(), "safety", r.getIsSafety())).toList());
            cfg.put("publishedAt", LocalDateTime.now().toString());
            for (Gateway g : gateways.findByFarmId(farmId)) {
                mqtt.publish(MqttGateway.configTopic(farmId, g.getGatewayCode()), om.writeValueAsString(cfg), true);
            }
        } catch (Exception e) {
            errorLog.add("CONFIG", "기준값 발행 실패 farm=" + farmId + ": " + e.getMessage());
        }
    }
}
