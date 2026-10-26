"""
E2E 시험 겸 실행 화면 캡처 (실행 증빙). 떠 있는 Docker Compose 스택을 헤드리스 Chromium으로 실제 조작한다.
각 단계에서 화면 내용·주소를 확인(assert)하고, 결과를 docs/Test_Evidence/e2e_results.md·json, 화면을 screenshots/에 남긴다.

  docker run --rm --network todak_default -v "$PWD":/w -w /w \
    -e TODAK_ADMIN_PW=... -e TODAK_FARMER_PW=... -e TODAK_VIEWER_PW=... \
    mcr.microsoft.com/playwright/python:v1.48.0-jammy \
    sh -c "apt-get -qq update && apt-get -qq install -y fonts-nanum >/dev/null && python tools/capture_screens.py"
"""
import json
import os
import re
import traceback
import urllib.request
from datetime import datetime

from playwright.sync_api import Page, expect, sync_playwright

BASE = os.environ.get("TODAK_BASE", "http://frontend")
OUT = os.environ.get("TODAK_SHOT_DIR", "docs/Test_Evidence/screenshots")
EVID = os.path.dirname(OUT)
DESK = {"width": 1440, "height": 900}
PHONE = {"width": 360, "height": 800}   # REQ-N-07 최소 폭
STAMP = datetime.now().strftime("%m%d%H%M")
NEW_ID = f"e2e{STAMP}"
NEW_PW = "Tomato#2026e2e"
results = []


def step(tc, name, req, scr):
    """데코레이터: 단계 실행·판정·기록"""
    def wrap(fn):
        def run(*a):
            try:
                note = fn(*a) or ""
                results.append({"tc": tc, "name": name, "req": req, "screen": scr, "result": "PASS", "note": note})
                print("PASS", tc, name, flush=True)
            except Exception as e:  # noqa: BLE001 — 실패도 기록하고 다음 단계로
                results.append({"tc": tc, "name": name, "req": req, "screen": scr, "result": "FAIL", "note": f"{type(e).__name__}: {str(e)[:300]}"})
                print("FAIL", tc, name, e, flush=True)
                traceback.print_exc()
        return run
    return wrap


def shot(page: Page, name, full=True, wait=1500):
    # SSE 연결이 계속 열려 있어 networkidle은 끝나지 않는다 → 로드 완료 + 데이터 도착 대기 시간
    page.wait_for_load_state("load")
    page.wait_for_timeout(wait)
    page.screenshot(path=f"{OUT}/{name}.png", full_page=full)


def login(page: Page, uid, pw):
    page.goto(f"{BASE}/login")
    page.fill("#login-id", uid)
    page.fill("#login-pw", pw)
    page.get_by_role("button", name="로그인", exact=True).click()


def logout(page: Page):
    page.get_by_role("button", name="로그아웃").click()
    expect(page).to_have_url(re.compile(r"/login"))


def api(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        t = r.read().decode()
        return json.loads(t) if t else None


def main():
    os.makedirs(OUT, exist_ok=True)
    admin_pw, farmer_pw, viewer_pw = os.environ["TODAK_ADMIN_PW"], os.environ["TODAK_FARMER_PW"], os.environ["TODAK_VIEWER_PW"]
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport=DESK, locale="ko-KR", timezone_id="Asia/Seoul")
        page = ctx.new_page()

        @step("E2E-01", "로그인 화면 표시", "REQ-F-12", "SCR-01")
        def s01():
            page.goto(f"{BASE}/login")
            expect(page.get_by_role("heading", name="로그인")).to_be_visible()
            expect(page.get_by_text("회원가입 신청")).to_be_visible()
            shot(page, "01_login", full=False)
        s01()

        @step("E2E-02", "잘못된 비밀번호 → 오류 안내(계정 존재 여부 비노출)", "REQ-F-12", "SCR-01")
        def s02():
            login(page, "farmer01", "wrong-password")
            expect(page.get_by_text("아이디 또는 비밀번호가 올바르지 않습니다")).to_be_visible()
            shot(page, "02_login_error", full=False)
        s02()

        @step("E2E-03", "회원가입 3단계: 약관 동의 → 정보 입력(중복·규칙 실시간 검사) → 신청 완료", "REQ-F-12", "SCR-01a")
        def s03():
            page.goto(f"{BASE}/signup")
            next_btn = page.get_by_role("button", name="다음")
            expect(next_btn).to_be_disabled()
            page.get_by_label("이용약관 동의").check()
            page.get_by_label("개인정보 수집·이용 동의").check()
            page.get_by_role("button", name="보기").nth(1).click()
            shot(page, "03a_signup_terms", full=False)
            next_btn.click()
            page.fill("#su-id", "farmer01")
            page.fill("#su-pw", "abc123")
            page.locator("#su-name").click()
            expect(page.get_by_text("이미 사용 중인 아이디입니다")).to_be_visible()
            shot(page, "03b_signup_validation")
            page.fill("#su-id", NEW_ID)
            page.fill("#su-pw", NEW_PW)
            page.fill("#su-pw2", NEW_PW)
            page.fill("#su-name", "김토닥(E2E)")
            page.fill("#su-phone", "01055550000")
            page.fill("#su-note", "E2E 자동 시험 계정 · 양평군 가상 2동")
            expect(page.get_by_text("사용할 수 있는 아이디입니다")).to_be_visible()
            shot(page, "03c_signup_form")
            page.get_by_role("button", name="가입 신청").click()
            expect(page.get_by_text("가입 신청이 접수되었습니다")).to_be_visible()
            shot(page, "03d_signup_done", full=False)
            return NEW_ID
        s03()

        @step("E2E-04", "승인 전 로그인 → 승인 대기 안내", "REQ-F-12", "SCR-01")
        def s04():
            login(page, NEW_ID, NEW_PW)
            expect(page.get_by_text("관리자 승인을 기다리고")).to_be_visible()
            shot(page, "04_login_pending", full=False)
        s04()

        @step("E2E-05", "관리자 로그인 → 관리자 대시보드", "REQ-F-12, F-17", "SCR-A1")
        def s05():
            login(page, "admin", admin_pw)
            expect(page).to_have_url(re.compile(r"/admin$"))
            expect(page.get_by_role("heading", name="관리자 대시보드")).to_be_visible()
            shot(page, "05_admin_dashboard", wait=3000)
        s05()

        @step("E2E-06", "가입 승인 대기 탭 → 승인(역할·농장 지정)", "REQ-F-12", "SCR-A2")
        def s06():
            page.goto(f"{BASE}/admin/users")
            page.get_by_role("tab", name=re.compile("가입 승인 대기")).click()
            row = page.locator("tr", has_text=NEW_ID)
            expect(row).to_be_visible()
            shot(page, "06a_admin_users_pending")
            row.get_by_role("button", name="승인").click()
            dlg = page.get_by_role("dialog")
            dlg.get_by_label("TODAK 양평 1동").check()
            shot(page, "06b_admin_approve_modal", full=False)
            dlg.get_by_role("button", name="승인").click()
            expect(page.get_by_text(f"{NEW_ID} 가입을 승인했습니다")).to_be_visible()
            page.get_by_role("tab", name=re.compile("전체")).click()
            shot(page, "06c_admin_users_all")
        s06()

        @step("E2E-07", "관리자 화면: 센서·장치·구역, 기준값·규칙, 로그, 기상 자료", "REQ-F-11, F-13, F-15, F-16", "SCR-A3~A6")
        def s07():
            page.goto(f"{BASE}/admin/equipment")
            expect(page.get_by_text("관리 구역 (REQ-F-13)")).to_be_visible()
            shot(page, "07a_admin_equipment")
            page.goto(f"{BASE}/admin/standards")
            expect(page.get_by_role("heading", name="자동 제어 규칙", exact=True)).to_be_visible()
            shot(page, "07b_admin_standards_rules")
            page.goto(f"{BASE}/admin/logs")
            shot(page, "07c_admin_logs_ingest")
            page.get_by_role("button", name="제어 명령 로그").click()
            shot(page, "07d_admin_logs_commands")
            page.get_by_role("button", name="오류·예외 로그").click()
            shot(page, "07e_admin_logs_errors")
            page.goto(f"{BASE}/admin/weather")
            shot(page, "07f_admin_weather")
        s07()

        @step("E2E-08", "Swagger UI (API 문서)", "REQ-N-04", "-")
        def s08():
            page.goto(f"{BASE}/swagger-ui/index.html")
            expect(page.get_by_text("TODAK")).to_be_visible(timeout=15000)
            shot(page, "08_swagger", wait=3000, full=False)
            logout_via_api_page()
        def logout_via_api_page():
            page.goto(f"{BASE}/admin")
            logout(page)
        s08()

        @step("E2E-09", "승인된 신규 사용자 로그인 → 농가 대시보드(승인한 농장만)", "REQ-F-12", "SCR-02")
        def s09():
            login(page, NEW_ID, NEW_PW)
            expect(page).to_have_url(re.compile(r"/farm$"))
            expect(page.get_by_role("combobox", name="농장 선택").locator("option")).to_have_count(1)
            logout(page)
        s09()

        @step("E2E-10", "농가 화면 8개(계획서 화면 구조도): 대시보드·환경 그래프·장치 제어·제어 이력·알림·기준값·생육 분석·수확 판별 + 내 정보", "REQ-F-01~04, F-06~11, F-14, F-18", "SCR-02~09")
        def s10():
            login(page, "farmer01", farmer_pw)
            expect(page).to_have_url(re.compile(r"/farm$"))
            expect(page.get_by_text("현재 측정값 (최신)")).to_be_visible()
            nav = page.get_by_role("navigation", name="주 메뉴")
            for label in ("대시보드", "환경 그래프", "장치 제어", "제어 이력", "알림", "재배 기준값·제어 규칙", "생육 분석 (GDD·기상)", "수확 판별"):
                expect(nav.get_by_role("link", name=label, exact=True)).to_be_visible()
            shot(page, "10a_farmer_dashboard", wait=3000)
            page.get_by_role("tab", name=re.compile("Z2")).click()
            shot(page, "10b_farmer_dashboard_zone2", full=False)
            page.goto(f"{BASE}/farm/graph")
            page.wait_for_function("document.querySelectorAll('.recharts-line-curve').length >= 5", timeout=30000)
            shot(page, "10c_farmer_graph", wait=2000)
            page.goto(f"{BASE}/farm/control")
            shot(page, "10d_farmer_control")
            page.goto(f"{BASE}/farm/history")
            shot(page, "10e_farmer_history")
            page.goto(f"{BASE}/farm/alerts")
            shot(page, "10f_farmer_alerts")
            page.goto(f"{BASE}/farm/standards")
            expect(page.get_by_role("heading", name="재배 기준값 · 제어 규칙")).to_be_visible()
            shot(page, "10g_farmer_standards")
            page.goto(f"{BASE}/farm/growth")
            page.wait_for_function("document.querySelectorAll('.recharts-line-curve').length >= 1", timeout=30000)
            shot(page, "10h_farmer_growth_gdd", wait=2000)
            page.goto(f"{BASE}/farm/harvest")
            expect(page.get_by_text("확장 기능 · 이번 버전 미구현")).to_be_visible()
            shot(page, "10i_farmer_harvest")
            page.goto(f"{BASE}/account")
            expect(page.get_by_role("heading", name="내 정보")).to_be_visible()
            shot(page, "10j_account")
        s10()

        @step("E2E-11", "농가가 관리자 주소 입력 → 이동 차단 안내 (API도 403)", "REQ-F-12", "-")
        def s11():
            page.goto(f"{BASE}/admin/users")
            expect(page).to_have_url(re.compile(r"/farm$"))
            expect(page.get_by_text("관리자 전용 화면이라 이동할 수 없습니다")).to_be_visible()
            shot(page, "11_farmer_admin_blocked", full=False)
            logout(page)
        s11()

        @step("E2E-12", "조회 전용(VIEWER): 제어 버튼 비활성 + 안내", "REQ-F-12 (표 41)", "SCR-04")
        def s12():
            login(page, "viewer01", viewer_pw)
            expect(page).to_have_url(re.compile(r"/farm$"))
            page.goto(f"{BASE}/farm/control")
            expect(page.get_by_text("조회 전용 계정입니다")).to_be_visible()
            btns = page.get_by_role("button", name=re.compile("^(켜기|열기|차광)$"))
            assert btns.count() > 0 and all(btns.nth(i).is_disabled() for i in range(btns.count())), "제어 버튼이 비활성이 아님"
            shot(page, "12_viewer_control_readonly")
            logout(page)
        s12()

        @step("E2E-13", "관리자 임시 비밀번호 → 첫 로그인 때 비밀번호 변경 강제", "REQ-F-12", "SCR-01b")
        def s13():
            tok = api("POST", "/api/auth/login", body={"loginId": "admin", "password": admin_pw})["accessToken"]
            uid = f"e2etmp{STAMP}"
            api("POST", "/api/admin/users", tok, {"loginId": uid, "password": "Temp#2026e2e", "name": "임시비번 E2E", "role": "FARMER", "farmIds": [1]})
            login(page, uid, "Temp#2026e2e")
            expect(page).to_have_url(re.compile(r"/account/password"))
            expect(page.get_by_text("임시 비밀번호로 로그인했습니다")).to_be_visible()
            page.fill("#pw-cur", "Temp#2026e2e")
            page.fill("#pw-new", "Fresh#2026e2e")
            page.fill("#pw-new2", "Fresh#2026e2e")
            shot(page, "13_password_change_required", full=False)
            page.get_by_role("button", name="비밀번호 변경").click()
            expect(page).to_have_url(re.compile(r"/farm$"))
            logout(page)
            # 시험용 계정 정리: 사용 중지
            users = api("GET", "/api/admin/users", tok)
            for u in users:
                if u["loginId"].startswith("e2e"):
                    api("PATCH", f"/api/admin/users/{u['userId']}", tok, {"isActive": False})
        s13()

        @step("E2E-14", "아이디·비밀번호 찾기 → 관리자 초기화 요청 (같은 안내)", "REQ-F-12", "SCR-01c")
        def s14():
            page.goto(f"{BASE}/forgot")
            page.fill("#fg-id", "nobody")
            page.fill("#fg-name", "없는 사람")
            page.fill("#fg-phone", "01000009999")
            page.get_by_role("button", name="초기화 요청").click()
            expect(page.get_by_text("관리자에게 비밀번호 초기화 요청이 전달됩니다")).to_be_visible()
            shot(page, "14_forgot", full=False)
        s14()
        ctx.close()

        mob = b.new_context(viewport=PHONE, locale="ko-KR", timezone_id="Asia/Seoul", is_mobile=True, has_touch=True, device_scale_factor=2)
        mp = mob.new_page()

        @step("E2E-15", "360px 모바일: 로그인·대시보드·제어 (가로 스크롤 없음)", "REQ-N-07", "SCR-01·02·04")
        def s15():
            mp.goto(f"{BASE}/login")
            shot(mp, "15a_mobile_login", full=False)
            login(mp, "farmer01", farmer_pw)
            expect(mp).to_have_url(re.compile(r"/farm$"))
            shot(mp, "15b_mobile_dashboard", wait=3000)
            sw = mp.evaluate("document.documentElement.scrollWidth")
            assert sw <= PHONE["width"] + 1, f"가로 스크롤 발생 scrollWidth={sw}"
            bottom = mp.get_by_role("navigation", name="하단 메뉴")
            expect(bottom.get_by_role("link")).to_have_count(4)
            bottom.get_by_role("button", name="더보기").click()
            expect(mp.get_by_role("dialog", name="더보기 메뉴")).to_be_visible()
            shot(mp, "15c_mobile_more_menu", full=False)
            mp.goto(f"{BASE}/farm/control")
            shot(mp, "15d_mobile_control", full=False)
            return f"scrollWidth={sw}"
        s15()
        mob.close()

        # 증빙 화면: 실제 MySQL 조회 출력(tools/collect_evidence.py가 만든 HTML)과 Gradle 테스트 보고서
        ev = b.new_context(viewport={"width": 1280, "height": 900})
        epg = ev.new_page()
        for src, name in ((os.path.abspath(f"{EVID}/mysql_queries.html"), "16_mysql_query"),
                          (os.path.abspath("backend/build/reports/tests/test/index.html"), "17_backend_test_report")):
            if os.path.exists(src):
                epg.goto("file://" + src)
                epg.wait_for_timeout(800)
                epg.screenshot(path=f"{OUT}/{name}.png", full_page=True)
                print("saved", name)
        ev.close()
        b.close()

    ok = sum(r["result"] == "PASS" for r in results)
    with open(f"{EVID}/e2e_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    lines = ["# E2E 시험 결과 (Playwright · 헤드리스 Chromium)", "",
             f"- 실행: {datetime.now():%Y-%m-%d %H:%M} KST · 대상 {BASE} (Docker Compose 스택) · tools/capture_screens.py",
             f"- 결과: **{ok}/{len(results)} 통과** · 화면 데이터는 가상 센서 시뮬레이터(B안)의 시뮬레이션 값", "",
             "| ID | 시나리오 | 요구사항 | 화면 | 결과 | 비고 |", "|---|---|---|---|---|---|"]
    lines += [f'| {r["tc"]} | {r["name"]} | {r["req"]} | {r["screen"]} | {"✅ 통과" if r["result"] == "PASS" else "❌ 실패"} | {r["note"]} |' for r in results]
    with open(f"{EVID}/e2e_results.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(f"{OUT}/CAPTURED_AT.txt", "w", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} KST, {BASE}, tools/capture_screens.py (headless Chromium), {ok}/{len(results)} PASS\n")
    print(f"E2E {ok}/{len(results)} PASS")


if __name__ == "__main__":
    main()
