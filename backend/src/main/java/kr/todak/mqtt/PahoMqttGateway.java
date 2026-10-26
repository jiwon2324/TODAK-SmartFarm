package kr.todak.mqtt;

import jakarta.annotation.PreDestroy;
import kr.todak.common.ErrorLog;
import kr.todak.config.TodakProperties;
import org.eclipse.paho.client.mqttv3.*;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;

/**
 * Eclipse Paho 클라이언트. 구독 토픽:
 * todak/+/+/sensor/+ (측정값), todak/+/device/+/ack, todak/+/device/+/state, todak/+/gw/+/status
 */
@Component
@ConditionalOnProperty(prefix = "todak.mqtt", name = "enabled", havingValue = "true")
public class PahoMqttGateway implements MqttGateway, MqttCallbackExtended {
    private static final Logger log = LoggerFactory.getLogger(PahoMqttGateway.class);
    private static final String[] TOPICS = {"todak/+/+/sensor/+", "todak/+/device/+/ack", "todak/+/device/+/state", "todak/+/gw/+/status"};

    private final TodakProperties.Mqtt cfg;
    private final MqttMessageRouter router;
    private final ErrorLog errorLog;
    private MqttClient client;

    /** router는 명령 서비스를 거쳐 다시 이 게이트웨이를 쓰므로 순환을 끊기 위해 지연 주입한다 */
    public PahoMqttGateway(TodakProperties props, @org.springframework.context.annotation.Lazy MqttMessageRouter router, ErrorLog errorLog) {
        this.cfg = props.mqtt();
        this.router = router;
        this.errorLog = errorLog;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void start() throws MqttException {
        client = new MqttClient(cfg.url(), cfg.clientId(), new MemoryPersistence());
        client.setCallback(this);
        MqttConnectOptions o = new MqttConnectOptions();
        o.setAutomaticReconnect(true);
        // 영구 세션: 서버가 잠시 끊겨도 브로커가 QoS 1 메시지를 보관했다가 재연결 시 전달한다
        o.setCleanSession(false);
        o.setMaxInflight(200);
        o.setKeepAliveInterval(20);
        if (cfg.username() != null && !cfg.username().isBlank()) {
            o.setUserName(cfg.username());
            o.setPassword(cfg.password() == null ? new char[0] : cfg.password().toCharArray());
        }
        try {
            client.connect(o);
            log.info("MQTT 연결 성공 {}", cfg.url());
        } catch (MqttException e) {
            errorLog.add("MQTT", "최초 연결 실패: " + e.getMessage());
            log.warn("MQTT 최초 연결 실패, 자동 재연결 대기: {}", e.getMessage());
            client.connectWithResult(o);
        }
    }

    @Override
    public void connectComplete(boolean reconnect, String serverURI) {
        try {
            int[] qos = {1, 1, 1, 1};
            client.subscribe(TOPICS, qos);
            log.info("MQTT 구독 완료 (reconnect={})", reconnect);
        } catch (MqttException e) {
            errorLog.add("MQTT", "구독 실패: " + e.getMessage());
        }
    }

    @Override
    public void connectionLost(Throwable cause) {
        errorLog.add("MQTT", "브로커 연결 끊김: " + (cause == null ? "" : cause.getMessage()));
    }

    @Override
    public void messageArrived(String topic, MqttMessage message) {
        try {
            router.route(topic, new String(message.getPayload(), StandardCharsets.UTF_8));
        } catch (Exception e) {
            errorLog.add("MQTT", topic + " 처리 실패: " + e.getMessage());
            log.warn("MQTT 메시지 처리 실패 {}", topic, e);
        }
    }

    @Override
    public void deliveryComplete(IMqttDeliveryToken token) {
    }

    @Override
    public void publish(String topic, String payload, boolean retained) {
        try {
            MqttMessage m = new MqttMessage(payload.getBytes(StandardCharsets.UTF_8));
            m.setQos(1);
            m.setRetained(retained);
            client.publish(topic, m);
        } catch (MqttException e) {
            errorLog.add("MQTT", "발행 실패 " + topic + ": " + e.getMessage());
            throw new IllegalStateException("MQTT 발행 실패", e);
        }
    }

    @Override
    public boolean isConnected() {
        return client != null && client.isConnected();
    }

    @PreDestroy
    public void stop() {
        try {
            if (client != null && client.isConnected()) {
                client.disconnect();
            }
        } catch (MqttException ignored) {
        }
    }
}
