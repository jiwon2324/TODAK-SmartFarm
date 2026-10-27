#!/usr/bin/env python3
"""
실행 증빙 모으기 (호스트에서 실행, Docker Compose 스택이 떠 있어야 함)
 1) backend/build/test-results JUnit XML → docs/Test_Evidence/backend_tests.md
 2) 실제 MySQL 조회 결과(mysql CLI 출력 그대로) → docs/Test_Evidence/mysql_queries.md, mysql_queries.html(화면 캡처용)
 3) 데이터 수집률(저장 성공률) → mysql_queries.md 안
비밀번호는 .env에서 읽고 출력하지 않는다.
"""
import glob
import html
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVID = os.path.join(ROOT, "docs", "Test_Evidence")


def env():
    e = {}
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            e[k] = v
    return e


def junit():
    rows, tot = [], {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
    for p in sorted(glob.glob(os.path.join(ROOT, "backend/build/test-results/test/*.xml"))):
        r = ET.parse(p).getroot()
        for k in ("tests", "failures", "errors", "skipped"):
            tot[k] += int(r.get(k))
        tot["time"] += float(r.get("time"))
        for tc in r.findall("testcase"):
            res = "❌ 실패" if tc.find("failure") is not None or tc.find("error") is not None else "⏭ 건너뜀" if tc.find("skipped") is not None else "✅ 통과"
            rows.append((r.get("name").split(".")[-1], tc.get("name"), res, tc.get("time")))
    ts = max((os.path.getmtime(p) for p in glob.glob(os.path.join(ROOT, "backend/build/test-results/test/*.xml"))), default=0)
    lines = ["# 백엔드 시험 결과 (JUnit 5 · 실제 MySQL todak_test)", "",
             f"- 실행 시각: {datetime.fromtimestamp(ts):%Y-%m-%d %H:%M} · 명령 `bash tools/run-backend-tests.sh` · HTML 보고서 `backend/build/reports/tests/test/index.html`",
             f"- 결과: **{tot['tests']}건 중 통과 {tot['tests'] - tot['failures'] - tot['errors'] - tot['skipped']}, 실패 {tot['failures'] + tot['errors']}, 미실행 {tot['skipped']}** · 소요 {tot['time']:.1f}초", "",
             "| 클래스 | 시험 | 결과 | 초 |", "|---|---|---|---|"]
    lines += [f"| {c} | {n} | {r} | {t} |" for c, n, r, t in rows]
    open(os.path.join(EVID, "backend_tests.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return tot


QUERIES = [
    ("테이블 목록 (22개)", "SHOW TABLES;"),
    ("Flyway 마이그레이션 이력", "SELECT version, description, success, installed_on FROM flyway_schema_history ORDER BY installed_rank;"),
    ("사용자·역할·승인 상태 (비밀번호는 BCrypt 해시 앞부분만)", "SELECT user_id, login_id, role, approval_status, is_active, LEFT(password_hash,7) AS hash_prefix, last_login_at FROM TB_USER ORDER BY user_id;"),
    ("센서별 최근 수집 (시뮬레이션 데이터)", "SELECT s.sensor_code, s.metric, s.status, COUNT(d.data_id) AS rows_total, MAX(d.measured_at) AS last_measured FROM TB_SENSOR s LEFT JOIN TB_SENSOR_DATA d ON d.sensor_id=s.sensor_id WHERE s.farm_id=1 GROUP BY s.sensor_id ORDER BY s.sensor_id;"),
    ("최근 측정값 10건", "SELECT d.data_id, s.sensor_code, d.measured_at, d.value, d.quality, d.is_buffered FROM TB_SENSOR_DATA d JOIN TB_SENSOR s ON s.sensor_id=d.sensor_id ORDER BY d.data_id DESC LIMIT 10;"),
    ("제어 명령 상태별 건수 (요청 ≠ 실행)", "SELECT source, status, COUNT(*) AS n FROM TB_CONTROL_COMMAND GROUP BY source, status ORDER BY source, status;"),
    ("최근 제어 명령 10건", "SELECT c.command_id, d.device_code, c.action, c.source, c.status, c.retry_count, c.requested_at, c.acked_at FROM TB_CONTROL_COMMAND c JOIN TB_DEVICE d ON d.device_id=c.device_id ORDER BY c.command_id DESC LIMIT 10;"),
    ("경보 유형별", "SELECT alert_type, severity, status, COUNT(*) AS n, SUM(occur_count) AS occurrences FROM TB_ALERT GROUP BY alert_type, severity, status ORDER BY alert_type;"),
    ("내부 GDD 최근 7일", "SELECT calc_date, source, method, tavg_c, gdd, cum_gdd, coverage_pct, is_complete FROM TB_GDD_DAILY WHERE source='INTERNAL' ORDER BY calc_date DESC LIMIT 7;"),
    ("외부 기상 자료(기상청 ASOS) 건수", "SELECT COUNT(*) AS kma_rows FROM TB_WEATHER_DAILY;"),
    ("시간대별 저장 건수 (최근 24시간, 농장 1 · 정상이면 시간당 11채널×60=660건)",
     "SELECT DATE_FORMAT(d.measured_at,'%m-%d %H시') AS hour, COUNT(*) AS saved, SUM(d.is_buffered) AS buffered "
     "FROM TB_SENSOR_DATA d JOIN TB_SENSOR s ON s.sensor_id=d.sensor_id WHERE s.farm_id=1 AND d.measured_at >= NOW() - INTERVAL 24 HOUR "
     "GROUP BY DATE_FORMAT(d.measured_at,'%m-%d %H시') ORDER BY 1;"),
]

RATE = """SELECT COUNT(*) AS saved, COUNT(DISTINCT s.sensor_id) AS sensors,
  TIMESTAMPDIFF(MINUTE, MIN(d.measured_at), MAX(d.measured_at)) + 1 AS minutes,
  ROUND(COUNT(*) / (COUNT(DISTINCT s.sensor_id) * (TIMESTAMPDIFF(MINUTE, MIN(d.measured_at), MAX(d.measured_at)) + 1)) * 100, 3) AS saved_pct
FROM TB_SENSOR_DATA d JOIN TB_SENSOR s ON s.sensor_id=d.sensor_id
WHERE s.farm_id=1 AND d.measured_at >= NOW() - INTERVAL {h} HOUR AND d.measured_at < NOW() - INTERVAL 2 MINUTE;"""


def mysql(sql, e):
    cmd = ["docker", "compose", "exec", "-T", "-e", f"MYSQL_PWD={e['DB_PASSWORD']}", "mysql", "mysql", "-u", e.get("DB_USER", "todak"),
           "--table", e.get("DB_NAME", "todak"), "-e", sql]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    return (r.stdout or r.stderr).rstrip()


def counters():
    """계획서 KPI 정의: 수신 메시지 수 대비 저장 행 수 (서버 기동 이후 누계). 관리자 비밀번호가 환경변수에 있을 때만"""
    pw = os.environ.get("TODAK_ADMIN_PW")
    if not pw:
        return None
    import json
    import urllib.request
    base = os.environ.get("TODAK_BASE", "http://localhost:8088")
    req = urllib.request.Request(base + "/api/auth/login", data=json.dumps({"loginId": "admin", "password": pw}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    tok = json.loads(urllib.request.urlopen(req, timeout=20).read())["accessToken"]
    req = urllib.request.Request(base + "/api/admin/summary", headers={"Authorization": f"Bearer {tok}"})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())["ingestCounters"]


def main():
    tot = junit()
    cnt = counters()
    e = env()
    blocks = [(t, q, mysql(q, e)) for t, q in QUERIES]
    rate = [(h, mysql(RATE.format(h=h), e)) for h in (1, 6)]
    now = datetime.now()
    md = ["# MySQL 실제 조회 결과", "", f"- 조회 시각: {now:%Y-%m-%d %H:%M} KST · `docker compose exec mysql mysql --table` 출력 그대로 (`tools/collect_evidence.py`)",
          "- DB: MySQL 8.4 `todak` (Workbench 접속 127.0.0.1:3307). 센서 값은 시뮬레이터(B안) 데이터", ""]
    for t, q, out in blocks:
        md += [f"## {t}", "", "```sql", q, "```", "", "```text", out, "```", ""]
    md += ["## 데이터 저장 성공률 (REQ-F-01 · KPI)", "", "구간 안 '센서 수 × 분'만큼 저장돼야 한다. 직전 2분은 집계 중이라 제외.", ""]
    for h, out in rate:
        md += [f"최근 {h}시간:", "", "```text", out, "```", ""]
    if cnt:
        ok = cnt.get("saved", 0) + cnt.get("duplicates", 0)
        rec = cnt.get("received", 0)
        md += ["### 수신 메시지 대비 저장 (계획서 KPI 정의, 백엔드 기동 이후 누계)", "",
               f"- 수신 {rec:,}건 · 저장 {cnt.get('saved', 0):,}건 · 중복(이미 저장됨) {cnt.get('duplicates', 0):,}건 · 거부 {cnt.get('rejected', 0):,}건",
               f"- 처리 성공률 (저장+중복)/수신 = **{(ok / rec * 100 if rec else 0):.3f}%** (목표 ≥ 99.9%)", ""]
    md += ["※ 2026-10-26 오후~10-27 02:53 사이에는 개발 PC 절전으로 수집이 실제로 끊겼다. 03:01 시뮬레이터 재시작 때 과거 데이터 생성(백필)이 "
           "10분 간격으로 그 구간을 채웠으므로 그 시간대의 시간당 건수는 660건보다 적다. 이 공백은 실제로 발생한 것이며 메우지 않았다. "
           "10-27 오전에도 개발 PC가 여러 번 절전(예: 07:55~09:33, 10:19~10:37)해 Docker 컨테이너가 함께 멈췄고, 그동안은 측정값 자체가 만들어지지 않았다. "
           "그래서 '구간 안 저장률'은 절전 구간이 끼면 낮게 나온다. 서버가 받은 메시지를 빠짐없이 저장했는지는 위 '수신 대비 저장'으로 판단한다.", ""]
    open(os.path.join(EVID, "mysql_queries.md"), "w", encoding="utf-8").write("\n".join(md))
    body = "".join(f"<div class='q'>mysql&gt; {html.escape(q)}</div><pre>{html.escape(out)}</pre>" for t, q, out in blocks[:7])
    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>MySQL 조회</title>
<style>body{{background:#1e1e1e;color:#d4d4d4;font:13px/1.45 'D2Coding','NanumGothicCoding',monospace;margin:0;padding:16px}}
.h{{color:#9cdcfe;margin-bottom:10px}}.q{{color:#ce9178;margin-top:14px}}pre{{margin:4px 0;white-space:pre}}</style></head>
<body><div class="h">$ docker compose exec mysql mysql -u todak --table todak · {now:%Y-%m-%d %H:%M} KST · 실제 출력 (센서 값은 시뮬레이션 데이터)</div>{body}</body></html>"""
    open(os.path.join(EVID, "mysql_queries.html"), "w", encoding="utf-8").write(page)
    print("backend tests", tot)
    print("mysql evidence written")


if __name__ == "__main__":
    main()
