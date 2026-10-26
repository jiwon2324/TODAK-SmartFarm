# -*- coding: utf-8 -*-
"""data.py에서 초기 데이터 SQL(02_seed.sql)을 만든다."""
import os
import data as D

OUT = os.path.join(os.path.dirname(__file__), "..", "TODAK_산출물", "schema", "02_seed.sql")

METRIC = {"S-T": ("TEMP", "C", -20, 60, 5), "S-H": ("HUMI", "%", 0, 100, 20), "S-CO2": ("CO2", "ppm", 0, 5000, 500),
          "S-SOL": ("SOLAR", "W/m2", 0, 1500, 600), "S-SM": ("SUBSTRATE", "%", 0, 100, 15), "S-EC": ("EC", "dS/m", 0, 10, 1.5),
          "S-PH": ("PH", "pH", 0, 14, 1.5), "S-TO": ("TEMP_OUT", "C", -40, 50, 5)}
DTYPE = {"D-VENT": "VENT", "D-FAN": "FAN", "D-HEAT": "HEATER", "D-SHADE": "SHADE", "D-LIGHT": "LIGHT", "D-VALVE": "VALVE", "D-NUT": "NUTRIENT"}


def q(s):
    return "NULL" if s is None else "'" + str(s).replace("'", "''") + "'"


def zone_ref(z):
    return {"Z1": "1", "Z2": "2"}.get(z, "NULL")


def main():
    L = ["-- TODAK 초기 데이터 (data.py에서 자동 생성). 01_schema.sql 실행 후 실행.", "USE todak;", ""]
    L.append("-- 관리자 계정: 비밀번호 해시는 애플리케이션 최초 실행 시 BCrypt로 교체한다 (평문 저장 금지)")
    L.append("INSERT INTO TB_USER (user_id, login_id, password_hash, name, role) VALUES")
    L.append("  (1, 'admin', '{bcrypt-hash-set-on-first-run}', '운영 관리자', 'ADMIN'),")
    L.append("  (2, 'farmer01', '{bcrypt-hash-set-on-first-run}', '양평 농가(가상)', 'FARMER'),")
    L.append("  (3, 'viewer01', '{bcrypt-hash-set-on-first-run}', '검수자', 'VIEWER');")
    L.append("")
    L.append("INSERT INTO TB_FARM (farm_id, owner_user_id, farm_name, region, area_m2, facility_type, culture_type, kma_station_id) VALUES")
    L.append("  (1, 2, 'TODAK 양평 1동', '경기도 양평군 (세부 주소 미정)', 330.58, '단동 비닐하우스', '코이어 배지 양액재배 (가정)', '202');")
    L.append("")
    L.append("INSERT INTO TB_ZONE (zone_id, farm_id, zone_code, zone_name, area_m2, x_from_m, x_to_m, description) VALUES")
    L.append("  (1, 1, 'Z1', '입구측 구역', 165.29, 0.00, 20.75, '출입구·난방기와 가까워 온도 변동이 큼'),")
    L.append("  (2, 1, 'Z2', '안쪽 구역', 165.29, 20.75, 41.50, '환기팬 쪽, 오후 일사·고온 영향');")
    L.append("")
    L.append("INSERT INTO TB_GATEWAY (gateway_id, farm_id, gateway_code, is_simulated) VALUES (1, 1, 'GW-01', 1);")
    L.append("")
    L.append("INSERT INTO TB_CROP_CYCLE (cycle_id, farm_id, variety, transplant_date, current_stage, gdd_base_c, gdd_upper_c) VALUES")
    L.append(f"  (1, 1, NULL, '2027-02-15', 'GROWTH', {D.GDD_BASE}, {D.GDD_UPPER});")
    L.append("")
    L.append("-- 재배 기준값 초기값: 개발 계획서 표 6-2 (근거 S4·S5·S6·S9), 시범운영 중 조정")
    L.append("INSERT INTO TB_CROP_STD (farm_id, zone_id, stage, version_no, day_temp_min, day_temp_max, night_temp_min, night_temp_max,")
    L.append("  humidity_min, humidity_max, ec_min, ec_max, ph_min, ph_max, substrate_moisture_min, source_note) VALUES")
    L.append("  (1, NULL, 'GROWTH',  1, 20.0, 28.0, 15.0, 18.0, 60.0, 90.0, 1.0, 2.0, 5.5, 6.8, 55.0, 'S4,S5,S6,S9'),")
    L.append("  (1, NULL, 'HARVEST', 1, 20.0, 28.0, 15.0, 18.0, 60.0, 90.0, 2.0, 2.5, 5.5, 6.8, 55.0, 'S4,S5,S6,S9');")
    L.append("")
    rows = []
    for sid, name, z, pos, inst, *_ in D.SENSORS:
        if sid.startswith("CAM"):
            continue
        key = next(k for k in sorted(METRIC, key=len, reverse=True) if sid.startswith(k))
        m, u, lo, hi, sp = METRIC[key]
        rows.append(f"  (1, {zone_ref(z)}, 1, {q(sid)}, {q(m)}, {q(u)}, {lo}, {hi}, {sp}, {q(inst)})")
    L.append("INSERT INTO TB_SENSOR (farm_id, zone_id, gateway_id, sensor_code, metric, unit, valid_min, valid_max, spike_limit, install_note) VALUES")
    L.append(",\n".join(rows) + ";")
    L.append("")
    rows = []
    for did, name, z, pos, inst, *_ in D.DEVICES:
        key = next((k for k in DTYPE if did.startswith(k)), None)
        if not key:
            continue
        state = "CLOSE" if DTYPE[key] in ("VENT", "SHADE") else "OFF"
        rows.append(f"  (1, {zone_ref(z)}, 1, {q(did)}, {q(DTYPE[key])}, {q(name)}, {q(state)})")
    L.append("INSERT INTO TB_DEVICE (farm_id, zone_id, gateway_id, device_code, device_type, device_name, current_state) VALUES")
    L.append(",\n".join(rows) + ";")
    L.append("")
    L.append("-- 자동 제어 규칙 초기값: 개발 계획서 표 14-3 (CR-01 ~ CR-06)")
    L.append("INSERT INTO TB_CONTROL_RULE (farm_id, rule_code, rule_name, metric, period, compare_op, on_threshold, off_threshold,")
    L.append("  target_device_type, action_on, action_off, min_run_sec, max_run_sec, max_daily_count, is_safety, priority) VALUES")
    L.append("  (1, 'CR-01', '주간 환기', 'TEMP', 'DAY', 'GE', 28.0, 26.0, 'VENT', 'OPEN', 'CLOSE', 180, NULL, NULL, 0, 5),")
    L.append("  (1, 'CR-02', '야간 난방', 'TEMP', 'NIGHT', 'LE', 14.0, 16.0, 'HEATER', 'ON', 'OFF', 300, NULL, NULL, 0, 5),")
    L.append("  (1, 'CR-03', '차광', 'SOLAR', 'DAY', 'GE', 800, 500, 'SHADE', 'CLOSE', 'OPEN', 600, NULL, NULL, 0, 6),")
    L.append("  (1, 'CR-04', '관수', 'SUBSTRATE', 'ALL', 'LE', 55.0, 100.0, 'VALVE', 'ON', 'OFF', 60, 300, 12, 0, 6),")
    L.append("  (1, 'CR-05', '고온 안전', 'TEMP', 'ALL', 'GE', 35.0, 32.0, 'VENT', 'OPEN', 'CLOSE', 180, NULL, NULL, 1, 1),")
    L.append("  (1, 'CR-06', '저온 안전', 'TEMP', 'ALL', 'LE', 5.0, 8.0, 'HEATER', 'ON', 'OFF', 300, NULL, NULL, 1, 1);")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("seed rows written")


if __name__ == "__main__":
    main()
