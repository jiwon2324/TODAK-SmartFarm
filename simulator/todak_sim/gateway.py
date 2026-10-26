# -*- coding: utf-8 -*-
"""
가상 게이트웨이 GW-01 (B안). 실제 게이트웨이와 같은 MQTT 토픽·JSON을 쓴다.
 발행: todak/{farm}/{zone}/sensor/{code}, todak/{farm}/device/{code}/ack|state, todak/{farm}/gw/{gw}/status (retained, LWT=offline)
 구독: todak/{farm}/device/+/cmd, todak/{farm}/gw/{gw}/config (retained), todak/{farm}/sim/scenario
단절 시나리오에서는 소켓을 강제로 끊어 브로커가 LWT를 보내게 하고, 그동안 측정값을 버퍼에 쌓으며
서버에서 받은 기준값 사본(config)의 안전 규칙으로 직접 장치를 제어한다(FAILSAFE). 재연결하면 버퍼를 재전송한다.
"""
import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

import paho.mqtt.client as mqtt

from .model import SENSORS, UNITS, Greenhouse, device_type, is_active

KST = timezone(timedelta(hours=9))
log = logging.getLogger("sim")


class VirtualGateway:
    def __init__(self, host, port, user, password, farm_id=1, gw_code="GW-01"):
        self.host, self.port, self.user, self.password = host, port, user, password
        self.farm, self.gw = farm_id, gw_code
        self.gh = Greenhouse()
        self.lock = threading.RLock()
        self.config = None
        self.connected = False
        self.disconnected_until = 0.0
        self.silent = {}          # 센서 코드 → 끝나는 시각
        self.failing = {}         # 장치 코드 → 끝나는 시각
        self.scenario_until = {}  # 시나리오 → 끝나는 시각
        self.buffer = []          # (topic, payload) 단절 중 측정값
        self.state_events = []    # 단절 중 FAILSAFE 상태 변화
        self.client = None

    # ---------------- 연결 ----------------
    def _new_client(self):
        c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-{self.gw}", clean_session=True)
        c.username_pw_set(self.user, self.password)
        c.will_set(self._t(f"gw/{self.gw}/status"), json.dumps({"status": "offline"}), qos=1, retain=True)
        c.on_connect = self._on_connect
        c.on_disconnect = self._on_disconnect
        c.on_message = self._on_message
        return c

    def connect(self):
        self.client = self._new_client()
        while True:
            try:
                self.client.connect(self.host, self.port, keepalive=10)
                break
            except OSError as e:
                log.warning("MQTT 연결 재시도: %s", e)
                time.sleep(3)
        self.client.loop_start()
        for _ in range(50):
            if self.connected:
                break
            time.sleep(0.1)

    def _on_connect(self, c, userdata, flags, reason, props):
        if reason.is_failure:
            log.error("MQTT 연결 거부: %s", reason)
            return
        self.connected = True
        c.subscribe([(self._t("device/+/cmd"), 1), (self._t(f"gw/{self.gw}/config"), 1), (self._t("sim/scenario"), 1)])
        self.heartbeat()
        log.info("MQTT 연결됨 %s:%s", self.host, self.port)

    def _on_disconnect(self, c, userdata, flags, reason, props):
        self.connected = False

    def _t(self, suffix):
        return f"todak/{self.farm}/{suffix}"

    def heartbeat(self):
        if self.client and self.connected:
            ver = self.config.get("version") if self.config else -1
            self.client.publish(self._t(f"gw/{self.gw}/status"), json.dumps({"status": "online", "configVersion": ver, "simulated": True}), qos=1, retain=True)

    # ---------------- 수신 ----------------
    def _on_message(self, c, userdata, msg):
        try:
            p = json.loads(msg.payload.decode())
        except ValueError:
            return
        parts = msg.topic.split("/")
        if msg.topic.endswith("/config"):
            self.config = p
            log.info("기준값 사본 수신 version=%s 규칙 %d개", p.get("version"), len(p.get("rules", [])))
        elif msg.topic.endswith("/sim/scenario"):
            self.apply_scenario(p.get("scenario", "normal"), p.get("durationSec"), p.get("target"))
        elif parts[2] == "device" and parts[4] == "cmd":
            threading.Thread(target=self._handle_cmd, args=(parts[3], p), daemon=True).start()

    def _handle_cmd(self, code, p):
        if code not in self.gh.devices:
            return
        if self.failing.get(code, 0) > time.time():
            log.info("device_fail: %s 명령 %s 무시 (ACK 없음)", code, p.get("commandId"))
            return
        time.sleep(0.4)  # 릴레이 동작 시간
        with self.lock:
            self.gh.devices[code] = p["action"]
        ack = {"commandId": p["commandId"], "result": "OK", "state": p["action"], "ackAt": datetime.now(KST).isoformat()}
        self.client.publish(self._t(f"device/{code}/ack"), json.dumps(ack), qos=1)
        log.info("명령 %s %s → %s (ACK)", p["commandId"], code, p["action"])

    # ---------------- 시나리오 ----------------
    def apply_scenario(self, name, duration=None, target=None):
        now = time.time()
        defaults = {"heat": 1200, "cold": 1200, "humid": 900, "dry": 900, "sensor_silent": 300, "disconnect": 180, "device_fail": 300}
        dur = duration or defaults.get(name, 0)
        log.info("시나리오 %s (%s초, 대상=%s)", name, dur, target)
        g = self.gh
        if name in ("normal", "recover"):
            g.temp_offset, g.rh_offset, g.dry_factor = 0.0, 0.0, 1.0
            self.silent.clear()
            self.failing.clear()
            self.scenario_until.clear()
            return
        self.scenario_until[name] = now + dur
        if name == "heat":
            g.temp_offset = 20.0
        elif name == "cold":
            g.temp_offset = -22.0
        elif name == "humid":
            g.rh_offset = 25.0
        elif name == "dry":
            g.dry_factor = 200.0  # 배지 수분이 분당 1% 남짓 떨어지는 급격한 건조
        elif name == "sensor_silent":
            self.silent[target or "S-T02"] = now + dur
        elif name == "device_fail":
            self.failing[target or "D-FAN01"] = now + dur
        elif name == "disconnect":
            self.disconnected_until = now + dur
            threading.Thread(target=self._drop_connection, daemon=True).start()

    def _expire_scenarios(self):
        now = time.time()
        g = self.gh
        for name, until in list(self.scenario_until.items()):
            if until <= now:
                del self.scenario_until[name]
                if name in ("heat", "cold"):
                    g.temp_offset = 0.0
                elif name == "humid":
                    g.rh_offset = 0.0
                elif name == "dry":
                    g.dry_factor = 1.0
                log.info("시나리오 %s 종료", name)

    def _drop_connection(self):
        """소켓을 강제로 닫아 브로커가 keepalive 초과로 LWT(offline)를 발행하게 한다"""
        log.info("통신 단절 시작")
        try:
            self.client.loop_stop()
            sock = self.client.socket()
            if sock:
                sock.close()
        except Exception:
            pass
        self.connected = False

    def _reconnect_and_flush(self):
        log.info("통신 복구 — 버퍼 %d건, 상태 변화 %d건 재전송", len(self.buffer), len(self.state_events))
        self.connect()
        for topic, payload in self.buffer:
            self.client.publish(topic, payload, qos=1)
        for topic, payload in self.state_events:
            self.client.publish(topic, payload, qos=1)
        self.buffer.clear()
        self.state_events.clear()

    # ---------------- 단절 중 안전 운전 ----------------
    def _failsafe(self, temps, sms, at):
        rules = (self.config or {}).get("rules", [])
        changes = {}
        tmax, tmin = max(temps), min(temps)
        for r in rules:
            if not r.get("safety"):
                continue
            targets = r["targets"].split(",")
            v = tmax if r["op"] == "GE" else tmin
            if (r["op"] == "GE" and v >= r["on"]) or (r["op"] == "LE" and v <= r["on"]):
                for code in self.gh.devices:
                    typ = device_type(code)
                    if typ in targets and not is_active(code, self.gh.devices[code]):
                        changes[code] = "OPEN" if typ == "VENT" else "ON"
        # 단절 중에는 관수를 멈춘다 (과관수 방지)
        for v in ("D-VALVE01", "D-VALVE02"):
            if self.gh.devices[v] == "ON":
                changes[v] = "OFF"
        for code, state in changes.items():
            self.gh.devices[code] = state
            ev = {"state": state, "changedBy": "FAILSAFE", "at": at.isoformat()}
            self.state_events.append((self._t(f"device/{code}/state"), json.dumps(ev)))
            log.info("FAILSAFE %s → %s", code, state)

    # ---------------- 측정·발행 ----------------
    def payloads(self, t: datetime, values: dict, buffered=False, prefix="SIM"):
        out = []
        stamp = t.strftime("%Y%m%dT%H%M")
        for code, zone, metric in SENSORS:
            p = {"msgId": f"{prefix}-{self.gw}-{stamp}-{code}", "gw": self.gw, "sensor": code, "metric": metric,
                 "unit": UNITS[metric], "ts": t.isoformat(), "value": values[code], "samples": 6, "buffered": buffered, "simulated": True}
            out.append((code, self._t(f"{zone}/sensor/{code}"), json.dumps(p)))
        return out

    def tick(self, t: datetime):
        """1분 진행 + 발행 (단절 중이면 버퍼링)"""
        with self.lock:
            self._expire_scenarios()
            values = self.gh.step(t)
            offline = time.time() < self.disconnected_until
            if offline:
                self._failsafe([values["S-T01"], values["S-T02"]], [values["S-SM01"], values["S-SM02"]], t)
            for code, topic, payload in self.payloads(t, values, buffered=offline):
                if self.silent.get(code, 0) > time.time():
                    continue
                if offline:
                    self.buffer.append((topic, payload))
                elif self.connected:
                    self.client.publish(topic, payload, qos=1)
            if not offline and not self.connected and self.disconnected_until:
                self.disconnected_until = 0.0
                self._reconnect_and_flush()
        return values

    def backfill(self, days: int, step_min: int = 10):
        """시작 시 과거 데이터 채우기: 모델을 1분씩 돌리고 step_min마다 발행 (간이 현장 제어 적용)"""
        if days <= 0:
            return
        now = datetime.now(KST).replace(second=0, microsecond=0)
        t = now - timedelta(days=days)
        sent = 0
        log.info("과거 %d일 시뮬레이션 데이터 백필 시작", days)
        while t < now - timedelta(minutes=2):
            self.gh.local_thermostat(t)
            values = self.gh.step(t)
            if t.minute % step_min == 0:
                for _, topic, payload in self.payloads(t, values, prefix="SIMBF"):
                    info = self.client.publish(topic, payload, qos=1)
                    sent += 1
                    if sent % 400 == 0:
                        info.wait_for_publish(timeout=10)
            t += timedelta(minutes=1)
        # 백필에 쓴 간이 제어 상태는 서버가 모르는 상태이므로 초기 상태로 되돌린다
        from .model import DEVICES
        self.gh.devices = dict(DEVICES)
        log.info("백필 완료 %d건", sent)
