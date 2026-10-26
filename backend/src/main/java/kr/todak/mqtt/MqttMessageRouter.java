package kr.todak.mqtt;

import kr.todak.control.CommandService;
import kr.todak.control.GatewayService;
import kr.todak.ingest.SensorIngestService;
import org.springframework.stereotype.Component;

/**
 * 토픽 구조 (개발 계획서 12장)
 * todak/{farmId}/{zoneCode|COMMON}/sensor/{sensorCode}
 * todak/{farmId}/device/{deviceCode}/ack | state
 * todak/{farmId}/gw/{gatewayCode}/status
 */
@Component
public class MqttMessageRouter {
    private final SensorIngestService ingest;
    private final CommandService commands;
    private final GatewayService gateways;

    public MqttMessageRouter(SensorIngestService ingest, CommandService commands, GatewayService gateways) {
        this.ingest = ingest;
        this.commands = commands;
        this.gateways = gateways;
    }

    public void route(String topic, String payload) {
        String[] t = topic.split("/");
        if (t.length < 5 || !"todak".equals(t[0])) {
            ingest.reject("알 수 없는 토픽: " + topic);
            return;
        }
        Integer farmId;
        try {
            farmId = Integer.valueOf(t[1]);
        } catch (NumberFormatException e) {
            ingest.reject("농장 ID 형식 오류: " + topic);
            return;
        }
        if ("sensor".equals(t[3])) {
            ingest.ingest(farmId, t[4], payload);
        } else if ("device".equals(t[2]) && "ack".equals(t[4])) {
            commands.handleAck(farmId, t[3], payload);
        } else if ("device".equals(t[2]) && "state".equals(t[4])) {
            commands.handleState(farmId, t[3], payload);
        } else if ("gw".equals(t[2]) && "status".equals(t[4])) {
            gateways.handleStatus(farmId, t[3], payload);
        }
    }
}
