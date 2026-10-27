# MySQL 실제 조회 결과

- 조회 시각: 2026-10-27 19:00 KST · `docker compose exec mysql mysql --table` 출력 그대로 (`tools/collect_evidence.py`)
- DB: MySQL 8.4 `todak` (Workbench 접속 127.0.0.1:3307). 센서 값은 시뮬레이터(B안) 데이터

## 테이블 목록 (22개)

```sql
SHOW TABLES;
```

```text
+-----------------------+
| Tables_in_todak       |
+-----------------------+
| TB_ALERT              |
| TB_ALERT_DELIVERY     |
| TB_BEEHIVE            |
| TB_CONTROL_COMMAND    |
| TB_CONTROL_LOG        |
| TB_CONTROL_RULE       |
| TB_CROP_CYCLE         |
| TB_CROP_STD           |
| TB_DEVICE             |
| TB_FARM               |
| TB_GATEWAY            |
| TB_GDD_DAILY          |
| TB_IMAGE_RESULT       |
| TB_REFRESH_TOKEN      |
| TB_SENSOR             |
| TB_SENSOR_DATA        |
| TB_SENSOR_DATA_HOURLY |
| TB_SETTING_HISTORY    |
| TB_USER               |
| TB_USER_FARM          |
| TB_WEATHER_DAILY      |
| TB_ZONE               |
| flyway_schema_history |
+-----------------------+
```

## Flyway 마이그레이션 이력

```sql
SELECT version, description, success, installed_on FROM flyway_schema_history ORDER BY installed_rank;
```

```text
+---------+----------------+---------+---------------------+
| version | description    | success | installed_on        |
+---------+----------------+---------+---------------------+
| 1       | schema         |       1 | 2026-10-26 15:51:10 |
| 2       | seed           |       1 | 2026-10-26 15:51:10 |
| 3       | plan alignment |       1 | 2026-10-27 03:28:25 |
+---------+----------------+---------+---------------------+
```

## 사용자·역할·승인 상태 (비밀번호는 BCrypt 해시 앞부분만)

```sql
SELECT user_id, login_id, role, approval_status, is_active, LEFT(password_hash,7) AS hash_prefix, last_login_at FROM TB_USER ORDER BY user_id;
```

```text
+---------+----------------+--------+-----------------+-----------+-------------+---------------------+
| user_id | login_id       | role   | approval_status | is_active | hash_prefix | last_login_at       |
+---------+----------------+--------+-----------------+-----------+-------------+---------------------+
|       1 | admin          | ADMIN  | APPROVED        |         1 | $2a$10$     | 2026-10-27 19:00:36 |
|       2 | farmer01       | FARMER | APPROVED        |         1 | $2a$10$     | 2026-10-27 18:58:58 |
|       3 | farmer02       | FARMER | APPROVED        |         1 | $2a$10$     | NULL                |
|       4 | viewer01       | VIEWER | APPROVED        |         1 | $2b$10$     | 2026-10-27 18:58:49 |
|       5 | yangpyeong02   | FARMER | PENDING         |         1 | $2a$10$     | NULL                |
|       6 | e2etmp10261831 | FARMER | APPROVED        |         0 | $2a$10$     | NULL                |
|       7 | e2e10261837    | FARMER | APPROVED        |         0 | $2a$10$     | 2026-10-27 03:38:11 |
|       8 | e2etmp10261837 | FARMER | APPROVED        |         0 | $2a$10$     | 2026-10-27 03:38:35 |
|       9 | e2e10261840    | FARMER | APPROVED        |         0 | $2a$10$     | 2026-10-27 03:40:44 |
|      10 | e2etmp10261840 | FARMER | APPROVED        |         0 | $2a$10$     | 2026-10-27 03:41:04 |
|      11 | e2e10261908    | FARMER | APPROVED        |         0 | $2a$10$     | 2026-10-27 04:09:40 |
|      12 | e2etmp10261908 | FARMER | APPROVED        |         0 | $2a$10$     | 2026-10-27 04:10:07 |
|      13 | e2e10261926    | FARMER | APPROVED        |         0 | $2a$10$     | 2026-10-27 04:27:01 |
|      14 | e2etmp10261926 | FARMER | APPROVED        |         0 | $2a$10$     | 2026-10-27 04:27:26 |
|      15 | nonayang       | FARMER | APPROVED        |         1 | $2a$10$     | 2026-10-27 15:06:58 |
|      16 | e2e10271857    | FARMER | APPROVED        |         0 | $2a$10$     | 2026-10-27 18:58:26 |
|      17 | e2etmp10271857 | FARMER | APPROVED        |         0 | $2a$10$     | 2026-10-27 18:58:52 |
+---------+----------------+--------+-----------------+-----------+-------------+---------------------+
```

## 센서별 최근 수집 (시뮬레이션 데이터)

```sql
SELECT s.sensor_code, s.metric, s.status, COUNT(d.data_id) AS rows_total, MAX(d.measured_at) AS last_measured FROM TB_SENSOR s LEFT JOIN TB_SENSOR_DATA d ON d.sensor_id=s.sensor_id WHERE s.farm_id=1 GROUP BY s.sensor_id ORDER BY s.sensor_id;
```

```text
+-------------+-----------+--------+------------+---------------------+
| sensor_code | metric    | status | rows_total | last_measured       |
+-------------+-----------+--------+------------+---------------------+
| S-T01       | TEMP      | ACTIVE |       2549 | 2026-10-27 19:00:00 |
| S-H01       | HUMI      | ACTIVE |       2549 | 2026-10-27 19:00:00 |
| S-T02       | TEMP      | ACTIVE |       2541 | 2026-10-27 19:00:00 |
| S-H02       | HUMI      | ACTIVE |       2549 | 2026-10-27 19:00:00 |
| S-CO2-01    | CO2       | ACTIVE |       2549 | 2026-10-27 19:00:00 |
| S-SOL01     | SOLAR     | ACTIVE |       2549 | 2026-10-27 19:00:00 |
| S-SM01      | SUBSTRATE | ACTIVE |       2549 | 2026-10-27 19:00:00 |
| S-SM02      | SUBSTRATE | ACTIVE |       2550 | 2026-10-27 19:00:00 |
| S-EC01      | EC        | ACTIVE |       2550 | 2026-10-27 19:00:00 |
| S-PH01      | PH        | ACTIVE |       2550 | 2026-10-27 19:00:00 |
| S-TO01      | TEMP_OUT  | ACTIVE |       2550 | 2026-10-27 19:00:00 |
+-------------+-----------+--------+------------+---------------------+
```

## 최근 측정값 10건

```sql
SELECT d.data_id, s.sensor_code, d.measured_at, d.value, d.quality, d.is_buffered FROM TB_SENSOR_DATA d JOIN TB_SENSOR s ON s.sensor_id=d.sensor_id ORDER BY d.data_id DESC LIMIT 10;
```

```text
+---------+-------------+---------------------+---------+---------+-------------+
| data_id | sensor_code | measured_at         | value   | quality | is_buffered |
+---------+-------------+---------------------+---------+---------+-------------+
|  124577 | S-TO01      | 2026-10-27 19:00:00 |  12.260 | OK      |           0 |
|  124576 | S-PH01      | 2026-10-27 19:00:00 |   6.140 | OK      |           0 |
|  124575 | S-EC01      | 2026-10-27 19:00:00 |   1.710 | OK      |           0 |
|  124574 | S-SM02      | 2026-10-27 19:00:00 |  57.700 | OK      |           0 |
|  124573 | S-SM01      | 2026-10-27 19:00:00 |  58.000 | OK      |           0 |
|  124572 | S-SOL01     | 2026-10-27 19:00:00 |  42.000 | OK      |           0 |
|  124571 | S-CO2-01    | 2026-10-27 19:00:00 | 507.000 | OK      |           0 |
|  124570 | S-H02       | 2026-10-27 19:00:00 |  62.900 | OK      |           0 |
|  124569 | S-T02       | 2026-10-27 19:00:00 |  25.480 | OK      |           0 |
|  124568 | S-H01       | 2026-10-27 19:00:00 |  62.600 | OK      |           0 |
+---------+-------------+---------------------+---------+---------+-------------+
```

## 제어 명령 상태별 건수 (요청 ≠ 실행)

```sql
SELECT source, status, COUNT(*) AS n FROM TB_CONTROL_COMMAND GROUP BY source, status ORDER BY source, status;
```

```text
+--------+---------+----+
| source | status  | n  |
+--------+---------+----+
| AUTO   | ACKED   | 45 |
| AUTO   | TIMEOUT |  3 |
| MANUAL | ACKED   | 23 |
| SAFETY | ACKED   | 26 |
| SAFETY | TIMEOUT |  3 |
+--------+---------+----+
```

## 최근 제어 명령 10건

```sql
SELECT c.command_id, d.device_code, c.action, c.source, c.status, c.retry_count, c.requested_at, c.acked_at FROM TB_CONTROL_COMMAND c JOIN TB_DEVICE d ON d.device_id=c.device_id ORDER BY c.command_id DESC LIMIT 10;
```

```text
+------------+-------------+--------+--------+--------+-------------+-------------------------+-------------------------+
| command_id | device_code | action | source | status | retry_count | requested_at            | acked_at                |
+------------+-------------+--------+--------+--------+-------------+-------------------------+-------------------------+
|        100 | D-LIGHT02   | OFF    | AUTO   | ACKED  |           0 | 2026-10-27 19:00:18.140 | 2026-10-27 19:00:18.565 |
|         99 | D-LIGHT01   | OFF    | AUTO   | ACKED  |           0 | 2026-10-27 19:00:18.135 | 2026-10-27 19:00:18.560 |
|         98 | D-HEAT01    | OFF    | AUTO   | ACKED  |           0 | 2026-10-27 19:00:18.118 | 2026-10-27 19:00:18.546 |
|         97 | D-LIGHT02   | ON     | AUTO   | ACKED  |           0 | 2026-10-27 16:55:52.053 | 2026-10-27 16:55:52.470 |
|         96 | D-LIGHT01   | ON     | AUTO   | ACKED  |           0 | 2026-10-27 16:55:52.045 | 2026-10-27 16:55:52.459 |
|         95 | D-VENT02    | CLOSE  | AUTO   | ACKED  |           0 | 2026-10-27 15:35:11.502 | 2026-10-27 15:35:11.921 |
|         94 | D-VENT01    | CLOSE  | AUTO   | ACKED  |           0 | 2026-10-27 15:35:11.486 | 2026-10-27 15:35:11.912 |
|         93 | D-VENT02    | OPEN   | AUTO   | ACKED  |           0 | 2026-10-27 15:30:11.230 | 2026-10-27 15:30:11.656 |
|         92 | D-VENT01    | OPEN   | AUTO   | ACKED  |           0 | 2026-10-27 15:30:11.221 | 2026-10-27 15:30:11.643 |
|         91 | D-HEAT01    | ON     | MANUAL | ACKED  |           0 | 2026-10-27 15:07:24.603 | 2026-10-27 15:07:25.020 |
+------------+-------------+--------+--------+--------+-------------+-------------------------+-------------------------+
```

## 경보 유형별

```sql
SELECT alert_type, severity, status, COUNT(*) AS n, SUM(occur_count) AS occurrences FROM TB_ALERT GROUP BY alert_type, severity, status ORDER BY alert_type;
```

```text
+--------------+----------+----------+----+-------------+
| alert_type   | severity | status   | n  | occurrences |
+--------------+----------+----------+----+-------------+
| BEE          | INFO     | OPEN     |  1 |           9 |
| DEVICE_NOACK | CRITICAL | RESOLVED |  1 |           6 |
| GW_OFFLINE   | CRITICAL | RESOLVED | 43 |          73 |
| OUTLIER      | WARN     | OPEN     |  5 |          19 |
| SENSOR_FAIL  | CRITICAL | RESOLVED |  4 |           6 |
| SENSOR_FAIL  | INFO     | RESOLVED |  1 |           1 |
| SENSOR_FAIL  | WARN     | RESOLVED | 56 |         100 |
| THRESHOLD    | CRITICAL | RESOLVED |  3 |           9 |
| THRESHOLD    | WARN     | OPEN     |  2 |           2 |
| THRESHOLD    | WARN     | RESOLVED | 24 |         549 |
+--------------+----------+----------+----+-------------+
```

## 내부 GDD 최근 7일

```sql
SELECT calc_date, source, method, tavg_c, gdd, cum_gdd, coverage_pct, is_complete FROM TB_GDD_DAILY WHERE source='INTERNAL' ORDER BY calc_date DESC LIMIT 7;
```

```text
+------------+----------+--------+--------+------+---------+--------------+-------------+
| calc_date  | source   | method | tavg_c | gdd  | cum_gdd | coverage_pct | is_complete |
+------------+----------+--------+--------+------+---------+--------------+-------------+
| 2026-10-26 | INTERNAL | HOURLY |   17.6 | 7.60 |  114.17 |        100.0 |           1 |
| 2026-10-25 | INTERNAL | HOURLY |   16.7 | 6.68 |  106.57 |        100.0 |           1 |
| 2026-10-24 | INTERNAL | HOURLY |   16.3 | 6.26 |   99.89 |        100.0 |           1 |
| 2026-10-23 | INTERNAL | HOURLY |   16.7 | 6.72 |   93.63 |        100.0 |           1 |
| 2026-10-22 | INTERNAL | HOURLY |   17.6 | 7.64 |   86.91 |        100.0 |           1 |
| 2026-10-21 | INTERNAL | HOURLY |   17.8 | 7.83 |   79.27 |        100.0 |           1 |
| 2026-10-20 | INTERNAL | HOURLY |   18.3 | 8.29 |   71.44 |        100.0 |           1 |
+------------+----------+--------+--------+------+---------+--------------+-------------+
```

## 외부 기상 자료(기상청 ASOS) 건수

```sql
SELECT COUNT(*) AS kma_rows FROM TB_WEATHER_DAILY;
```

```text
+----------+
| kma_rows |
+----------+
|       26 |
+----------+
```

## 시간대별 저장 건수 (최근 24시간, 농장 1 · 정상이면 시간당 11채널×60=660건)

```sql
SELECT DATE_FORMAT(d.measured_at,'%m-%d %H시') AS hour, COUNT(*) AS saved, SUM(d.is_buffered) AS buffered FROM TB_SENSOR_DATA d JOIN TB_SENSOR s ON s.sensor_id=d.sensor_id WHERE s.farm_id=1 AND d.measured_at >= NOW() - INTERVAL 24 HOUR GROUP BY DATE_FORMAT(d.measured_at,'%m-%d %H시') ORDER BY 1;
```

```text
+-------------+-------+----------+
| hour        | saved | buffered |
+-------------+-------+----------+
| 10-26 19시 |    55 |        0 |
| 10-26 20시 |    77 |        0 |
| 10-26 21시 |    77 |        0 |
| 10-26 22시 |    88 |        0 |
| 10-26 23시 |    77 |        0 |
| 10-27 00시 |    77 |        0 |
| 10-27 01시 |    99 |        0 |
| 10-27 02시 |   165 |        0 |
| 10-27 03시 |   660 |        0 |
| 10-27 04시 |   286 |        0 |
| 10-27 05시 |   132 |        0 |
| 10-27 06시 |   242 |        0 |
| 10-27 07시 |   315 |       33 |
| 10-27 08시 |    99 |        0 |
| 10-27 09시 |   187 |        0 |
| 10-27 10시 |   403 |        0 |
| 10-27 11시 |   627 |       33 |
| 10-27 12시 |   242 |        0 |
| 10-27 13시 |    33 |        0 |
| 10-27 14시 |   176 |        0 |
| 10-27 15시 |   506 |        0 |
| 10-27 16시 |    22 |        0 |
| 10-27 17시 |    11 |        0 |
| 10-27 18시 |   385 |        0 |
| 10-27 19시 |    11 |        0 |
+-------------+-------+----------+
```

## 데이터 저장 성공률 (REQ-F-01 · KPI)

구간 안 '센서 수 × 분'만큼 저장돼야 한다. 직전 2분은 집계 중이라 제외.

최근 1시간:

```text
+-------+---------+---------+-----------+
| saved | sensors | minutes | saved_pct |
+-------+---------+---------+-----------+
|   374 |      11 |      53 |    64.151 |
+-------+---------+---------+-----------+
```

최근 6시간:

```text
+-------+---------+---------+-----------+
| saved | sensors | minutes | saved_pct |
+-------+---------+---------+-----------+
|  1122 |      11 |     350 |    29.143 |
+-------+---------+---------+-----------+
```

### 수신 메시지 대비 저장 (계획서 KPI 정의, 백엔드 기동 이후 누계)

- 수신 69,840건 · 저장 3,589건 · 중복(이미 저장됨) 66,251건 · 거부 0건
- 처리 성공률 (저장+중복)/수신 = **100.000%** (목표 ≥ 99.9%)

※ 2026-10-26 오후~10-27 02:53 사이에는 개발 PC 절전으로 수집이 실제로 끊겼다. 03:01 시뮬레이터 재시작 때 과거 데이터 생성(백필)이 10분 간격으로 그 구간을 채웠으므로 그 시간대의 시간당 건수는 660건보다 적다. 이 공백은 실제로 발생한 것이며 메우지 않았다. 10-27 오전에도 개발 PC가 여러 번 절전(예: 07:55~09:33, 10:19~10:37)해 Docker 컨테이너가 함께 멈췄고, 그동안은 측정값 자체가 만들어지지 않았다. 그래서 '구간 안 저장률'은 절전 구간이 끼면 낮게 나온다. 서버가 받은 메시지를 빠짐없이 저장했는지는 위 '수신 대비 저장'으로 판단한다.
