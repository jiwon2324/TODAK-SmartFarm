package kr.todak.web;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import kr.todak.common.ApiException;
import kr.todak.common.FarmAccess;
import kr.todak.control.GatewayService;
import kr.todak.domain.Beehive;
import kr.todak.domain.CropCycle;
import kr.todak.domain.CropStd;
import kr.todak.domain.SettingHistory;
import kr.todak.repo.BeehiveRepository;
import kr.todak.repo.CropCycleRepository;
import kr.todak.repo.CropStdRepository;
import kr.todak.repo.SettingHistoryRepository;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Tag(name = "재배 관리", description = "재배 기준값(버전)·작기·벌통 [REQ-F-11, REQ-F-14, REQ-F-06] [TB_CROP_STD, TB_CROP_CYCLE, TB_BEEHIVE, TB_SETTING_HISTORY]")
@RestController
@RequestMapping("/api")
public class CropController {
    private final FarmAccess access;
    private final CropStdRepository stds;
    private final CropCycleRepository cycles;
    private final BeehiveRepository hives;
    private final SettingHistoryRepository history;
    private final GatewayService gateways;

    public CropController(FarmAccess access, CropStdRepository stds, CropCycleRepository cycles, BeehiveRepository hives,
                          SettingHistoryRepository history, GatewayService gateways) {
        this.access = access;
        this.stds = stds;
        this.cycles = cycles;
        this.hives = hives;
        this.history = history;
        this.gateways = gateways;
    }

    @Operation(summary = "재배 기준값 (현재 버전 + 이력)")
    @GetMapping("/crop-standards")
    public Map<String, Object> standards(@RequestParam Integer farmId) {
        access.check(farmId);
        return Map.of("current", stds.findByFarmIdAndIsCurrentTrueOrderByStage(farmId), "all", stds.findByFarmIdOrderByStageAscVersionNoDesc(farmId));
    }

    public record StdRequest(@NotNull Integer farmId, @Pattern(regexp = "NURSERY|GROWTH|FLOWER|HARVEST") String stage,
                             @NotNull Double dayTempMin, @NotNull Double dayTempMax, @NotNull Double nightTempMin, @NotNull Double nightTempMax,
                             @NotNull Double humidityMin, @NotNull Double humidityMax, @NotNull Double ecMin, @NotNull Double ecMax,
                             @NotNull Double phMin, @NotNull Double phMax, Double substrateMoistureMin, @Size(max = 200) String sourceNote) {
    }

    @Operation(summary = "재배 기준값 새 버전 등록", description = "이전 버전은 is_current=0으로 남고 새 버전이 적용된다. 저장 즉시 게이트웨이 config 재발행. 400: 최소>최대")
    @PostMapping("/crop-standards")
    @Transactional
    public CropStd create(@Valid @RequestBody StdRequest r) {
        access.check(r.farmId());
        if (r.dayTempMin() >= r.dayTempMax() || r.nightTempMin() >= r.nightTempMax() || r.humidityMin() >= r.humidityMax()
                || r.ecMin() >= r.ecMax() || r.phMin() >= r.phMax()) {
            throw ApiException.badRequest("각 항목의 최솟값은 최댓값보다 작아야 합니다");
        }
        CropStd prev = stds.findFirstByFarmIdAndStageOrderByVersionNoDesc(r.farmId(), r.stage()).orElse(null);
        if (prev != null) {
            prev.setIsCurrent(false);
            stds.saveAndFlush(prev);
        }
        CropStd s = new CropStd();
        s.setFarmId(r.farmId());
        s.setStage(r.stage());
        s.setVersionNo(prev == null ? 1 : prev.getVersionNo() + 1);
        s.setDayTempMin(r.dayTempMin());
        s.setDayTempMax(r.dayTempMax());
        s.setNightTempMin(r.nightTempMin());
        s.setNightTempMax(r.nightTempMax());
        s.setHumidityMin(r.humidityMin());
        s.setHumidityMax(r.humidityMax());
        s.setEcMin(r.ecMin());
        s.setEcMax(r.ecMax());
        s.setPhMin(r.phMin());
        s.setPhMax(r.phMax());
        s.setSubstrateMoistureMin(r.substrateMoistureMin());
        s.setSourceNote(r.sourceNote());
        s.setCreatedBy(access.user().userId());
        if (prev != null) {
            s.setDayStartTime(prev.getDayStartTime());
            s.setNightStartTime(prev.getNightStartTime());
        }
        s = stds.save(s);
        record("CROP_STD", s.getStdId().longValue(), "version_no(" + r.stage() + ")", prev == null ? null : String.valueOf(prev.getVersionNo()), String.valueOf(s.getVersionNo()));
        gateways.publishConfig(r.farmId());
        return s;
    }

    @Operation(summary = "현재 작기")
    @GetMapping("/crop-cycles/current")
    public CropCycle currentCycle(@RequestParam Integer farmId) {
        access.check(farmId);
        return cycles.findFirstByFarmIdAndStatusOrderByCycleIdDesc(farmId, "ACTIVE").orElseThrow(() -> ApiException.notFound("작기"));
    }

    public record CycleRequest(LocalDate transplantDate, @Pattern(regexp = "NURSERY|GROWTH|FLOWER|HARVEST") String currentStage,
                               @DecimalMin("0") @DecimalMax("20") Double gddBaseC, @DecimalMin("20") @DecimalMax("40") Double gddUpperC) {
    }

    @Operation(summary = "작기 수정 (정식일·생육 단계·GDD 기준온도)", description = "변경 내역은 TB_SETTING_HISTORY에 남고, 저장된 GDD는 다음 조회 때 새 기준으로 다시 계산된다")
    @PatchMapping("/crop-cycles/{cycleId}")
    @Transactional
    public CropCycle updateCycle(@PathVariable Integer cycleId, @Valid @RequestBody CycleRequest r) {
        CropCycle c = cycles.findById(cycleId).orElseThrow(() -> ApiException.notFound("작기"));
        access.check(c.getFarmId());
        if (r.transplantDate() != null && !r.transplantDate().equals(c.getTransplantDate())) {
            record("CROP_CYCLE", cycleId.longValue(), "transplant_date", String.valueOf(c.getTransplantDate()), String.valueOf(r.transplantDate()));
            c.setTransplantDate(r.transplantDate());
        }
        if (r.currentStage() != null && !r.currentStage().equals(c.getCurrentStage())) {
            record("CROP_CYCLE", cycleId.longValue(), "current_stage", c.getCurrentStage(), r.currentStage());
            c.setCurrentStage(r.currentStage());
        }
        if (r.gddBaseC() != null && !r.gddBaseC().equals(c.getGddBaseC())) {
            record("CROP_CYCLE", cycleId.longValue(), "gdd_base_c", String.valueOf(c.getGddBaseC()), String.valueOf(r.gddBaseC()));
            c.setGddBaseC(r.gddBaseC());
        }
        if (r.gddUpperC() != null && !r.gddUpperC().equals(c.getGddUpperC())) {
            record("CROP_CYCLE", cycleId.longValue(), "gdd_upper_c", String.valueOf(c.getGddUpperC()), String.valueOf(r.gddUpperC()));
            c.setGddUpperC(r.gddUpperC());
        }
        if (c.getGddUpperC() <= c.getGddBaseC()) {
            throw ApiException.badRequest("상한온도는 기준온도보다 커야 합니다");
        }
        cycles.save(c);
        gateways.publishConfig(c.getFarmId());
        return c;
    }

    @Operation(summary = "벌통 목록")
    @GetMapping("/beehives")
    public List<Beehive> hives(@RequestParam Integer farmId) {
        access.check(farmId);
        CropCycle c = cycles.findFirstByFarmIdAndStatusOrderByCycleIdDesc(farmId, "ACTIVE").orElse(null);
        return c == null ? List.of() : hives.findByCycleIdOrderByHiveIdDesc(c.getCycleId());
    }

    public record HiveRequest(@NotNull Integer farmId, @NotNull LocalDate placedDate, @NotNull @Min(1) @Max(60) Integer replaceDays) {
    }

    @Operation(summary = "벌통 등록", description = "교체 예정일 하루 전부터 BEE 알림")
    @PostMapping("/beehives")
    public Beehive addHive(@Valid @RequestBody HiveRequest r) {
        access.check(r.farmId());
        CropCycle c = cycles.findFirstByFarmIdAndStatusOrderByCycleIdDesc(r.farmId(), "ACTIVE").orElseThrow(() -> ApiException.notFound("작기"));
        hives.findByCycleIdOrderByHiveIdDesc(c.getCycleId()).stream().filter(h -> h.getRemovedDate() == null).forEach(h -> {
            h.setRemovedDate(r.placedDate());
            hives.save(h);
        });
        Beehive h = new Beehive();
        h.setCycleId(c.getCycleId());
        h.setPlacedDate(r.placedDate());
        h.setReplaceDays(r.replaceDays());
        return hives.save(h);
    }

    private void record(String type, Long id, String field, String oldV, String newV) {
        SettingHistory h = new SettingHistory();
        h.setEntityType(type);
        h.setEntityId(id);
        h.setFieldName(field);
        h.setOldValue(oldV);
        h.setNewValue(newV);
        h.setChangedBy(access.user().userId());
        h.setChangedAt(LocalDateTime.now());
        history.save(h);
    }
}
