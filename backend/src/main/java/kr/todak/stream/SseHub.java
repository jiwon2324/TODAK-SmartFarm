package kr.todak.stream;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/** 농장별 SSE 구독자 관리. 이벤트: reading, device, alert, command [REQ-F-18] */
@Component
public class SseHub {
    private final Map<Integer, List<SseEmitter>> byFarm = new ConcurrentHashMap<>();

    public SseEmitter subscribe(Integer farmId) {
        SseEmitter e = new SseEmitter(30 * 60 * 1000L);
        List<SseEmitter> list = byFarm.computeIfAbsent(farmId, k -> new CopyOnWriteArrayList<>());
        list.add(e);
        e.onCompletion(() -> list.remove(e));
        e.onTimeout(() -> list.remove(e));
        e.onError(t -> list.remove(e));
        try {
            e.send(SseEmitter.event().name("hello").data(Map.of("farmId", farmId)));
        } catch (IOException ex) {
            list.remove(e);
        }
        return e;
    }

    public void publish(Integer farmId, String event, Object data) {
        List<SseEmitter> list = byFarm.get(farmId);
        if (list == null) {
            return;
        }
        for (SseEmitter e : list) {
            try {
                e.send(SseEmitter.event().name(event).data(data));
            } catch (Exception ex) {
                list.remove(e);
            }
        }
    }

    /** 프록시가 유휴 연결을 끊지 않도록 25초마다 주석 이벤트 */
    @Scheduled(fixedRate = 25000)
    public void heartbeat() {
        byFarm.forEach((farm, list) -> list.forEach(e -> {
            try {
                e.send(SseEmitter.event().comment("ping"));
            } catch (Exception ex) {
                list.remove(e);
            }
        }));
    }

    public int subscriberCount() {
        return byFarm.values().stream().mapToInt(List::size).sum();
    }
}
