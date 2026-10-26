package kr.todak.alert;

import kr.todak.config.TodakProperties;
import kr.todak.domain.Alert;
import kr.todak.domain.AlertDelivery;
import kr.todak.repo.AlertDeliveryRepository;
import kr.todak.repo.AlertRepository;
import kr.todak.repo.UserFarmRepository;
import kr.todak.repo.UserRepository;
import kr.todak.stream.SseHub;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 경보 생성·중복 억제·해결. [REQ-F-09]
 * 같은 dedupe_key의 경보가 열려 있으면(OPEN·ACK) 새로 만들지 않고 발생 횟수만 올린다.
 * 해결된 뒤 다시 발생하면 새 경보다. 새 경보는 농장 사용자에게 WEB 채널로 발송 기록을 남기고 SSE로 보낸다.
 */
@Service
public class AlertService {
    private final AlertRepository alerts;
    private final AlertDeliveryRepository deliveries;
    private final UserFarmRepository userFarms;
    private final UserRepository users;
    private final SseHub sse;
    private final int dedupeMinutes;

    public AlertService(AlertRepository alerts, AlertDeliveryRepository deliveries, UserFarmRepository userFarms, UserRepository users,
                        SseHub sse, TodakProperties props) {
        this.alerts = alerts;
        this.deliveries = deliveries;
        this.userFarms = userFarms;
        this.users = users;
        this.sse = sse;
        this.dedupeMinutes = props.control().alertDedupeMinutes();
    }

    @Transactional
    public Alert raise(Integer farmId, Integer zoneId, String type, String severity, String dedupeKey, String message) {
        LocalDateTime now = LocalDateTime.now();
        Alert open = alerts.findFirstByDedupeKeyAndStatusNotOrderByAlertIdDesc(dedupeKey, "RESOLVED").orElse(null);
        if (open != null) {
            open.setOccurCount(open.getOccurCount() + 1);
            open.setLastAt(now);
            open.setMessage(message);
            return alerts.save(open);
        }
        Alert a = new Alert();
        a.setFarmId(farmId);
        a.setZoneId(zoneId);
        a.setAlertType(type);
        a.setSeverity(severity);
        a.setDedupeKey(dedupeKey);
        a.setMessage(message.length() > 300 ? message.substring(0, 300) : message);
        a.setFirstAt(now);
        a.setLastAt(now);
        a = alerts.save(a);
        for (var uf : userFarms.findByFarmId(farmId)) {
            AlertDelivery d = new AlertDelivery();
            d.setAlertId(a.getAlertId());
            d.setUserId(uf.getUserId());
            d.setChannel("WEB");
            d.setResult("SENT");
            deliveries.save(d);
        }
        for (var admin : users.findAll()) {
            if ("ADMIN".equals(admin.getRole())) {
                AlertDelivery d = new AlertDelivery();
                d.setAlertId(a.getAlertId());
                d.setUserId(admin.getUserId());
                d.setChannel("WEB");
                d.setResult("SENT");
                deliveries.save(d);
            }
        }
        sse.publish(farmId, "alert", view(a));
        return a;
    }

    @Transactional
    public void resolve(String dedupeKey) {
        for (Alert a : alerts.findByDedupeKeyAndStatusNot(dedupeKey, "RESOLVED")) {
            a.setStatus("RESOLVED");
            a.setResolvedAt(LocalDateTime.now());
            alerts.save(a);
            sse.publish(a.getFarmId(), "alert", view(a));
        }
    }

    public int dedupeMinutes() {
        return dedupeMinutes;
    }

    public static Map<String, Object> view(Alert a) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("alertId", a.getAlertId());
        m.put("farmId", a.getFarmId());
        m.put("zoneId", a.getZoneId());
        m.put("type", a.getAlertType());
        m.put("severity", a.getSeverity());
        m.put("message", a.getMessage());
        m.put("status", a.getStatus());
        m.put("occurCount", a.getOccurCount());
        m.put("firstAt", a.getFirstAt());
        m.put("lastAt", a.getLastAt());
        m.put("resolvedAt", a.getResolvedAt());
        return m;
    }
}
