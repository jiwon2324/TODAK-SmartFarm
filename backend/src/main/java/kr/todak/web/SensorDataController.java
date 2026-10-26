package kr.todak.web;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import kr.todak.common.ApiException;
import kr.todak.common.FarmAccess;
import kr.todak.domain.Sensor;
import kr.todak.repo.SensorDataHourlyRepository;
import kr.todak.repo.SensorDataRepository;
import kr.todak.repo.SensorRepository;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.*;

@Tag(name = "센서·측정값", description = "[REQ-F-01, REQ-F-10] [TB_SENSOR, TB_SENSOR_DATA, TB_SENSOR_DATA_HOURLY]")
@RestController
@RequestMapping("/api")
public class SensorDataController {
    private static final long RAW_MAX_DAYS = 90;
    private final FarmAccess access;
    private final SensorRepository sensors;
    private final SensorDataRepository data;
    private final SensorDataHourlyRepository hourly;
    private final JdbcTemplate jdbc;

    public SensorDataController(FarmAccess access, SensorRepository sensors, SensorDataRepository data, SensorDataHourlyRepository hourly, JdbcTemplate jdbc) {
        this.access = access;
        this.sensors = sensors;
        this.data = data;
        this.hourly = hourly;
        this.jdbc = jdbc;
    }

    @Operation(summary = "농장 센서 목록")
    @GetMapping("/sensors")
    public List<Sensor> list(@RequestParam Integer farmId) {
        access.check(farmId);
        return sensors.findByFarmIdOrderBySensorId(farmId);
    }

    @Operation(summary = "센서 기간 조회", description = "interval=raw(1분, 최대 90일) 또는 hour(시간 집계). 400 VALIDATION_ERROR: 기간 역전·90일 초과 raw")
    @GetMapping("/sensor-data/series")
    public Map<String, Object> series(@RequestParam Integer sensorId,
                                      @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime from,
                                      @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime to,
                                      @RequestParam(defaultValue = "raw") String interval) {
        Sensor s = access.sensor(sensorId);
        if (!from.isBefore(to)) {
            throw ApiException.badRequest("from은 to보다 앞이어야 합니다");
        }
        List<Map<String, Object>> points = new ArrayList<>();
        if ("hour".equals(interval)) {
            hourly.findBySensorIdAndHourAtBetweenOrderByHourAt(sensorId, from, to).forEach(h -> points.add(
                    Map.of("t", h.getHourAt(), "avg", h.getAvgValue(), "min", h.getMinValue(), "max", h.getMaxValue(), "okCount", h.getOkCount())));
        } else {
            if (ChronoUnit.DAYS.between(from, to) > RAW_MAX_DAYS) {
                throw ApiException.badRequest("raw 조회는 최대 90일입니다. interval=hour를 쓰세요");
            }
            data.findBySensorIdAndMeasuredAtBetweenOrderByMeasuredAt(sensorId, from, to).forEach(d -> points.add(
                    Map.of("t", d.getMeasuredAt(), "value", d.getValue(), "quality", d.getQuality(), "buffered", d.getIsBuffered())));
        }
        return Map.of("sensorId", sensorId, "sensorCode", s.getSensorCode(), "metric", s.getMetric(), "unit", s.getUnit(),
                "simulated", s.getIsSimulated(), "interval", interval, "points", points);
    }

    @Operation(summary = "측정값 CSV 다운로드", description = "농장 전체 센서의 원시 1분 데이터. 열: measured_at, sensor_code, metric, value, unit, quality, data_source")
    @GetMapping("/sensor-data/export.csv")
    public void export(@RequestParam Integer farmId,
                       @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime from,
                       @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime to,
                       HttpServletResponse res) throws IOException {
        access.check(farmId);
        if (!from.isBefore(to) || ChronoUnit.DAYS.between(from, to) > RAW_MAX_DAYS) {
            throw ApiException.badRequest("기간 오류 (최대 90일)");
        }
        res.setContentType("text/csv; charset=UTF-8");
        res.setHeader("Content-Disposition", "attachment; filename=\"todak_farm" + farmId + "_sensor_data.csv\"");
        PrintWriter w = new PrintWriter(new java.io.OutputStreamWriter(res.getOutputStream(), StandardCharsets.UTF_8));
        w.write('﻿');
        w.println("measured_at,sensor_code,metric,value,unit,quality,data_source");
        jdbc.query("""
                SELECT d.measured_at, s.sensor_code, s.metric, d.value, s.unit, d.quality, s.is_simulated
                FROM TB_SENSOR_DATA d JOIN TB_SENSOR s ON s.sensor_id = d.sensor_id
                WHERE s.farm_id = ? AND d.measured_at >= ? AND d.measured_at < ? ORDER BY d.measured_at, s.sensor_id
                """, rs -> {
            w.println(rs.getTimestamp(1).toLocalDateTime() + "," + rs.getString(2) + "," + rs.getString(3) + "," + rs.getBigDecimal(4).stripTrailingZeros().toPlainString()
                    + "," + rs.getString(5) + "," + rs.getString(6) + "," + (rs.getBoolean(7) ? "SIMULATION" : "SENSOR"));
        }, farmId, from, to);
        w.flush();
    }
}
