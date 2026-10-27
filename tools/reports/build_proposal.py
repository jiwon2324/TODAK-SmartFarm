# -*- coding: utf-8 -*-
"""
시스템 제안서 (Word + PowerPoint).
계획서 v2.0과 같은 원본 데이터(tools/plan_docs/data.py)에서 만들어 제안서·개발 계획서·완료 보고서의 수치가 일치한다.
실행: TODAK_GITHUB_URL=... TODAK_SITE_URL=... python3 tools/reports/build_proposal.py [출력 폴더]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plan_docs"))
import data as P  # noqa: E402
import evidence as E  # noqa: E402
import build_docs as BD  # noqa: E402
import build_ppt as BP  # noqa: E402
import content as C  # noqa: E402
from docgen import Doc  # noqa: E402

OUTDIR = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(E.ROOT, ".."))
FIG = os.path.join(E.ROOT, "tools", "plan_docs", "fig")
GITHUB = os.environ.get("TODAK_GITHUB_URL")
SITE = os.environ.get("TODAK_SITE_URL")
VIDEO = os.environ.get("TODAK_VIDEO_URL")


def fig(n):
    return os.path.join(FIG, n + ".png")


def won(n):
    return f"{n:,}원"


GOALS = [
    ("야간·주말 관리 공백 해소", "기준 이탈을 1분 안에 감지해 자동 제어하고 휴대폰으로 알린다"),
    ("경험이 아닌 기준값으로 운영", "생육 단계별 기준값과 제어 규칙을 화면에서 관리하고 변경 이력을 남긴다"),
    ("생육 상태를 숫자로 설명", "하우스 내부와 기상청 외부 자료로 유효적산온도(GDD)를 따로 계산해 비교한다"),
    ("장애에도 안전", "통신이 끊겨도 현장 게이트웨이가 마지막 기준값으로 안전 운전하고, 복구 후 자료를 다시 보낸다"),
]
SCOPE = [
    ("MVP (16건)", "환경 수집, 온도·광·관수 자동 제어, 수정 지원 알림, 원격 제어, 경보, 이력·그래프, 기준값, 사용자·권한, 구역, GDD, 외부 기상, 명령 추적, 시뮬레이터, 실시간 갱신"),
    ("확장 (2건)", "REQ-F-05 육묘 모니터링, REQ-F-07 카메라 수확 판별 — 이번 사업 범위 밖, 구조만 준비"),
    ("범위 밖", "파종·수정·수확 동작 자체의 기계화, 양액 조성 자동화(기존 양액기 사용), 문자 발송(유료)"),
]
ARCH = [
    ("현장", "센서 11채널, 제어장치 11종, 현장 게이트웨이(기준값 사본·안전 운전·24시간 버퍼)"),
    ("통신", "MQTT(QoS 1, LWT로 단절 감지) + 예비 HTTP 수집, 1분 주기"),
    ("서버", "Spring Boot: 수집·검증, 규칙 엔진(히스테리시스), 명령·ACK 추적, 경보, GDD 배치, JWT 인증"),
    ("DB", "MySQL: 측정값·시간 집계·명령·실행 이력·경보·기준값·기상 자료 (계획 20개 테이블)"),
    ("웹", "React 반응형 웹: 대시보드·그래프·제어·이력·알림·기준값·생육 분석, 관리자 화면"),
]
VERIFY = [
    ("B안 (이번 사업)", "가상 센서 시뮬레이터가 실제 게이트웨이와 같은 MQTT 규격으로 값을 보내고 명령에 응답", "실장비 없이 고온·저온·관수 부족·센서 무응답·통신 단절을 일부러 일으켜 시험"),
    ("A안 (확장)", "실제 센서·장비를 Modbus 게이트웨이로 연결", "'알림만' 모드로 1주 시범 후 자동 제어 전환"),
]


def proposal_word():
    d = Doc("시스템 제안서", "방울토마토 스마트 농업 정보시스템 (TODAK) 구축 제안", "TODAK-PRP-001", "v1.0", "제출본")
    d.cover(date=BD.TODAY)
    d.doc_control([("v1.0", BD.TODAY, "RFP 초안을 대체하는 정식 시스템 제안서. 개발 계획서 v2.0·완료 보고서와 수치 일치", "양지원")], approvals=False)
    d.toc()

    BD.assignment_map(d, "01 시스템 제안서 (손 농사 6가지 작업별 제안: '제안 배경과 필요성')")
    d.h("제안 개요", 1)
    d.table(["항목", "내용"], [("사업명", P.PROJECT["name"]), ("대상", f"{P.PROJECT['region']} · {P.PROJECT['facility']} {P.PROJECT['area']}"),
                              ("작물", P.PROJECT["crop"]), ("사업비", f"{won(P.PROJECT['budget'])} (부가세 포함, 추정)"),
                              ("기간", P.PROJECT["period"]), ("개발 방법", P.PROJECT["method"]), ("서비스 형태", P.PROJECT["service"]),
                              ("제안 시스템", "TODAK — 하우스 환경을 1분마다 수집하고 기준값에 맞춰 환기·난방·차광·관수를 자동 제어하며, 이상 시 알림·원격 제어·생육 분석(GDD)을 제공하는 웹 시스템")],
            [3, 13.5], caption="제안 개요", first_col_bold=True)
    d.p("표기 원칙: 양평 기후는 기상청 관측 자료(실측), 발주 농가·사업 기간·사업비는 과제 설정(가상), 하우스 센서·장치 값은 가상 센서 시뮬레이터(B안) 데이터다.", size=9)

    d.h("제안 배경과 필요성", 1)
    d.h("농사를 손으로 한다면 — 6가지 작업 분석", 2)
    d.p("RFP가 제시한 손 농사 6가지 작업을 하나씩 나눠 지금의 방식과 문제를 정리하고, 효과와 비용을 따져 자동화 수준을 정했다. 모든 작업을 기계로 바꾸지 않는다.")
    d.table(["작업", "지금(손으로)", "문제", "자동화 수준", "TODAK 제안", "요구사항"], [(t[0], t[1], t[2], t[3], t[4], t[8]) for t in P.MANUAL_TASKS],
            [2.2, 3, 2.8, 2.2, 4.8, 1.6], caption="손 농사 6가지 작업과 제안", size=7.5)
    d.h("사업 대상지 — 양평 기후 (기상청 평년값 1991~2020, 실측)", 2)
    d.p(f"1월 평균 최저 {P.CLIMATE['tmin'][0]}℃, 8월 평균 최고 {P.CLIMATE['tmax'][7]}℃, 7월 강수 {P.CLIMATE['rain'][6]}mm. "
        "겨울 야간 저온, 여름 한낮 고온, 장마철 다습이 하우스 관리의 핵심 위험이다. 이 위험이 곧 야간 난방 감시·한낮 환기와 차광·습도 경보 요구사항이 된다.")
    d.image(fig("f_climate_temp"), "양평 월별 기온 평년값", width_cm=14)
    d.image(fig("f_season_risk"), "계절별 재배 위험", width_cm=14)
    d.h("현재(AS-IS)와 목표(TO-BE)", 2)
    d.image(fig("d_asis_tobe"), "현재와 목표 업무", width_cm=15)

    d.h("제안 목표와 범위", 1)
    d.table(["목표", "내용"], GOALS, [5, 11.5], caption="제안 목표", first_col_bold=True)
    d.table(["구분", "내용"], SCOPE, [3, 13.5], caption="사업 범위", first_col_bold=True)
    d.table(["지표", "목표", "측정 방법"], P.KPIS, [5, 5.5, 6], caption="핵심 성과지표(KPI)", size=8.5)

    d.h("요구사항", 1)
    d.p("기능 18건(MVP 16 · 확장 2), 비기능 7건. 모든 요구사항에 검증 기준을 붙였다. 상세 명세는 『개발 계획서 v2.0』 요구사항 정의서와 같다.")
    d.table(["ID", "요구사항", "설명", "구분", "검증 기준"], [(r[0], r[1], r[2], r[8], r[10]) for r in P.REQ_F], [1.8, 2.8, 5.2, 1.6, 5.1], caption="기능 요구사항", size=7.5)
    d.table(["ID", "구분", "요구 내용", "검증 방법"], [(r[0], r[1], r[2], r[3]) for r in P.REQ_N], [1.8, 2, 8.5, 4.2], caption="비기능 요구사항", size=7.5)

    d.h("제안 시스템 구성", 1)
    d.image(fig("d_architecture"), "시스템 구성도", width_cm=15.5)
    d.table(["계층", "구성"], ARCH, [2.5, 14], caption="계층별 구성", first_col_bold=True)
    d.image(fig("d_comm_structure"), "통신·데이터 수집 구조", width_cm=15.5)
    d.image(fig("d_control_authority"), "제어 주체: 평상시 서버, 통신 단절 시 게이트웨이", width_cm=15)
    d.h("센서·장치 배치", 2)
    d.table(["구역", "이름", "범위", "특징"], P.ZONES, [1.5, 3, 5, 7], caption="관리 구역")
    d.image(fig("l_sensors"), "센서 배치도", width_cm=15.5)
    d.image(fig("l_devices"), "제어장치 배치도", width_cm=15.5)
    d.h("자동 제어 규칙", 2)
    d.table(["ID", "규칙", "기준", "작동", "해제", "동작", "조건"], P.CONTROL_RULES, [1.3, 2, 2.3, 2.3, 2.3, 4.2, 2.1], caption="자동 제어 규칙 (히스테리시스)", size=8)
    d.h("데이터와 화면", 2)
    d.image(fig("u_erd"), "데이터 모델 (ERD)", width_cm=16)
    d.image(fig("u_sitemap"), "화면 구조도", width_cm=15.5)
    d.image(fig("u_usecase"), "유스케이스 다이어그램", width_cm=15)

    d.h("검증 방법", 1)
    d.table(["구분", "방법", "검증"], VERIFY, [3, 7, 6.5], caption="검증 방안", first_col_bold=True)

    d.h("수행 계획", 1)
    d.table(["ID", "작업", "주차", "담당", "산출물"], [(w[0], w[1], f"{w[2]}~{w[3]}주", w[4], w[5]) for w in P.WBS], [1.2, 5, 2, 2, 6.3], caption="작업 분해(WBS)", size=8)
    d.image(fig("f_gantt"), "일정표 (관문 G1~G4)", width_cm=15.5)
    d.table(["주차", "관문"], [(f"{g[0]}주", g[1]) for g in P.GATES], [3, 13.5], caption="단계 관문 (폭포수)")

    d.h("사업비", 1)
    d.table(["항목", "내용", "금액"], [(b[0], b[1], won(b[2])) for b in P.BUDGET] + [("합계", "", won(sum(b[2] for b in P.BUDGET)))], [3, 10, 3.5], caption="사업비 구성 (추정)", size=8)
    d.image(fig("f_budget"), "사업비 비중", width_cm=12)
    d.note("견적 없이 산정한 추정치다. 학생 실제 개발(B안)은 보유 PC와 무료 도구로 하여 실비 0원이며, 가상 사업비와 섞지 않는다.")

    d.h("위험 관리", 1)
    d.table(["ID", "위험", "가능성", "영향", "대응"], [(r[0], r[1], r[2], r[3], r[4]) for r in P.RISKS], [1.2, 4.5, 1.4, 1.4, 8], caption="주요 위험", size=8)
    d.image(fig("f_risk_matrix"), "위험 매트릭스", width_cm=11)

    d.h("기대 효과", 1)
    d.bullets(["야간·주말 저온·고온 위험을 자동 제어와 알림으로 줄인다", "경험에 의존하던 판단을 측정값·기준값·이력으로 바꾼다",
               "내부·외부 GDD 비교로 난방 효과와 생육 진행을 설명할 수 있다", "같은 통신 규격으로 실장비(A안)·수확 판별로 넓힐 수 있다"])

    d.h("참고: 제안 이후 진행 결과", 1)
    d.p("이 제안대로 개발 계획서(v2.0)를 작성하고 실제로 동작하는 시스템을 구현했다. 결과는 『시스템 개발 완료 보고서』에 있다.")
    d.table(["항목", "위치"], [r for r in (("웹 사이트 (로그인 없이 둘러보기)", SITE and SITE + "/demo"), ("시연 영상", VIDEO), ("소스 코드", GITHUB)) if r[1]],
            [5, 11.5], caption="확인 방법", first_col_bold=True)
    return d.save(os.path.join(OUTDIR, "01_시스템_제안서_v1.0.docx"))


def proposal_ppt():
    d = BP.Deck(f"TODAK 시스템 제안서 v1.0  |  {BD.TODAY}")
    d.cover("방울토마토 스마트 농업 정보시스템\n시스템 제안서", "경기도 양평군 · 비닐하우스 1동 100평 · 5,000만 원 · 12주 · 반응형 웹", "TODAK-PRP-001",
            "양평 100평 비닐하우스에서 방울토마토를 키우는 농가를 위한 스마트 농업 정보시스템을 제안합니다.")
    BP.assignment_slide(d, "01 시스템 제안서 — 손 농사 6가지 작업별 제안 포함")
    sl = d.slide("한 장 요약", notes="숫자 네 개로 요약하면 100평, 5천만 원, 12주, 센서 11개와 장치 11개입니다.")
    d.stats(sl, [("100평", "단동 비닐하우스 1동\n(330.58㎡, 양평)"), ("5천만 원", "부가세 포함\n(추정 예산)"), ("12주", "폭포수 · 관문 4개"), ("11 + 11", "센서 채널 + 제어 장치")])
    d.text(sl, 0.6, 3.9, 12.1, 2.8, ["**무엇을**: 하우스 환경 1분 수집 → 기준값 자동 제어 → 이상 알림·원격 제어 → 생육 분석(GDD)",
                                     f"**왜**: 야간·주말 관리 공백, 양평 겨울 저온(1월 평균 최저 {P.CLIMATE['tmin'][0]}℃)과 여름 고온·장마 다습",
                                     "**어떻게**: 반응형 웹 + 서버 + DB + MQTT, 통신이 끊겨도 현장 안전 운전",
                                     "**검증**: 실장비 없이도 같은 규격의 가상 센서 시뮬레이터(B안)로 전 과정 시험"], 15)
    sl = d.slide("농사를 손으로 한다면 — 6가지 작업", "지금의 방식과 문제", notes="RFP의 손 농사 6가지 작업입니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["작업", "지금(손으로)", "문제"], [(t[0], t[1], t[2]) for t in P.MANUAL_TASKS], [2.0, 5.2, 4.9], 12, 0.72)
    sl = d.slide("6가지 작업별 제안 — 자동화 수준을 나눴다", "완전 자동화는 온도, 씨 뿌리기는 범위 밖", notes="효과와 비용을 따져 자동화 수준을 정했습니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["작업", "자동화 수준", "TODAK 제안", "요구사항"], [(t[0], t[3], t[4], t[8]) for t in P.MANUAL_TASKS], [1.8, 2.0, 6.8, 1.5], 11, 0.78)
    sl = d.slide("양평 기후가 요구사항을 만든다", "기상청 평년값 1991~2020 (실측)", notes="양평의 실제 기후 자료입니다.")
    d.pic(sl, fig("f_climate_temp"), 0.6, 1.55, 7.6, 5.3)
    d.card(sl, 8.5, 1.6, 4.2, 5.2)
    d.text(sl, 8.7, 1.8, 3.9, 4.9, [f"**{P.CLIMATE['tmin'][0]}℃**", "1월 평균 최저 → 야간 난방 감시", "", f"**{P.CLIMATE['tmax'][7]}℃**",
                                   "8월 평균 최고 → 한낮 환기·차광", "", f"**{P.CLIMATE['rain'][6]}mm**", "7월 강수 → 습도 경보"], 15)
    sl = d.slide("현재(AS-IS)와 목표(TO-BE)", notes="사람이 지켜보던 일을 시스템이 감시하고 알립니다.")
    d.pic(sl, fig("d_asis_tobe"), 0.6, 1.5, 12.1, 5.35)
    sl = d.slide("제안 목표와 범위", notes="목표 네 가지와 사업 범위입니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["목표", "내용"], GOALS, [3.6, 8.5], 13, 0.5)
    d.table(sl, 0.6, 4.25, 12.1, ["구분", "내용"], SCOPE, [2.0, 10.1], 11.5, 0.62)
    sl = d.slide("요구사항 — 기능 18 · 비기능 7", "모든 요구사항에 검증 기준", notes="요구사항 25건입니다.")
    d.table(sl, 0.6, 1.45, 6.6, ["ID", "기능 요구사항", "구분"], [(r[0], r[1], r[8]) for r in P.REQ_F], [1.4, 2.8, 2.4], 9, 0.265)
    d.table(sl, 7.2, 1.5, 5.5, ["ID", "비기능", "요구 내용"], [(r[0], r[1], r[2]) for r in P.REQ_N], [1.4, 1.2, 2.9], 9, 0.62)
    sl = d.slide("제안 시스템 구성", notes="현장, 통신, 서버, DB, 웹의 다섯 계층입니다.")
    d.pic(sl, fig("d_architecture"), 0.6, 1.5, 6.9, 5.35)
    d.table(sl, 7.7, 1.5, 5.0, ["계층", "구성"], ARCH, [1.0, 4.0], 10, 0.8)
    sl = d.slide("제어 주체를 하나로: 평상시 서버, 단절 시 게이트웨이", notes="통신이 끊겨도 현장은 안전하게 운전합니다.")
    d.pic(sl, fig("d_control_authority"), 0.6, 1.5, 12.1, 5.35)
    sl = d.slide("통신·데이터 수집 구조", notes="센서 값은 게이트웨이를 거쳐 MQTT로 서버에 들어옵니다.")
    d.pic(sl, fig("d_comm_structure"), 0.6, 1.5, 12.1, 5.35)
    sl = d.slide("센서 배치 — 2개 구역에 온습도·배지수분 1세트씩", notes="입구측 Z1과 안쪽 Z2로 나눴습니다.")
    d.pic(sl, fig("l_sensors"), 0.6, 1.5, 12.1, 5.35)
    sl = d.slide("제어장치 배치", notes="측창, 환기팬, 난방기, 차광막, 보광등, 관수 밸브입니다.")
    d.pic(sl, fig("l_devices"), 0.6, 1.5, 12.1, 5.35)
    sl = d.slide("자동 제어 규칙 6개 — 히스테리시스와 안전 한계", notes="켜는 값과 끄는 값을 다르게 둬 반복 작동을 막습니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["ID", "규칙", "작동", "해제", "동작", "조건"], [(r[0], r[1], r[3], r[4], r[5], r[6]) for r in P.CONTROL_RULES],
            [0.9, 1.4, 1.9, 1.7, 4.1, 2.1], 11.5, 0.7)
    sl = d.slide("데이터 모델 (ERD)", notes="명령과 실제 장치 상태를 분리했습니다.")
    d.pic(sl, fig("u_erd"), 0.6, 1.5, 12.1, 5.35)
    sl = d.slide("화면 구조", notes="대시보드와 일곱 개 메뉴, 관리자 메뉴입니다.")
    d.pic(sl, fig("u_sitemap"), 0.6, 1.5, 12.1, 5.35)
    sl = d.slide("유스케이스", notes="농가, 관리자, 검수자, 스케줄러가 시스템을 쓰는 방법입니다.")
    d.pic(sl, fig("u_usecase"), 0.6, 1.5, 12.1, 5.35)
    sl = d.slide("검증 방법 — 실장비 없이도 같은 코드로", notes="이번 사업은 시뮬레이터로 검증하고, 실장비는 확장 단계입니다.")
    d.table(sl, 0.6, 1.6, 12.1, ["구분", "방법", "검증"], VERIFY, [2.2, 5.2, 4.7], 14, 1.0)
    sl = d.slide("수행 일정 — 12주, 관문 4개", notes="폭포수 모델로 관문마다 승인을 받습니다.")
    d.pic(sl, fig("f_gantt"), 0.6, 1.5, 12.1, 5.35)
    sl = d.slide("사업비 5,000만 원 (추정)", notes="견적 없는 추정치입니다.")
    d.pic(sl, fig("f_budget"), 0.6, 1.5, 6.0, 5.3)
    d.table(sl, 6.9, 1.5, 5.8, ["항목", "금액(만 원)"], [(b[0], f"{b[2] // 10000:,}") for b in P.BUDGET] + [("합계", f"{sum(b[2] for b in P.BUDGET) // 10000:,}")], [3.6, 2.2], 12, 0.5)
    sl = d.slide("위험 관리 — 최우선은 기존 설비 연동", notes="가능성과 영향을 곱해 우선순위를 정했습니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["ID", "위험", "가능성", "영향", "대응"], [(r[0], r[1], r[2], r[3], r[4]) for r in P.RISKS], [0.9, 3.8, 1.0, 0.9, 5.5], 10.5, 0.6)
    sl = d.slide("핵심 성과지표(KPI)", notes="성과는 이 지표로 측정합니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["지표", "목표", "측정 방법"], P.KPIS, [3.6, 4.2, 4.3], 12, 0.48)
    sl = d.slide("", dark=True, notes="제안을 마칩니다.")
    d.text(sl, 0.8, 2.0, 11.5, 0.8, "제안 요약", 32, True, BP.WHITE)
    lines = ["손 농사 6가지를 분석해 자동화 수준을 정하고, 양평 기후 위험에 맞춘 자동 제어·알림 시스템을 제안한다",
             "MVP 16건은 실장비 없이 시뮬레이터로 개발·검증, 확장 2건(육묘·수확 판별)은 다음 단계"]
    if SITE:
        lines.append("구현 결과 (로그인 없이 둘러보기): " + SITE + "/demo")
    if VIDEO:
        lines.append("시연 영상: " + VIDEO)
    if GITHUB:
        lines.append("소스 코드: " + GITHUB)
    d.text(sl, 0.8, 3.0, 11.5, 3.5, lines, 17, False, BP.MOSS)
    return d.save("01_시스템_제안서_v1.0.pptx")


if __name__ == "__main__":
    BP.OUTDIR = OUTDIR
    print(proposal_word())
    print(proposal_ppt())
