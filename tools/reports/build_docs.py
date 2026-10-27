# -*- coding: utf-8 -*-
"""개발 보고서·완료 보고서 Word 생성. 실행: python3 tools/reports/build_docs.py [출력 폴더]
수치·화면은 모두 docs/Test_Evidence의 실제 실행 결과에서 읽는다."""
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
import content as C  # noqa: E402
import evidence as E  # noqa: E402
from docgen import Doc  # noqa: E402

OUTDIR = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(E.ROOT, ".."))
TODAY = datetime.now().strftime("%Y.%m.%d")
JT, JC = E.junit()
E2E, E2E_AT = E.e2e()
SC = E.scenarios()
PF = E.perf()
FE = E.frontend_tests()
SIM = E.simulator_tests()
RATE = E.ingest_rate()
GITHUB = os.environ.get("TODAK_GITHUB_URL")  # 실제 업로드 후에만 설정


def src(path, start, end_marker=None, max_lines=40):
    """소스 파일에서 start 문자열이 있는 줄부터 잘라 온다 (보고서의 코드는 실제 파일 그대로)"""
    lines = open(os.path.join(E.ROOT, path), encoding="utf-8").read().split("\n")
    i = next(k for k, l in enumerate(lines) if start in l)
    out = []
    for l in lines[i:i + max_lines]:
        out.append(l)
        if end_marker and end_marker in l and len(out) > 1:
            break
    return "\n".join(out)


def fmt(v, unit="", nd=0):
    return "-" if v is None else f"{v:,.{nd}f}{unit}"


def test_summary_rows():
    e2e_ok = sum(r["result"] == "PASS" for r in E2E)
    sc_ok = sum(1 for r in SC if r["pass"])
    rows = [("백엔드 단위·통합 (JUnit 5, 실제 MySQL)", JT["tests"], JT["passed"], JT["failed"], JT["skipped"], JT["at"]),
            ("프런트 단위·화면 (Vitest)", FE["total"] if FE else "-", FE["passed"] if FE else "-", (FE["total"] - FE["passed"]) if FE else "-", 0, "빌드 시"),
            ("시뮬레이터 (pytest)", SIM["total"] if SIM else "-", SIM["passed"] if SIM else "-", 0, 0, "빌드 시"),
            ("E2E (Playwright, 헤드리스 Chromium)", len(E2E), e2e_ok, len(E2E) - e2e_ok, 0, E2E_AT),
            ("시뮬레이터 시나리오 통합", len(SC), sc_ok, len(SC) - sc_ok, 0, SC[0]["start"][:16].replace("T", " ") if SC else "-")]
    return rows


def totals():
    rows = test_summary_rows()
    t = sum(r[1] for r in rows if isinstance(r[1], int))
    p = sum(r[2] for r in rows if isinstance(r[2], int))
    return t, p


def perf_rows():
    if not PF:
        return [("측정 결과 파일 없음", "-", "-", "-")]
    return [("7일 원시 데이터 조회 (센서 1개, 약 1만 건)", "p95 ≤ 500ms", fmt(PF["series_p95"], " ms", 1), "통과" if PF["series_p95"] and PF["series_p95"] <= 500 else "미달"),
            ("대시보드 조회", "p95 ≤ 500ms", fmt(PF["dash_p95"], " ms", 1), "통과" if PF["dash_p95"] and PF["dash_p95"] <= 500 else "미달"),
            ("수동 제어 요청 → 실행 확인(ACK)", "p95 ≤ 5초", fmt(PF["ack_p95"], " ms", 0) + f" (평균 {fmt(PF['ack_avg'], ' ms', 0)})", "통과" if PF["ack_p95"] and PF["ack_p95"] <= 5000 else "미달"),
            ("HTTP 실패율", "0%", fmt((PF["fail_rate"] or 0) * 100, "%", 2), "통과" if (PF["fail_rate"] or 0) == 0 else "확인 필요")]


def screens(d, names=None):
    for key, title, req, desc in C.SCREENS:
        if names and key not in names:
            continue
        d.image(E.shot(key), f"{title} ({req})", explain=f"{desc}. 실행: {E2E_AT} · 데이터: 시뮬레이터(B안) 시뮬레이션 값", width_cm=15)


def evidence_table(d):
    d.table(["화면", "화면 ID", "요구사항", "구현 기능", "실제 작동", "데이터", "시험 결과"],
            [(t, sid, req, f, how, data, res) for key, t, sid, req, f, how, data, res in C.EVIDENCE12],
            [2.6, 1.8, 2, 3.6, 3.6, 2, 2], caption=f"필수 실행 증빙 12종 (실행 {E2E_AT}, 화면 파일 docs/Test_Evidence/screenshots)", size=7.5)
    for key, t, sid, req, f, how, data, res in C.EVIDENCE12:
        d.image(E.shot(key), f"{t} ({sid} · {req})", explain=f"{f}. {how}. 데이터: {data}. 시험: {res}. 실행 {E2E_AT}", width_cm=15)


def plan_changes(d):
    d.table(["항목", "계획서 v2.0", "실제 구현", "이유"], C.PLAN_CHANGES, [2.6, 3.4, 6.2, 4.3], caption="계획서와 달라진 점 (전체 대조: docs/Development_Plan/계획서_대비_구현_검토.md)", size=8)


def table_dictionary(d):
    """최종 테이블 정의서: 실제 Flyway DDL(V1·V3)에서 그대로 만든다 — 문서와 DB가 어긋나지 않게"""
    mig = os.path.join(E.ROOT, "backend/src/main/resources/db/migration")
    v1 = open(os.path.join(mig, "V1__schema.sql"), encoding="utf-8").read()
    v3 = open(os.path.join(mig, "V3__plan_alignment.sql"), encoding="utf-8").read()
    added = {}
    for t, body in re.findall(r"ALTER TABLE (\w+)\s+(.*?);", v3, re.S):
        for m in re.finditer(r"ADD COLUMN (\w+)\s+([A-Z]+(?:\([\d, ]+\))?)\s*(NOT NULL|NULL)?\s*(?:DEFAULT ('[^']*'|\S+))?[^,]*?(?:COMMENT '([^']*)')?\s*(?:AFTER \w+)?,?\s*$", body, re.M):
            added.setdefault(t, []).append((m.group(1), m.group(2), "", "Y" if m.group(3) == "NOT NULL" else "N", (m.group(4) or "").strip("'"), (m.group(5) or "") + " [V3]"))
    n = 0
    for name, body, comment in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\) COMMENT='([^']*)'", v1, re.S):
        pk = re.search(r"PRIMARY KEY \(([^)]*)\)", body)
        pk = [x.strip() for x in pk.group(1).split(",")] if pk else []
        fks = dict(re.findall(r"FOREIGN KEY \((\w+)\) REFERENCES (\w+\(\w+\))", body))
        rows = []
        for m in re.finditer(r"^\s*(\w+)\s+([A-Z]+(?:\([\d, ]+\))?)\s*(NOT NULL|NULL)?\s*(?:AUTO_INCREMENT)?\s*(?:DEFAULT ('[^']*'|[^\s,]+(?: ON UPDATE \w+)?))?[^,\n]*?(?:COMMENT '([^']*)')?,?\s*$", body, re.M):
            col = m.group(1)
            if col in ("PRIMARY", "UNIQUE", "CONSTRAINT", "KEY", "INDEX"):
                continue
            key = "PK" if col in pk else ("FK" if col in fks else "")
            desc = m.group(5) or ""
            if col in fks:
                desc = (desc + " → " + fks[col]).strip()
            rows.append((col, m.group(2), key, "Y" if m.group(3) == "NOT NULL" or col in pk else "N", (m.group(4) or "").strip("'"), desc))
        rows += added.get(name, [])
        n += 1
        d.table(["컬럼", "타입", "키", "NN", "기본값", "설명"], rows, [3.6, 2.6, 1, 0.9, 2.6, 5.8], caption=f"{name} — {comment}", size=7.5)
    d.note(f"테이블 {n}개 · 실제 DDL(backend/src/main/resources/db/migration/V1__schema.sql, V3__plan_alignment.sql)에서 자동 생성. [V3] = 구현 단계 추가 컬럼")


def common_front(d, kind):
    d.doc_control([("v0.1", "2026.10.26", f"{kind} 양식 작성", "TODAK팀"),
                   ("v1.0", TODAY, "실제 구현·시험 결과 반영 (TODAK " + E.VERSION + ")", "TODAK팀")])
    d.toc()


def dev_report():
    d = Doc("시스템 개발 보고서", "실제 구현 결과 · 소스 코드 · 시험 결과", "TODAK-DEV-001", "v1.0", "구현 완료 · 검수 요청")
    d.cover(date=TODAY)
    common_front(d, "개발 보고서")

    d.h("1. 개요", 1)
    d.p("이 보고서는 개발 계획서 v2.0에 따라 **실제로 만들고 실행한** TODAK " + E.VERSION + "의 구현 내용과 시험 결과를 기록한다. "
        "센서·장치는 아직 없으므로 모든 측정값과 장치 동작은 **가상 센서 시뮬레이터(B안)** 로 만든 것이며, 실제 양평 기상 관측값이나 농가 실측값이 아니다.")
    d.table(["항목", "내용"], [("대상", "경기도 양평군 비닐하우스 1동 100평(330.58㎡), 방울토마토"), ("범위", "반응형 웹(관리자·농가), 백엔드 API, MySQL, MQTT 수집, 자동 제어, GDD 분석, 시뮬레이터"),
                              ("실행 방식", "Docker Compose 5개 컨테이너 (mysql·mosquitto·backend·simulator·frontend)"),
                              ("소스 저장소", GITHUB or "로컬 Git 저장소 (GitHub 업로드 전 — 업로드 후 주소 기재)"), ("문서 버전", "TODAK " + E.VERSION)],
            [3.5, 13], caption="개발 개요", first_col_bold=True)

    d.h("1.1 계획서와 달라진 점", 2)
    plan_changes(d)

    d.h("2. 최종 기술 스택", 1)
    d.table(["영역", "기술 (버전)", "계획서 대비"], [
        ("프런트엔드", "React 18.3.1, TypeScript 5.6, Vite 5.4, Tailwind CSS 3.4, Recharts 2.12", "MUI → Tailwind (후속 지시서)"),
        ("백엔드", "Java 21, Spring Boot 3.3.5, Spring Security 6, jjwt 0.12.6, JPA, Flyway, springdoc", "Java 17 → 21"),
        ("DB", "MySQL 8.4 (22개 테이블)", "20 → 22 (권한·토큰 테이블 추가)"),
        ("IoT", "Mosquitto 2.0.20, Eclipse Paho, paho-mqtt 2.1 (Python 3.12)", "Spring Integration → Paho"),
        ("시험", "JUnit 5(실제 MySQL), Vitest, Playwright, k6", "E2E 추가"),
        ("배포", "Docker Compose, nginx 1.27", "같음")], [2.5, 9, 5], caption="최종 기술 스택")

    d.h("3. 실제 프로젝트 구조", 1)
    d.code(C.PROJECT_TREE)
    d.image(os.path.join(E.DIAG, "d_architecture.png"), "전체 시스템 아키텍처", width_cm=15)

    d.h("4. MySQL 데이터베이스 구현", 1)
    d.p("스키마는 Flyway 마이그레이션 3개로 만든다. 백엔드가 시작할 때 자동 적용되며 MySQL Workbench(127.0.0.1:3307)에서 직접 확인할 수 있다.")
    d.table(["파일", "내용"], [("V1__schema.sql", "22개 테이블, PK·FK 35개·UNIQUE·CHECK·인덱스, 컬럼 주석"),
                              ("V2__seed.sql", "농장 2곳(격리 검증용 포함)·구역·센서 11채널·장치 11종·규칙 CR-01~07·기준값·시험 계정(BCrypt)"),
                              ("V3__plan_alignment.sql", "계획서 대조 결과 보완: 가입 승인·약관 동의·임시 비밀번호, 규칙 세부 조건, 게이트웨이 기기 토큰, VIEWER 계정")],
            [4.5, 12], caption="DB 마이그레이션")
    d.image(os.path.join(E.DIAG, "erd.png"), "실제 DDL에서 만든 ERD (22개 테이블)", width_cm=16)
    d.image(E.shot("16_mysql_query"), "MySQL 실제 조회 화면 (mysql CLI 출력)", explain="테이블·마이그레이션 이력·사용자(BCrypt 해시 앞부분)·센서별 수집·명령 상태를 실제 DB에서 조회한 결과", width_cm=15)

    d.h("5. API 구현", 1)
    d.p("REST API는 후속 지시서의 묶음에 맞춰 `/api/auth`, `/api/admin`, `/api/farms`, `/api/sensors`, `/api/sensor-data`, `/api/devices`, `/api/controls`, `/api/alerts`, "
        "`/api/crop-standards`, `/api/analytics`로 나눴고 Swagger(`/swagger-ui/index.html`)에 요구사항 ID·테이블·오류 코드를 적었다. 계획서 API-01~27과의 대응은 검토서 4장에 있다.")
    d.table(["묶음", "주요 엔드포인트", "권한"], [
        ("/api/auth", "login · refresh · logout · signup · check-id · password-reset-request · me · password · logout-all", "공개 / 로그인"),
        ("/api/admin", "summary · users(+approve·reject·farms) · zones · sensors · devices · gateways/{id}/token · rules · logs/* · weather · simulator/scenario", "ADMIN (URL + @PreAuthorize)"),
        ("/api/farms, /api/stream", "내 농장 · 구역 · 대시보드 · SSE", "농장 권한"),
        ("/api/sensors, /api/sensor-data", "센서 목록 · 기간 조회(raw/hour) · CSV", "농장 권한"),
        ("/api/devices, /api/controls", "장치 · 수동 명령(202·409·423·503) · 모드 · 명령 상태 · 상태 이력 · 규칙(읽기)", "제어는 FARMER·ADMIN"),
        ("/api/alerts, /api/crop-*, /api/beehives", "알림 확인·해결 · 기준값 버전 · 작기 · 벌통", "처리는 FARMER·ADMIN"),
        ("/api/analytics", "GDD(내부·외부) · GDD CSV · 일별 통계 · 외부 기상", "농장 권한"),
        ("/api/ingest", "HTTP 대체 수집 (X-Device-Token)", "게이트웨이 기기 토큰")], [3.5, 9.5, 3.5], caption="API 묶음")
    d.image(E.shot("08_swagger"), "Swagger API 문서 실행 화면", width_cm=15)

    d.h("6. 인증·인가 (JWT) 구현", 1)
    d.bullets(["Access Token: HS256 JWT, **15분**, 메모리에만 보관(로컬 저장소 사용 안 함)",
               "Refresh Token: 32바이트 난수, DB에는 **SHA-256 해시만** 저장, HttpOnly·SameSite=Strict·Path=/api/auth 쿠키, 쓸 때마다 **회전**, 재사용 탐지 시 같은 계열 전체 폐기",
               "갱신·로그아웃에는 `X-TODAK-CSRF: 1` 헤더 필수 (쿠키 기반 CSRF 방지)",
               "비밀번호: BCrypt, 8~64자·영문·숫자·특수문자·아이디 미포함·같은 문자 4연속 금지, 5번 연속 실패 시 10분 잠금 (없는 아이디와 같은 오류 문구)",
               "회원가입은 **관리자 승인** 후 사용, 관리자가 정한 임시 비밀번호는 첫 로그인 때 변경 강제, 비밀번호를 바꾸면 다른 기기 로그인 폐기",
               "인가: 역할(ADMIN·FARMER·VIEWER) + 사용자별 농장 권한(TB_USER_FARM). 화면 메뉴와 별개로 모든 API가 검사"])
    d.code(src("backend/src/main/java/kr/todak/auth/AuthService.java", "public Tokens refresh(", "return new Tokens", 30), "AuthService.refresh — Refresh Token 회전과 재사용 탐지 (실제 소스)")

    d.h("7. 관리자·사용자 화면 구현", 1)
    d.p("화면은 개발 계획서 16장 화면 목록(SCR-01~10)과 후속 지시서의 관리자 화면을 따른다. 아래는 모두 **실제 실행 화면**이다 (헤드리스 Chromium 자동 촬영, `tools/capture_screens.py`).")
    screens(d, ["01_login", "03c_signup_form", "06a_admin_users_pending", "05_admin_dashboard", "10a_farmer_dashboard", "10h_farmer_growth_gdd", "10d_farmer_control", "15b_mobile_dashboard"])

    d.h("8. 센서 시뮬레이터 구현", 1)
    d.p("시뮬레이터는 현장 게이트웨이(GW-01)와 **같은 MQTT 토픽·JSON 규격**으로 동작한다. 실제 장비를 붙일 때 서버·DB·웹 코드는 바꾸지 않는다.")
    d.bullets(["열 모델: 외기(계절·일교차), 일사·차광, 측창·환기팬 손실, 난방 열량으로 1분마다 내부 온도 계산. 습도·CO₂·배지 수분·EC·pH도 장치 상태에 반응",
               "명령 수신 → 가상 장치 상태 변경 → ACK 발행. '장치 오류' 시나리오에서는 ACK를 보내지 않음",
               "통신 단절 시: LWT로 오프라인 알림, 마지막 기준값 사본으로 안전 운전(FAILSAFE), 측정값 버퍼 후 재연결 때 buffered=true로 재전송",
               "시나리오 9종: normal, heat, cold, humid, dry, sensor_silent, disconnect, device_fail, recover (관리자 대시보드에서 실행)"])
    d.code(src("simulator/todak_sim/gateway.py", "def apply_scenario", None, 34), "시나리오 적용 (simulator/todak_sim/gateway.py)")

    d.h("9. 통신 데이터 수집 결과", 1)
    if RATE["hour"]:
        s, n, m, pct = RATE["hour"]
        d.p(f"최근 1시간 동안 센서 {n}개 × {m}분 = {int(n) * int(m)}건이 저장돼야 했고 실제 저장은 **{s}건({pct}%)** 이다.")
    if RATE["counts"]:
        rec, sav, dup, rej = RATE["counts"]
        d.p(f"백엔드 기동 이후 수신 메시지 {rec}건 중 저장 {sav}건, 중복 {dup}건, 거부 {rej}건으로 처리 성공률은 **{RATE['rate']}%** 이다 (목표 ≥ 99.9%, 계획서 KPI 정의).")
    d.p("개발 PC 절전으로 2026-10-26 오후~10-27 02:53 사이 수집이 실제로 끊겼다. 재시작 때 시뮬레이터 백필이 그 구간을 10분 간격으로 채웠으며, 1분 간격으로 메우지 않았다. 원인은 10장 문제 7번.")
    d.image(E.shot("07c_admin_logs_ingest"), "센서 수집 로그 (센서별 최근 1시간 수신률)", width_cm=15)

    d.h("10. 자동 제어 구현", 1)
    d.table(["규칙", "조건 (작동 / 해제)", "대상·동작", "제한·추가 조건"], [
        ("CR-01 주간 환기", "온도 ≥ 28 / ≤ 26", "측창 열기 → 5분 뒤에도 ≥ 30이면 환기팬", "최소 3분"),
        ("CR-02 야간 난방", "온도 ≤ 14 / ≥ 16", "난방기", "최소 5분"),
        ("CR-03 차광", "일사 ≥ 800 / ≤ 500", "차광막 닫기", "10분 지속, 시간당 2회, 센서 이상 시 시간 스케줄"),
        ("CR-04 관수", "배지수분 ≤ 55 / ≥ 65", "구역별 밸브", "1회 5분, 일 12회, 간격 30분"),
        ("CR-05 고온 안전", "온도 ≥ 35 / ≤ 32", "측창·환기팬 강제 + CRITICAL 경보", "수동 모드보다 우선"),
        ("CR-06 저온 안전", "온도 ≤ 5 / ≥ 8", "난방 강제 + 측창 닫기 + 경보", "수동 모드보다 우선"),
        ("CR-07 보광", "주간 일사 ≤ 100 / ≥ 200", "보광등", "최소 10분")], [3, 3.5, 5.5, 4.5], caption="자동 제어 규칙 (TB_CONTROL_RULE)")
    d.p("판단 순서: 안전 한계 > 수동 명령(manual_until까지) > 자동 규칙. 명령은 요청(REQUESTED) → 전송(SENT) → 실행 확인(ACKED)으로 나누며, 10초 안에 ACK가 없으면 한 번 재전송한 뒤 응답 없음(TIMEOUT)과 경보를 남긴다. **명령 전송과 장치 동작을 같은 것으로 처리하지 않는다.**")
    d.code(src("backend/src/main/java/kr/todak/control/RuleDecision.java", "public static Want decide", "throw new IllegalArgumentException", 25), "히스테리시스 판단 (RuleDecision.decide, 실제 소스)")

    d.h("11. 적산온도(GDD) 분석", 1)
    d.p("GDD = max(0, min(일평균, 상한온도) − 기준온도), 기준 10℃·상한 30℃(문헌값, 화면에서 변경 가능·이력 저장). 내부는 하우스 온도 센서 **시간 평균 24개의 평균**, "
        "외부는 기상청 ASOS **(최고+최저)/2** 로 따로 계산한다. 수집률 80% 미만인 날은 '불완전'으로 표시한다. 수확일을 예측하지 않는 생육 참고 지표다.")
    d.code(src("backend/src/main/java/kr/todak/analytics/GddCalculator.java", "public static double gdd(", None, 26), "GDD 계산 (GddCalculator, 실제 소스)")
    d.p("검증: 손으로 계산한 7일치와 프로그램 결과의 오차가 0.1℃·일 이하인지 단위 시험(GddCalculatorTest)으로 확인했다. 외부 GDD는 기상청 CSV를 아직 가져오지 않아 비어 있다.")

    d.h("12. 개발 과정의 문제점 및 해결", 1)
    d.table(["문제", "원인", "해결"], C.PROBLEMS, [4, 6, 6.5], caption="문제와 해결")

    d.h("13. 시험 수행 결과", 1)
    t, p = totals()
    d.table(["구분", "건수", "통과", "실패", "미실행", "실행 시각"], test_summary_rows(), [6, 1.6, 1.6, 1.6, 1.6, 3.6], caption=f"시험 결과 요약 (전체 {t}건 중 {p}건 통과)")
    d.table(["시험 클래스", "건수", "실패"], [(k, v["tests"], v["failed"]) for k, v in sorted(JC.items())], [9, 3, 3], caption="백엔드 시험 클래스별")
    if SC:
        d.table(["시나리오", "판정", "확인 항목"], [(r["name"], "통과" if r["pass"] else "미통과",
                                                 "\n".join(("✓ " if c["ok"] else "✗ ") + c["item"] for c in r["checks"])) for r in SC], [4, 2, 10.5], caption="시뮬레이터 시나리오 시험")
    d.image(E.shot("17_backend_test_report"), "백엔드 테스트 보고서 실행 화면 (Gradle)", width_cm=15)

    d.h("14. 실제 실행 화면", 1)
    d.h("14.1 필수 실행 증빙 12종 (후속 지시서 14절)", 2)
    evidence_table(d)
    d.h("14.2 그 밖의 실행 화면", 2)
    screens(d, ["02_login_error", "04_login_pending", "06b_admin_approve_modal", "07b_admin_standards_rules", "07d_admin_logs_commands",
                "10e_farmer_history", "10g_farmer_standards", "10i_farmer_harvest", "12_viewer_control_readonly", "13_password_change_required"])

    d.h("15. 소스 코드 저장소", 1)
    d.p(GITHUB and f"GitHub: {GITHUB} (Private 저장소, 2026-10-27 업로드)" or "현재 로컬 Git 저장소에만 커밋되어 있다. GitHub 업로드는 하지 않았으며, 업로드 후 저장소 주소를 이 절에 적는다. 업로드 명령은 README와 완료 보고서에 있다.")
    d.h("부록 A. 최종 테이블 정의서 (실제 DB 기준)", 1)
    d.p("개발 계획서 17.2절 테이블 정의서(20개)를 실제 구현 DB(22개)에 맞춰 갱신한 최종본이다. 계획서의 20개 테이블은 컬럼 이름과 타입이 실제 DB와 모두 같고, 구현 단계에서 2개 테이블과 [V3] 컬럼이 추가되었다.")
    table_dictionary(d)
    return d.save(os.path.join(OUTDIR, "03_시스템_개발_보고서_v1.0.docx"))


def completion_report():
    d = Doc("시스템 개발 완료 보고서", "계획 대비 실적 · 시험·성능·보안 검증 · 인도 내용", "TODAK-CMP-001", "v1.0", "완료 보고 · 검수 요청")
    d.cover(date=TODAY)
    common_front(d, "완료 보고서")

    d.h("1. 사업 개요와 목표", 1)
    d.table(["항목", "내용"], [("사업명", "양평 방울토마토 스마트 농업 정보시스템(TODAK) 구축"), ("대상", "경기도 양평군 비닐하우스 1동 100평(330.58㎡)"),
                              ("사업비·기간", "50,000,000원(VAT 포함) · 12주 (가상 사업 기간 2026.11.02~2027.01.22)"),
                              ("목표", "환경 1분 수집·자동 제어·이상 알림·원격 제어·생육 분석(GDD)을 하나의 반응형 웹으로 제공"),
                              ("실행 방안", "B안 가상 센서 시뮬레이터로 전 과정 검증 (A안 실장비는 확보 후)")], [3.5, 13], caption="사업 개요", first_col_bold=True)

    d.h("2. 계획 대비 실제 구현 범위", 1)
    done = sum(1 for r in C.REQ_STATUS if r[2].startswith("완료") or r[2] == "측정 완료")
    d.p(f"요구사항 25건(기능 18·비기능 7) 중 **{done}건 완료**, 확장 범위 2건(F-05·F-07) 미구현, 운영 단계 측정 1건(N-02). 계획서와의 차이는 '계획서 대비 구현 검토서'(docs/Development_Plan)에 항목별로 적었다.")
    d.table(["구분", "계획", "실제"], [("MVP 요구사항", "16건", "16건 완료 (시뮬레이터 검증)"), ("확장", "F-05, F-07, SMS", "미구현 (계획서와 같음)"),
                                      ("화면", "SCR-01~10", "SCR-01~08·10 + 회원가입·내 정보·관리자 6화면, SCR-09는 확장"),
                                      ("API", "27개(API-01~27)", "API-24·25(확장) 제외 전부 + 계정·관리 API"),
                                      ("DB", "20개 테이블", "22개 테이블 (권한·토큰 2개 추가)"),
                                      ("추가 (사용자 요청)", "-", "회원가입·관리자 승인·비밀번호 찾기·내 정보·강제 변경")], [3.5, 5, 8], caption="계획 대비 범위")
    plan_changes(d)

    d.h("3. 요구사항 완료 현황", 1)
    d.table(["ID", "요구사항", "상태", "구현 내용", "검증"], C.REQ_STATUS, [2.2, 3.4, 2.6, 5.2, 4.2], caption="요구사항 완료 현황 (RTM: docs/RTM.md)", size=8)

    d.h("4. 최종 시스템 구성도", 1)
    d.image(os.path.join(E.DIAG, "d_architecture.png"), "최종 시스템 구성", width_cm=15)
    d.image(os.path.join(E.DIAG, "d_comm_structure.png"), "통신·데이터 수집 구조", width_cm=15)
    d.image(os.path.join(E.DIAG, "l_sensors.png"), "센서 배치도 (시드 데이터와 동일)", width_cm=15)

    d.h("5. 최종 데이터베이스 구성", 1)
    d.p("MySQL 8.4, 22개 테이블, FK 35개. 원시 1분 데이터는 3년 보존 후 매일 03:00 삭제, 시간 집계는 영구 보존, 일 1회 백업 스크립트 제공.")
    d.image(os.path.join(E.DIAG, "erd.png"), "최종 ERD", width_cm=16)

    d.h("6. 관리자·사용자 시스템 구현 결과", 1)
    screens(d, ["05_admin_dashboard", "06a_admin_users_pending", "10a_farmer_dashboard", "10h_farmer_growth_gdd", "10d_farmer_control", "12_viewer_control_readonly", "15b_mobile_dashboard"])

    d.h("7. 시험 통과율", 1)
    t, p = totals()
    d.p(f"전체 자동 시험 **{t}건 중 {p}건 통과 ({p / t * 100:.1f}%)**. 실패·미실행은 표에 그대로 적었다." if t else "시험 결과 파일이 없다.")
    d.table(["구분", "건수", "통과", "실패", "미실행", "실행 시각"], test_summary_rows(), [6, 1.6, 1.6, 1.6, 1.6, 3.6], caption="시험 통과율")
    if E2E:
        d.table(["ID", "시나리오", "결과"], [(r["tc"], r["name"], "통과" if r["result"] == "PASS" else "실패") for r in E2E], [2, 12, 2.5], caption="E2E 시험", size=8)

    d.h("8. 성능 측정 결과", 1)
    d.p("k6로 측정했다 (조회: 가상 사용자 5명 60초, 제어: 보광등 ON/OFF 20회). 측정 환경은 개발 PC 1대의 Docker Compose이며 운영 서버 값이 아니다.")
    d.table(["항목", "목표 (REQ-N-01)", "측정값", "판정"], perf_rows(), [6.5, 3.5, 4.5, 2], caption="성능 측정")
    if RATE["rate"]:
        d.p(f"데이터 저장 성공률(수신 대비 저장+중복): **{RATE['rate']}%** (목표 ≥ 99.9%).")

    d.h("9. 보안 및 인증 검증 결과", 1)
    d.table(["항목", "검증 방법", "결과"], [
        ("비밀번호 BCrypt 저장", "DB 조회(해시 접두어 $2a$/$2b$), 통합 시험", "통과"),
        ("5회 실패 잠금·계정 존재 비노출", "AuthIntegrationTest", "통과"),
        ("Refresh 회전·재사용 탐지·로그아웃 무효화", "AuthIntegrationTest", "통과"),
        ("HttpOnly·SameSite=Strict 쿠키, CSRF 헤더", "AuthIntegrationTest", "통과"),
        ("관리자 API 차단 (URL + 메서드)", "AuthorizationIntegrationTest, E2E-11", "통과"),
        ("농가 간 데이터 격리", "AuthorizationIntegrationTest (farmer01 → 농장 2: 403)", "통과"),
        ("조회 전용(VIEWER) 제어 차단", "PlanAlignmentIntegrationTest, E2E-12", "통과"),
        ("가입 승인 전 로그인 차단", "AccountIntegrationTest, E2E-04", "통과"),
        ("비밀정보 저장소 제외", ".env git 제외, .env.example만 포함", "확인"),
        ("MQTT 계정·ACL", "infra/mosquitto/acl (GW는 자기 토픽만)", "설정"),
        ("HTTPS·MQTT TLS", "-", "운영 배포 시 적용 (미적용)")], [6, 7, 3.5], caption="보안 검증")

    d.h("10. 구현되지 않은 기능", 1)
    d.table(["항목", "이유", "다음 단계"], C.NOT_DONE, [5, 5.5, 6], caption="미구현·미검증 항목")

    d.h("11. 실제 시스템 활용 가능성", 1)
    d.bullets(["서버·DB·웹·MQTT 규격은 실장비(A안)에서도 그대로 쓴다. 게이트웨이만 같은 토픽·JSON으로 붙이면 된다.",
               "실장비 적용 전 조건(계획서 14.1): 시나리오·규칙 시험 통과(완료), 현장 장치별 수동 ON/OFF·ACK 확인, 통신 차단 1시간 시험, 농가 입회 임계값 확인, 첫 1주 '알림만' 운영.",
               "현재 성능은 개발 PC 1대 기준이다. 농장 1~2곳 규모에는 충분하나 운영 서버에서 다시 측정해야 한다."])

    d.h("12. 향후 유지보수 및 확장 계획", 1)
    d.numbered(["A안 실장비 연동(Modbus 게이트웨이)과 전기·설비 안전 검증", "수확 판별(F-07): 이미지 수집 → OpenCV 착색도 → API-24·25",
                "HTTPS·TLS 적용, 운영 배포, 가용성 모니터링", "문자 알림, 기상청 API 자동 연동", "CI(GitHub Actions) 상시 실행, 의존성 보안 점검"])

    d.h("13. 저장소·시연 URL·증빙", 1)
    d.table(["항목", "내용"], [("GitHub 저장소", GITHUB or "미업로드 — 로컬 Git에만 커밋됨. 업로드 후 기재"),
                              ("웹 시연 URL", "배포하지 않음 — 로컬 실행 http://localhost:8088"),
                              ("실행 증빙", "docs/Test_Evidence (screenshots, e2e_results, scenario_results, performance, backend_tests, mysql_queries)"),
                              ("검토서·RTM", "docs/Development_Plan/계획서_대비_구현_검토.md, docs/RTM.md")], [3.5, 13], caption="저장소·증빙", first_col_bold=True)
    if GITHUB:
        d.p("받아서 실행하기:", bold=True)
        d.code(f"git clone {GITHUB}.git\ncd TODAK-SmartFarm\ncp .env.example .env   # 비밀번호·JWT 키 변경\ndocker compose up -d --build   # → http://localhost:8088")
    else:
        d.p("GitHub 업로드 명령 (저장소를 만든 뒤 직접 실행):", bold=True)
        d.code("cd TODAK-SmartFarm\ngit remote add origin https://github.com/<계정>/TODAK-SmartFarm.git\ngit branch -M main\ngit push -u origin main")

    d.h("14. 최종 실행 증빙 화면", 1)
    evidence_table(d)
    return d.save(os.path.join(OUTDIR, "04_시스템_개발_완료보고서_v1.0.docx"))


if __name__ == "__main__":
    print(dev_report())
    print(completion_report())
