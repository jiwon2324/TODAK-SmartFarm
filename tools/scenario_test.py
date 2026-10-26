#!/usr/bin/env python3
"""
시뮬레이터 시나리오 통합 시험 (B안, 가상 장치만 사용).

실행 중인 Docker Compose 스택에 관리자 계정으로 로그인해 시나리오를 차례로 보내고,
각 구간에서 실제로 생긴 경보·제어 명령·센서 수신을 API로 읽어 판정한 뒤
docs/Test_Evidence/scenario_results.md 와 .json 으로 남긴다.

사용:
  TODAK_ADMIN_ID=admin TODAK_ADMIN_PW=... python3 tools/scenario_test.py [--base http://localhost:8088]
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta

FARM = 1


class Api:
    def __init__(self, base, uid, pw):
        self.base, self.uid, self.pw, self.token, self.at = base, uid, pw, None, 0

    def _req(self, method, path, body=None):
        if not self.token or time.time() - self.at > 600:
            self.login()
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(self.base + path, data=data, method=method,
                                   headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=30) as res:
            t = res.read().decode()
            return json.loads(t) if t else None

    def login(self):
        r = urllib.request.Request(self.base + "/api/auth/login", method="POST",
                                   data=json.dumps({"loginId": self.uid, "password": self.pw}).encode(),
                                   headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=30) as res:
            self.token = json.loads(res.read())["accessToken"]
            self.at = time.time()

    get = lambda self, p: self._req("GET", p)
    post = lambda self, p, b: self._req("POST", p, b)


def ts(s):
    return datetime.fromisoformat(str(s)[:19]) if s else None


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def window(api, start, end):
    alerts = [a for a in api.get(f"/api/alerts?farmId={FARM}&size=300") if ts(a["lastAt"]) and ts(a["lastAt"]) >= start]
    cmds = [c for c in api.get(f"/api/controls/commands?farmId={FARM}&size=300") if start <= ts(c["requestedAt"]) <= end]
    return alerts, cmds


def run(api, name, scen, wait, extra=None, check=None, after=0):
    log(f"▶ {name}: {scen} (관찰 {wait}s)")
    start = datetime.now() - timedelta(seconds=2)
    for s in scen:
        api.post("/api/admin/simulator/scenario", {"farmId": FARM, **s})
    time.sleep(wait)
    end = datetime.now()
    alerts, cmds = window(api, start, end)
    ctx = {"start": start, "end": end}
    if extra:
        ctx.update(extra(api, start, end))
    if after:
        api.post("/api/admin/simulator/scenario", {"farmId": FARM, "scenario": "recover"})
        log(f"  복구 후 {after}s 관찰")
        time.sleep(after)
        ctx["after_alerts"] = [a for a in api.get(f"/api/alerts?farmId={FARM}&size=300") if ts(a["firstAt"]) and ts(a["firstAt"]) >= start]
    checks = check(alerts, cmds, ctx) if check else []
    ok = all(c[1] for c in checks)
    log(f"  → {'통과' if ok else '미통과'} " + "; ".join(f"{c[0]}={'O' if c[1] else 'X'}" for c in checks))
    return {"name": name, "scenarios": scen, "start": start.isoformat(timespec="seconds"), "end": end.isoformat(timespec="seconds"),
            "pass": ok, "checks": [{"item": c[0], "ok": c[1], "evidence": c[2]} for c in checks],
            "alerts": alerts, "commands": cmds}


def has_cmd(cmds, prefix, actions, sources=None):
    hit = [c for c in cmds if c["deviceCode"] and c["deviceCode"].startswith(prefix) and c["action"] in actions
           and (sources is None or c["source"] in sources)]
    return bool(hit), ", ".join(f'#{c["commandId"]} {c["deviceCode"]} {c["action"]} {c["source"]} {c["status"]}' for c in hit[:4]) or "없음"


def has_alert(alerts, typ, word=None):
    hit = [a for a in alerts if a["type"] == typ and (word is None or word in (a["message"] or ""))]
    return bool(hit), " / ".join(f'#{a["alertId"]} {a["message"]} ({a["status"]})' for a in hit[:3]) or "없음"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8088")
    ap.add_argument("--out", default="docs/Test_Evidence")
    a = ap.parse_args()
    uid, pw = os.environ.get("TODAK_ADMIN_ID", "admin"), os.environ.get("TODAK_ADMIN_PW")
    if not pw:
        sys.exit("TODAK_ADMIN_PW 환경변수가 필요합니다")
    api = Api(a.base, uid, pw)
    api.post("/api/admin/simulator/scenario", {"farmId": FARM, "scenario": "recover"})
    time.sleep(5)
    results = []

    def heat_check(al, cm, _):
        r = [("고온 기준 이탈 경보", *has_alert(al, "THRESHOLD"))]
        r.append(("측창 열기 자동 명령", *has_cmd(cm, "D-VENT", {"OPEN"})))
        r.append(("환기팬 가동 명령", *has_cmd(cm, "D-FAN", {"ON"})))
        nack = [c for c in cm if c["deviceCode"] == "D-FAN01" and c["status"] in ("TIMEOUT", "FAILED")]
        r.append(("D-FAN01 장치 오류 → 응답 없음 처리", bool(nack) or has_alert(al, "DEVICE_NOACK")[0],
                  ", ".join(f'#{c["commandId"]} {c["status"]}' for c in nack[:3]) or has_alert(al, "DEVICE_NOACK")[1]))
        return r
    results.append(run(api, "갑작스러운 고온 + 장치 오류", [{"scenario": "heat", "durationSec": 600}, {"scenario": "device_fail", "durationSec": 600, "target": "D-FAN01"}],
                       630, check=heat_check, after=150))

    results.append(run(api, "저온", [{"scenario": "cold", "durationSec": 300}], 330,
                       check=lambda al, cm, _: [("저온 기준 이탈 경보", *has_alert(al, "THRESHOLD")), ("난방기 가동 명령", *has_cmd(cm, "D-HEAT", {"ON"}))], after=150))

    results.append(run(api, "습도 이상", [{"scenario": "humid", "durationSec": 240}], 270,
                       check=lambda al, cm, _: [("습도 기준 이탈 경보", *has_alert(al, "THRESHOLD", "습도"))], after=60))

    results.append(run(api, "관수 부족", [{"scenario": "dry", "durationSec": 480}], 510,
                       check=lambda al, cm, _: [("관수 밸브 자동 개방", *has_cmd(cm, "D-VALVE", {"ON"}))], after=60))

    def silent_check(al, cm, ctx):
        r = [("S-T02 무응답 경보", *has_alert(al, "SENSOR_FAIL"))]
        res = [x for x in ctx.get("after_alerts", []) if x["type"] == "SENSOR_FAIL" and x["status"] == "RESOLVED"]
        r.append(("송신 재개 후 자동 해제", bool(res), ", ".join(f'#{x["alertId"]} {x["resolvedAt"]}' for x in res) or "미해제"))
        return r
    results.append(run(api, "센서 무응답", [{"scenario": "sensor_silent", "durationSec": 300, "target": "S-T02"}], 330, check=silent_check, after=120))

    def gap(api_, start, end):
        s = api_.get(f"/api/sensor-data/series?sensorId=1&from={start:%Y-%m-%dT%H:%M:%S}&to={end:%Y-%m-%dT%H:%M:%S}&interval=raw")
        return {"points": len(s["points"]), "minutes": int((end - start).total_seconds() // 60)}

    def disc_check(al, cm, ctx):
        r = [("게이트웨이 오프라인 경보", *has_alert(al, "GW_OFFLINE"))]
        r.append(("단절 구간 데이터 재전송(누락 없음)", ctx["points"] >= ctx["minutes"] - 1, f'S-T01 {ctx["points"]}건 / 구간 {ctx["minutes"]}분'))
        return r
    results.append(run(api, "통신 단절", [{"scenario": "disconnect", "durationSec": 180}], 300, extra=gap, check=disc_check))

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "scenario_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    lines = ["# 시뮬레이터 시나리오 시험 결과", "",
             f"- 실행: {datetime.now():%Y-%m-%d %H:%M} (tools/scenario_test.py, Docker Compose 스택)",
             "- 대상: 농장 1 가상 게이트웨이 GW-01 (B안). **모든 값은 시뮬레이션 데이터이며 실제 장비·실측값이 아님**", "",
             "| 시나리오 | 시간 | 판정 | 확인 항목 |", "|---|---|---|---|"]
    for r in results:
        items = "<br>".join(f'{"✅" if c["ok"] else "❌"} {c["item"]}: {c["evidence"]}' for c in r["checks"])
        lines.append(f'| {r["name"]} | {r["start"][11:16]}~{r["end"][11:16]} | {"통과" if r["pass"] else "미통과"} | {items} |')
    lines += ["", f'종합: {sum(r["pass"] for r in results)}/{len(results)} 통과', ""]
    with open(os.path.join(a.out, "scenario_results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"완료: {sum(r['pass'] for r in results)}/{len(results)} 통과")


if __name__ == "__main__":
    main()
