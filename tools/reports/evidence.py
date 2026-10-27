# -*- coding: utf-8 -*-
"""보고서에 넣을 실제 실행 결과를 증빙 파일에서 읽는다. 값을 손으로 적지 않는다."""
import glob
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EVID = os.path.join(ROOT, "docs", "Test_Evidence")
SHOTS = os.path.join(EVID, "screenshots")
DIAG = os.path.join(ROOT, "docs", "Diagrams")
VERSION = "v1.1"


def junit():
    files = glob.glob(os.path.join(ROOT, "backend/build/test-results/test/*.xml"))
    by_class, tot = {}, {"tests": 0, "failed": 0, "skipped": 0}
    for p in files:
        r = ET.parse(p).getroot()
        name = r.get("name").split(".")[-1]
        t, f, e, s = (int(r.get(k)) for k in ("tests", "failures", "errors", "skipped"))
        by_class[name] = {"tests": t, "failed": f + e, "skipped": s,
                          "cases": [tc.get("name") for tc in r.findall("testcase")]}
        tot["tests"] += t; tot["failed"] += f + e; tot["skipped"] += s
    tot["passed"] = tot["tests"] - tot["failed"] - tot["skipped"]
    tot["at"] = datetime.fromtimestamp(max(os.path.getmtime(p) for p in files)).strftime("%Y-%m-%d %H:%M") if files else "-"
    return tot, by_class


def e2e():
    p = os.path.join(EVID, "e2e_results.json")
    rows = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
    at = open(os.path.join(SHOTS, "CAPTURED_AT.txt"), encoding="utf-8").read().split(",")[0] if os.path.exists(os.path.join(SHOTS, "CAPTURED_AT.txt")) else "-"
    return rows, at


def scenarios():
    p = os.path.join(EVID, "scenario_results.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


def perf():
    p = os.path.join(EVID, "performance.json")
    if not os.path.exists(p):
        return None
    m = json.load(open(p, encoding="utf-8"))["metrics"]

    def g(name, key):
        for k, v in m.items():
            if k == name:
                return v.get(key)
        return None
    return {
        "series_p95": g("http_req_duration{api:series7d}", "p(95)"),
        "series_avg": g("http_req_duration{api:series7d}", "avg"),
        "dash_p95": g("http_req_duration{api:dashboard}", "p(95)"),
        "ack_p95": g("control_ack_ms", "p(95)"),
        "ack_avg": g("control_ack_ms", "avg"),
        "ack_max": g("control_ack_ms", "max"),
        "reqs": g("http_reqs", "count"),
        "fail_rate": g("http_req_failed", "value"),
        "checks": g("checks", "value"),
    }


def frontend_tests():
    p = os.path.join(EVID, "frontend_tests.txt")
    if not os.path.exists(p):
        return None
    s = open(p, encoding="utf-8").read()
    m = re.search(r"Tests\s+(\d+) passed \((\d+)\)", s)
    return {"passed": int(m.group(1)), "total": int(m.group(2))} if m else None


def simulator_tests():
    p = os.path.join(EVID, "simulator_tests.txt")
    if not os.path.exists(p):
        return None
    m = re.search(r"(\d+) passed", open(p, encoding="utf-8").read())
    return {"passed": int(m.group(1)), "total": int(m.group(1))} if m else None


def mysql_md():
    p = os.path.join(EVID, "mysql_queries.md")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def ingest_rate():
    s = mysql_md()
    m = re.search(r"처리 성공률 \(저장\+중복\)/수신 = \*\*([\d.]+)%\*\*", s)
    m2 = re.search(r"수신 ([\d,]+)건 · 저장 ([\d,]+)건 · 중복\(이미 저장됨\) ([\d,]+)건 · 거부 ([\d,]+)건", s)
    m3 = re.search(r"최근 1시간:\s+```text\s+\+[-+]+\+\s+\|[^\n]+\n\+[-+]+\+\s+\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)", s)
    return {"rate": m.group(1) if m else None, "counts": m2.groups() if m2 else None,
            "hour": m3.groups() if m3 else None}


def shot(name):
    p = os.path.join(SHOTS, name + ".png")
    return p if os.path.exists(p) else None


def uiux():
    """docs/Test_Evidence/uiux_audit.md 의 요약 표 (기준, 결과, 판정)"""
    path = os.path.join(EVID, "uiux_audit.md")
    if not os.path.exists(path):
        return []
    s = open(path, encoding="utf-8").read()
    part = s.split("## 요약", 1)[1].split("## 화면별", 1)[0]
    rows = []
    for line in part.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] not in ("기준", "---"):
            rows.append(tuple(cells))
    return rows
