package kr.todak.alert;

import kr.todak.config.TodakProperties;
import kr.todak.domain.Beehive;
import kr.todak.domain.CropCycle;
import kr.todak.domain.Gateway;
import kr.todak.domain.Sensor;
import kr.todak.repo.BeehiveRepository;
import kr.todak.repo.CropCycleRepository;
import kr.todak.repo.GatewayRepository;
import kr.todak.repo.SensorRepository;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;

/** 센서 무응답 감지(30초마다)와 벌통 교체 알림(매일 08:00·기동 시). [REQ-F-09, REQ-F-06] */
@Component
public class MonitoringJobs {
    private final SensorRepository sensors;
    private final GatewayRepository gateways;
    private final BeehiveRepository hives;
    private final CropCycleRepository cycles;
    private final AlertService alerts;
    private final int staleSeconds;

    public MonitoringJobs(SensorRepository sensors, GatewayRepository gateways, BeehiveRepository hives, CropCycleRepository cycles,
                          AlertService alerts, TodakProperties props) {
        this.sensors = sensors;
        this.gateways = gateways;
        this.hives = hives;
        this.cycles = cycles;
        this.alerts = alerts;
        this.staleSeconds = props.control().staleSeconds();
    }

    /** 수신 이력이 있는 센서가 stale_seconds 동안 조용하면 FAULT + 경보. 게이트웨이가 오프라인이면 GW 경보가 대신한다. */
    @Scheduled(fixedDelay = 30000, initialDelay = 30000)
    @Transactional
    public void staleSensors() {
        LocalDateTime limit = LocalDateTime.now().minusSeconds(staleSeconds);
        for (Sensor s : sensors.findAll()) {
            if ("RETIRED".equals(s.getStatus()) || s.getLastReceivedAt() == null || s.getLastReceivedAt().isAfter(limit)) {
                continue;
            }
            Gateway g = gateways.findById(s.getGatewayId()).orElse(null);
            if (g != null && "OFFLINE".equals(g.getStatus())) {
                continue;
            }
            if (!"FAULT".equals(s.getStatus())) {
                s.setStatus("FAULT");
                sensors.save(s);
            }
            alerts.raise(s.getFarmId(), s.getZoneId(), "SENSOR_FAIL", "WARN", "SENSOR_FAIL:" + s.getFarmId() + ":" + s.getSensorCode(),
                    s.getSensorCode() + " 무응답 " + ChronoUnit.SECONDS.between(s.getLastReceivedAt(), LocalDateTime.now()) + "초 — 해당 센서는 제어 판단에서 제외");
        }
    }

    @EventListener(ApplicationReadyEvent.class)
    @Scheduled(cron = "0 0 8 * * *")
    @Transactional
    public void beehives() {
        LocalDate today = LocalDate.now();
        for (Beehive h : hives.findByRemovedDateIsNull()) {
            LocalDate due = h.getPlacedDate().plusDays(h.getReplaceDays());
            long left = ChronoUnit.DAYS.between(today, due);
            if (left <= 1) {
                CropCycle c = cycles.findById(h.getCycleId()).orElse(null);
                if (c == null) {
                    continue;
                }
                alerts.raise(c.getFarmId(), h.getZoneId(), "BEE", "INFO", "BEE:" + h.getHiveId() + ":" + due,
                        "벌통 #" + h.getHiveId() + " 교체 예정일 " + due + (left < 0 ? " (지남)" : left == 0 ? " (오늘)" : " (내일)"));
            }
        }
    }
}
