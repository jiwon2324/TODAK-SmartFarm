# -*- coding: utf-8 -*-
"""
비닐하우스 1동(100평) 가상 환경 모델. 1분 단위로 상태를 진행한다.
모든 값은 시뮬레이션이며 양평 실측·기상청 관측값이 아니다.

열 수지(°C/분):  dT = k_env·(T_out − T_in) + k_sol·S_in + heater·H − (vent_loss + fan_loss)·(T_in − T_out)
 - k_env 0.02: 닫힌 하우스 자연 손실
 - k_sol 0.00048: 일사 500 W/㎡에서 외부보다 약 12°C 높게 평형
 - H 0.24: 난방기만으로 외부보다 약 12°C 높게 평형
 - 측창 1개 0.03, 환기팬 1대 0.04 추가 손실
"""
import math
import random
from dataclasses import dataclass, field
from datetime import datetime

K_ENV, K_SOL, HEAT = 0.02, 0.00048, 0.24
VENT_LOSS, FAN_LOSS = 0.03, 0.04

SENSORS = [
    # (코드, 구역, 지표)
    ("S-T01", "Z1", "TEMP"), ("S-H01", "Z1", "HUMI"), ("S-T02", "Z2", "TEMP"), ("S-H02", "Z2", "HUMI"),
    ("S-CO2-01", "COMMON", "CO2"), ("S-SOL01", "COMMON", "SOLAR"), ("S-SM01", "Z1", "SUBSTRATE"), ("S-SM02", "Z2", "SUBSTRATE"),
    ("S-EC01", "COMMON", "EC"), ("S-PH01", "COMMON", "PH"), ("S-TO01", "COMMON", "TEMP_OUT"),
]
UNITS = {"TEMP": "C", "HUMI": "%", "CO2": "ppm", "SOLAR": "W/m2", "SUBSTRATE": "%", "EC": "dS/m", "PH": "pH", "TEMP_OUT": "C"}

DEVICES = {
    "D-VENT01": "CLOSE", "D-VENT02": "CLOSE", "D-FAN01": "OFF", "D-FAN02": "OFF", "D-HEAT01": "OFF", "D-SHADE01": "OPEN",
    "D-LIGHT01": "OFF", "D-LIGHT02": "OFF", "D-VALVE01": "OFF", "D-VALVE02": "OFF", "D-NUT01": "OFF",
}


@dataclass
class Scenario:
    name: str = "normal"
    until: float = 0.0          # epoch 초, 0이면 계속
    target: str | None = None


@dataclass
class Greenhouse:
    t_in: float = 18.0
    rh: float = 75.0
    co2: float = 450.0
    sm: dict = field(default_factory=lambda: {"Z1": 62.0, "Z2": 62.0})
    ec: float = 1.8
    ph: float = 6.1
    devices: dict = field(default_factory=lambda: dict(DEVICES))
    rnd: random.Random = field(default_factory=lambda: random.Random(42))
    cloud_by_day: dict = field(default_factory=dict)
    temp_offset: float = 0.0     # heat/cold 시나리오
    rh_offset: float = 0.0       # humid 시나리오
    dry_factor: float = 1.0      # dry 시나리오

    # ---------- 외부 조건 (시뮬레이션) ----------
    def outside_temp(self, t: datetime) -> float:
        h = t.hour + t.minute / 60
        doy = t.timetuple().tm_yday
        seasonal = 12.5 - 15.0 * math.cos(2 * math.pi * (doy - 15) / 365)   # 1월 약 −2.5, 7월 약 27.5 (가상 계절 곡선)
        daily = 5.5 * math.sin(2 * math.pi * (h - 9) / 24)
        return seasonal + daily + self.temp_offset_out()

    def temp_offset_out(self) -> float:
        return min(self.temp_offset, 0.0)  # cold: 외부 기온을 내림

    def solar(self, t: datetime) -> float:
        h = t.hour + t.minute / 60
        if h < 6.5 or h > 17.5:
            return 0.0
        day = t.date().isoformat()
        if day not in self.cloud_by_day:
            self.cloud_by_day[day] = self.rnd.uniform(0.45, 1.0)
        peak = 780.0 * self.cloud_by_day[day]
        return max(0.0, peak * math.sin(math.pi * (h - 6.5) / 11.0))

    # ---------- 1분 진행 ----------
    def step(self, t: datetime) -> dict:
        d = self.devices
        t_out = self.outside_temp(t)
        s_out = self.solar(t)
        shade = 0.5 if d["D-SHADE01"] == "CLOSE" else 1.0
        s_in = s_out * 0.7 * shade
        vents = sum(1 for k in ("D-VENT01", "D-VENT02") if d[k] == "OPEN")
        fans = sum(1 for k in ("D-FAN01", "D-FAN02") if d[k] == "ON")
        heater = 1 if d["D-HEAT01"] == "ON" else 0
        loss = vents * VENT_LOSS + fans * FAN_LOSS
        dT = K_ENV * (t_out - self.t_in) + K_SOL * s_in + heater * HEAT - loss * (self.t_in - t_out)
        self.t_in += dT
        heat_bias = max(self.temp_offset, 0.0) * 0.15    # heat: 하우스 내부만 서서히 올림
        self.t_in += heat_bias / 10.0

        # 습도: 온도가 오르면 낮아지고 환기하면 외기 쪽으로, 관수하면 오른다
        target_rh = 88 - 2.2 * (self.t_in - 15) + self.rh_offset
        if vents or fans:
            target_rh -= 6
        if d["D-VALVE01"] == "ON" or d["D-VALVE02"] == "ON":
            target_rh += 4
        self.rh += 0.08 * (target_rh - self.rh)
        self.rh = min(99.0, max(35.0, self.rh))

        # CO2: 낮에는 광합성으로 줄고, 환기하면 외기(420)로
        target_co2 = 520 - 0.18 * s_in
        if vents or fans:
            target_co2 = 420
        self.co2 += 0.05 * (target_co2 - self.co2)

        # 배지 수분: 증산으로 줄고 관수 밸브가 열리면 늘어난다
        for z, valve in (("Z1", "D-VALVE01"), ("Z2", "D-VALVE02")):
            et = (0.006 + 0.00007 * s_in) * self.dry_factor
            self.sm[z] += (0.8 if d[valve] == "ON" else 0.0) - et
            self.sm[z] = min(85.0, max(25.0, self.sm[z]))

        self.ec += self.rnd.uniform(-0.01, 0.01) + 0.002 * (1.8 - self.ec)
        self.ph += self.rnd.uniform(-0.005, 0.005) + 0.002 * (6.1 - self.ph)

        n = self.rnd.gauss
        z1 = self.t_in + (0.8 if heater else 0.0) + n(0, 0.15)
        z2 = self.t_in + 0.6 * s_in / 500 + n(0, 0.15)
        light = 0.0
        if d["D-LIGHT01"] == "ON" or d["D-LIGHT02"] == "ON":
            light = 40.0
        return {
            "S-T01": round(z1, 2), "S-H01": round(self.rh + n(0, 0.8), 1), "S-T02": round(z2, 2), "S-H02": round(self.rh - 1.5 + n(0, 0.8), 1),
            "S-CO2-01": round(self.co2 + n(0, 6), 0), "S-SOL01": round(s_in + light + abs(n(0, 3)), 0),
            "S-SM01": round(self.sm["Z1"] + n(0, 0.3), 1), "S-SM02": round(self.sm["Z2"] + n(0, 0.3), 1),
            "S-EC01": round(self.ec, 2), "S-PH01": round(self.ph, 2), "S-TO01": round(t_out + n(0, 0.2), 2),
        }

    # ---------- 백필용 간이 현장 제어 (서버 명령 대신 과거 이력을 그럴듯하게 만들 때만 사용) ----------
    def local_thermostat(self, t: datetime):
        day = 7 <= t.hour < 19
        d = self.devices
        if self.t_in >= 28:
            d["D-VENT01"] = d["D-VENT02"] = "OPEN"
        elif self.t_in <= 26:
            d["D-VENT01"] = d["D-VENT02"] = "CLOSE"
        if not day and self.t_in <= 14:
            d["D-HEAT01"] = "ON"
        elif self.t_in >= 16 or day:
            d["D-HEAT01"] = "OFF"
        for z, v in (("Z1", "D-VALVE01"), ("Z2", "D-VALVE02")):
            if self.sm[z] <= 55:
                d[v] = "ON"
            elif self.sm[z] >= 65:
                d[v] = "OFF"


def device_type(code: str) -> str:
    for prefix, typ in (("D-VENT", "VENT"), ("D-FAN", "FAN"), ("D-HEAT", "HEATER"), ("D-SHADE", "SHADE"),
                        ("D-LIGHT", "LIGHT"), ("D-VALVE", "VALVE"), ("D-NUT", "NUTRIENT")):
        if code.startswith(prefix):
            return typ
    return "UNKNOWN"


def is_active(code: str, state: str) -> bool:
    if code.startswith("D-VENT"):
        return state == "OPEN"
    if code.startswith("D-SHADE"):
        return state == "CLOSE"
    return state == "ON"
