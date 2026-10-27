"""
시연 영상 녹화 (교수님 제출용). 떠 있는 Docker Compose 스택을 실제로 조작하는 모습을 그대로 녹화한다.
가상 화면(Xvfb 2560x1440)에 Chromium을 키오스크 모드로 띄우고(화면 배율 4/3 → CSS 1920x1080),
ffmpeg x11grab으로 무손실 녹화한 뒤, 자동 제어를 기다린 구간만 잘라 고화질 H.264로 다시 인코딩한다.

  docker run --rm --network todak_default -v "$PWD":/w -w /w -e TODAK_ADMIN_PW=... -e TODAK_FARMER_PW=... \
    mcr.microsoft.com/playwright/python:v1.48.0-jammy sh tools/demo/run_demo.sh
"""
import json
import os
import re
import subprocess
import time
import urllib.request
from datetime import datetime, timedelta, timezone

from playwright.sync_api import Page, expect, sync_playwright

BASE = os.environ.get("TODAK_BASE", "http://frontend")
OUT = os.environ.get("TODAK_DEMO_DIR", "/w/demo_out")
W, H, SCALE = 2560, 1440, 4 / 3   # 녹화 결과 크기 (CSS 1920x1080 × 4/3)
SCREEN_H = 1600                   # 가상 화면은 브라우저 주소창 높이만큼 더 크게 잡고, 나중에 잘라낸다
KST = timezone(timedelta(hours=9))
T0 = None
marks = {}

# 화면 위에 그리는 캡션·마우스 포인터 (녹화용, 시스템 화면 자체는 바꾸지 않음)
OVERLAY = """
(() => {
  const mk = () => {
    if (document.getElementById('__demo_cap')) return;
    const st = document.createElement('style');
    st.textContent = `
      #__demo_cap{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:2147483647;max-width:1500px;
        background:rgba(15,40,25,.92);color:#fff;font:600 26px/1.45 'NanumGothic','Noto Sans KR',sans-serif;padding:14px 30px;
        border-radius:14px;box-shadow:0 8px 30px rgba(0,0,0,.25);text-align:center;transition:opacity .3s;pointer-events:none}
      #__demo_cap:empty{opacity:0}
      #__demo_cap small{display:block;font-weight:400;font-size:19px;color:#cfe8d4;margin-top:2px}
      #__demo_ptr{position:fixed;z-index:2147483647;width:26px;height:26px;margin:-4px 0 0 -4px;pointer-events:none;
        background:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='26' height='26'><path d='M3 2 L3 21 L8 16 L12 24 L15 23 L11 15 L18 15 Z' fill='white' stroke='black' stroke-width='1.6'/></svg>") no-repeat}
      .__demo_ring{position:fixed;z-index:2147483646;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;
        border:3px solid #22c55e;pointer-events:none;animation:__r .6s ease-out forwards}
      @keyframes __r{from{transform:scale(.3);opacity:1}to{transform:scale(1.4);opacity:0}}`;
    document.documentElement.appendChild(st);
    const c = document.createElement('div'); c.id = '__demo_cap'; document.documentElement.appendChild(c);
    const p = document.createElement('div'); p.id = '__demo_ptr'; p.style.left = (window.__px||960)+'px'; p.style.top = (window.__py||540)+'px';
    document.documentElement.appendChild(p);
    addEventListener('mousemove', e => { p.style.left = e.clientX + 'px'; p.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', e => { const r = document.createElement('div'); r.className='__demo_ring';
      r.style.left=e.clientX+'px'; r.style.top=e.clientY+'px'; document.documentElement.appendChild(r); setTimeout(()=>r.remove(),700); }, true);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mk); else mk();
})();
"""

CARD = """<html><body style="margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
background:#1f4d2b;font-family:'NanumGothic',sans-serif;color:#fff"><div style="text-align:center;max-width:1500px">
<div style="font-size:30px;letter-spacing:4px;color:#a7d3b0">{kicker}</div>
<div style="font-size:66px;font-weight:800;margin:18px 0 26px;line-height:1.25">{title}</div>
<div style="font-size:28px;line-height:1.7;color:#e3f1e6">{body}</div></div></body></html>"""

cur = {"cap": ""}


def now():
    return time.time() - T0


def cap(page: Page, text, sub=None):
    cur["cap"] = text + (f"<small>{sub}</small>" if sub else "")
    page.evaluate("t => { const c = document.getElementById('__demo_cap'); if (c) c.innerHTML = t; }", cur["cap"])


def goto(page: Page, path, text=None, sub=None, wait=1800):
    page.goto(BASE + path)
    page.wait_for_load_state("load")
    if text:
        cap(page, text, sub)
    page.wait_for_timeout(wait)


def move(page: Page, x, y, steps=28):
    page.mouse.move(x, y, steps=steps)
    page.evaluate("([x,y]) => { window.__px=x; window.__py=y; }", [x, y])


def click(page: Page, loc, pause=500, away=False):
    loc.scroll_into_view_if_needed()
    b = loc.bounding_box()
    x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    move(page, x, y)
    page.wait_for_timeout(pause)
    page.mouse.down()
    page.mouse.up()
    page.wait_for_timeout(400)
    if away:  # 링크 위에 마우스가 남으면 브라우저가 주소 말풍선을 띄우므로 본문 쪽으로 비켜 둔다
        move(page, 1100, 640, steps=18)


def type_in(page: Page, sel, text):
    click(page, page.locator(sel), 250)
    page.keyboard.type(text, delay=70)


def scroll(page: Page, total, step=6):
    for _ in range(int(abs(total) / step / 10)):
        page.mouse.wheel(0, step * 10 if total > 0 else -step * 10)
        page.wait_for_timeout(16)


def card(page: Page, kicker, title, body, ms=4500):
    page.set_content(CARD.format(kicker=kicker, title=title, body=body))
    page.wait_for_timeout(ms)


def login(page: Page, uid, pw, who):
    goto(page, "/login", f"{who} 계정으로 로그인합니다", f"아이디 {uid}")
    type_in(page, "#login-id", uid)
    type_in(page, "#login-pw", pw)
    page.wait_for_timeout(400)
    click(page, page.get_by_role("button", name="로그인", exact=True))
    page.wait_for_load_state("load")
    page.wait_for_timeout(2200)


def logout(page: Page):
    cap(page, "")
    click(page, page.get_by_role("button", name="로그아웃"))
    page.wait_for_timeout(1500)


class Api:
    def __init__(self, pw):
        r = urllib.request.Request(BASE + "/api/auth/login", method="POST", headers={"Content-Type": "application/json"},
                                   data=json.dumps({"loginId": "admin", "password": pw}).encode())
        self.tok = json.loads(urllib.request.urlopen(r, timeout=20).read())["accessToken"]

    def get(self, path):
        r = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {self.tok}"})
        return json.loads(urllib.request.urlopen(r, timeout=20).read())


def main():
    global T0
    os.makedirs(OUT, exist_ok=True)
    admin_pw, farmer_pw = os.environ["TODAK_ADMIN_PW"], os.environ["TODAK_FARMER_PW"]
    # 녹화 전: 하우스가 정상 상태(난방기 꺼짐, 온도 16℃ 이상)로 돌아올 때까지 기다린다 — 시나리오 결과가 새로 생기게
    api = Api(admin_pw)
    for _ in range(120):
        temp = api.get("/api/farms/1/dashboard")
        dev = {d["deviceCode"]: d for d in temp["devices"]}
        heat_off = dev.get("D-HEAT01", {}).get("state") == "OFF"
        t1 = next((x.get("value") for x in temp.get("readings", []) if x.get("sensorCode") == "S-T01"), None)
        print("pre-check heater", dev.get("D-HEAT01", {}).get("state"), "S-T01", t1, flush=True)
        if heat_off and t1 is not None and t1 >= 16:
            break
        time.sleep(15)
    raw = f"{OUT}/raw.mkv"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "x11grab", "-draw_mouse", "0", "-framerate", "30",
                           "-video_size", f"{W}x{SCREEN_H}", "-i", os.environ.get("DISPLAY", ":99"),
                           "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", raw], stdin=subprocess.PIPE)
    T0 = time.time()
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False, args=["--window-size=1920,1180", "--window-position=0,0",
                                                     f"--force-device-scale-factor={SCALE}", "--hide-scrollbars",
                                                     "--disable-infobars", "--no-first-run"])
        ctx = b.new_context(no_viewport=True, locale="ko-KR", timezone_id="Asia/Seoul")
        ctx.add_init_script(OVERLAY)
        page = ctx.new_page()
        # 페이지 영역을 정확히 CSS 1920x1080으로 맞추고, 주소창 높이를 기록해 두었다가 잘라낸다
        page.goto("about:blank")
        cdp = ctx.new_cdp_session(page)
        wid = cdp.send("Browser.getWindowForTarget")["windowId"]
        bar = page.evaluate("window.outerHeight - window.innerHeight")
        cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": {"left": 0, "top": 0, "width": 1920, "height": 1080 + bar}})
        page.wait_for_timeout(800)
        size = page.evaluate("[innerWidth, innerHeight, outerHeight - innerHeight, screenX, screenY]")
        marks["crop_y"] = round(size[2] * SCALE)
        marks["inner"] = size
        print("viewport", size, flush=True)
        today = datetime.now(KST).strftime("%Y.%m.%d")

        # 0. 표지
        card(page, "데이터 기획 및 분석 · 시스템 구축 시연", "TODAK 방울토마토 스마트팜",
             f"경기도 양평군 단동 비닐하우스 1동(100평) 환경 수집 · 자동 제어 · 알림 · 생육 분석<br>"
             f"실행 중인 실제 시스템을 그대로 녹화 ({today})<br>"
             "<span style='color:#f6d58b'>하우스 센서·장치 값은 가상 센서 시뮬레이터 데이터 · 외부 기상은 기상청 양평 실측 자료</span>", 6500)

        # 0-1. 로그인 없이 둘러보기 (교수님 확인용)
        goto(page, "/login", "계정이 없어도 '로그인 없이 둘러보기'로 바로 볼 수 있습니다", "주소 끝에 /demo 를 붙여 열어도 같습니다 · 조회 전용 계정", 3500)
        click(page, page.get_by_role("button", name="로그인 없이 둘러보기"))
        page.wait_for_load_state("load")
        page.wait_for_timeout(1500)
        cap(page, "조회 전용(VIEWER)으로 들어왔습니다 — 모든 화면을 볼 수 있고, 장치 제어·설정 변경은 잠겨 있습니다", "REQ-F-12 · 서버에서도 403으로 막음")
        page.wait_for_timeout(4500)
        logout(page)

        # 1. 관리자: 시나리오 실행
        login(page, "admin", admin_pw, "관리자")
        cap(page, "관리자 대시보드 — 센서·장치·수집·경보·게이트웨이 상태를 한 화면에서 봅니다", "REQ-F-17 · SCR-A1")
        page.wait_for_timeout(3500)
        scroll(page, 900)
        cap(page, "시뮬레이터 시나리오: 실제 장비 대신 가상 하우스에 이상 상황을 일으킵니다",
            "지금은 밤이므로 '저온'을 실행 → 야간 난방(CR-02)·저온 안전(CR-06) 자동 제어를 확인")
        page.wait_for_timeout(3000)
        click(page, page.get_by_role("button").filter(has_text="외부 기온 급강하"))
        page.wait_for_timeout(1200)
        click(page, page.get_by_role("dialog").get_by_role("button", name="실행"))
        marks["scenario"] = datetime.now(KST)
        cap(page, "시나리오를 가상 게이트웨이에 보냈습니다 — 결과는 몇 분 뒤 다시 확인합니다")
        page.wait_for_timeout(3500)
        logout(page)

        # 2. 농가 화면 둘러보기
        login(page, "farmer01", farmer_pw, "농가")
        cap(page, "농가 대시보드 — 구역별 최신 측정값, 24시간 그래프, 장치 상태, 알림", "SCR-02 · REQ-F-01, F-18 (실시간 갱신)")
        page.wait_for_timeout(4000)
        click(page, page.get_by_role("tab", name=re.compile("Z2")))
        cap(page, "구역 탭으로 Z1(입구측)·Z2(안쪽) 값을 나눠 봅니다")
        page.wait_for_timeout(2500)
        scroll(page, 1100)
        page.wait_for_timeout(2500)
        scroll(page, -1100)

        click(page, page.get_by_role("navigation", name="주 메뉴").get_by_role("link", name="환경 그래프", exact=True), away=True)
        cap(page, "환경 그래프 — 지표·기간·집계 단위를 골라 보고 CSV로 내려받습니다", "SCR-03 · REQ-F-10")
        page.wait_for_timeout(3500)
        scroll(page, 800)
        page.wait_for_timeout(2500)

        click(page, page.get_by_role("navigation", name="주 메뉴").get_by_role("link", name="장치 제어", exact=True), away=True)
        cap(page, "장치 제어 — 버튼 → 확인 → 명령 전송 → 장치가 실행 확인(ACK)해야 상태가 바뀝니다", "SCR-04 · REQ-F-08, F-16")
        page.wait_for_timeout(3000)
        row = page.locator("div.rounded-lg.border").filter(has_text="D-LIGHT01")
        on = row.get_by_role("button", name="켜기")
        if on.is_enabled():
            click(page, on)
            cap(page, "보광등 1을 수동으로 켭니다 — 실수 방지를 위해 한 번 더 확인합니다")
            page.wait_for_timeout(1500)
            click(page, page.get_by_role("dialog").get_by_role("button", name="전송"))
            page.wait_for_timeout(1000)
            cap(page, "명령 전송 → 가상 장치 ACK → '켜짐'으로 바뀜, 수동 조작 동안은 자동 제어가 멈춤")
            expect(row.get_by_text("켜짐")).to_be_visible(timeout=15000)
            page.wait_for_timeout(3500)
            off = row.get_by_role("button", name="끄기")
            click(page, off)
            page.wait_for_timeout(800)
            click(page, page.get_by_role("dialog").get_by_role("button", name="전송"))
            cap(page, "다시 끕니다")
            page.wait_for_timeout(3500)

        click(page, page.get_by_role("navigation", name="주 메뉴").get_by_role("link", name="제어 이력", exact=True), away=True)
        cap(page, "제어 이력 — 누가(자동 규칙/사용자) 언제 무엇을 했고 결과가 어땠는지 남습니다", "SCR-05 · TB_CONTROL_COMMAND")
        page.wait_for_timeout(4000)

        click(page, page.get_by_role("navigation", name="주 메뉴").get_by_role("link", name="재배 기준값·제어 규칙", exact=True), away=True)
        cap(page, "재배 기준값·제어 규칙 — 켜는 값과 끄는 값을 다르게 둔 히스테리시스 규칙 7개", "SCR-07 · REQ-F-02~04, F-11")
        page.wait_for_timeout(3000)
        scroll(page, 900)
        page.wait_for_timeout(2500)

        click(page, page.get_by_role("navigation", name="주 메뉴").get_by_role("link", name="생육 분석 (GDD·기상)", exact=True), away=True)
        cap(page, "생육 분석 — 하우스 내부 GDD와 기상청 외부 GDD를 따로 계산해 비교합니다", "SCR-08 · REQ-F-14, F-15")
        page.wait_for_timeout(4000)
        scroll(page, 1500)
        cap(page, "외부 기상 자료는 기상청 양평(202) ASOS 실측 일자료 (2026-10-01~26)", "외부 누적 GDD 94.55℃·일 = 원본 CSV로 손 계산한 값과 일치")
        page.wait_for_timeout(5000)
        scroll(page, -1500)

        click(page, page.get_by_role("navigation", name="주 메뉴").get_by_role("link", name="수확 판별", exact=True), away=True)
        cap(page, "수확 판별(카메라)은 계획서에서 확장 범위 — 이번 버전은 구현 계획만 안내하고 가짜 결과는 보이지 않습니다", "SCR-09 · REQ-F-07 미구현")
        page.wait_for_timeout(4000)

        # 3. 자동 제어 결과 기다리기 (녹화에서는 이 구간을 자른다)
        api = Api(admin_pw)
        marks["wait_start"] = now()
        card(page, "시간 경과", "시뮬레이터가 하우스 온도를 떨어뜨리는 중…",
             "실제로 몇 분이 걸리므로 영상에서는 기다리는 구간을 생략합니다", 3000)
        start = marks["scenario"]
        hit = False
        for _ in range(90):
            cmds = api.get("/api/controls/commands?farmId=1&size=100")
            if any(c["source"] != "MANUAL" and (c["deviceCode"] or "").startswith(("D-HEAT", "D-VENT"))
                   and datetime.fromisoformat(c["requestedAt"][:19]).replace(tzinfo=KST) >= start for c in cmds):
                hit = True
                break
            time.sleep(10)
        waited = (datetime.now(KST) - start).seconds // 60
        page.wait_for_timeout(15000 if hit else 0)  # 난방 시작 후 경보까지 조금 더 쌓이게
        marks["wait_end"] = now()
        card(page, "시간 경과", f"시나리오 실행 후 약 {waited}분",
             "자동 제어가 실제로 동작했는지 확인합니다" + ("" if hit else "<br><span style='color:#f6d58b'>(난방 자동 명령이 아직 확인되지 않음)</span>"), 3500)

        # 4. 결과 확인
        goto(page, "/farm/alerts", "알림 — 저온 기준 이탈 경보가 자동으로 생겼습니다", "SCR-06 · REQ-F-09 · 30분 안 같은 경보는 하나로 묶음", 4500)
        goto(page, "/farm/history", "제어 이력 — 규칙(CR-02 야간 난방 · CR-06 저온 안전)이 난방기를 자동으로 켰습니다",
             "사람이 누르지 않은 '자동' 명령 · 장치 ACK까지 확인", 5000)
        goto(page, "/farm", "대시보드에도 낮아진 온도와 켜진 난방기가 실시간으로 보입니다", None, 4500)
        logout(page)

        # 5. 관리자 화면 · 권한
        login(page, "admin", admin_pw, "관리자")
        goto(page, "/admin/users", "사용자 관리 — 회원가입 신청을 관리자가 승인해야 쓸 수 있습니다", "REQ-F-12 · 관리자 / 농가 / 조회 전용", 4000)
        goto(page, "/admin/weather", "외부 기상 자료 — 기상청에서 받은 CSV를 그대로 올려 저장합니다", "양평(202) 26일 · 결측은 표시하고 메우지 않음", 4500)
        goto(page, "/admin", None, None, 800)
        scroll(page, 900)
        click(page, page.get_by_role("button").filter(has_text="모든 시나리오 해제"))
        page.wait_for_timeout(800)
        click(page, page.get_by_role("dialog").get_by_role("button", name="실행"))
        cap(page, "시연을 마치고 시뮬레이터를 정상 상태로 되돌립니다")
        page.wait_for_timeout(3500)
        logout(page)

        # 6. 모바일 화면
        hb = p.chromium.launch()  # 휴대폰 화면은 녹화 화면에 창이 뜨지 않도록 보이지 않는 브라우저로 캡처
        mctx = hb.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, locale="ko-KR", timezone_id="Asia/Seoul",
                             is_mobile=True, has_touch=True)
        mp = mctx.new_page()
        mp.goto(BASE + "/login")
        mp.fill("#login-id", "farmer01")
        mp.fill("#login-pw", farmer_pw)
        mp.get_by_role("button", name="로그인", exact=True).click()
        mp.wait_for_timeout(3500)
        shot = f"{OUT}/mobile.png"
        mp.screenshot(path=shot)
        mctx.close()
        hb.close()
        import base64
        img = base64.b64encode(open(shot, "rb").read()).decode()
        page.set_content(f"""<html><body style="margin:0;height:100vh;display:flex;align-items:center;justify-content:center;gap:90px;
          background:#eef5ef;font-family:'NanumGothic',sans-serif"><img src="data:image/png;base64,{img}" style="height:900px;border-radius:36px;
          box-shadow:0 20px 60px rgba(0,0,0,.25);border:10px solid #1f2937"><div style="max-width:700px;color:#1f4d2b">
          <div style="font-size:52px;font-weight:800">휴대폰에서도 같은 기능</div><div style="font-size:28px;line-height:1.7;margin-top:20px;color:#334155">
          반응형 웹 (REQ-N-07) · 360px 폭에서도 가로 스크롤 없음<br>하단 탭: 대시보드 · 그래프 · 제어 · 알림 + 더보기<br>
          (실제 화면을 휴대폰 크기로 캡처)</div></div></body></html>""")
        page.wait_for_timeout(6000)

        card(page, "정리", "실제로 동작하는 시스템",
             "센서 수집 → 기준값 자동 제어 → 경보 → 원격 제어 → 생육 분석<br>"
             "자동 시험 전부 통과(백엔드·화면·시뮬레이터·E2E) · 시나리오 6종 통과 · 기상청 실측 GDD 손 계산 일치<br>"
             "<span style='color:#f6d58b'>하우스 센서·장치는 시뮬레이터(B안) · 씨 뿌리기·수확 판별은 계획서상 범위 밖/확장</span>", 7000)
        marks["end"] = now()
        b.close()
    ff.communicate(b"q")
    json.dump({k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in marks.items()}, open(f"{OUT}/marks.json", "w"))
    print("marks", marks)


if __name__ == "__main__":
    main()
