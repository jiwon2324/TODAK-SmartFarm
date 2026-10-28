"""
스냅샷 데모용 API 응답 기록 → docs/app/snapshot/
실행 중인 로컬 시스템(관리자 계정)에서 화면이 부르는 GET 응답을 그대로 저장한다.
프런트의 스냅샷 모드(src/snapshot.ts)는 같은 규칙(normalize)으로 키를 만들어 이 파일을 찾는다.
  TODAK_ADMIN_PW=... python3 tools/snapshot/record.py
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "docs", "app", "snapshot")
BASE = os.environ.get("TODAK_BASE", "http://localhost:8088")
DROP = {"from", "to", "size"}  # 시간·개수 조건은 화면에서 잘라 쓴다


def normalize(url):
    p = urllib.parse.urlsplit(url)
    q = sorted((k, v) for k, v in urllib.parse.parse_qsl(p.query) if k not in DROP)
    return p.path + ("?" + urllib.parse.urlencode(q) if q else "")


def call(path, token=None, body=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, method="POST" if body is not None else "GET")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"null")


def main():
    token = call("/api/auth/login", body={"loginId": "admin", "password": os.environ["TODAK_ADMIN_PW"]})["accessToken"]
    os.makedirs(OUT, exist_ok=True)
    now = datetime.now().replace(second=0, microsecond=0)
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:00")  # noqa: E731
    day = lambda d: d.strftime("%Y-%m-%d")  # noqa: E731
    index = {}

    def rec(path):
        data = call(path, token)
        if path == "/api/admin/users":  # 공개 저장소이므로 실제 이메일을 가진 계정(개인 가입)은 빼고 가상·검수 계정만 남긴다
            data = [u for u in data if not u.get("email")]
        key = normalize(path)
        name = f"{len(index):03d}.json"
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        index[key] = name
        return data

    for p in ["/api/auth/me", "/api/admin/summary", "/api/admin/users", "/api/admin/logs/ingest", "/api/admin/logs/errors",
              "/api/admin/logs/commands?size=200", "/api/admin/logs/deliveries?size=200", "/api/admin/logs/settings?size=200",
              f"/api/admin/weather?station=202&from={day(now - timedelta(days=400))}&to={day(now)}"]:
        rec(p)
    for farm in rec("/api/farms"):
        fid = farm["farmId"]
        for p in [f"/api/farms/{fid}/dashboard", f"/api/farms/{fid}/zones", f"/api/devices?farmId={fid}", f"/api/beehives?farmId={fid}",
                  f"/api/controls/commands?farmId={fid}&size=300", f"/api/controls/logs?farmId={fid}&size=300",
                  f"/api/controls/rules?farmId={fid}", f"/api/admin/rules?farmId={fid}", f"/api/crop-cycles/current?farmId={fid}",
                  f"/api/crop-standards?farmId={fid}", f"/api/analytics/gdd?farmId={fid}&source=INTERNAL",
                  f"/api/analytics/gdd?farmId={fid}&source=EXTERNAL",
                  f"/api/analytics/daily?farmId={fid}&from={day(now - timedelta(days=31))}&to={day(now)}",
                  f"/api/analytics/weather?farmId={fid}&from={day(now - timedelta(days=61))}&to={day(now)}"]:
            try:
                rec(p)
            except urllib.error.HTTPError as e:  # 작물 주기 없는 농장 등
                print("skip", p, e.code)
        for st in ["", "OPEN", "ACK", "RESOLVED"]:
            rec(f"/api/alerts?farmId={fid}" + (f"&status={st}" if st else "") + "&size=200")
        for s in rec(f"/api/sensors?farmId={fid}"):
            sid = s.get("sensorId", s.get("id"))
            rec(f"/api/sensor-data/series?sensorId={sid}&from={iso(now - timedelta(days=31))}&to={iso(now)}&interval=hour")
            rec(f"/api/sensor-data/series?sensorId={sid}&from={iso(now - timedelta(days=3, hours=1))}&to={iso(now)}&interval=raw")
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"capturedAt": now.isoformat(), "files": index}, f, ensure_ascii=False, indent=0)
    print(len(index), "responses →", OUT)


if __name__ == "__main__":
    main()
