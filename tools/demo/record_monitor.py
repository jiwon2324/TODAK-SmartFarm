"""
시연 영상 추가 장면: 통합 관제(SCR-M1) → 고온 시나리오 → 경보로 바뀌는 모습 → 운영 점검(SCR-A7).
record_demo.py와 같은 화면 설정·캡션 스타일로 녹화하고, 시나리오 결과를 기다린 구간은 cut_monitor.py에서 잘라낸다.
  TODAK_ADMIN_PW=... sh tools/demo/record_monitor.sh
"""
import json
import os
import time
import urllib.request
from datetime import datetime

from playwright.sync_api import sync_playwright

import record_demo as R

OUT = R.OUT
marks = {}


def mark(k):
    marks[k] = R.now()


def api(path, token, body=None):
    req = urllib.request.Request(R.BASE + path, method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(req, timeout=20).read() or b"null")


def main():
    pw = os.environ["TODAK_ADMIN_PW"]
    tok = R.Api(pw).tok
    api("/api/admin/simulator/scenario", tok, {"farmId": 1, "scenario": "recover"})
    for f in ("start.flag", "started.txt", "stop.flag"):
        if os.path.exists(f"{OUT}/{f}"):
            os.remove(f"{OUT}/{f}")
    # 녹화 전 정상 상태 확인: 관제 종합 판정이 경보가 아닐 때까지
    for _ in range(40):
        m = api("/api/farms/1/monitor", tok)
        print("pre-check", m["overall"], m["summary"], flush=True)
        if m["summary"].get("ALARM", 0) == 0 and m["summary"].get("STALE", 0) == 0:
            break
        time.sleep(15)
    open(f"{OUT}/start.flag", "w").close()
    while not os.path.exists(f"{OUT}/started.txt") or not open(f"{OUT}/started.txt").read():
        time.sleep(0.05)
    R.T0 = float(open(f"{OUT}/started.txt").read())
    R.cur["step"] = 26  # 원래 영상의 캡션 번호에 이어서

    with sync_playwright() as p:
        b = p.chromium.launch(headless=False, args=["--window-size=1920,1180", "--window-position=0,0",
                                                     f"--force-device-scale-factor={R.SCALE}", "--hide-scrollbars",
                                                     "--disable-infobars", "--no-first-run"])
        ctx = b.new_context(no_viewport=True, locale="ko-KR", timezone_id="Asia/Seoul")
        ctx.add_init_script(R.OVERLAY)
        page = ctx.new_page()
        page.goto("about:blank")
        cdp = ctx.new_cdp_session(page)
        wid = cdp.send("Browser.getWindowForTarget")["windowId"]
        bar = page.evaluate("window.outerHeight - window.innerHeight")
        cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": {"left": 0, "top": 0, "width": 1920, "height": 1080 + bar}})
        page.wait_for_timeout(800)
        size = page.evaluate("[innerWidth, innerHeight, outerHeight - innerHeight]")
        marks["crop_y"] = round(size[2] * R.SCALE)

        mark("s_card")
        R.card(page, "운영 이관 · 추가 기능", "통합 관제 소프트웨어",
               "하우스 평면 위에서 센서 판정 · 장치 상태 · 실시간 이벤트를 한 화면으로<br>"
               "<span style='color:#f6d58b'>개발 이후 운영팀 이관을 위해 더한 화면 (SCR-M1 · SCR-A7)</span>", 5000)

        # 관리자 로그인은 화면 밖에서 (쿠키만 받아 둠): 첫 화면을 바로 관제로
        page.goto(R.BASE + "/login")
        page.fill("#login-id", "admin")
        page.fill("#login-pw", pw)
        page.get_by_role("button", name="로그인", exact=True).click()
        page.wait_for_load_state("load")
        page.wait_for_timeout(1500)

        mark("s_monitor")
        R.goto(page, "/monitor", "통합 관제 — 제출 PPT의 센서·장치 배치도 위에 실시간 상태를 겹쳐 봅니다",
               "초록 = 정상 · 주황 = 주의 · 빨강 = 경보 · 회색 = 수신 끊김 (판정은 서버가 계산)", 6500)
        # 센서 하나 눌러 판정 이유 보기
        dot = page.locator("svg g[role=button]").filter(has_text="T01").first
        R.click(page, dot, 400)
        R.cap(page, "센서를 누르면 현재 값 · 기준 범위 · 판정 이유가 나옵니다", "S-T01 온도 Z1")
        page.wait_for_timeout(4500)
        R.scroll(page, 700)
        page.wait_for_timeout(2500)
        R.scroll(page, -700)

        mark("s_scenario")
        R.goto(page, "/admin", "관리자 대시보드에서 '갑작스러운 고온' 시나리오를 보냅니다", "가상 하우스 온도를 급히 올림 · 실제 장비에는 영향 없음", 1500)
        R.scroll(page, 900)
        R.click(page, page.get_by_role("button", name="갑작스러운 고온"), 400)
        page.wait_for_timeout(800)
        R.click(page, page.get_by_role("button", name="실행", exact=True), 400)
        page.wait_for_timeout(2500)

        R.goto(page, "/monitor", "다시 관제 화면 — 다음 측정값이 들어오면 판정이 바뀝니다", None, 2500)
        marks["wait_start"] = R.now()
        # 시나리오 결과(온도 센서 판정이 경보로) 기다리기 — 이 구간은 편집에서 잘라낸다
        for _ in range(60):
            m = api("/api/farms/1/monitor", tok)
            temps = [s["level"] for s in m["sensors"] if s["metric"] == "TEMP"]
            if any(l == "ALARM" for l in temps):
                break
            time.sleep(5)
        page.wait_for_timeout(4000)  # 화면이 3초 안에 다시 받아 그리도록
        marks["wait_end"] = R.now()
        mark("s_alarm")
        R.cap(page, "온도 센서가 빨간 경보로 바뀌고, 경보가 오른쪽 이벤트 목록에 바로 나타납니다",
              "새 값은 SSE로 즉시 · 판정은 3초 안에 서버에서 다시 받음")
        page.wait_for_timeout(8000)

        mark("s_ops")
        R.goto(page, "/admin/ops", "운영 점검 — 매일 아침 9개 항목을 서버가 자동 판정합니다",
               "판정이 바뀐 항목에는 운영 매뉴얼의 조치 절차 번호가 함께 나옵니다", 7000)
        R.cap(page, "")
        page.wait_for_timeout(600)
        marks["end"] = R.now()
        b.close()
    api("/api/admin/simulator/scenario", tok, {"farmId": 1, "scenario": "recover"})
    open(f"{OUT}/stop.flag", "w").close()
    json.dump(marks, open(f"{OUT}/marks_monitor.json", "w"))
    print("marks", marks)


if __name__ == "__main__":
    main()
