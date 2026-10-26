package kr.todak.it;

import kr.todak.analytics.WeatherImportService;
import kr.todak.repo.*;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MvcResult;

import java.nio.charset.Charset;
import java.time.LocalDate;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** TC-010·011·013·014·015 · 관리자 CRUD · 엔티티-테이블 매핑 */
class AnalyticsAndAdminIntegrationTest extends IntegrationTestBase {
    @Autowired
    List<JpaRepository<?, ?>> repositories;

    private void hourly(int sensorId, LocalDate day, int hours, double value) {
        for (int h = 0; h < hours; h++) {
            jdbc.update("INSERT INTO TB_SENSOR_DATA_HOURLY (sensor_id, hour_at, avg_value, min_value, max_value, ok_count) VALUES (?,?,?,?,?,60)",
                    sensorId, day.atTime(h, 0), value, value - 1, value + 1);
        }
    }

    @Test
    @DisplayName("TC-014 내부 GDD: 두 구역 센서 시간 평균 → 일평균 → GDD, 결측 20% 초과일은 불완전, 누적은 정식일부터")
    void internalGdd() throws Exception {
        LocalDate start = jdbc.queryForObject("SELECT transplant_date FROM TB_CROP_CYCLE WHERE cycle_id=1", LocalDate.class);
        hourly(1, start, 24, 19.0);
        hourly(3, start, 24, 21.0);           // 두 센서 평균 20.0 → GDD 10.0
        hourly(1, start.plusDays(1), 12, 18.0); // 12시간뿐 → 불완전, GDD 8.0
        String t = login("farmer01", FARMER_PW);
        MvcResult r = mvc.perform(get("/api/analytics/gdd?farmId=1&source=INTERNAL").header("Authorization", bearer(t)))
                .andExpect(status().isOk()).andReturn();
        var days = json(r).get("days");
        assertThat(days.get(0).get("tavg").asDouble()).isEqualTo(20.0);
        assertThat(days.get(0).get("gdd").asDouble()).isEqualTo(10.0);
        assertThat(days.get(0).get("complete").asBoolean()).isTrue();
        assertThat(days.get(1).get("gdd").asDouble()).isEqualTo(8.0);
        assertThat(days.get(1).get("complete").asBoolean()).isFalse();
        assertThat(days.get(1).get("cumGdd").asDouble()).isEqualTo(18.0);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_GDD_DAILY WHERE source='INTERNAL'", Integer.class)).isGreaterThanOrEqualTo(2);
    }

    @Test
    @DisplayName("TC-014 기준온도 변경은 이력이 남고 다음 계산에 반영된다")
    void baseTempChange() throws Exception {
        LocalDate start = jdbc.queryForObject("SELECT transplant_date FROM TB_CROP_CYCLE WHERE cycle_id=1", LocalDate.class);
        hourly(1, start, 24, 20.0);
        String t = login("farmer01", FARMER_PW);
        mvc.perform(patch("/api/crop-cycles/1").header("Authorization", bearer(t)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"gddBaseC\":12.0}")).andExpect(status().isOk());
        MvcResult r = mvc.perform(get("/api/analytics/gdd?farmId=1").header("Authorization", bearer(t))).andReturn();
        assertThat(json(r).get("days").get(0).get("gdd").asDouble()).isEqualTo(8.0);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_SETTING_HISTORY WHERE field_name='gdd_base_c'", Integer.class)).isEqualTo(1);
        jdbc.update("UPDATE TB_CROP_CYCLE SET gdd_base_c=10.0 WHERE cycle_id=1");
    }

    @Test
    @DisplayName("TC-015 기상자료개방포털 형식(CP949) CSV 가져오기 → 외부 GDD는 (최고+최저)/2, 결측 표시")
    void weatherImportAndExternalGdd() throws Exception {
        LocalDate start = jdbc.queryForObject("SELECT transplant_date FROM TB_CROP_CYCLE WHERE cycle_id=1", LocalDate.class);
        String csv = "지점,지점명,일시,평균기온(°C),최저기온(°C),최고기온(°C),일강수량(mm),평균 상대습도(%),합계 일조시간(hr)\n"
                + "202,양평," + start + ",14.0,8.0,22.0,,70.1,6.5\n"
                + "202,양평," + start.plusDays(1) + ",11.0,,,0.5,80.0,2.1\n";
        String admin = login("admin", ADMIN_PW);
        MvcResult r = mvc.perform(multipart("/api/admin/weather/import")
                        .file(new MockMultipartFile("file", "OBS_ASOS_DD_test.csv", "text/csv", csv.getBytes(Charset.forName("MS949"))))
                        .header("Authorization", bearer(admin)))
                .andExpect(status().isOk()).andReturn();
        assertThat(json(r).get("rows").asInt()).isEqualTo(2);
        assertThat(json(r).get("missingDays").asInt()).isEqualTo(1);   // 2일차 최저·최고 결측 (강수량 공란은 결측 집계 대상 아님)
        MvcResult g = mvc.perform(get("/api/analytics/gdd?farmId=1&source=EXTERNAL").header("Authorization", bearer(admin))).andReturn();
        var d0 = json(g).get("days").get(0);
        assertThat(d0.get("tavg").asDouble()).isEqualTo(15.0);   // (22+8)/2, 보고된 평균 14.0이 아님
        assertThat(d0.get("gdd").asDouble()).isEqualTo(5.0);
        assertThat(json(g).get("days").get(1).get("complete").asBoolean()).isFalse();
    }

    @Test
    @DisplayName("TC-010 CSV 행 수 = DB 행 수, 데이터 출처 열 포함")
    void csvExport() throws Exception {
        for (int m = 0; m < 5; m++) {
            jdbc.update("INSERT INTO TB_SENSOR_DATA (sensor_id, measured_at, value, quality, msg_id) VALUES (1, ?, 20.0, 'OK', ?)",
                    LocalDate.now().atTime(3, m), "csv-" + m);
        }
        String t = login("farmer01", FARMER_PW);
        MvcResult r = mvc.perform(get("/api/sensor-data/export.csv?farmId=1&from=" + LocalDate.now() + "T00:00:00&to=" + LocalDate.now() + "T23:59:59")
                .header("Authorization", bearer(t))).andExpect(status().isOk()).andReturn();
        String body = r.getResponse().getContentAsString();
        assertThat(body.lines().count()).isEqualTo(6);
        assertThat(body).contains("data_source").contains("SIMULATION");
    }

    @Test
    @DisplayName("TC-011 기준값 새 버전: 이전 버전 보존, 최소>최대 400")
    void cropStandardVersion() throws Exception {
        String t = login("farmer01", FARMER_PW);
        String body = "{\"farmId\":1,\"stage\":\"GROWTH\",\"dayTempMin\":19,\"dayTempMax\":27,\"nightTempMin\":15,\"nightTempMax\":18,"
                + "\"humidityMin\":60,\"humidityMax\":90,\"ecMin\":1.2,\"ecMax\":2.2,\"phMin\":5.6,\"phMax\":6.6,\"substrateMoistureMin\":55}";
        mvc.perform(post("/api/crop-standards").header("Authorization", bearer(t)).contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk()).andExpect(jsonPath("$.versionNo").value(2));
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_CROP_STD WHERE farm_id=1 AND stage='GROWTH'", Integer.class)).isEqualTo(2);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_CROP_STD WHERE farm_id=1 AND stage='GROWTH' AND is_current=1", Integer.class)).isEqualTo(1);
        assertThat(mqtt.published().stream().anyMatch(p -> p.topic().endsWith("/config") && p.retained())).isTrue();
        mvc.perform(post("/api/crop-standards").header("Authorization", bearer(t)).contentType(MediaType.APPLICATION_JSON)
                .content(body.replace("\"ecMin\":1.2", "\"ecMin\":3.2"))).andExpect(status().isBadRequest());
        jdbc.update("DELETE FROM TB_CROP_STD WHERE farm_id=1 AND stage='GROWTH' AND version_no=2");
        jdbc.update("UPDATE TB_CROP_STD SET is_current=1 WHERE farm_id=1 AND stage='GROWTH' AND version_no=1");
    }

    @Test
    @DisplayName("관리자 사용자 CRUD: 등록(BCrypt)·조회·수정·비활성화(세션 폐기)·농장 권한, 중복 아이디 409")
    void userCrud() throws Exception {
        String admin = login("admin", ADMIN_PW);
        MvcResult c = mvc.perform(post("/api/admin/users").header("Authorization", bearer(admin)).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"loginId\":\"newfarmer\",\"password\":\"Tomato#2026a\",\"name\":\"신규 농가\",\"role\":\"FARMER\",\"farmIds\":[1]}"))
                .andExpect(status().isOk()).andReturn();
        int id = json(c).get("userId").asInt();
        assertThat(jdbc.queryForObject("SELECT password_hash FROM TB_USER WHERE user_id=?", String.class, id)).startsWith("$2a$");
        mvc.perform(post("/api/admin/users").header("Authorization", bearer(admin)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"loginId\":\"newfarmer\",\"password\":\"Tomato#2026a\",\"name\":\"x\"}")).andExpect(status().isConflict());
        login("newfarmer", "Tomato#2026a");
        mvc.perform(patch("/api/admin/users/" + id).header("Authorization", bearer(admin)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"이름 변경\",\"isActive\":false}")).andExpect(status().isOk()).andExpect(jsonPath("$.isActive").value(false));
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_REFRESH_TOKEN WHERE user_id=? AND revoked_at IS NULL", Integer.class, id)).isZero();
        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON).content("{\"loginId\":\"newfarmer\",\"password\":\"Tomato#2026a\"}"))
                .andExpect(status().isForbidden()).andExpect(jsonPath("$.code").value("ACCOUNT_DISABLED"));
        jdbc.update("DELETE FROM TB_USER_FARM WHERE user_id=?", id);
        jdbc.update("DELETE FROM TB_REFRESH_TOKEN WHERE user_id=?", id);
        jdbc.update("DELETE FROM TB_USER WHERE user_id=?", id);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_USER WHERE login_id='newfarmer'", Integer.class)).isZero();
    }

    @Test
    @DisplayName("관리자 센서 등록·수정, 규칙 히스테리시스 방향 검사")
    void sensorAndRuleAdmin() throws Exception {
        String admin = login("admin", ADMIN_PW);
        MvcResult s = mvc.perform(post("/api/admin/sensors").header("Authorization", bearer(admin)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"farmId\":1,\"zoneId\":1,\"gatewayId\":1,\"sensorCode\":\"S-T99\",\"metric\":\"TEMP\",\"unit\":\"C\",\"validMin\":-20,\"validMax\":60}"))
                .andExpect(status().isOk()).andReturn();
        int sid = json(s).get("sensorId").asInt();
        mvc.perform(patch("/api/admin/sensors/" + sid).header("Authorization", bearer(admin)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"installNote\":\"시험 설치\",\"status\":\"RETIRED\"}")).andExpect(jsonPath("$.status").value("RETIRED"));
        jdbc.update("DELETE FROM TB_SENSOR WHERE sensor_id=?", sid);
        int rule = jdbc.queryForObject("SELECT rule_id FROM TB_CONTROL_RULE WHERE rule_code='CR-01'", Integer.class);
        mvc.perform(patch("/api/admin/rules/" + rule).header("Authorization", bearer(admin)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"offThreshold\":29}")).andExpect(status().isBadRequest());
        mvc.perform(patch("/api/admin/rules/" + rule).header("Authorization", bearer(admin)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"onThreshold\":28.5}")).andExpect(status().isOk());
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM TB_SETTING_HISTORY WHERE entity_type='CONTROL_RULE'", Integer.class)).isEqualTo(1);
        jdbc.update("UPDATE TB_CONTROL_RULE SET on_threshold=28.0 WHERE rule_id=?", rule);
    }

    @Test
    @DisplayName("엔티티 22개가 실제 테이블과 매핑된다 (모든 리포지토리 조회 성공)")
    void allEntitiesMapped() {
        assertThat(repositories).hasSizeGreaterThanOrEqualTo(22);
        for (JpaRepository<?, ?> r : repositories) {
            r.findAll();
        }
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name LIKE 'TB\\_%'", Integer.class))
                .isEqualTo(22);
    }
}
