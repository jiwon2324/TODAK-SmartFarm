package kr.todak.mqtt;

/** MQTT 발행 추상화. 운영은 PahoMqttGateway, 테스트는 기록용 구현을 쓴다. */
public interface MqttGateway {
    void publish(String topic, String payload, boolean retained);

    boolean isConnected();

    static String cmdTopic(Integer farmId, String deviceCode) {
        return "todak/" + farmId + "/device/" + deviceCode + "/cmd";
    }

    static String configTopic(Integer farmId, String gatewayCode) {
        return "todak/" + farmId + "/gw/" + gatewayCode + "/config";
    }

    static String scenarioTopic(Integer farmId) {
        return "todak/" + farmId + "/sim/scenario";
    }
}
