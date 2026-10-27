-- =====================================================================
-- TODAK 방울토마토 스마트 농업 정보시스템 - MySQL 8.0 스키마 v2.0
-- 기준 문서: 개발 계획서 v2.0 (2026.10.26) 7장 데이터 설계
-- 기존 9개 테이블(TB_USER ~ TB_IMAGE_RESULT)을 유지·보완하고 10개를 추가했다.
-- 문자셋 utf8mb4, 엔진 InnoDB, 시간은 모두 KST(Asia/Seoul) 기준 DATETIME.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS todak
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE todak;

-- ---------------------------------------------------------------------
-- 1. 사용자 (기존 보완: 역할 3종, 잠금 컬럼)            REQ-F-12, REQ-N-04
-- ---------------------------------------------------------------------
CREATE TABLE TB_USER (
  user_id         INT          NOT NULL AUTO_INCREMENT,
  login_id        VARCHAR(30)  NOT NULL,
  password_hash   VARCHAR(100) NOT NULL COMMENT 'BCrypt 해시',
  name            VARCHAR(30)  NOT NULL,
  phone           VARCHAR(20)  NULL,
  email           VARCHAR(100) NULL,
  role            VARCHAR(10)  NOT NULL DEFAULT 'FARMER' COMMENT 'ADMIN / FARMER / VIEWER',
  failed_count    TINYINT      NOT NULL DEFAULT 0,
  locked_until    DATETIME     NULL,
  is_active       TINYINT(1)   NOT NULL DEFAULT 1,
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  UNIQUE KEY uk_user_login (login_id),
  CONSTRAINT ck_user_role CHECK (role IN ('ADMIN','FARMER','VIEWER'))
) COMMENT='사용자';

-- ---------------------------------------------------------------------
-- 2. 농장(재배동) (기존 보완: 지역·면적·기상 지점)
-- ---------------------------------------------------------------------
CREATE TABLE TB_FARM (
  farm_id         INT          NOT NULL AUTO_INCREMENT,
  owner_user_id   INT          NOT NULL,
  farm_name       VARCHAR(50)  NOT NULL,
  region          VARCHAR(100) NOT NULL COMMENT '예: 경기도 양평군',
  area_m2         DECIMAL(8,2) NOT NULL COMMENT '330.58',
  facility_type   VARCHAR(30)  NOT NULL COMMENT '단동 비닐하우스',
  culture_type    VARCHAR(30)  NULL     COMMENT '코이어 배지 양액재배 (가정)',
  kma_station_id  VARCHAR(10)  NULL     COMMENT '외부 기상 ASOS 지점 (양평 202, 재확인 필요)',
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (farm_id),
  CONSTRAINT fk_farm_owner FOREIGN KEY (owner_user_id) REFERENCES TB_USER(user_id)
) COMMENT='농장(재배동)';

-- ---------------------------------------------------------------------
-- 3. 관리 구역 (신규)                                     REQ-F-13
-- ---------------------------------------------------------------------
CREATE TABLE TB_ZONE (
  zone_id         INT          NOT NULL AUTO_INCREMENT,
  farm_id         INT          NOT NULL,
  zone_code       VARCHAR(10)  NOT NULL COMMENT 'Z1, Z2',
  zone_name       VARCHAR(30)  NOT NULL,
  area_m2         DECIMAL(8,2) NOT NULL,
  x_from_m        DECIMAL(5,2) NULL COMMENT '하우스 길이 방향 시작 (출입구=0)',
  x_to_m          DECIMAL(5,2) NULL,
  description     VARCHAR(200) NULL,
  PRIMARY KEY (zone_id),
  UNIQUE KEY uk_zone_code (farm_id, zone_code),
  CONSTRAINT fk_zone_farm FOREIGN KEY (farm_id) REFERENCES TB_FARM(farm_id)
) COMMENT='관리 구역';

-- ---------------------------------------------------------------------
-- 4. 작기 (신규) - 정식일, GDD 기준온도               REQ-F-14
-- ---------------------------------------------------------------------
CREATE TABLE TB_CROP_CYCLE (
  cycle_id        INT          NOT NULL AUTO_INCREMENT,
  farm_id         INT          NOT NULL,
  variety         VARCHAR(50)  NULL     COMMENT '품종 (미정)',
  transplant_date DATE         NOT NULL COMMENT '정식일 = GDD 누적 시작일',
  end_date        DATE         NULL,
  current_stage   VARCHAR(10)  NOT NULL DEFAULT 'GROWTH' COMMENT 'NURSERY/GROWTH/FLOWER/HARVEST',
  gdd_base_c      DECIMAL(4,1) NOT NULL DEFAULT 10.0,
  gdd_upper_c     DECIMAL(4,1) NOT NULL DEFAULT 30.0,
  status          VARCHAR(10)  NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE/CLOSED',
  PRIMARY KEY (cycle_id),
  CONSTRAINT fk_cycle_farm FOREIGN KEY (farm_id) REFERENCES TB_FARM(farm_id),
  CONSTRAINT ck_cycle_gdd CHECK (gdd_upper_c > gdd_base_c)
) COMMENT='작기';

-- ---------------------------------------------------------------------
-- 5. 재배 기준값 (기존 보완: 구역·버전·주야 구분)    REQ-F-11
-- ---------------------------------------------------------------------
CREATE TABLE TB_CROP_STD (
  std_id          INT          NOT NULL AUTO_INCREMENT,
  farm_id         INT          NOT NULL,
  zone_id         INT          NULL     COMMENT 'NULL = 농장 공통',
  stage           VARCHAR(10)  NOT NULL COMMENT 'NURSERY/GROWTH/FLOWER/HARVEST',
  version_no      INT          NOT NULL DEFAULT 1,
  day_start_time  TIME         NOT NULL DEFAULT '07:00:00',
  night_start_time TIME        NOT NULL DEFAULT '19:00:00',
  day_temp_min    DECIMAL(4,1) NOT NULL,
  day_temp_max    DECIMAL(4,1) NOT NULL,
  night_temp_min  DECIMAL(4,1) NOT NULL,
  night_temp_max  DECIMAL(4,1) NOT NULL,
  humidity_min    DECIMAL(4,1) NOT NULL,
  humidity_max    DECIMAL(4,1) NOT NULL,
  ec_min          DECIMAL(3,1) NOT NULL,
  ec_max          DECIMAL(3,1) NOT NULL,
  ph_min          DECIMAL(3,1) NOT NULL,
  ph_max          DECIMAL(3,1) NOT NULL,
  substrate_moisture_min DECIMAL(4,1) NULL COMMENT '관수 시작 배지수분(%)',
  source_note     VARCHAR(200) NULL     COMMENT '근거 출처 ID (S4, S5 ...)',
  effective_from  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_current      TINYINT(1)   NOT NULL DEFAULT 1,
  created_by      INT          NULL,
  PRIMARY KEY (std_id),
  UNIQUE KEY uk_std_version (farm_id, zone_id, stage, version_no),
  CONSTRAINT fk_std_farm FOREIGN KEY (farm_id) REFERENCES TB_FARM(farm_id),
  CONSTRAINT fk_std_zone FOREIGN KEY (zone_id) REFERENCES TB_ZONE(zone_id),
  CONSTRAINT fk_std_user FOREIGN KEY (created_by) REFERENCES TB_USER(user_id),
  CONSTRAINT ck_std_range CHECK (day_temp_min < day_temp_max AND night_temp_min < night_temp_max
                                 AND humidity_min < humidity_max AND ec_min < ec_max AND ph_min < ph_max)
) COMMENT='재배 기준값 (버전 관리)';

-- ---------------------------------------------------------------------
-- 6. 게이트웨이 (신규) - 하트비트, 기준값 동기화     REQ-N-03
-- ---------------------------------------------------------------------
CREATE TABLE TB_GATEWAY (
  gateway_id      INT          NOT NULL AUTO_INCREMENT,
  farm_id         INT          NOT NULL,
  gateway_code    VARCHAR(20)  NOT NULL COMMENT 'GW-01',
  is_simulated    TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '1 = B안 시뮬레이터',
  status          VARCHAR(10)  NOT NULL DEFAULT 'OFFLINE' COMMENT 'ONLINE/OFFLINE',
  last_heartbeat_at DATETIME   NULL,
  synced_std_version INT       NULL COMMENT '게이트웨이가 보유한 기준값 버전',
  PRIMARY KEY (gateway_id),
  UNIQUE KEY uk_gateway_code (gateway_code),
  CONSTRAINT fk_gw_farm FOREIGN KEY (farm_id) REFERENCES TB_FARM(farm_id)
) COMMENT='현장 게이트웨이';

-- ---------------------------------------------------------------------
-- 7. 센서 채널 (기존 보완: 1행 = 1측정 채널)          REQ-F-01
-- ---------------------------------------------------------------------
CREATE TABLE TB_SENSOR (
  sensor_id       INT          NOT NULL AUTO_INCREMENT,
  farm_id         INT          NOT NULL,
  zone_id         INT          NULL     COMMENT 'NULL = 공용/외부',
  gateway_id      INT          NOT NULL,
  sensor_code     VARCHAR(20)  NOT NULL COMMENT 'S-T01 ...',
  metric          VARCHAR(20)  NOT NULL COMMENT 'TEMP/HUMI/CO2/SOLAR/SUBSTRATE/EC/PH/TEMP_OUT',
  unit            VARCHAR(10)  NOT NULL COMMENT 'C, %, ppm, W/m2, dS/m, pH',
  valid_min       DECIMAL(10,3) NOT NULL COMMENT '물리적 유효 범위 하한',
  valid_max       DECIMAL(10,3) NOT NULL,
  spike_limit     DECIMAL(10,3) NULL    COMMENT '1분 급변 허용치',
  install_note    VARCHAR(100) NULL     COMMENT '설치 위치·높이',
  is_simulated    TINYINT(1)   NOT NULL DEFAULT 1,
  status          VARCHAR(10)  NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE/FAULT/RETIRED',
  last_received_at DATETIME    NULL,
  PRIMARY KEY (sensor_id),
  UNIQUE KEY uk_sensor_code (farm_id, sensor_code),
  CONSTRAINT fk_sensor_farm FOREIGN KEY (farm_id) REFERENCES TB_FARM(farm_id),
  CONSTRAINT fk_sensor_zone FOREIGN KEY (zone_id) REFERENCES TB_ZONE(zone_id),
  CONSTRAINT fk_sensor_gw   FOREIGN KEY (gateway_id) REFERENCES TB_GATEWAY(gateway_id)
) COMMENT='센서 채널';

-- ---------------------------------------------------------------------
-- 8. 센서 원시 데이터 (기존 보완: 품질 플래그, 중복 방지)  REQ-F-01, REQ-N-05
--    약 578만 행/년 (11채널 × 1,440 × 365). 3년 보관 후 삭제 배치.
-- ---------------------------------------------------------------------
CREATE TABLE TB_SENSOR_DATA (
  data_id         BIGINT        NOT NULL AUTO_INCREMENT,
  sensor_id       INT           NOT NULL,
  measured_at     DATETIME      NOT NULL COMMENT '1분 구간 시작 시각',
  value           DECIMAL(10,3) NOT NULL COMMENT '1분 평균',
  value_min       DECIMAL(10,3) NULL,
  value_max       DECIMAL(10,3) NULL,
  sample_count    SMALLINT      NULL     COMMENT '10초 샘플 수 (정상 6)',
  quality         VARCHAR(10)   NOT NULL DEFAULT 'OK' COMMENT 'OK/SUSPECT/OUT_RANGE/SPIKE',
  msg_id          VARCHAR(80)   NOT NULL COMMENT '게이트웨이 메시지 ID (중복 방지)',
  is_buffered     TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '통신 복구 후 재전송분',
  received_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (data_id),
  UNIQUE KEY uk_data_msg (msg_id),
  UNIQUE KEY uk_data_sensor_time (sensor_id, measured_at),
  CONSTRAINT fk_data_sensor FOREIGN KEY (sensor_id) REFERENCES TB_SENSOR(sensor_id),
  CONSTRAINT ck_data_quality CHECK (quality IN ('OK','SUSPECT','OUT_RANGE','SPIKE'))
) COMMENT='센서 원시 데이터 (1분)';

-- ---------------------------------------------------------------------
-- 9. 센서 시간 집계 (신규) - 장기 조회·그래프            REQ-F-10
-- ---------------------------------------------------------------------
CREATE TABLE TB_SENSOR_DATA_HOURLY (
  sensor_id       INT           NOT NULL,
  hour_at         DATETIME      NOT NULL,
  avg_value       DECIMAL(10,3) NOT NULL,
  min_value       DECIMAL(10,3) NOT NULL,
  max_value       DECIMAL(10,3) NOT NULL,
  ok_count        SMALLINT      NOT NULL COMMENT '품질 OK 분 수 (최대 60)',
  PRIMARY KEY (sensor_id, hour_at),
  CONSTRAINT fk_hourly_sensor FOREIGN KEY (sensor_id) REFERENCES TB_SENSOR(sensor_id)
) COMMENT='센서 시간 집계';

-- ---------------------------------------------------------------------
-- 10. 제어 장치 (기존 보완: 구역, 수동 유지 시간, 상태) REQ-F-08
-- ---------------------------------------------------------------------
CREATE TABLE TB_DEVICE (
  device_id       INT          NOT NULL AUTO_INCREMENT,
  farm_id         INT          NOT NULL,
  zone_id         INT          NULL     COMMENT 'NULL = 동 전체',
  gateway_id      INT          NOT NULL,
  device_code     VARCHAR(20)  NOT NULL COMMENT 'D-FAN01 ...',
  device_type     VARCHAR(20)  NOT NULL COMMENT 'VENT/FAN/HEATER/SHADE/LIGHT/VALVE/NUTRIENT',
  device_name     VARCHAR(30)  NOT NULL,
  mode            VARCHAR(10)  NOT NULL DEFAULT 'AUTO' COMMENT 'AUTO/MANUAL',
  manual_until    DATETIME     NULL     COMMENT '수동 모드 종료 시각 (지나면 AUTO 복귀)',
  current_state   VARCHAR(10)  NOT NULL DEFAULT 'OFF' COMMENT '마지막 ACK 기준 ON/OFF/OPEN/CLOSE',
  state_changed_at DATETIME    NULL,
  is_simulated    TINYINT(1)   NOT NULL DEFAULT 1,
  PRIMARY KEY (device_id),
  UNIQUE KEY uk_device_code (farm_id, device_code),
  CONSTRAINT fk_device_farm FOREIGN KEY (farm_id) REFERENCES TB_FARM(farm_id),
  CONSTRAINT fk_device_zone FOREIGN KEY (zone_id) REFERENCES TB_ZONE(zone_id),
  CONSTRAINT fk_device_gw   FOREIGN KEY (gateway_id) REFERENCES TB_GATEWAY(gateway_id),
  CONSTRAINT ck_device_mode CHECK (mode IN ('AUTO','MANUAL'))
) COMMENT='제어 장치';

-- ---------------------------------------------------------------------
-- 11. 자동 제어 규칙 (신규) - 히스테리시스·안전 한계    REQ-F-02~04
-- ---------------------------------------------------------------------
CREATE TABLE TB_CONTROL_RULE (
  rule_id         INT           NOT NULL AUTO_INCREMENT,
  farm_id         INT           NOT NULL,
  rule_code       VARCHAR(10)   NOT NULL COMMENT 'CR-01 ...',
  rule_name       VARCHAR(50)   NOT NULL,
  zone_id         INT           NULL,
  metric          VARCHAR(20)   NOT NULL,
  period          VARCHAR(10)   NOT NULL DEFAULT 'ALL' COMMENT 'DAY/NIGHT/ALL',
  compare_op      VARCHAR(2)    NOT NULL COMMENT 'GE / LE',
  on_threshold    DECIMAL(10,3) NOT NULL,
  off_threshold   DECIMAL(10,3) NOT NULL COMMENT '히스테리시스 해제값',
  target_device_type VARCHAR(20) NOT NULL,
  action_on       VARCHAR(10)   NOT NULL,
  action_off      VARCHAR(10)   NOT NULL,
  min_run_sec     INT           NOT NULL DEFAULT 180,
  max_run_sec     INT           NULL     COMMENT '관수 1회 최대',
  max_daily_count INT           NULL     COMMENT '관수 일 최대',
  is_safety       TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '1 = 수동 모드보다 우선',
  priority        TINYINT       NOT NULL DEFAULT 5 COMMENT '작을수록 우선',
  is_enabled      TINYINT(1)    NOT NULL DEFAULT 1,
  PRIMARY KEY (rule_id),
  UNIQUE KEY uk_rule_code (farm_id, rule_code),
  CONSTRAINT fk_rule_farm FOREIGN KEY (farm_id) REFERENCES TB_FARM(farm_id),
  CONSTRAINT fk_rule_zone FOREIGN KEY (zone_id) REFERENCES TB_ZONE(zone_id)
) COMMENT='자동 제어 규칙';

-- ---------------------------------------------------------------------
-- 12. 제어 명령 (신규) - 명령 수명주기, 멱등키          REQ-F-16
-- ---------------------------------------------------------------------
CREATE TABLE TB_CONTROL_COMMAND (
  command_id      BIGINT       NOT NULL AUTO_INCREMENT,
  device_id       INT          NOT NULL,
  action          VARCHAR(10)  NOT NULL COMMENT 'ON/OFF/OPEN/CLOSE',
  duration_sec    INT          NULL,
  source          VARCHAR(10)  NOT NULL COMMENT 'AUTO/MANUAL/SAFETY/FAILSAFE',
  rule_id         INT          NULL,
  requested_by    INT          NULL     COMMENT '수동 명령 사용자',
  idempotency_key VARCHAR(64)  NOT NULL,
  status          VARCHAR(10)  NOT NULL DEFAULT 'REQUESTED' COMMENT 'REQUESTED/SENT/ACKED/FAILED/TIMEOUT/REJECTED',
  retry_count     TINYINT      NOT NULL DEFAULT 0,
  reason          VARCHAR(200) NULL,
  requested_at    DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  sent_at         DATETIME(3)  NULL,
  acked_at        DATETIME(3)  NULL,
  PRIMARY KEY (command_id),
  UNIQUE KEY uk_cmd_idem (idempotency_key),
  KEY idx_cmd_device_time (device_id, requested_at),
  CONSTRAINT fk_cmd_device FOREIGN KEY (device_id) REFERENCES TB_DEVICE(device_id),
  CONSTRAINT fk_cmd_rule   FOREIGN KEY (rule_id) REFERENCES TB_CONTROL_RULE(rule_id),
  CONSTRAINT fk_cmd_user   FOREIGN KEY (requested_by) REFERENCES TB_USER(user_id)
) COMMENT='제어 명령';

-- ---------------------------------------------------------------------
-- 13. 장치 상태 이력 (기존 TB_CONTROL_LOG 의미 변경: 명령이 아닌 실제 상태 변화)
-- ---------------------------------------------------------------------
CREATE TABLE TB_CONTROL_LOG (
  log_id          BIGINT       NOT NULL AUTO_INCREMENT,
  device_id       INT          NOT NULL,
  command_id      BIGINT       NULL     COMMENT 'NULL = 게이트웨이 안전 운전 등 서버 밖 변화',
  prev_state      VARCHAR(10)  NULL,
  new_state       VARCHAR(10)  NOT NULL,
  changed_by      VARCHAR(10)  NOT NULL COMMENT 'AUTO/MANUAL/SAFETY/FAILSAFE',
  changed_at      DATETIME(3)  NOT NULL,
  PRIMARY KEY (log_id),
  KEY idx_log_device_time (device_id, changed_at),
  CONSTRAINT fk_log_device FOREIGN KEY (device_id) REFERENCES TB_DEVICE(device_id),
  CONSTRAINT fk_log_cmd    FOREIGN KEY (command_id) REFERENCES TB_CONTROL_COMMAND(command_id)
) COMMENT='장치 상태 이력';

-- ---------------------------------------------------------------------
-- 14. 알림 (기존 보완: 심각도, 중복 억제, 처리 상태)    REQ-F-09
-- ---------------------------------------------------------------------
CREATE TABLE TB_ALERT (
  alert_id        BIGINT       NOT NULL AUTO_INCREMENT,
  farm_id         INT          NOT NULL,
  zone_id         INT          NULL,
  alert_type      VARCHAR(20)  NOT NULL COMMENT 'THRESHOLD/SENSOR_FAIL/OUTLIER/DEVICE_NOACK/GW_OFFLINE/POWER/BEE/HARVEST',
  severity        VARCHAR(10)  NOT NULL COMMENT 'INFO/WARN/CRITICAL',
  dedupe_key      VARCHAR(100) NOT NULL COMMENT '예: THRESHOLD:Z1:TEMP_HIGH',
  message         VARCHAR(300) NOT NULL,
  status          VARCHAR(10)  NOT NULL DEFAULT 'OPEN' COMMENT 'OPEN/ACK/RESOLVED',
  occur_count     INT          NOT NULL DEFAULT 1,
  first_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  acked_by        INT          NULL,
  resolved_at     DATETIME     NULL,
  PRIMARY KEY (alert_id),
  KEY idx_alert_dedupe (dedupe_key, status),
  KEY idx_alert_farm_time (farm_id, first_at),
  CONSTRAINT fk_alert_farm FOREIGN KEY (farm_id) REFERENCES TB_FARM(farm_id),
  CONSTRAINT fk_alert_zone FOREIGN KEY (zone_id) REFERENCES TB_ZONE(zone_id),
  CONSTRAINT fk_alert_user FOREIGN KEY (acked_by) REFERENCES TB_USER(user_id)
) COMMENT='알림';

-- 알림 발송 내역 (알림 1건 → 채널별 발송 n건)
CREATE TABLE TB_ALERT_DELIVERY (
  delivery_id     BIGINT       NOT NULL AUTO_INCREMENT,
  alert_id        BIGINT       NOT NULL,
  user_id         INT          NOT NULL,
  channel         VARCHAR(10)  NOT NULL COMMENT 'WEB/SMS/EMAIL',
  result          VARCHAR(10)  NOT NULL COMMENT 'SENT/FAILED',
  try_count       TINYINT      NOT NULL DEFAULT 1,
  sent_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (delivery_id),
  CONSTRAINT fk_deliv_alert FOREIGN KEY (alert_id) REFERENCES TB_ALERT(alert_id),
  CONSTRAINT fk_deliv_user  FOREIGN KEY (user_id) REFERENCES TB_USER(user_id)
) COMMENT='알림 발송 내역';

-- ---------------------------------------------------------------------
-- 15. 벌통 (신규)                                         REQ-F-06
-- ---------------------------------------------------------------------
CREATE TABLE TB_BEEHIVE (
  hive_id         INT          NOT NULL AUTO_INCREMENT,
  cycle_id        INT          NOT NULL,
  zone_id         INT          NULL,
  placed_date     DATE         NOT NULL,
  replace_days    INT          NOT NULL COMMENT '교체 주기(일), 농가 설정',
  removed_date    DATE         NULL,
  PRIMARY KEY (hive_id),
  CONSTRAINT fk_hive_cycle FOREIGN KEY (cycle_id) REFERENCES TB_CROP_CYCLE(cycle_id),
  CONSTRAINT fk_hive_zone  FOREIGN KEY (zone_id) REFERENCES TB_ZONE(zone_id)
) COMMENT='벌통';

-- ---------------------------------------------------------------------
-- 16. 수확 판별 결과 (기존 보완: 단계, 이미지 품질)      REQ-F-07
-- ---------------------------------------------------------------------
CREATE TABLE TB_IMAGE_RESULT (
  image_id        BIGINT       NOT NULL AUTO_INCREMENT,
  zone_id         INT          NOT NULL,
  camera_code     VARCHAR(20)  NOT NULL COMMENT 'CAM-01',
  image_path      VARCHAR(255) NOT NULL,
  captured_at     DATETIME     NOT NULL,
  image_quality   VARCHAR(10)  NOT NULL COMMENT 'GOOD/BACKLIT/BLUR/DARK',
  red_ratio_pct   DECIMAL(5,2) NULL     COMMENT '과실 영역 중 붉은 화소 비율',
  ripeness_stage  VARCHAR(10)  NULL     COMMENT 'GREEN/BREAKER/TURNING/PINK/LIGHTRED/RED',
  harvest_candidate TINYINT(1) NOT NULL DEFAULT 0,
  algorithm_ver   VARCHAR(20)  NOT NULL,
  label_stage     VARCHAR(10)  NULL     COMMENT '사람이 붙인 정답 (정확도 측정용)',
  PRIMARY KEY (image_id),
  KEY idx_img_zone_time (zone_id, captured_at),
  CONSTRAINT fk_img_zone FOREIGN KEY (zone_id) REFERENCES TB_ZONE(zone_id)
) COMMENT='수확 판별 결과';

-- ---------------------------------------------------------------------
-- 17. 외부 기상 일자료 (신규)                             REQ-F-15
-- ---------------------------------------------------------------------
CREATE TABLE TB_WEATHER_DAILY (
  station_id      VARCHAR(10)  NOT NULL COMMENT '202',
  obs_date        DATE         NOT NULL,
  tavg_c          DECIMAL(4,1) NULL,
  tmax_c          DECIMAL(4,1) NULL,
  tmin_c          DECIMAL(4,1) NULL,
  rain_mm         DECIMAL(6,1) NULL,
  rh_pct          DECIMAL(4,1) NULL,
  sunshine_hr     DECIMAL(4,1) NULL,
  solar_mj_m2     DECIMAL(5,2) NULL,
  missing_flags   VARCHAR(50)  NULL     COMMENT '결측 요소 목록',
  source_file     VARCHAR(100) NOT NULL COMMENT '기상자료개방포털 다운로드 파일명',
  imported_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (station_id, obs_date)
) COMMENT='외부 기상 일자료 (ASOS)';

-- ---------------------------------------------------------------------
-- 18. 유효적산온도 일별 (신규) - 내부/외부 구분 저장    REQ-F-14
-- ---------------------------------------------------------------------
CREATE TABLE TB_GDD_DAILY (
  cycle_id        INT          NOT NULL,
  calc_date       DATE         NOT NULL,
  source          VARCHAR(10)  NOT NULL COMMENT 'INTERNAL(하우스 센서) / EXTERNAL(기상청)',
  method          VARCHAR(10)  NOT NULL COMMENT 'HOURLY(시간 평균) / MAXMIN((최고+최저)/2)',
  tavg_c          DECIMAL(4,1) NULL,
  base_c          DECIMAL(4,1) NOT NULL,
  upper_c         DECIMAL(4,1) NOT NULL,
  gdd             DECIMAL(5,2) NULL,
  cum_gdd         DECIMAL(7,2) NULL,
  coverage_pct    DECIMAL(5,1) NOT NULL COMMENT '유효 데이터 비율',
  is_complete     TINYINT(1)   NOT NULL COMMENT 'coverage ≥ 80%',
  calculated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (cycle_id, calc_date, source),
  CONSTRAINT fk_gdd_cycle FOREIGN KEY (cycle_id) REFERENCES TB_CROP_CYCLE(cycle_id)
) COMMENT='유효적산온도 일별';

-- ---------------------------------------------------------------------
-- 19. 설정 변경 이력 (신규) - 기준온도·규칙·모드 변경 감사
-- ---------------------------------------------------------------------
CREATE TABLE TB_SETTING_HISTORY (
  history_id      BIGINT       NOT NULL AUTO_INCREMENT,
  entity_type     VARCHAR(20)  NOT NULL COMMENT 'CROP_STD/CONTROL_RULE/CROP_CYCLE/DEVICE',
  entity_id       BIGINT       NOT NULL,
  field_name      VARCHAR(50)  NOT NULL,
  old_value       VARCHAR(200) NULL,
  new_value       VARCHAR(200) NULL,
  changed_by      INT          NOT NULL,
  changed_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (history_id),
  KEY idx_hist_entity (entity_type, entity_id),
  CONSTRAINT fk_hist_user FOREIGN KEY (changed_by) REFERENCES TB_USER(user_id)
) COMMENT='설정 변경 이력';

-- ---------------------------------------------------------------------
-- 보존 정책 (REQ-N-05): 매일 03:00 배치
--   DELETE FROM TB_SENSOR_DATA WHERE measured_at < NOW() - INTERVAL 3 YEAR LIMIT 10000; (반복)
-- 운영 확장: 데이터가 커지면 TB_SENSOR_DATA를 월 단위 RANGE 파티션으로 전환
--   (파티션 키를 PK에 포함해야 하므로 PK를 (data_id, measured_at)으로 변경 필요)
-- ---------------------------------------------------------------------
