package kr.todak.mqtt;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/** MQTT를 끈 환경(테스트)에서 발행 메시지를 기록만 한다. todak.mqtt.enabled=false */
@Component
@ConditionalOnProperty(prefix = "todak.mqtt", name = "enabled", havingValue = "false")
public class RecordingMqttGateway implements MqttGateway {
    public record Published(String topic, String payload, boolean retained) {
    }

    private final List<Published> published = new ArrayList<>();

    @Override
    public synchronized void publish(String topic, String payload, boolean retained) {
        published.add(new Published(topic, payload, retained));
    }

    @Override
    public boolean isConnected() {
        return true;
    }

    public synchronized List<Published> published() {
        return new ArrayList<>(published);
    }

    public synchronized void clear() {
        published.clear();
    }
}
