package kr.todak.control;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import kr.todak.alert.AlertService;
import kr.todak.common.ApiException;
import kr.todak.common.ErrorLog;
import kr.todak.config.TodakProperties;
import kr.todak.domain.ControlCommand;
import kr.todak.domain.ControlLog;
import kr.todak.domain.Device;
import kr.todak.domain.Gateway;
import kr.todak.mqtt.MqttGateway;
import kr.todak.repo.ControlCommandRepository;
import kr.todak.repo.ControlLogRepository;
import kr.todak.repo.DeviceRepository;
import kr.todak.repo.GatewayRepository;
import org.springframework.http.HttpStatus;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 제어 명령 수명주기 [REQ-F-08, REQ-F-16]
 * REQUESTED(저장) → SENT(MQTT 발행) → ACKED(장치 응답 OK) / FAILED(장치 응답 ERROR·발행 실패) / TIMEOUT(재전송 후에도 무응답)
 * 명령을 보낸 것과 장치가 실제로 동작한 것을 구분해, 장치 상태(TB_DEVICE.current_state)와 TB_CONTROL_LOG는 ACK를 받았을 때만 바꾼다.
 */
@Service
public class CommandService {
    private static final ZoneId SEOUL = ZoneId.of("Asia/Seoul");
    public static final List<String> PENDING = List.of("REQUESTED", "SENT");
    private final ObjectMapper om = new ObjectMapper();
    private final ControlCommandRepository commands;
    private final ControlLogRepository logs;
    private final DeviceRepository devices;
    private final GatewayRepository gateways;
    private final MqttGateway mqtt;
    private final AlertService alerts;
    private final kr.todak.stream.SseHub sse;
    private final ErrorLog errorLog;
    private final int ackTimeout;

    public CommandService(ControlCommandRepository commands, ControlLogRepository logs, DeviceRepository devices, GatewayRepository gateways,
                          MqttGateway mqtt, AlertService alerts, kr.todak.stream.SseHub sse, ErrorLog errorLog, TodakProperties props) {
        this.commands = commands;
        this.logs = logs;
        this.devices = devices;
        this.gateways = gateways;
        this.mqtt = mqtt;
        this.alerts = alerts;
        this.sse = sse;
        this.errorLog = errorLog;
        this.ackTimeout = props.control().ackTimeoutSeconds();
    }

    /**
     * 멱등키가 이미 있으면 기존 명령을 돌려준다(중복 실행 방지).
     * 트랜잭션을 걸지 않는다: 명령 행을 먼저 커밋하고 발행해야, 빠르게 돌아온 ACK가 명령을 찾을 수 있다.
     */
    public ControlCommand create(Device d, String action, String source, Integer ruleId, Integer userId, String idemKey, String reason, Integer durationSec) {
        var existing = commands.findByIdempotencyKey(idemKey);
        if (existing.isPresent()) {
            return existing.get();
        }
        String act = DeviceStates.normalize(d.getDeviceType(), action);
        Gateway gw = gateways.findById(d.getGatewayId()).orElseThrow();
        if ("OFFLINE".equals(gw.getStatus())) {
            if ("MANUAL".equals(source)) {
                throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "GATEWAY_OFFLINE", "게이트웨이 " + gw.getGatewayCode() + " 오프라인 — 명령을 보낼 수 없습니다");
            }
            return null;
        }
        ControlCommand c = new ControlCommand();
        c.setDeviceId(d.getDeviceId());
        c.setAction(act);
        c.setDurationSec(durationSec);
        c.setSource(source);
        c.setRuleId(ruleId);
        c.setRequestedBy(userId);
        c.setIdempotencyKey(idemKey);
        c.setReason(reason);
        c.setRequestedAt(LocalDateTime.now());
        c = commands.saveAndFlush(c);
        send(c, d);
        return c;
    }

    private void send(ControlCommand c, Device d) {
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("commandId", c.getCommandId());
        p.put("action", c.getAction());
        p.put("durationSec", c.getDurationSec());
        p.put("source", c.getSource());
        p.put("issuedAt", OffsetDateTime.now(SEOUL).toString());
        // SENT를 먼저 저장한 뒤 발행: ACK가 저장보다 먼저 도착해 상태를 덮어쓰는 경쟁을 막는다
        c.setStatus("SENT");
        c.setSentAt(LocalDateTime.now());
        commands.saveAndFlush(c);
        try {
            mqtt.publish(MqttGateway.cmdTopic(d.getFarmId(), d.getDeviceCode()), om.writeValueAsString(p), false);
        } catch (Exception e) {
            c.setStatus("FAILED");
            c.setReason(trim((c.getReason() == null ? "" : c.getReason() + " / ") + "발행 실패: " + e.getMessage()));
            errorLog.add("COMMAND", "명령 " + c.getCommandId() + " 발행 실패: " + e.getMessage());
            commands.save(c);
        }
        sse.publish(d.getFarmId(), "command", view(c, d));
    }

    @Transactional
    public void handleAck(Integer farmId, String deviceCode, String payload) {
        JsonNode j;
        try {
            j = om.readTree(payload);
        } catch (Exception e) {
            errorLog.add("ACK", "ACK JSON 오류 " + deviceCode);
            return;
        }
        long id = j.path("commandId").asLong(-1);
        ControlCommand c = commands.findById(id).orElse(null);
        Device d = devices.findByFarmIdAndDeviceCode(farmId, deviceCode).orElse(null);
        if (c == null || d == null || !c.getDeviceId().equals(d.getDeviceId())) {
            errorLog.add("ACK", "알 수 없는 명령 ACK " + deviceCode + " id=" + id);
            return;
        }
        if (!PENDING.contains(c.getStatus()) && !"TIMEOUT".equals(c.getStatus())) {
            return;
        }
        LocalDateTime now = LocalDateTime.now();
        String result = j.path("result").asText("OK");
        boolean wasTimeout = "TIMEOUT".equals(c.getStatus());
        if ("OK".equals(result)) {
            String newState = j.path("state").asText(c.getAction());
            c.setStatus("ACKED");
            c.setAckedAt(now);
            changeState(d, newState, c.getSource(), c.getCommandId(), now);
            if (wasTimeout) {
                c.setReason(trim("시간 초과 후 늦은 ACK 수신"));
            }
            alerts.resolve("DEVICE_NOACK:" + farmId + ":" + deviceCode);
            alerts.resolve("DEVICE_FAIL:" + farmId + ":" + deviceCode);
        } else {
            c.setStatus("FAILED");
            c.setAckedAt(now);
            c.setReason(trim("장치 응답 오류: " + j.path("error").asText(result)));
            alerts.raise(farmId, d.getZoneId(), "DEVICE_NOACK", "WARN", "DEVICE_FAIL:" + farmId + ":" + deviceCode,
                    d.getDeviceName() + " 제어 실패 (" + c.getAction() + "): " + j.path("error").asText(result));
        }
        commands.save(c);
        sse.publish(farmId, "command", view(c, d));
    }

    /** 서버 명령 없이 바뀐 상태 보고 (게이트웨이 안전 운전 FAILSAFE, 현장 수동 조작 LOCAL) */
    @Transactional
    public void handleState(Integer farmId, String deviceCode, String payload) {
        try {
            JsonNode j = om.readTree(payload);
            Device d = devices.findByFarmIdAndDeviceCode(farmId, deviceCode).orElse(null);
            if (d == null) {
                errorLog.add("STATE", "알 수 없는 장치 " + deviceCode);
                return;
            }
            LocalDateTime at = j.hasNonNull("at") ? OffsetDateTime.parse(j.get("at").asText()).atZoneSameInstant(SEOUL).toLocalDateTime() : LocalDateTime.now();
            changeState(d, j.path("state").asText(), j.path("changedBy").asText("FAILSAFE"), null, at);
        } catch (Exception e) {
            errorLog.add("STATE", "상태 보고 처리 실패 " + deviceCode + ": " + e.getMessage());
        }
    }

    private void changeState(Device d, String newState, String changedBy, Long commandId, LocalDateTime at) {
        String prev = d.getCurrentState();
        if (!newState.equals(prev)) {
            d.setCurrentState(newState);
            d.setStateChangedAt(at);
            devices.save(d);
        }
        ControlLog l = new ControlLog();
        l.setDeviceId(d.getDeviceId());
        l.setCommandId(commandId);
        l.setPrevState(prev);
        l.setNewState(newState);
        l.setChangedBy(changedBy.length() > 10 ? changedBy.substring(0, 10) : changedBy);
        l.setChangedAt(at);
        logs.save(l);
        Map<String, Object> ev = new LinkedHashMap<>();
        ev.put("deviceId", d.getDeviceId());
        ev.put("deviceCode", d.getDeviceCode());
        ev.put("state", newState);
        ev.put("mode", d.getMode());
        ev.put("changedBy", changedBy);
        ev.put("at", at.toString());
        sse.publish(d.getFarmId(), "device", ev);
    }

    /** ACK 대기 시간 초과: 1회 재전송, 그래도 없으면 TIMEOUT + 경보 */
    @Scheduled(fixedDelay = 2000)
    public void checkTimeouts() {
        LocalDateTime limit = LocalDateTime.now().minusSeconds(ackTimeout);
        for (ControlCommand c : commands.findByStatusIn(List.of("SENT"))) {
            if (c.getSentAt() == null || c.getSentAt().isAfter(limit)) {
                continue;
            }
            Device d = devices.findById(c.getDeviceId()).orElse(null);
            if (d == null) {
                continue;
            }
            if (c.getRetryCount() == 0) {
                c.setRetryCount((byte) 1);
                send(c, d);
            } else {
                c.setStatus("TIMEOUT");
                commands.save(c);
                alerts.raise(d.getFarmId(), d.getZoneId(), "DEVICE_NOACK", "CRITICAL", "DEVICE_NOACK:" + d.getFarmId() + ":" + d.getDeviceCode(),
                        d.getDeviceName() + " 응답 없음 — 명령 " + c.getCommandId() + "(" + c.getAction() + ") 재전송 후에도 ACK 없음");
                sse.publish(d.getFarmId(), "command", view(c, d));
            }
        }
    }

    /** 안전 한계 명령이 최근 10분 안에 장치를 활성화했는지 */
    public boolean safetyLocked(Device d) {
        return commands.findFirstByDeviceIdAndStatusOrderByCommandIdDesc(d.getDeviceId(), "ACKED")
                .filter(c -> "SAFETY".equals(c.getSource()) && c.getAckedAt() != null
                        && ChronoUnit.MINUTES.between(c.getAckedAt(), LocalDateTime.now()) < 10
                        && DeviceStates.isActive(d.getDeviceType(), c.getAction()))
                .isPresent();
    }

    public static Map<String, Object> view(ControlCommand c, Device d) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("commandId", c.getCommandId());
        m.put("deviceId", c.getDeviceId());
        m.put("deviceCode", d == null ? null : d.getDeviceCode());
        m.put("deviceName", d == null ? null : d.getDeviceName());
        m.put("action", c.getAction());
        m.put("source", c.getSource());
        m.put("status", c.getStatus());
        m.put("retryCount", c.getRetryCount());
        m.put("reason", c.getReason());
        m.put("requestedAt", c.getRequestedAt());
        m.put("sentAt", c.getSentAt());
        m.put("ackedAt", c.getAckedAt());
        return m;
    }

    private static String trim(String s) {
        return s.length() > 200 ? s.substring(0, 200) : s;
    }
}
