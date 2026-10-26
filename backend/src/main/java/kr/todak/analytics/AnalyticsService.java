package kr.todak.analytics;

import kr.todak.domain.CropCycle;
import kr.todak.domain.GddDaily;
import kr.todak.domain.WeatherDaily;
import kr.todak.repo.CropCycleRepository;
import kr.todak.repo.FarmRepository;
import kr.todak.repo.GddDailyRepository;
import kr.todak.repo.WeatherDailyRepository;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.*;

/**
 * 생육 분석: 일별 환경 통계, 내부·외부 GDD. [REQ-F-14, REQ-F-15, REQ-F-10]
 * 내부 GDD는 하우스 온도센서(metric TEMP) 시간 집계에서, 외부 GDD는 TB_WEATHER_DAILY(기상청 ASOS)에서 따로 계산한다.
 * 하우스 밖 센서(TEMP_OUT, 시뮬레이션)는 외부 GDD에 쓰지 않는다 — 출처가 다르기 때문.
 */
@Service
public class AnalyticsService {
    private final JdbcTemplate jdbc;
    private final CropCycleRepository cycles;
    private final GddDailyRepository gddRepo;
    private final WeatherDailyRepository weather;
    private final FarmRepository farms;

    public AnalyticsService(JdbcTemplate jdbc, CropCycleRepository cycles, GddDailyRepository gddRepo, WeatherDailyRepository weather, FarmRepository farms) {
        this.jdbc = jdbc;
        this.cycles = cycles;
        this.gddRepo = gddRepo;
        this.weather = weather;
        this.farms = farms;
    }

    public record GddRow(LocalDate date, Double tavg, Double gdd, Double cumGdd, double coverage, boolean complete) {
    }

    /** 일별 GDD와 정식일부터의 누적. 지난 날짜는 TB_GDD_DAILY에 저장(오늘은 진행 중이라 저장하지 않음). */
    @Transactional
    public List<GddRow> gdd(CropCycle c, String source, LocalDate from, LocalDate to) {
        LocalDate start = c.getTransplantDate();
        LocalDate today = LocalDate.now();
        LocalDate end = to.isAfter(today) ? today : to;
        List<GddRow> out = new ArrayList<>();
        double cum = 0;
        Map<LocalDate, GddCalculator.Day> days = "EXTERNAL".equals(source) ? externalDays(c, start, end) : internalDays(c, start, end);
        for (LocalDate d = start; !d.isAfter(end); d = d.plusDays(1)) {
            GddCalculator.Day day = days.getOrDefault(d, new GddCalculator.Day(null, null, 0.0, false));
            if (day.gdd() != null) {
                cum += day.gdd();
            }
            if (d.isBefore(today)) {
                save(c, d, source, day, cum);
            }
            if (!d.isBefore(from)) {
                out.add(new GddRow(d, day.tavg(), day.gdd(), day.gdd() == null && cum == 0 ? null : GddCalculator.round(cum, 2), day.coveragePct(), day.complete()));
            }
        }
        return out;
    }

    private Map<LocalDate, GddCalculator.Day> internalDays(CropCycle c, LocalDate from, LocalDate to) {
        // 시간대별로 TEMP 센서(구역 2개) 평균을 먼저 낸 뒤, 그 시간 평균들로 일평균을 계산
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT DATE(h.hour_at) d, h.hour_at hr, AVG(h.avg_value) v
                FROM TB_SENSOR_DATA_HOURLY h JOIN TB_SENSOR s ON s.sensor_id = h.sensor_id
                WHERE s.farm_id = ? AND s.metric = 'TEMP' AND h.hour_at >= ? AND h.hour_at < ?
                GROUP BY DATE(h.hour_at), h.hour_at ORDER BY hr
                """, c.getFarmId(), from.atStartOfDay(), to.plusDays(1).atStartOfDay());
        Map<LocalDate, List<Double>> byDay = new TreeMap<>();
        for (var r : rows) {
            LocalDate d = ((java.sql.Date) r.get("d")).toLocalDate();
            byDay.computeIfAbsent(d, k -> new ArrayList<>()).add(((Number) r.get("v")).doubleValue());
        }
        Map<LocalDate, GddCalculator.Day> m = new HashMap<>();
        byDay.forEach((d, hours) -> m.put(d, GddCalculator.fromHourly(hours, c.getGddBaseC(), c.getGddUpperC())));
        return m;
    }

    private Map<LocalDate, GddCalculator.Day> externalDays(CropCycle c, LocalDate from, LocalDate to) {
        String station = farms.findById(c.getFarmId()).map(f -> f.getKmaStationId()).orElse(null);
        Map<LocalDate, GddCalculator.Day> m = new HashMap<>();
        if (station == null) {
            return m;
        }
        for (WeatherDaily w : weather.findByStationIdAndObsDateBetweenOrderByObsDate(station, from, to)) {
            m.put(w.getObsDate(), GddCalculator.fromMaxMin(w.getTmaxC(), w.getTminC(), w.getTavgC(), c.getGddBaseC(), c.getGddUpperC()));
        }
        return m;
    }

    private void save(CropCycle c, LocalDate d, String source, GddCalculator.Day day, double cum) {
        GddDaily g = gddRepo.findById(new GddDaily.Key(c.getCycleId(), d, source)).orElseGet(GddDaily::new);
        g.setCycleId(c.getCycleId());
        g.setCalcDate(d);
        g.setSource(source);
        g.setMethod("EXTERNAL".equals(source) ? "MAXMIN" : "HOURLY");
        g.setTavgC(day.tavg());
        g.setBaseC(c.getGddBaseC());
        g.setUpperC(c.getGddUpperC());
        g.setGdd(day.gdd());
        g.setCumGdd(GddCalculator.round(cum, 2));
        g.setCoveragePct(day.coveragePct());
        g.setIsComplete(day.complete());
        g.setCalculatedAt(java.time.LocalDateTime.now());
        gddRepo.save(g);
    }

    /** 매일 00:30 전날까지 다시 계산해 저장 */
    @Scheduled(cron = "0 30 0 * * *")
    @Transactional
    public void nightly() {
        LocalDate y = LocalDate.now().minusDays(1);
        for (CropCycle c : cycles.findByStatus("ACTIVE")) {
            gdd(c, "INTERNAL", y, y);
            gdd(c, "EXTERNAL", y, y);
        }
    }

    /** 일별 하우스 내부 환경 통계 (시간 집계 기준) + 외부 기상청 자료(있으면) */
    public List<Map<String, Object>> daily(Integer farmId, LocalDate from, LocalDate to) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT DATE(h.hour_at) d, s.metric m, AVG(h.avg_value) av, MIN(h.min_value) mn, MAX(h.max_value) mx, SUM(h.ok_count) n
                FROM TB_SENSOR_DATA_HOURLY h JOIN TB_SENSOR s ON s.sensor_id = h.sensor_id
                WHERE s.farm_id = ? AND s.metric IN ('TEMP','HUMI','TEMP_OUT','SOLAR') AND h.hour_at >= ? AND h.hour_at < ?
                GROUP BY DATE(h.hour_at), s.metric ORDER BY d
                """, farmId, from.atStartOfDay(), to.plusDays(1).atStartOfDay());
        Map<LocalDate, Map<String, Object>> byDay = new TreeMap<>();
        for (var r : rows) {
            LocalDate d = ((java.sql.Date) r.get("d")).toLocalDate();
            Map<String, Object> day = byDay.computeIfAbsent(d, k -> new LinkedHashMap<>(Map.of("date", k.toString())));
            String m = (String) r.get("m");
            double av = ((Number) r.get("av")).doubleValue();
            double mn = ((Number) r.get("mn")).doubleValue();
            double mx = ((Number) r.get("mx")).doubleValue();
            switch (m) {
                case "TEMP" -> {
                    day.put("tempAvg", r1(av));
                    day.put("tempMin", r1(mn));
                    day.put("tempMax", r1(mx));
                    day.put("diurnal", r1(mx - mn));
                }
                case "HUMI" -> day.put("humiAvg", r1(av));
                case "TEMP_OUT" -> {
                    day.put("outSensorAvg", r1(av));
                    day.put("outSensorMin", r1(mn));
                    day.put("outSensorMax", r1(mx));
                }
                case "SOLAR" -> day.put("dliEstimate", r1(av * 24 * 3600 * 2.02 / 1_000_000));
                default -> {
                }
            }
        }
        String station = farms.findById(farmId).map(f -> f.getKmaStationId()).orElse(null);
        if (station != null) {
            for (WeatherDaily w : weather.findByStationIdAndObsDateBetweenOrderByObsDate(station, from, to)) {
                Map<String, Object> day = byDay.computeIfAbsent(w.getObsDate(), k -> new LinkedHashMap<>(Map.of("date", k.toString())));
                day.put("kmaTavg", w.getTavgC());
                day.put("kmaTmin", w.getTminC());
                day.put("kmaTmax", w.getTmaxC());
            }
        }
        return new ArrayList<>(byDay.values());
    }

    private static Double r1(double v) {
        return Math.round(v * 10) / 10.0;
    }
}
