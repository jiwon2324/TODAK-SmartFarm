package kr.todak.web;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import kr.todak.alert.AlertService;
import kr.todak.common.ApiException;
import kr.todak.common.FarmAccess;
import kr.todak.domain.Alert;
import kr.todak.repo.AlertRepository;
import kr.todak.stream.SseHub;
import org.springframework.data.domain.PageRequest;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Tag(name = "알림", description = "[REQ-F-09, REQ-F-06] [TB_ALERT, TB_ALERT_DELIVERY]")
@RestController
@RequestMapping("/api/alerts")
public class AlertController {
    private final FarmAccess access;
    private final AlertRepository alerts;
    private final SseHub sse;

    public AlertController(FarmAccess access, AlertRepository alerts, SseHub sse) {
        this.access = access;
        this.alerts = alerts;
        this.sse = sse;
    }

    @Operation(summary = "알림 목록", description = "farmId 없으면 접근 가능한 모든 농장. status=OPEN|ACK|RESOLVED")
    @GetMapping
    public List<Map<String, Object>> list(@RequestParam(required = false) Integer farmId, @RequestParam(required = false) String status,
                                          @RequestParam(defaultValue = "100") int size) {
        List<Integer> farms;
        if (farmId != null) {
            access.check(farmId);
            farms = List.of(farmId);
        } else {
            farms = access.allowedFarmIds();
        }
        var page = PageRequest.of(0, Math.min(size, 300));
        var p = status == null ? alerts.findByFarmIdInOrderByAlertIdDesc(farms, page) : alerts.findByFarmIdInAndStatusOrderByAlertIdDesc(farms, status, page);
        return p.map(AlertService::view).getContent();
    }

    public record StatusRequest(@Pattern(regexp = "ACK|RESOLVED") String status) {
    }

    @Operation(summary = "알림 확인·해결 처리")
    @PatchMapping("/{alertId}")
    public Map<String, Object> update(@PathVariable Long alertId, @Valid @RequestBody StatusRequest req) {
        Alert a = alerts.findById(alertId).orElseThrow(() -> ApiException.notFound("알림"));
        access.check(a.getFarmId());
        a.setStatus(req.status());
        if ("ACK".equals(req.status())) {
            a.setAckedBy(access.user().userId());
        } else {
            a.setResolvedAt(LocalDateTime.now());
        }
        alerts.save(a);
        sse.publish(a.getFarmId(), "alert", AlertService.view(a));
        return AlertService.view(a);
    }
}
