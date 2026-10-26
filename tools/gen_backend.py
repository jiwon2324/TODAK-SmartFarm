# -*- coding: utf-8 -*-
"""
V1__schema.sql 에서 JPA 엔티티와 Spring Data 리포지토리를 생성한다.
스키마를 바꾸면 이 스크립트를 다시 실행해 엔티티를 DDL과 맞춘다.
    python3 tools/gen_backend.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACK = os.path.join(ROOT, "backend")
SCHEMA = os.path.join(BACK, "src/main/resources/db/migration/V1__schema.sql")
DOMAIN = os.path.join(BACK, "src/main/java/kr/todak/domain")
REPO = os.path.join(BACK, "src/main/java/kr/todak/repo")

NAMES = {"TB_USER": "User", "TB_FARM": "Farm", "TB_USER_FARM": "UserFarm", "TB_ZONE": "Zone", "TB_CROP_CYCLE": "CropCycle",
         "TB_CROP_STD": "CropStd", "TB_GATEWAY": "Gateway", "TB_SENSOR": "Sensor", "TB_SENSOR_DATA": "SensorData",
         "TB_SENSOR_DATA_HOURLY": "SensorDataHourly", "TB_DEVICE": "Device", "TB_CONTROL_RULE": "ControlRule",
         "TB_CONTROL_COMMAND": "ControlCommand", "TB_CONTROL_LOG": "ControlLog", "TB_ALERT": "Alert",
         "TB_ALERT_DELIVERY": "AlertDelivery", "TB_BEEHIVE": "Beehive", "TB_IMAGE_RESULT": "ImageResult",
         "TB_WEATHER_DAILY": "WeatherDaily", "TB_GDD_DAILY": "GddDaily", "TB_SETTING_HISTORY": "SettingHistory",
         "TB_REFRESH_TOKEN": "RefreshToken"}

REPO_METHODS = {
    "User": ["Optional<User> findByLoginId(String loginId);"],
    "UserFarm": ["List<UserFarm> findByUserId(Integer userId);", "List<UserFarm> findByFarmId(Integer farmId);",
                 "boolean existsByUserIdAndFarmId(Integer userId, Integer farmId);", "void deleteByUserId(Integer userId);"],
    "Zone": ["List<Zone> findByFarmIdOrderByZoneCode(Integer farmId);"],
    "CropCycle": ["Optional<CropCycle> findFirstByFarmIdAndStatusOrderByCycleIdDesc(Integer farmId, String status);",
                  "List<CropCycle> findByStatus(String status);"],
    "CropStd": ["List<CropStd> findByFarmIdAndIsCurrentTrueOrderByStage(Integer farmId);",
                "List<CropStd> findByFarmIdOrderByStageAscVersionNoDesc(Integer farmId);",
                "Optional<CropStd> findFirstByFarmIdAndStageAndIsCurrentTrue(Integer farmId, String stage);",
                "Optional<CropStd> findFirstByFarmIdAndStageOrderByVersionNoDesc(Integer farmId, String stage);"],
    "Gateway": ["Optional<Gateway> findByGatewayCode(String code);", "List<Gateway> findByFarmId(Integer farmId);"],
    "Sensor": ["List<Sensor> findByFarmIdOrderBySensorId(Integer farmId);",
               "Optional<Sensor> findByFarmIdAndSensorCode(Integer farmId, String code);",
               "List<Sensor> findByFarmIdAndMetric(Integer farmId, String metric);"],
    "SensorData": ["boolean existsByMsgId(String msgId);",
                   "boolean existsBySensorIdAndMeasuredAt(Integer sensorId, LocalDateTime t);",
                   "Optional<SensorData> findFirstBySensorIdOrderByMeasuredAtDesc(Integer sensorId);",
                   "List<SensorData> findBySensorIdAndMeasuredAtBetweenOrderByMeasuredAt(Integer sensorId, LocalDateTime from, LocalDateTime to);",
                   "long countByReceivedAtAfter(LocalDateTime t);",
                   "long countBySensorIdAndReceivedAtAfter(Integer sensorId, LocalDateTime t);",
                   "@Query(\"select max(d.receivedAt) from SensorData d\") LocalDateTime lastReceivedAt();"],
    "SensorDataHourly": ["List<SensorDataHourly> findBySensorIdAndHourAtBetweenOrderByHourAt(Integer sensorId, LocalDateTime from, LocalDateTime to);"],
    "Device": ["List<Device> findByFarmIdOrderByDeviceId(Integer farmId);",
               "Optional<Device> findByFarmIdAndDeviceCode(Integer farmId, String code);"],
    "ControlRule": ["List<ControlRule> findByFarmIdAndIsEnabledTrueOrderByPriority(Integer farmId);",
                    "List<ControlRule> findByFarmIdOrderByPriority(Integer farmId);"],
    "ControlCommand": ["List<ControlCommand> findByStatusIn(Collection<String> statuses);",
                       "Optional<ControlCommand> findByIdempotencyKey(String key);",
                       "boolean existsByDeviceIdAndStatusIn(Integer deviceId, Collection<String> statuses);",
                       "long countByDeviceIdAndSourceAndActionAndRequestedAtAfter(Integer deviceId, String source, String action, LocalDateTime t);",
                       "Optional<ControlCommand> findFirstByDeviceIdAndStatusOrderByCommandIdDesc(Integer deviceId, String status);",
                       "Page<ControlCommand> findByDeviceIdInOrderByCommandIdDesc(Collection<Integer> deviceIds, Pageable p);",
                       "long countByRequestedAtAfterAndStatus(LocalDateTime t, String status);"],
    "ControlLog": ["Page<ControlLog> findByDeviceIdInOrderByLogIdDesc(Collection<Integer> deviceIds, Pageable p);"],
    "Alert": ["Optional<Alert> findFirstByDedupeKeyAndStatusNotOrderByAlertIdDesc(String key, String status);",
              "List<Alert> findByDedupeKeyAndStatusNot(String key, String status);",
              "Page<Alert> findByFarmIdInOrderByAlertIdDesc(Collection<Integer> farmIds, Pageable p);",
              "Page<Alert> findByFarmIdInAndStatusOrderByAlertIdDesc(Collection<Integer> farmIds, String status, Pageable p);",
              "long countByFarmIdInAndStatusNot(Collection<Integer> farmIds, String status);"],
    "AlertDelivery": ["Page<AlertDelivery> findAllByOrderByDeliveryIdDesc(Pageable p);"],
    "Beehive": ["List<Beehive> findByCycleIdOrderByHiveIdDesc(Integer cycleId);", "List<Beehive> findByRemovedDateIsNull();"],
    "ImageResult": ["List<ImageResult> findByZoneIdInOrderByCapturedAtDesc(Collection<Integer> zoneIds);"],
    "WeatherDaily": ["List<WeatherDaily> findByStationIdAndObsDateBetweenOrderByObsDate(String stationId, LocalDate from, LocalDate to);"],
    "GddDaily": ["List<GddDaily> findByCycleIdAndSourceAndCalcDateBetweenOrderByCalcDate(Integer cycleId, String source, LocalDate from, LocalDate to);"],
    "SettingHistory": ["Page<SettingHistory> findAllByOrderByHistoryIdDesc(Pageable p);"],
    "RefreshToken": ["Optional<RefreshToken> findByTokenHash(String hash);",
                     "List<RefreshToken> findByFamilyIdAndRevokedAtIsNull(String familyId);",
                     "List<RefreshToken> findByUserIdAndRevokedAtIsNull(Integer userId);"],
}


def camel(s):
    p = s.split("_")
    return p[0] + "".join(x.capitalize() for x in p[1:])


def jtype(t):
    t = t.upper()
    if t.startswith("BIGINT"):
        return "Long"
    if t == "TINYINT(1)":
        return "Boolean"
    if t.startswith("TINYINT"):
        return "Byte"
    if t.startswith("SMALLINT"):
        return "Short"
    if t.startswith("INT"):
        return "Integer"
    if t.startswith("DECIMAL"):
        return "Double"
    if t.startswith("DATETIME"):
        return "LocalDateTime"
    if t == "DATE":
        return "LocalDate"
    if t == "TIME":
        return "LocalTime"
    return "String"


def parse():
    sql = open(SCHEMA, encoding="utf-8").read()
    for m in re.finditer(r"CREATE TABLE (\w+) \((.*?)\n\) COMMENT='([^']*)';", sql, re.S):
        tname, body, comment = m.groups()
        lines = [l.strip().rstrip(",") for l in body.split("\n") if l.strip()]
        pk = []
        for l in lines:
            if l.startswith("PRIMARY KEY"):
                pk = [x.strip() for x in re.search(r"\((.*)\)", l).group(1).split(",")]
        cols = []
        for l in lines:
            if l.startswith(("PRIMARY", "UNIQUE", "KEY", "CONSTRAINT", "INDEX")):
                continue
            cm = re.match(r"(\w+)\s+([A-Z]+(?:\([\d,]+\))?)\s*(.*)", l)
            if not cm:
                continue
            c, t, rest = cm.groups()
            dm = re.search(r"DEFAULT ('[^']*'|[\w.\-()]+)", rest)
            cols.append((c, t, rest, dm.group(1) if dm else None))
        yield tname, comment, pk, cols


def entity(tname, comment, pk, cols):
    cls = NAMES[tname]
    composite = len(pk) > 1
    o = ["package kr.todak.domain;", "", "import jakarta.persistence.*;", "import lombok.Getter;", "import lombok.NoArgsConstructor;",
         "import lombok.Setter;", "", "import java.io.Serializable;", "import java.time.*;", "import java.util.Objects;", "",
         f"/** {tname} — {comment} (tools/gen_backend.py로 생성) */", "@Entity", f'@Table(name = "{tname}")']
    if composite:
        o.append(f"@IdClass({cls}.Key.class)")
    o += ["@Getter", "@Setter", "@NoArgsConstructor", f"public class {cls} {{", ""]
    for c, t, rest, d in cols:
        jt = jtype(t)
        if c in pk:
            o.append("    @Id")
            if "AUTO_INCREMENT" in rest:
                o.append("    @GeneratedValue(strategy = GenerationType.IDENTITY)")
        o.append(f'    @Column(name = "{c}"' + (", nullable = false" if "NOT NULL" in rest else "") + ")")
        init = ""
        if d and "AUTO_INCREMENT" not in rest:
            if d.startswith("CURRENT_TIMESTAMP"):
                init = " = LocalDateTime.now()"
            elif jt == "LocalTime":
                init = f' = LocalTime.parse("{d.strip(chr(39))}")'
            elif d.startswith("'"):
                init = f' = "{d[1:-1]}"'
            elif jt == "Boolean":
                init = " = " + ("true" if d == "1" else "false")
            elif jt == "Byte":
                init = f" = (byte) {d}"
            elif jt == "Integer":
                init = f" = {d}"
            elif jt == "Double":
                init = f" = {float(d)}"
        o.append(f"    private {jt} {camel(c)}{init};")
        o.append("")
    if composite:
        flds = [(jtype(t), camel(c)) for c, t, r, d in cols if c in pk]
        o += ["    /** 복합 기본키 */", "    @Getter", "    @Setter", "    @NoArgsConstructor", "    public static class Key implements Serializable {"]
        o += [f"        private {a} {b};" for a, b in flds]
        o.append("")
        o.append("        public Key(" + ", ".join(f"{a} {b}" for a, b in flds) + ") {")
        o += [f"            this.{b} = {b};" for a, b in flds]
        o += ["        }", "", "        @Override", "        public boolean equals(Object o) {", "            if (this == o) {", "                return true;", "            }",
              "            if (!(o instanceof Key k)) {", "                return false;", "            }",
              "            return " + " && ".join(f"Objects.equals({b}, k.{b})" for a, b in flds) + ";", "        }", "",
              "        @Override", "        public int hashCode() {", "            return Objects.hash(" + ", ".join(b for a, b in flds) + ");", "        }", "    }"]
    o.append("}")
    open(os.path.join(DOMAIN, cls + ".java"), "w", encoding="utf-8").write("\n".join(o) + "\n")


def repo(cls, pk_type):
    o = ["package kr.todak.repo;", "", "import kr.todak.domain.*;", "import org.springframework.data.domain.Page;",
         "import org.springframework.data.domain.Pageable;", "import org.springframework.data.jpa.repository.JpaRepository;",
         "import org.springframework.data.jpa.repository.Query;", "", "import java.time.*;", "import java.util.*;", "",
         f"public interface {cls}Repository extends JpaRepository<{cls}, {pk_type}> {{"]
    o += ["    " + m for m in REPO_METHODS.get(cls, [])]
    o.append("}")
    open(os.path.join(REPO, cls + "Repository.java"), "w", encoding="utf-8").write("\n".join(o) + "\n")


def main():
    os.makedirs(DOMAIN, exist_ok=True)
    os.makedirs(REPO, exist_ok=True)
    n = 0
    for tname, comment, pk, cols in parse():
        entity(tname, comment, pk, cols)
        cls = NAMES[tname]
        if len(pk) > 1:
            pk_type = f"{cls}.Key"
        else:
            pk_type = jtype(next(t for c, t, r, d in cols if c == pk[0]))
        repo(cls, pk_type)
        n += 1
    print(n, "entities + repositories")


if __name__ == "__main__":
    main()
