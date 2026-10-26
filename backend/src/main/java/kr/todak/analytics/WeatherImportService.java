package kr.todak.analytics;

import kr.todak.common.ApiException;
import kr.todak.domain.WeatherDaily;
import kr.todak.repo.WeatherDailyRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.Charset;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.*;

/**
 * 기상자료개방포털(data.kma.go.kr) 종관기상관측(ASOS) 일자료 CSV 가져오기. [REQ-F-15]
 * 열 이름으로 위치를 찾는다: 지점, 일시, 평균기온, 최저기온, 최고기온, 일강수량, 평균 상대습도, 합계 일조시간, 합계 일사량.
 * 포털 CSV는 보통 CP949(EUC-KR)라 UTF-8로 읽히지 않으면 CP949로 다시 읽는다.
 */
@Service
public class WeatherImportService {
    private final WeatherDailyRepository repo;

    public WeatherImportService(WeatherDailyRepository repo) {
        this.repo = repo;
    }

    public record Result(String station, int rows, int missingDays, int overwritten, int skipped) {
    }

    @Transactional
    public Result importCsv(byte[] bytes, String fileName) {
        String text = decode(bytes);
        List<String> lines = text.lines().filter(l -> !l.isBlank()).toList();
        if (lines.size() < 2) {
            throw ApiException.badRequest("CSV에 데이터 행이 없습니다");
        }
        String[] head = split(lines.get(0));
        int cStation = find(head, "지점");
        int cDate = find(head, "일시");
        int cAvg = find(head, "평균기온");
        int cMin = find(head, "최저기온");
        int cMax = find(head, "최고기온");
        int cRain = find(head, "일강수량");
        int cRh = find(head, "평균 상대습도");
        int cSun = find(head, "합계 일조시간");
        int cSolar = find(head, "합계 일사량");
        if (cStation < 0 || cDate < 0 || (cAvg < 0 && (cMin < 0 || cMax < 0))) {
            throw ApiException.badRequest("필수 열(지점, 일시, 평균기온 또는 최저·최고기온)을 찾지 못했습니다");
        }
        String station = null;
        int rows = 0, missing = 0, overwritten = 0, skipped = 0;
        for (int i = 1; i < lines.size(); i++) {
            String[] f = split(lines.get(i));
            try {
                String st = f[cStation].trim();
                station = st;
                LocalDate d = LocalDate.parse(f[cDate].trim().substring(0, 10));
                WeatherDaily.Key key = new WeatherDaily.Key(st, d);
                WeatherDaily w = repo.findById(key).orElse(null);
                if (w != null) {
                    overwritten++;
                } else {
                    w = new WeatherDaily();
                    w.setStationId(st);
                    w.setObsDate(d);
                }
                List<String> miss = new ArrayList<>();
                w.setTavgC(num(f, cAvg, "tavg", miss));
                w.setTminC(num(f, cMin, "tmin", miss));
                w.setTmaxC(num(f, cMax, "tmax", miss));
                w.setRainMm(num(f, cRain, null, miss));
                w.setRhPct(num(f, cRh, "rh", miss));
                w.setSunshineHr(num(f, cSun, "sun", miss));
                w.setSolarMjM2(num(f, cSolar, null, miss));
                w.setMissingFlags(miss.isEmpty() ? null : String.join(",", miss));
                w.setSourceFile(fileName == null ? "upload.csv" : (fileName.length() > 100 ? fileName.substring(0, 100) : fileName));
                w.setImportedAt(java.time.LocalDateTime.now());
                repo.save(w);
                rows++;
                if (!miss.isEmpty()) {
                    missing++;
                }
            } catch (Exception e) {
                skipped++;
            }
        }
        return new Result(station, rows, missing, overwritten, skipped);
    }

    private static Double num(String[] f, int col, String name, List<String> miss) {
        if (col < 0 || col >= f.length || f[col].isBlank()) {
            if (name != null) {
                miss.add(name);
            }
            return null;
        }
        return Double.valueOf(f[col].trim());
    }

    private static int find(String[] head, String name) {
        for (int i = 0; i < head.length; i++) {
            if (head[i].replace("\"", "").trim().startsWith(name)) {
                return i;
            }
        }
        return -1;
    }

    private static String[] split(String line) {
        return line.replace("﻿", "").replace("\"", "").split(",", -1);
    }

    static String decode(byte[] b) {
        try {
            return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(b)).toString();
        } catch (CharacterCodingException e) {
            return new String(b, Charset.forName("MS949"));
        }
    }
}
