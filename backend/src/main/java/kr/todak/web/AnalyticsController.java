package kr.todak.web;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import kr.todak.analytics.AnalyticsService;
import kr.todak.common.ApiException;
import kr.todak.common.FarmAccess;
import kr.todak.domain.CropCycle;
import kr.todak.repo.CropCycleRepository;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Tag(name = "생육 분석", description = "일별 환경 통계·유효적산온도(GDD) [REQ-F-14, REQ-F-15, REQ-F-10] [TB_SENSOR_DATA_HOURLY, TB_GDD_DAILY, TB_WEATHER_DAILY]")
@RestController
@RequestMapping("/api/analytics")
public class AnalyticsController {
    private final FarmAccess access;
    private final AnalyticsService analytics;
    private final CropCycleRepository cycles;

    public AnalyticsController(FarmAccess access, AnalyticsService analytics, CropCycleRepository cycles) {
        this.access = access;
        this.analytics = analytics;
        this.cycles = cycles;
    }

    @Operation(summary = "일별 GDD와 누적", description = """
            source=INTERNAL(하우스 온도센서, 시간 평균) 또는 EXTERNAL(기상청 ASOS 일자료, (최고+최저)/2).
            GDD = max(0, min(Tavg, Tupper) − Tbase). 누적은 정식일부터. coverage < 80%면 complete=false""")
    @GetMapping("/gdd")
    public Map<String, Object> gdd(@RequestParam Integer farmId, @RequestParam(defaultValue = "INTERNAL") String source,
                                   @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                   @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        access.check(farmId);
        if (!List.of("INTERNAL", "EXTERNAL").contains(source)) {
            throw ApiException.badRequest("source는 INTERNAL 또는 EXTERNAL");
        }
        CropCycle c = cycles.findFirstByFarmIdAndStatusOrderByCycleIdDesc(farmId, "ACTIVE").orElseThrow(() -> ApiException.notFound("작기"));
        LocalDate f = from == null ? c.getTransplantDate() : from;
        LocalDate t = to == null ? LocalDate.now() : to;
        if (ChronoUnit.DAYS.between(f, t) > 400) {
            throw ApiException.badRequest("최대 400일");
        }
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("cycleId", c.getCycleId());
        m.put("transplantDate", c.getTransplantDate());
        m.put("source", source);
        m.put("method", "EXTERNAL".equals(source) ? "MAXMIN" : "HOURLY");
        m.put("base", c.getGddBaseC());
        m.put("upper", c.getGddUpperC());
        m.put("dataOrigin", "EXTERNAL".equals(source) ? "기상청 ASOS 일자료 (가져온 CSV)" : "하우스 온도센서 (시뮬레이터 연결 시 시뮬레이션 데이터)");
        List<AnalyticsService.GddRow> rows = analytics.gdd(c, source, f, t);
        m.put("days", rows);
        m.put("summary", analytics.summary(c, source, rows));
        return m;
    }

    @Operation(summary = "GDD CSV 다운로드")
    @GetMapping("/gdd/export.csv")
    public void gddCsv(@RequestParam Integer farmId, @RequestParam(defaultValue = "INTERNAL") String source, HttpServletResponse res) throws IOException {
        Map<String, Object> g = gdd(farmId, source, null, null);
        res.setContentType("text/csv; charset=UTF-8");
        res.setHeader("Content-Disposition", "attachment; filename=\"todak_gdd_" + source.toLowerCase() + ".csv\"");
        PrintWriter w = new PrintWriter(new OutputStreamWriter(res.getOutputStream(), StandardCharsets.UTF_8));
        w.write('﻿');
        w.println("date,tavg_c,gdd,cum_gdd,coverage_pct,complete,source,base_c,upper_c");
        @SuppressWarnings("unchecked")
        List<AnalyticsService.GddRow> days = (List<AnalyticsService.GddRow>) g.get("days");
        for (var d : days) {
            w.println(d.date() + "," + nz(d.tavg()) + "," + nz(d.gdd()) + "," + nz(d.cumGdd()) + "," + d.coverage() + "," + d.complete() + ","
                    + source + "," + g.get("base") + "," + g.get("upper"));
        }
        w.flush();
    }

    @Operation(summary = "일별 환경 통계", description = "하우스 내부 평균·최고·최저 온도, 일교차, 평균 습도, DLI 추정치, 하우스 밖 센서(시뮬레이션), 기상청 외부 기온(가져온 경우)")
    @GetMapping("/daily")
    public List<Map<String, Object>> daily(@RequestParam Integer farmId,
                                           @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                           @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        access.check(farmId);
        if (from.isAfter(to) || ChronoUnit.DAYS.between(from, to) > 400) {
            throw ApiException.badRequest("기간 오류 (최대 400일)");
        }
        return analytics.daily(farmId, from, to);
    }

    @Operation(summary = "외부 기상 일자료 (농장 기상 지점)", description = "기상청 ASOS 일자료 중 농장에 지정된 지점(양평 202). 관리자가 CSV로 가져온 값만 있다 [REQ-F-15, API-22] [TB_WEATHER_DAILY]")
    @GetMapping("/weather")
    public List<kr.todak.domain.WeatherDaily> weather(@RequestParam Integer farmId,
                                                      @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                                      @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        access.check(farmId);
        return analytics.weatherFor(farmId, from, to);
    }

    private static String nz(Object o) {
        return o == null ? "" : o.toString();
    }
}
