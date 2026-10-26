package kr.todak.web;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import kr.todak.common.ApiException;
import kr.todak.common.CurrentUser;
import kr.todak.common.FarmAccess;
import kr.todak.config.TodakProperties;
import kr.todak.control.CommandService;
import kr.todak.control.DeviceStates;
import kr.todak.domain.ControlCommand;
import kr.todak.domain.Device;
import kr.todak.domain.SettingHistory;
import kr.todak.repo.ControlCommandRepository;
import kr.todak.repo.ControlLogRepository;
import kr.todak.repo.DeviceRepository;
import kr.todak.repo.SettingHistoryRepository;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.*;

@Tag(name = "장치·제어", description = "[REQ-F-08, REQ-F-16] [TB_DEVICE, TB_CONTROL_COMMAND, TB_CONTROL_LOG, TB_SETTING_HISTORY]")
@RestController
@RequestMapping("/api")
public class DeviceController {
    private final FarmAccess access;
    private final DeviceRepository devices;
    private final ControlCommandRepository commands;
    private final ControlLogRepository logs;
    private final SettingHistoryRepository history;
    private final CommandService commandService;
    private final int manualDefault;
    private final kr.todak.repo.ControlRuleRepository rules;

    public DeviceController(FarmAccess access, DeviceRepository devices, ControlCommandRepository commands, ControlLogRepository logs,
                            SettingHistoryRepository history, CommandService commandService, TodakProperties props,
                            kr.todak.repo.ControlRuleRepository rules) {
        this.access = access;
        this.rules = rules;
        this.devices = devices;
        this.commands = commands;
        this.logs = logs;
        this.history = history;
        this.commandService = commandService;
        this.manualDefault = props.control().manualDefaultMinutes();
    }

    @Operation(summary = "농장 장치 목록·상태·모드")
    @GetMapping("/devices")
    public List<Map<String, Object>> list(@RequestParam Integer farmId) {
        access.check(farmId);
        return devices.findByFarmIdOrderByDeviceId(farmId).stream().map(FarmController::deviceView).toList();
    }

    public record CommandRequest(@NotBlank String action, @Min(1) @Max(720) Integer manualMinutes, String reason, Boolean confirm) {
    }

    @Operation(summary = "수동 제어 명령", description = """
            헤더 Idempotency-Key 필수(같은 키 재요청 시 기존 명령 반환). 본문 confirm=true 필수(화면 확인 절차).
            action: ON/OFF 또는 OPEN/CLOSE. 장치를 manualMinutes(기본 60분) 동안 MANUAL 모드로 바꾸고 자동 규칙을 멈춘다.
            202 {commandId,status}. 400 CONFIRM_REQUIRED, 403, 409 DUPLICATE_REQUEST(같은 키·다른 본문), 423 SAFETY_LOCKED(안전 한계 작동 중 해제 요청), 503 GATEWAY_OFFLINE""")
    @PostMapping("/devices/{deviceId}/commands")
    public ResponseEntity<Map<String, Object>> command(@PathVariable Integer deviceId, @RequestHeader("Idempotency-Key") String idem,
                                                       @Valid @RequestBody CommandRequest req) {
        access.requireOperator();
        Device d = access.device(deviceId);
        CurrentUser u = access.user();
        if (!Boolean.TRUE.equals(req.confirm())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "CONFIRM_REQUIRED", "제어 확인(confirm=true)이 필요합니다");
        }
        if (idem.isBlank() || idem.length() > 64) {
            throw ApiException.badRequest("Idempotency-Key는 1~64자");
        }
        String action;
        try {
            action = DeviceStates.normalize(d.getDeviceType(), req.action().toUpperCase());
        } catch (IllegalArgumentException e) {
            throw ApiException.badRequest(e.getMessage());
        }
        String key = "MAN-" + u.userId() + "-" + idem;
        var prev = commandService.findByKey(key);
        if (prev.isPresent()) {
            // 같은 키 재요청: 본문이 같으면 기존 명령을 돌려주고, 다르면 409 (계획서 표 67 DUPLICATE_REQUEST)
            if (!prev.get().getDeviceId().equals(deviceId) || !prev.get().getAction().equals(action)) {
                throw new ApiException(HttpStatus.CONFLICT, "DUPLICATE_REQUEST", "같은 Idempotency-Key로 다른 요청을 보냈습니다");
            }
            return ResponseEntity.status(HttpStatus.ACCEPTED).body(CommandService.view(prev.get(), d));
        }
        if (!DeviceStates.isActive(d.getDeviceType(), action) && commandService.safetyLocked(d)) {
            throw new ApiException(HttpStatus.LOCKED, "SAFETY_LOCKED", "안전 한계(고온·저온) 제어가 작동 중이라 해제할 수 없습니다");
        }
        int minutes = req.manualMinutes() == null ? manualDefault : req.manualMinutes();
        String prevMode = d.getMode();
        d.setMode("MANUAL");
        d.setManualUntil(LocalDateTime.now().plusMinutes(minutes));
        devices.save(d);
        record(d.getDeviceId(), "mode", prevMode, "MANUAL(" + minutes + "분)", u.userId());
        ControlCommand c = commandService.create(d, action, "MANUAL", null, u.userId(), key,
                req.reason() == null ? "수동 제어" : req.reason(), null);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(CommandService.view(c, d));
    }

    public record ModeRequest(@Pattern(regexp = "AUTO|MANUAL") String mode, @Min(1) @Max(720) Integer manualMinutes) {
    }

    @Operation(summary = "자동/수동 모드 전환", description = "MANUAL이면 manualMinutes 뒤 AUTO로 자동 복귀")
    @PatchMapping("/devices/{deviceId}/mode")
    @Transactional
    public Map<String, Object> mode(@PathVariable Integer deviceId, @Valid @RequestBody ModeRequest req) {
        access.requireOperator();
        Device d = access.device(deviceId);
        String prev = d.getMode();
        d.setMode(req.mode());
        d.setManualUntil("MANUAL".equals(req.mode()) ? LocalDateTime.now().plusMinutes(req.manualMinutes() == null ? manualDefault : req.manualMinutes()) : null);
        devices.save(d);
        record(deviceId, "mode", prev, req.mode(), access.user().userId());
        return FarmController.deviceView(d);
    }

    @Operation(summary = "명령 상태 조회")
    @GetMapping("/controls/commands/{commandId}")
    public Map<String, Object> commandStatus(@PathVariable Long commandId) {
        ControlCommand c = commands.findById(commandId).orElseThrow(() -> ApiException.notFound("명령"));
        Device d = access.device(c.getDeviceId());
        return CommandService.view(c, d);
    }

    @Operation(summary = "제어 명령 이력", description = "최근 순, size 최대 200")
    @GetMapping("/controls/commands")
    public List<Map<String, Object>> commandList(@RequestParam Integer farmId, @RequestParam(defaultValue = "50") int size) {
        access.check(farmId);
        Map<Integer, Device> ds = byId(farmId);
        return commands.findByDeviceIdInOrderByCommandIdDesc(ds.keySet(), PageRequest.of(0, Math.min(size, 200)))
                .map(c -> CommandService.view(c, ds.get(c.getDeviceId()))).getContent();
    }

    @Operation(summary = "장치 상태 변경 이력", description = "ACK·FAILSAFE로 실제 바뀐 상태만 기록")
    @GetMapping("/controls/logs")
    public List<Map<String, Object>> stateLogs(@RequestParam Integer farmId, @RequestParam(defaultValue = "50") int size) {
        access.check(farmId);
        Map<Integer, Device> ds = byId(farmId);
        return logs.findByDeviceIdInOrderByLogIdDesc(ds.keySet(), PageRequest.of(0, Math.min(size, 200))).map(l -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("logId", l.getLogId());
            m.put("deviceCode", ds.get(l.getDeviceId()).getDeviceCode());
            m.put("deviceName", ds.get(l.getDeviceId()).getDeviceName());
            m.put("commandId", l.getCommandId());
            m.put("prevState", l.getPrevState());
            m.put("newState", l.getNewState());
            m.put("changedBy", l.getChangedBy());
            m.put("changedAt", l.getChangedAt());
            return m;
        }).getContent();
    }

    private Map<Integer, Device> byId(Integer farmId) {
        Map<Integer, Device> m = new LinkedHashMap<>();
        devices.findByFarmIdOrderByDeviceId(farmId).forEach(d -> m.put(d.getDeviceId(), d));
        return m;
    }

    private void record(Integer deviceId, String field, String oldV, String newV, Integer userId) {
        SettingHistory h = new SettingHistory();
        h.setEntityType("DEVICE");
        h.setEntityId(deviceId.longValue());
        h.setFieldName(field);
        h.setOldValue(oldV);
        h.setNewValue(newV);
        h.setChangedBy(userId);
        history.save(h);
    }

    @Operation(summary = "자동 제어 규칙 조회 (읽기 전용)", description = "농가·조회 전용 사용자도 자기 농장 규칙을 볼 수 있다. 수정은 관리자 API(/api/admin/rules) [API-17, REQ-F-02~04] [TB_CONTROL_RULE]")
    @GetMapping("/controls/rules")
    public List<kr.todak.domain.ControlRule> rules(@RequestParam Integer farmId) {
        access.check(farmId);
        return rules.findByFarmIdOrderByPriority(farmId);
    }
}
