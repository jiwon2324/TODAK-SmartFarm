-- TODAK 초기 데이터 (Flyway V2)
-- 테스트 계정 비밀번호는 README '테스트 계정' 절 참조. 운영 배포 전 반드시 변경한다.
-- 농장 2는 농가 간 데이터 격리(인수 기준 6번)를 검증하기 위한 비교용 가상 농가다.
-- 작기 정식일은 실행일 기준 14일 전으로 두어 시뮬레이터 과거 데이터로 GDD를 바로 확인할 수 있게 했다 (시뮬레이션 작기).

INSERT INTO TB_USER (user_id, login_id, password_hash, name, phone, role) VALUES
  (1, 'admin',    '$2a$10$KwJi1l3cKw1r4QsX77IoxOC/FPCvHbaYCzvM9VxbNBAPaJEqZGTTu', '운영 관리자',     '010-0000-0000', 'ADMIN'),
  (2, 'farmer01', '$2a$10$OWKkpAz9kT2iUPrVdHrfZuMVSNuDhoFqn1P5dm6er0Ewc8LL8HCHm', '양평 농가(가상)', '010-0000-0001', 'FARMER'),
  (3, 'farmer02', '$2a$10$OWKkpAz9kT2iUPrVdHrfZuMVSNuDhoFqn1P5dm6er0Ewc8LL8HCHm', '비교 농가(가상)', '010-0000-0002', 'FARMER');

INSERT INTO TB_FARM (farm_id, owner_user_id, farm_name, region, area_m2, facility_type, culture_type, kma_station_id) VALUES
  (1, 2, 'TODAK 양평 1동', '경기도 양평군 (세부 주소 미정)', 330.58, '단동 비닐하우스', '코이어 배지 양액재배 (가정)', '202'),
  (2, 3, '비교 농가 1동', '가상 (격리 검증용)', 330.58, '단동 비닐하우스', NULL, NULL);

INSERT INTO TB_USER_FARM (user_id, farm_id) VALUES (2, 1), (3, 2);

INSERT INTO TB_ZONE (zone_id, farm_id, zone_code, zone_name, area_m2, x_from_m, x_to_m, description) VALUES
  (1, 1, 'Z1', '입구측 구역', 165.29, 0.00, 20.75, '출입구·난방기와 가까워 온도 변동이 큼'),
  (2, 1, 'Z2', '안쪽 구역',   165.29, 20.75, 41.50, '환기팬 쪽, 오후 일사·고온 영향'),
  (3, 2, 'Z1', '단일 구역',   330.58, 0.00, 41.50, '격리 검증용');

INSERT INTO TB_GATEWAY (gateway_id, farm_id, gateway_code, is_simulated) VALUES
  (1, 1, 'GW-01', 1), (2, 2, 'GW-02', 1);

INSERT INTO TB_CROP_CYCLE (cycle_id, farm_id, variety, transplant_date, current_stage, gdd_base_c, gdd_upper_c) VALUES
  (1, 1, '시뮬레이션 작기 (품종 미정)', DATE_SUB(CURDATE(), INTERVAL 14 DAY), 'GROWTH', 10.0, 30.0),
  (2, 2, '격리 검증용', DATE_SUB(CURDATE(), INTERVAL 14 DAY), 'GROWTH', 10.0, 30.0);

INSERT INTO TB_CROP_STD (farm_id, zone_id, stage, version_no, day_temp_min, day_temp_max, night_temp_min, night_temp_max,
  humidity_min, humidity_max, ec_min, ec_max, ph_min, ph_max, substrate_moisture_min, source_note) VALUES
  (1, NULL, 'GROWTH',  1, 20.0, 28.0, 15.0, 18.0, 60.0, 90.0, 1.0, 2.0, 5.5, 6.8, 55.0, 'S4,S5,S6,S9 (개발 계획서 4.3)'),
  (1, NULL, 'FLOWER',  1, 20.0, 28.0, 15.0, 18.0, 60.0, 90.0, 1.5, 2.5, 5.5, 6.8, 55.0, 'S4,S5,S6,S9'),
  (1, NULL, 'HARVEST', 1, 20.0, 28.0, 15.0, 18.0, 60.0, 90.0, 2.0, 2.5, 5.5, 6.8, 55.0, 'S4,S5,S6,S9'),
  (2, NULL, 'GROWTH',  1, 20.0, 28.0, 15.0, 18.0, 60.0, 90.0, 1.0, 2.0, 5.5, 6.8, 55.0, '격리 검증용');

INSERT INTO TB_SENSOR (sensor_id, farm_id, zone_id, gateway_id, sensor_code, metric, unit, valid_min, valid_max, spike_limit, install_note) VALUES
  (1,  1, 1,    1, 'S-T01',    'TEMP',      'C',    -20, 60,   5,   '생장점 높이 1.5m, 통풍식 복사 차폐함'),
  (2,  1, 1,    1, 'S-H01',    'HUMI',      '%',    0,   100,  20,  'S-T01과 동일 함체'),
  (3,  1, 2,    1, 'S-T02',    'TEMP',      'C',    -20, 60,   5,   '생장점 높이 1.5m'),
  (4,  1, 2,    1, 'S-H02',    'HUMI',      '%',    0,   100,  20,  'S-T02와 동일 함체'),
  (5,  1, NULL, 1, 'S-CO2-01', 'CO2',       'ppm',  0,   5000, 500, '높이 1.2m, 중앙'),
  (6,  1, NULL, 1, 'S-SOL01',  'SOLAR',     'W/m2', 0,   1500, 600, '지붕 필름 아래 3.0m'),
  (7,  1, 1,    1, 'S-SM01',   'SUBSTRATE', '%',    0,   100,  15,  '대표 배지 슬래브 중앙'),
  (8,  1, 2,    1, 'S-SM02',   'SUBSTRATE', '%',    0,   100,  15,  '대표 배지 슬래브 중앙'),
  (9,  1, NULL, 1, 'S-EC01',   'EC',        'dS/m', 0,   10,   1.5, '양액 공급 배관 인라인'),
  (10, 1, NULL, 1, 'S-PH01',   'PH',        'pH',   0,   14,   1.5, '양액 공급 배관 인라인'),
  (11, 1, NULL, 1, 'S-TO01',   'TEMP_OUT',  'C',    -40, 50,   5,   '하우스 밖 북측 1.5m'),
  (12, 2, 3,    2, 'S-T01',    'TEMP',      'C',    -20, 60,   5,   '격리 검증용');

INSERT INTO TB_DEVICE (device_id, farm_id, zone_id, gateway_id, device_code, device_type, device_name, current_state) VALUES
  (1,  1, NULL, 1, 'D-VENT01',  'VENT',     '측창 개폐기(좌)', 'CLOSE'),
  (2,  1, NULL, 1, 'D-VENT02',  'VENT',     '측창 개폐기(우)', 'CLOSE'),
  (3,  1, 2,    1, 'D-FAN01',   'FAN',      '환기팬 1',        'OFF'),
  (4,  1, 2,    1, 'D-FAN02',   'FAN',      '환기팬 2',        'OFF'),
  (5,  1, 1,    1, 'D-HEAT01',  'HEATER',   '온풍난방기',      'OFF'),
  (6,  1, NULL, 1, 'D-SHADE01', 'SHADE',    '차광막 모터',     'OPEN'),
  (7,  1, 1,    1, 'D-LIGHT01', 'LIGHT',    '보광등 회로 1',   'OFF'),
  (8,  1, 2,    1, 'D-LIGHT02', 'LIGHT',    '보광등 회로 2',   'OFF'),
  (9,  1, 1,    1, 'D-VALVE01', 'VALVE',    '관수 밸브 1',     'OFF'),
  (10, 1, 2,    1, 'D-VALVE02', 'VALVE',    '관수 밸브 2',     'OFF'),
  (11, 1, NULL, 1, 'D-NUT01',   'NUTRIENT', '양액기(기존)',    'OFF'),
  (12, 2, 3,    2, 'D-FAN01',   'FAN',      '환기팬 1',        'OFF');

-- 자동 제어 규칙 (개발 계획서 표 14 CR-01~06 + 구현 단계 보광 CR-07)
-- 장치 동작은 유형별로 정한다: VENT 활성=OPEN, SHADE 활성=CLOSE(차광), 나머지 활성=ON
INSERT INTO TB_CONTROL_RULE (farm_id, rule_code, rule_name, metric, period, compare_op, on_threshold, off_threshold,
  target_device_type, action_on, action_off, min_run_sec, max_run_sec, max_daily_count, is_safety, priority) VALUES
  (1, 'CR-01', '주간 환기', 'TEMP',      'DAY',   'GE', 28.0, 26.0, 'VENT',     'OPEN',  'CLOSE', 180, NULL, NULL, 0, 5),
  (1, 'CR-02', '야간 난방', 'TEMP',      'NIGHT', 'LE', 14.0, 16.0, 'HEATER',   'ON',    'OFF',   300, NULL, NULL, 0, 5),
  (1, 'CR-03', '차광',      'SOLAR',     'DAY',   'GE', 800,  500,  'SHADE',    'CLOSE', 'OPEN',  600, NULL, NULL, 0, 6),
  (1, 'CR-04', '관수',      'SUBSTRATE', 'ALL',   'LE', 55.0, 65.0, 'VALVE',    'ON',    'OFF',   60,  300,  12,   0, 6),
  (1, 'CR-05', '고온 안전', 'TEMP',      'ALL',   'GE', 35.0, 32.0, 'VENT,FAN', 'ON',    'OFF',   180, NULL, NULL, 1, 1),
  (1, 'CR-06', '저온 안전', 'TEMP',      'ALL',   'LE', 5.0,  8.0,  'HEATER',   'ON',    'OFF',   300, NULL, NULL, 1, 1),
  (1, 'CR-07', '보광',      'SOLAR',     'DAY',   'LE', 100,  200,  'LIGHT',    'ON',    'OFF',   600, NULL, NULL, 0, 7);

INSERT INTO TB_BEEHIVE (cycle_id, zone_id, placed_date, replace_days) VALUES
  (1, NULL, DATE_SUB(CURDATE(), INTERVAL 5 DAY), 6);
