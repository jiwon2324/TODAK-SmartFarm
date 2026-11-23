# -*- coding: utf-8 -*-
"""
운영 이관 보고서 3종의 발표 자료(.pptx): 08 운영 매뉴얼 · 09 설치 보고서 · 11 바이브 코딩 기록.
01 시스템 제안서 발표 자료와 같은 디자인(build_ppt.Deck)을 쓰고, 표 내용은 원본 마크다운(docs/Operations/*.md)에서 그대로 읽는다.
  python3 tools/reports/build_ops_ppt.py [출력 폴더]
"""
import os
import re
import sys

# 공개 주소 (GitHub Pages 스냅샷 데모·시연 영상, GitHub 저장소) — build_ppt가 읽기 전에 정한다
os.environ.setdefault("TODAK_GITHUB_URL", "https://github.com/jiwon2324/TODAK-SmartFarm")
os.environ.setdefault("TODAK_SITE_URL", "https://jiwon2324.github.io/TODAK-SmartFarm/app")
os.environ.setdefault("TODAK_VIDEO_URL", "https://jiwon2324.github.io/TODAK-SmartFarm/Demo/")

sys.path.insert(0, os.path.dirname(__file__))
import brand  # noqa: E402
import build_ppt as BP  # noqa: E402
import evidence as E  # noqa: E402

E.VERSION = "v1.2.0"
# 표지 작성자 줄: 운영 이관 산출물은 기말고사 대체과제로 제출 (교수님 안내 2026-11)
brand.STUDENT_LINE = "한양여자대학교 · 2402180 양지원  |  데이터 기획 및 분석 · 1학기 기말고사 대체과제"
ROOT = E.ROOT
OPS = os.path.join(ROOT, "docs", "Operations")
SHOT = os.path.join(ROOT, "docs", "Test_Evidence", "install")
ARCH = os.path.join(ROOT, "docs", "Diagrams", "d_software_architecture_ops.png")
BRANCH = "https://github.com/jiwon2324/TODAK-SmartFarm/tree/ops-handover"
COURSE = "데이터 기획 및 분석 · 1학기 기말고사 대체과제"


def md_table(md, heading, nth=1):
    """마크다운에서 heading(앞부분 일치)으로 시작하는 절의 nth번째 표를 (헤더, 행)으로"""
    lines = open(os.path.join(OPS, md), encoding="utf-8").read().split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith("#") and l.lstrip("#").strip().startswith(heading))
    found = 0
    while i < len(lines):
        i += 1
        if lines[i].startswith("#"):
            raise KeyError(f"{md}: '{heading}' 아래 표 {nth} 없음")
        if lines[i].startswith("|"):
            found += 1
            buf = []
            while i < len(lines) and lines[i].startswith("|"):
                buf.append([c.strip().replace("`", "") for c in lines[i].strip().strip("|").split("|")])
                i += 1
            if found == nth:
                return buf[0], buf[2:]


def clip(rows, cols, n=80):
    return [tuple((r[c][:n] + "…") if len(r[c]) > n else r[c] for c in cols) for r in rows]


def links_slide(d, extra=None):
    """시스템 바로가기 — 누르면 바로 열리는 버튼 + 주소 표"""
    sl = d.slide("시스템 바로가기", "버튼을 누르면 바로 열립니다 (슬라이드 쇼에서도 클릭 가능)", notes="발표 중에 바로 열어 보여 줄 수 있는 주소입니다.")
    btns = [("▶  사이트 (로그인 없이)", os.environ["TODAK_SITE_URL"] + "/demo"), ("▶  시연 영상", os.environ["TODAK_VIDEO_URL"]),
            ("▶  GitHub 소스", os.environ["TODAK_GITHUB_URL"]), ("▶  운영 이관 변경분", BRANCH)]
    w = (12.1 - 0.25 * 3) / 4
    for i, (label, url) in enumerate(btns):
        BP.link_button(d, sl, 0.6 + i * (w + 0.25), 1.6, w, 0.62, label, url)
    rows = [("웹 사이트 — 로그인 없이 둘러보기 (스냅샷 데모)", os.environ["TODAK_SITE_URL"] + "/demo"),
            ("시연 영상 (4K, 약 4분 42초)", os.environ["TODAK_VIDEO_URL"]),
            ("소스 코드", os.environ["TODAK_GITHUB_URL"]),
            ("운영 이관 변경분 (운영 점검·통합 관제·GA4)", BRANCH),
            ("직접 실행 (실시간 동작)", "docker compose up -d → http://localhost:8088  (통합 관제 /monitor · 운영 점검 /admin/ops)")]
    rows += extra or []
    d.table(sl, 0.6, 2.5, 12.1, ["항목", "주소"], rows, [4.0, 8.1], 12, 0.5)
    d.text(sl, 0.6, 6.55, 12.1, 0.4, "스냅샷 데모는 기록한 응답을 재생하는 읽기 전용 화면입니다(제어·설정 변경 불가). 통합 관제·운영 점검 화면도 들어 있고, 실시간 경보 변화는 시연 영상 3:39부터 볼 수 있습니다.",
           10.5, False, BP.MUTED)


def agenda(d, items, notes):
    sl = d.slide("목차", notes=notes)
    half = (len(items) + 1) // 2
    for col, chunk in enumerate((items[:half], items[half:])):
        x = 0.6 + col * 6.15
        for k, (no, title, sub) in enumerate(chunk):
            y = 1.55 + k * 0.82
            d.card(sl, x, y, 5.9, 0.7)
            d.text(sl, x + 0.12, y + 0.14, 1.05, 0.45, no, 15 if len(no) > 2 else 18, True, BP.GREEN)
            d.text(sl, x + 1.2, y + 0.06, 4.6, 0.35, title, 15, True)
            d.text(sl, x + 1.2, y + 0.38, 4.6, 0.3, sub, 10, False, BP.MUTED)


def closing(d, title, lines, notes):
    sl = d.slide("", dark=True, notes=notes)
    d.text(sl, 0.8, 1.6, 11.5, 0.8, title, 32, True, BP.WHITE)
    d.text(sl, 0.8, 2.7, 11.5, 3.0, lines, 16, False, BP.MOSS)
    # 어두운 배경에서는 글자 링크가 짙은 파랑으로 바뀌어 안 보이므로, 누르면 열리는 초록 버튼으로
    for i, (label, url) in enumerate((("▶  사이트 (로그인 없이)", os.environ["TODAK_SITE_URL"] + "/demo"), ("▶  시연 영상", os.environ["TODAK_VIDEO_URL"]),
                                       ("▶  GitHub 소스", os.environ["TODAK_GITHUB_URL"]))):
        BP.link_button(d, sl, 0.8 + i * 3.9, 5.85, 3.6, 0.6, label, url)


def cover(d, title, sub, docid, notes):
    d.cover(title, sub, docid, notes)


# ---------------------------------------------------------------- 08 운영 매뉴얼
def manual_deck():
    M = "운영_매뉴얼.md"
    d = BP.Deck(f"TODAK 운영 매뉴얼 v1.0  |  {BP.TODAY}")
    cover(d, "방울토마토 스마트 농업 정보시스템\n운영 매뉴얼", "운영팀 이관 · 일일 점검 · 통합 관제 · 백업·복구 · 장애 대응 · GA4", "TODAK-OPS-001",
          "개발을 마친 TODAK 시스템을 운영팀이 넘겨받아 매일 같은 방법으로 점검하고, 장애가 나면 같은 순서로 대응하도록 만든 운영 매뉴얼입니다.")
    sl = d.slide("한 장 요약", "운영팀이 할 일은 세 가지로 줄어든다", notes="매일 운영 점검 화면을 보고, 근무 중에는 통합 관제를 띄워 두고, 판정이 바뀌면 매뉴얼의 절차 번호를 따라갑니다.")
    d.stats(sl, [("9개", "일일 점검 항목\n서버가 자동 판정"), ("5단계", "통합 관제 판정\n정상·주의·경보·끊김·값 없음"), ("1일 1회", "DB 백업 (04:00)\n7일 보관 + 외부 사본"), ("3등급", "장애 대응\n30분 · 4시간 · 다음 근무일")])
    d.text(sl, 0.6, 3.9, 12.1, 2.8, ["**매일 09:00** 관리자 → 운영 점검: 종합 판정 확인, 문제 항목은 화면에 나온 절차 번호(예: 매뉴얼 6.3)를 따라 조치, 점검표 CSV 보관",
                                     "**근무 중** 통합 관제(/monitor)를 전체 화면으로: 하우스 평면 위 센서 판정·장치 상태·실시간 이벤트",
                                     "**장애 시** 6장 공통 순서 → 증상별 절차 → 1·2등급은 장애 보고서",
                                     "**운영 시작 전** 비밀값·시드 계정 비밀번호 교체, HTTPS 적용 (11.1)"], 15)
    agenda(d, [("1", "개요", "목적·범위·독자·용어·참고 문서"), ("2", "시스템 구성", "아키텍처·주소·역할"), ("3", "운영 조직", "역할·장애 등급"),
               ("4", "일상 운영", "일일 점검·경보·주간 점검·통합 관제"), ("5", "데이터 관리", "백업·복구·보존"), ("6", "장애 대응", "MQTT·수집·센서·제어·재시작"),
               ("7~8", "사용자·설정 관리", "가입 승인·비밀번호·기준값 변경"), ("9~11", "GA4 · 업데이트 · 보안", "이용 통계·배포·보안 점검"),
               ("12", "맺음말", "문서 개정"), ("부록", "양식·명령", "점검표·장애 보고·명령")],
           "매뉴얼은 열두 개 장과 부록으로 되어 있습니다.")
    links_slide(d)
    sl = d.slide("목적과 적용 범위", "1장 개요", notes="운영팀이 넘겨받는 범위와 제외 범위입니다.")
    h, r = md_table(M, "1.2 적용 범위")
    d.table(sl, 0.6, 1.5, 12.1, h, r, [2.2, 9.9], 13, 0.75)
    h, r = md_table(M, "1.4 용어 정의")
    sl = d.slide("용어 정의", "1장 개요", notes="매뉴얼에 자주 나오는 용어입니다.")
    d.table(sl, 0.6, 1.5, 12.1, h, r, [3.0, 9.1], 12, 0.58)
    sl = d.slide("소프트웨어 아키텍처", "제출 PPT의 실제 구현 구성도 + 운영 이관 추가분(보라색)", notes="보라색이 이번 운영 이관에서 더한 통합 관제, 운영 점검, 백업 연결, GA4입니다.")
    d.pic(sl, ARCH, 0.6, 1.5, 12.1, 5.4)
    sl = d.slide("역할과 장애 등급", "3장 운영 조직과 연락 체계", notes="역할별 담당과 장애 등급별 대응 시간입니다.")
    h, r = md_table(M, "3. 운영 조직")
    d.table(sl, 0.6, 1.5, 12.1, h, r, [2.2, 6.4, 3.5], 12, 0.5)
    h, r = md_table(M, "3. 운영 조직", 2)
    d.table(sl, 0.6, 4.3, 12.1, h, r, [1.4, 5.6, 1.6, 3.5], 12, 0.55)
    sl = d.slide("일일 점검 — 9개 항목 자동 판정", "4.1 · 매일 09:00, 약 5분", notes="운영 점검 화면이 아홉 개 항목을 자동 판정합니다. 절차 칸의 번호가 매뉴얼 절 번호입니다.")
    h, r = md_table(M, "4.1 일일 점검")
    d.table(sl, 0.6, 1.5, 12.1, h, r, [2.6, 3.0, 2.4, 3.0, 1.1], 10.5, 0.5)
    sl = d.slide("운영 점검 화면 (SCR-A7)", "설치 직후 실제 화면 · 관리자 → 설정 → 운영 점검", notes="실제 화면입니다. 종합 판정, 서버 가동 시간, 마지막 백업, 디스크 여유가 맨 위에 있습니다.")
    d.pic(sl, os.path.join(SHOT, "ops_desk.png"), 0.6, 1.5, 12.1, 5.4)
    sl = d.slide("통합 관제 화면 (SCR-M1)", "4.4 · 근무 중 전체 화면으로 상시 표시", notes="PPT 배치도를 옮긴 하우스 평면 위에 센서 판정과 장치 상태, 실시간 이벤트를 보여 줍니다.")
    d.pic(sl, os.path.join(SHOT, "monitor_desk.png"), 0.6, 1.5, 7.4, 5.4)
    h, r = md_table(M, "4.4 통합 관제", 2)
    d.table(sl, 8.2, 1.5, 4.5, ["판정", "뜻", "할 일"], clip(r, (0, 2, 3), 46), [0.8, 2.2, 1.5], 9, 0.85)
    sl = d.slide("백업과 복구", "5장 데이터 관리", notes="매일 04시에 백업하고, 매월 한 번 임시 MySQL에 풀어 복구 시험을 합니다.")
    d.text(sl, 0.6, 1.5, 5.9, 4.9, ["**백업**: tools/backup-db.sh가 todak DB 전체를 backups/에 .sql.gz로, 7일 지난 파일 삭제",
                                   "**cron**: 매일 04:00 (보존 배치 03:00 이후)", "**외부 사본**: 주 1회 NAS·클라우드로 복사",
                                   "**복구**: 지금 상태 백업 → backend·simulator 중지 → 풀기 → 시작 → 운영 점검 재확인",
                                   "**복구 시험(매월)**: 임시 컨테이너에 풀어 건수 확인 — 설치 때 테이블 23개·측정값 22,231건 일치"], 13)
    d.card(sl, 6.8, 1.5, 5.9, 4.9)
    d.text(sl, 7.0, 1.65, 5.6, 4.6, ["crontab -e", "0 4 * * * /opt/TODAK-SmartFarm/tools/backup-db.sh \\", "  >> backups/backup.log 2>&1", "",
                                    "# 복구", "sh tools/backup-db.sh", "docker compose stop backend simulator", "gunzip -c backups/<파일>.sql.gz | \\",
                                    "  docker compose exec -T mysql sh -c 'mysql -uroot -p…'", "docker compose start backend simulator"], 11)
    sl = d.slide("장애 대응 — 증상별 절차", "6장 · 공통 순서: 운영 점검 → docker compose ps → 로그 → 절차 → 기록", notes="증상에 따라 해당 절로 갑니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["절", "증상", "확인", "조치"], [
        ("6.2", "MQTT 브로커 연결 끊김", "docker compose ps mosquitto · 로그", "mosquitto 재시작 → 안 되면 backend 재시작 (끊긴 동안 현장 안전 운전·재연결 후 재전송)"),
        ("6.3", "게이트웨이 오프라인·수집 중단", "게이트웨이 하트비트·simulator 로그", "B안: simulator 재시작 / A안: 현장 전원·LTE 확인, 농가 전화"),
        ("6.4", "센서 오류·이상치", "센서 수집 로그(수신률)", "3분 무수신이면 자동 FAULT → 수리 후 자동 복귀, 철거 시 '폐기'"),
        ("6.5", "제어 실패·응답 없음", "제어 명령 로그(FAILED·TIMEOUT)", "반복되면 수동 모드로 바꾸고 현장 확인, 안전 한계 장치는 1등급"),
        ("6.6", "서버 오류 로그", "로그 → 오류·예외", "반복 시 로그 저장 → GitHub 이슈로 개발 지원 요청"),
        ("6.7", "정전·재부팅", "docker compose ps", "docker compose up -d → 1~2분 뒤 운영 점검")], [0.7, 2.7, 3.1, 5.6], 11, 0.72)
    sl = d.slide("사용자·권한과 설정 변경", "7장 · 8장", notes="가입은 전화로 본인 확인 후 승인하고, 기준값은 농가와 함께 확인한 뒤 바꿉니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["업무", "방법"], [
        ("가입 승인 (7.1)", "사용자 관리 → 승인 대기 — 농가 담당이 전화로 본인 확인 후 역할·농장 지정"),
        ("비밀번호 초기화 (7.2)", "임시 비밀번호 → 발급 → 전화로 전달 (문자·메신저 금지), 첫 로그인 때 변경 강제"),
        ("잠금 해제 (7.3)", "5회 실패 10분 잠금, 급하면 '잠금 해제'"),
        ("권한 회수 (7.4)", "농장 배정 삭제 즉시 403, 퇴사자는 '사용 중지' (이력 보존)"),
        ("기준값·규칙 변경 (8장)", "농가와 값 확인 → 변경 → 게이트웨이 '기준값 v' 갱신 확인, 안전 한계는 한 번에 2℃ 이내, 모든 변경은 이력에 남음")], [3.0, 9.1], 13, 0.72)
    sl = d.slide("이용 통계 (GA4)", "9장 · 측정 ID를 넣고 프런트엔드를 다시 빌드하면 수집 시작", notes="아이디나 이름 같은 개인정보는 보내지 않고 역할만 보냅니다.")
    h, r = md_table(M, "9.2 수집하는")
    d.table(sl, 0.6, 1.5, 7.6, h, r, [2.3, 2.3, 3.0], 10.5, 0.46)
    d.card(sl, 8.5, 1.5, 4.2, 4.7)
    d.text(sl, 8.7, 1.65, 3.9, 4.4, ["**설정 순서**", "1. GA4 속성·웹 스트림 생성", "2. .env에 GA_MEASUREMENT_ID", "3. docker compose up -d --build frontend",
                                    "4. 운영 점검 화면 GA4 '수집 중' 확인", "5. 보관 14개월, Google 신호 끔", "", "**개인정보**", "아이디·이름·연락처·농장 이름 미전송", "개인정보처리방침 6항 고지"], 12)
    sl = d.slide("운영 시작 전 보안 점검", "11.1 · 반드시 할 일", notes="지금 설치는 HTTP라 인터넷 공개용이 아닙니다. 운영 전에 이 다섯 가지를 합니다.")
    d.text(sl, 0.6, 1.5, 12.1, 5.0, ["☐  .env 비밀값을 모두 무작위 값으로 교체 (openssl rand -base64 48)",
                                    "☐  시드 계정(admin·farmer01·farmer02·viewer01) 비밀번호 변경, 안 쓰는 계정 사용 중지",
                                    "☐  '로그인 없이 둘러보기'가 필요 없으면 DEMO_LOGIN_ID= (빈 값)",
                                    "☐  HTTPS 역방향 프록시(Caddy) + COOKIE_SECURE=true",
                                    "☐  방화벽: 8088(또는 443)만 공개, 8080·3307·1883은 내부망",
                                    "☐  임시 공개 터널(Cloudflare)은 시연용 — 운영에서는 끔"], 17)
    closing(d, "운영 매뉴얼 요약", ["매일: 운영 점검 화면 → 절차 번호대로 조치 → 점검표 보관",
                                  "근무 중: 통합 관제 화면 상시 표시", "장애: 6장 공통 순서 → 증상별 절차 → 장애 보고",
                                  "개정: 업데이트·장애 보고 때마다 매뉴얼과 화면 절차 번호를 함께 고친다"], "운영 매뉴얼을 마칩니다.")
    return d.save("08_운영_매뉴얼_v1.0.pptx")


# ---------------------------------------------------------------- 09 설치 보고서
def install_deck():
    M = "설치_보고서.md"
    d = BP.Deck(f"TODAK 설치 보고서 v1.0  |  {BP.TODAY}")
    cover(d, "방울토마토 스마트 농업 정보시스템\n설치 보고서", "깨끗한 환경에 v1.2.0 설치 · 설치 결과 확인 15항목 · 발견한 문제와 조치", "TODAK-INS-001",
          "운영팀 이관을 위해 깨끗한 환경에 시스템을 처음부터 설치하고, 실제 명령 출력으로 확인한 결과입니다.")
    sl = d.slide("한 장 요약", "설치 절차는 운영팀에 넘길 수 있는 상태", notes="한 번의 명령으로 1분 17초 만에 설치되었고, 확인 항목 15개 중 14개가 통과했습니다.")
    d.stats(sl, [("1분 17초", "docker compose up -d --build\n컨테이너 5개 기동"), ("14 / 15", "설치 확인 항목 통과\n(1개는 GA4 ID 미발급)"),
                 ("2건", "설치 중 찾은 결함\n수정 후 재확인"), ("22,231건", "백업 → 복구 시험\n측정값 그대로 복구")])
    d.text(sl, 0.6, 3.9, 12.1, 2.8, ["**어디에**: 개발 PC (Apple M3 Pro, macOS 15.5, Docker 29.7) — 기존 개발 DB와 분리한 새 프로젝트·새 볼륨",
                                     "**무엇을**: TODAK v1.2.0 = 커밋 366feb1 + 운영 이관 변경분(운영 점검·GA4·백업 연결·기동 순서 수정)",
                                     "**확인**: 상태 API·웹·로그인·스키마·수집·권한 차단·운영 점검·백업·복구·GA4 빌드",
                                     "**남은 일**: 운영 서버에서 같은 절차 반복, HTTPS·cron·GA4 측정 ID·시드 비밀번호"], 15)
    agenda(d, [("1", "개요", "목적·범위·참고 문서·요약"), ("2", "설치 환경", "하드웨어·OS·Docker"), ("3", "설치 구성", "컨테이너·포트·볼륨"),
               ("4", "사전 준비", "Docker·소스·포트·.env"), ("5", "설치 절차", "실제로 실행한 명령"), ("6", "설치 결과 확인", "15항목"),
               ("7", "발견한 문제와 조치", "결함 2건"), ("8", "남은 일과 제약", "운영 서버·HTTPS·GA4"), ("9", "인수인계", "서명"), ("10", "결론", "")],
           "보고서는 열 개 장입니다.")
    links_slide(d)
    sl = d.slide("설치 환경과 구성", "2장 · 3장", notes="개발 PC에 설치했고, 운영 서버 권장 사양은 2 vCPU, 4GB 메모리입니다.")
    h, r = md_table(M, "2. 설치 환경")
    d.table(sl, 0.6, 1.5, 5.6, h, r, [1.6, 4.0], 11, 0.5)
    h, r = md_table(M, "3. 설치 구성")
    d.table(sl, 6.5, 1.5, 6.2, h, r, [1.3, 2.0, 1.2, 1.7], 9.5, 0.62)
    d.text(sl, 0.6, 4.75, 5.6, 1.6, "운영 서버 권장(농장 1~2곳): 2 vCPU · 메모리 4GB · 디스크 40GB · Ubuntu 22.04 + Docker Compose v2", 11, False, BP.MUTED)
    sl = d.slide("소프트웨어 아키텍처", "설치한 시스템의 구성", notes="이번에 설치한 다섯 개 컨테이너와 운영 이관 추가분입니다.")
    d.pic(sl, ARCH, 0.6, 1.5, 12.1, 5.4)
    sl = d.slide("설치 절차 — 실제로 실행한 명령", "4장 사전 준비 · 5장 설치 절차", notes="비밀값을 무작위로 바꾼 뒤 명령 한 줄로 설치했습니다.")
    d.card(sl, 0.6, 1.5, 7.2, 4.9)
    d.text(sl, 0.8, 1.65, 6.9, 4.6, ["git clone https://github.com/jiwon2324/TODAK-SmartFarm.git", "cd TODAK-SmartFarm", "cp .env.example .env   # 비밀값 5개 무작위 교체",
                                    "docker compose up -d --build   # 1분 17초", "docker compose ps   # 5개 Up, backend·mysql healthy", "sh tools/backup-db.sh   # 첫 백업"], 12)
    d.text(sl, 8.1, 1.5, 4.6, 4.9, ["**기동 순서**", "mysql(healthy) → backend(healthy) → simulator", "frontend는 backend 시작 뒤", "",
                                   "**참고**", "이전 빌드의 Docker 층 캐시가 있어 1분 17초. 새 서버는 의존성 내려받기로 더 걸림(미측정)"], 13)
    h, r = md_table(M, "6. 설치 결과 확인")
    for part, chunk in ((1, r[:8]), (2, r[8:])):
        sl = d.slide(f"설치 결과 확인 ({part}/2)", "6장 · 실제 명령 출력으로 확인", notes="각 항목의 기대값과 실제 결과입니다.")
        d.table(sl, 0.6, 1.5, 12.1, ["#", "확인 항목", "기대", "결과", "판정"], clip(chunk, (0, 1, 3, 4, 5), 70), [0.5, 2.4, 3.2, 5.0, 1.0], 10.5, 0.6)
    sl = d.slide("설치 직후 운영 점검 화면", "확인 #14 · 정상 8 · 확인 1 (미해결 경보 7건은 시뮬레이터 과거 데이터 경보)", notes="수정 뒤 운영 점검 결과입니다.")
    d.pic(sl, os.path.join(SHOT, "ops_desk.png"), 0.6, 1.5, 12.1, 5.4)
    sl = d.slide("설치 중 발견한 문제와 조치", "7장 · 시험은 모두 통과하던 상태에서 설치로 찾은 결함", notes="기동 순서 문제와 미개통 게이트웨이 판정 문제를 고쳤습니다.")
    h, r = md_table(M, "7. 설치 중")
    d.table(sl, 0.6, 1.5, 12.1, h, clip(r, range(5), 90), [0.5, 2.8, 3.3, 3.3, 2.2], 10.5, 1.2)
    sl = d.slide("남은 일과 제약", "8장", notes="운영 서버에서 다시 설치하고 HTTPS, cron, GA4, 시드 비밀번호를 마쳐야 합니다.")
    h, r = md_table(M, "8. 남은 일")
    d.table(sl, 0.6, 1.5, 12.1, h, clip(r, range(3), 80), [2.6, 4.7, 4.8], 11, 0.62)
    sl = d.slide("인수인계", "9장 · 서명을 받아야 운영 이관 완료", notes="설치자, 인수자, 승인자의 확인을 받습니다.")
    h, r = md_table(M, "9. 인수인계")
    d.table(sl, 0.6, 1.5, 12.1, h, r, [1.2, 1.6, 1.8, 4.3, 1.6, 1.6], 13, 0.7)
    d.text(sl, 0.6, 4.6, 12.1, 1.2, "전달물: 운영 매뉴얼 v1.0, 설치 보고서 v1.0, 소프트웨어 아키텍처 그림, .env 비밀값(별도 안전한 경로 — 문서·메신저에 적지 않음), 관리자 계정", 13)
    closing(d, "결론", ["명령 한 번으로 1분 17초에 설치, 확인 15항목 중 14개 통과 (GA4는 ID 미발급)",
                       "설치로만 보이던 결함 2건을 찾아 고침, 백업 → 복구로 데이터 그대로 확인",
                       "→ 설치 절차는 운영팀에 넘길 수 있는 상태",
                       "다음: 운영 서버에서 재설치 · HTTPS · cron · GA4 · 시드 비밀번호 → 인수인계 서명"], "설치 보고를 마칩니다.")
    return d.save("09_설치_보고서_v1.0.pptx")


# ---------------------------------------------------------------- 11 바이브 코딩
def vibe_deck():
    M = "바이브코딩_관제_소프트웨어.md"
    d = BP.Deck(f"TODAK 바이브 코딩 기록 v1.0  |  {BP.TODAY}")
    cover(d, "바이브 코딩으로\n스마트팜 관제 소프트웨어 만들기", "일단 시작 · 그런데 궁금한 것 — 어떤 Framework을 사용하는 것일까?", "TODAK-VIB-001",
          "메모의 바이브 코딩 항목을 실제로 해 본 기록입니다. 무엇을 만들었고, 어떻게 진행했고, 어떤 프레임워크를 쓰는지 답합니다.")
    sl = d.slide("한 장 요약", notes="PPT 배치도 위에 실시간 판정을 겹친 관제 화면을 만들었고, 새 프레임워크 없이 기존 구조 위에 지었습니다.")
    d.stats(sl, [("1개 화면", "통합 관제 /monitor\nSCR-M1"), ("571줄", "화면 320 · 좌표 47\nAPI 204"), ("5건", "관제 시험 추가\n(백엔드 2 · 화면 3)"), ("0개", "새로 넣은 Framework\n(기존 구조 재사용)")])
    d.text(sl, 0.6, 3.9, 12.1, 2.8, ["**만든 것**: 하우스 평면(PPT 배치도) 위에 센서 판정·장치 상태·이벤트를 실시간 표시하는 관제 소프트웨어",
                                     "**어떻게**: 말로 범위를 정하고 AI(Claude Code)가 코드를 씀 → 사람이 시험·설치·화면으로 확인",
                                     "**Framework**: 화면 React(+TS·Tailwind) · 서버 Spring Boot(+Security·JPA·SSE) · 통신 MQTT(Mosquitto·Paho)",
                                     "**알게 된 것**: 결과를 확인하는 단계에서 AI 문구 오류·기동 순서 결함·겹친 글자를 찾음"], 15)
    agenda(d, [("1", "개요", "목적·구성·바로가기"), ("2", "만든 것", "스마트팜 관제 소프트웨어"), ("3", "바이브 코딩으로 시작", "진행 순서·확인·알게 된 점"),
               ("4", "어떤 Framework?", "계층별 기술·데이터 흐름·바뀐 선택"), ("5", "다음에 궁금한 것", ""), ("6", "결론", "")], "여섯 개 장입니다.")
    links_slide(d, [("관제 화면 코드", "https://github.com/jiwon2324/TODAK-SmartFarm/blob/ops-handover/frontend/src/pages/monitor/Monitor.tsx")])
    sl = d.slide("만든 것 — 통합 관제 화면", "2장 · PPT 센서·제어장치 배치도 위에 실시간 판정", notes="센서는 판정 색과 현재 값, 장치는 작동 상태, 오른쪽은 실시간 이벤트입니다.")
    d.pic(sl, os.path.join(SHOT, "monitor_desk.png"), 0.6, 1.5, 12.1, 5.4)
    sl = d.slide("바이브 코딩으로 시작하기 — 실제 진행 순서", "3장 · 사람은 무엇을 만들지 정하고 결과를 확인, AI는 코드를 씀", notes="메모 사진에서 시작해 PPT를 기준으로 삼고, 구현, 시험, 화면 확인, 시나리오 시험까지 진행했습니다.")
    h, r = md_table(M, "3.2 실제 진행")
    d.table(sl, 0.6, 1.5, 12.1, h, clip(r, range(4), 62), [1.6, 3.6, 4.0, 2.9], 9.5, 0.6)
    sl = d.slide("해 보니 알게 된 것", "3.3", notes="AI가 쓴 글과 코드는 반드시 확인해야 했습니다.")
    cards = [("AI가 쓴 글도 코드와 대조", "매뉴얼 초안의 '점검 중 상태', '변경 사유 입력'은 실제 화면에 없었다 → 코드를 보고 고침"),
             ("직접 설치해 봐야 보이는 결함", "시험은 모두 통과했지만 새 설치에서 기동 순서 결함·미개통 게이트웨이 오판정 발견"),
             ("화면은 눈으로", "시험 통과 후에도 브라우저에서 온도·습도 값 상자가 겹친 것을 발견 → 좌표 수정"),
             ("결정은 사람이", "범위, 기준 PPT, 기말고사 대체과제 표기, 커밋 시점은 모두 사람이 정함")]
    for i, (hd, body) in enumerate(cards):
        x = 0.6 + (i % 2) * 6.15
        y = 1.5 + (i // 2) * 2.6
        d.card(sl, x, y, 5.9, 2.4)
        d.text(sl, x + 0.2, y + 0.12, 5.5, 0.5, hd, 16, True, BP.GREEN)
        d.text(sl, x + 0.2, y + 0.7, 5.5, 1.6, body, 13)
    sl = d.slide("어떤 Framework을 사용하는 것일까?", "4.1 Framework와 라이브러리", notes="프레임워크는 뼈대와 흐름을 정해 주고, 라이브러리는 필요할 때 불러 씁니다.")
    for i, (hd, body) in enumerate([("Framework", ["프로그램의 뼈대와 실행 흐름을 정해 준다", "개발자는 정해진 자리에 코드를 끼워 넣는다", "예: Spring Boot가 요청을 받으면 MonitorController.monitor()를 불러 준다"]),
                                    ("라이브러리", ["필요할 때 우리 코드가 불러 쓰는 도구 묶음", "", "예: Recharts(그래프), Paho(MQTT 통신), lucide-react(아이콘)"])]):
        x = 0.6 + i * 6.15
        d.card(sl, x, 1.6, 5.9, 4.6)
        d.text(sl, x + 0.25, 1.8, 5.4, 0.6, hd, 22, True, BP.GREEN)
        d.text(sl, x + 0.25, 2.6, 5.4, 3.4, body, 15)
    h, r = md_table(M, "4.2 계층별")
    for part, chunk in ((1, r[:10]), (2, r[10:])):
        sl = d.slide(f"계층별로 쓰는 것 ({part}/2)", "4.2", notes="계층별 기술과 버전, 관제에서 쓰인 곳입니다.")
        d.table(sl, 0.6, 1.5, 12.1, ["계층", "이름", "버전", "종류", "관제에서 쓰인 곳"], clip(chunk, (0, 1, 2, 3, 5), 48), [0.9, 2.6, 1.4, 2.6, 4.6], 10.5, 0.47)
    sl = d.slide("관제 화면이 한 번 갱신될 때 거치는 길", "4.3", notes="센서 값이 시뮬레이터에서 브라우저까지 오는 경로입니다.")
    steps = [("Python · paho-mqtt", "시뮬레이터가 1분마다\nMQTT로 측정값 송신"), ("Mosquitto", "브로커가\n서버로 전달"), ("Spring Boot · Paho · JPA", "검증 후\nMySQL에 저장"),
             ("SseEmitter", "브라우저로\nreading 이벤트"), ("React · EventSource", "평면 위 값\n즉시 변경"), ("MonitorController", "3초 뒤 판정\n다시 받아 색 갱신")]
    w = 12.1 / len(steps)
    for i, (t, s) in enumerate(steps):
        x = 0.6 + i * w
        d.card(sl, x, 2.2, w - 0.25, 2.6)
        d.text(sl, x + 0.1, 2.35, w - 0.45, 0.4, str(i + 1), 22, True, BP.GREEN)
        d.text(sl, x + 0.1, 2.95, w - 0.45, 0.8, t, 12, True)
        d.text(sl, x + 0.1, 3.75, w - 0.45, 1.0, s, 11, False, BP.MUTED)
    d.text(sl, 0.6, 5.2, 12.1, 1.0, "판정은 서버 한 곳(MonitorController)에서만 — 자동 제어·경보와 같은 기준(재배 기준값·안전 한계 CR-05·06)", 14)
    sl = d.slide("계획서와 달라진 선택, 새 Framework을 넣지 않은 이유", "4.4 · 4.5", notes="계획서 대비 바뀐 기술과, 관제에 새 프레임워크를 넣지 않은 이유입니다.")
    h, r = md_table(M, "4.4 계획서")
    d.table(sl, 0.6, 1.5, 12.1, h, r, [1.6, 2.6, 3.0, 4.9], 11, 0.55)
    d.text(sl, 0.6, 4.6, 12.1, 2.0, ["**평면도는 SVG로 직접** — 배치 좌표 22개면 충분, 의존성 0", "**실시간은 기존 SSE 재사용** — 서버→화면 한 방향이면 WebSocket 불필요",
                                    "**판정은 서버 한 곳에서** — 관제와 자동 제어가 다른 기준을 쓰지 않게"], 14)
    sl = d.slide("다음에 궁금한 것", "5장", notes="실장비, 농장 증가, 사용량, 휴대폰 알림이 다음 질문입니다.")
    h, r = md_table(M, "5. 다음")
    d.table(sl, 0.6, 1.5, 12.1, h, r, [3.6, 4.0, 4.5], 12, 0.75)
    closing(d, "결론", ["관제 소프트웨어는 PPT의 요구사항·배치도를 근거로 통합 관제 화면 + 관제 API로 완성",
                       "바이브 코딩에서 효과가 컸던 것은 사람이 범위를 정하고 결과를 확인한 단계",
                       "Framework 답: 화면 React · 서버 Spring Boot · 통신 MQTT — 관제는 새 Framework 없이 기존 구조 위에"], "바이브 코딩 기록을 마칩니다.")
    return d.save("11_바이브코딩_관제소프트웨어_v1.0.pptx")



# ---------------------------------------------------------------- 13 운영 이관 기획서
def plan_deck():
    M = "운영이관_기획서.md"
    DG = os.path.join(ROOT, "docs", "Diagrams")
    d = BP.Deck(f"TODAK 운영 이관 기획서 v1.0  |  {BP.TODAY}")
    cover(d, "방울토마토 스마트 농업 정보시스템\n운영 이관 기획서", "문제 정의 → 현황 분석 → 목표 → 해결안 → 실행 계획 → 검증 (12주차 '기획이란 무엇인가')",
          "TODAK-PLN-001", "12주차 강의의 기획 여섯 단계와 기획서 아홉 항목에 맞춰, 운영팀 이관 작업을 기획서로 정리했습니다.")
    sl = d.slide("한 장 요약", "왜 · 무엇을 · 얼마나 · 언제까지", notes="강의에서 말한 한 장 요약입니다. 이 장만 읽어도 왜, 무엇을, 얼마나, 언제까지를 알 수 있게 했습니다.")
    d.stats(sl, [("5가지", "해결안\n관제·점검·GA4·매뉴얼·설치"), ("6 / 7", "KPI 달성\n(GA4 실제 수집 보류)"), ("3일", "기획→구현→검증 반복\n11-16 ~ 11-18"), ("0개", "새 Framework\n기존 구조 위에")])
    h, r = md_table(M, "한 장 요약")
    d.table(sl, 0.6, 3.8, 12.1, h, clip(r[:4], (0, 1), 150), [1.6, 10.5], 10.5, 0.62)
    agenda(d, [("①", "문제 정의", "증상과 원인 · 5 Whys · 로직 트리"), ("②", "현황 분석", "As-Is·To-Be · 5W1H · SWOT · 사용자"),
               ("③", "목표 설정", "SMART · KPI 7개와 결과"), ("④", "해결안", "범위(In/Out) · 대안 비교"),
               ("⑤", "실행 계획", "데이터와 지표 · WBS·간트"), ("⑥", "검증", "리스크(가능성×영향) · 검증 방법"),
               ("+", "기말 과제 관점", "대시보드 · 코드 관리 · 유지 운영"), ("+", "기획과 AI", "바이브 코딩 · R-C-T-F · 역할")],
           "강의의 여섯 단계 순서로 진행합니다.")
    links_slide(d, [("통합 관제 (공개 데모)", "https://jiwon2324.github.io/TODAK-SmartFarm/app/monitor")])
    sl = d.slide("① 문제 정의 — 증상이 아니라 원인", "5 Whys", notes="증상은 '어떻게 넘기지'였고, 다섯 번 왜를 물어 원인까지 내려갔습니다.")
    h, r = md_table(M, "2.2 5 Whys")
    d.table(sl, 0.6, 1.5, 12.1, h, r, [0.7, 4.6, 6.8], 11.5, 0.62)
    sl = d.slide("① 문제 정의 — 로직 트리 (MECE)", "보기 · 판단 · 행동 · 근거 네 갈래", notes="원인을 빠짐없이, 겹치지 않게 네 갈래로 나누고 갈래마다 해결안을 하나씩 붙였습니다.")
    d.pic(sl, os.path.join(DG, "d_plan_logic_tree.png"), 0.6, 1.5, 12.1, 5.4)
    sl = d.slide("② 현황 분석 — As-Is와 To-Be", "현재를 데이터로 알고, 목표를 정하고, 사이를 메운다", notes="이관 전 커밋과 이관 후 병합 커밋을 기준으로 비교했습니다.")
    d.pic(sl, os.path.join(DG, "d_plan_asis_tobe.png"), 0.6, 1.5, 12.1, 5.4)
    sl = d.slide("② 현황 분석 — 5W1H와 SWOT", notes="빠진 정보가 없는지 5W1H로, 내부와 외부 환경은 SWOT으로 정리했습니다.")
    h, r = md_table(M, "3.2 5W1H")
    d.table(sl, 0.6, 1.5, 5.8, h, r, [1.4, 4.4], 10, 0.55)
    h, r = md_table(M, "3.3 SWOT")
    d.table(sl, 6.7, 1.5, 6.0, ["", "도움", "해"], clip(r, (0, 1, 2), 90), [0.9, 2.55, 2.55], 9.5, 1.5)
    sl = d.slide("② 현황 분석 — 대상과 사용자", "누가, 어떤 상황에서, 무엇이 필요한가", notes="운영 관리자, 시스템 담당, 농가, 검수자 네 사용자의 상황과 필요를 정리했습니다.")
    h, r = md_table(M, "3.4 대상과 사용자")
    d.table(sl, 0.6, 1.5, 12.1, h, r, [2.2, 4.8, 5.1], 12, 0.7)
    sl = d.slide("③ 목표 — SMART와 KPI", "KPI 7개 중 6개 달성, 1개 보류", notes="목표를 숫자로 잴 수 있는 지표로 바꾸고, 실제 결과로 확인했습니다. GA4 실제 수집만 측정 아이디가 없어 보류입니다.")
    h, r = md_table(M, "4.2 KPI")
    d.table(sl, 0.6, 1.5, 12.1, ["#", "지표", "목표값", "실제 결과", "판정"], clip(r, (0, 1, 2, 4, 5), 60), [0.5, 3.0, 2.7, 4.9, 1.0], 10.5, 0.6)
    sl = d.slide("④ 범위와 해결안", "포함·제외, 대안 비교와 선택 이유", notes="하지 않을 것을 정하는 것도 기획입니다. 대안마다 선택 이유를 적었습니다.")
    h, r = md_table(M, "6. 해결안")
    d.table(sl, 0.6, 1.5, 12.1, ["문제", "대안", "선택", "이유"], clip(r, (0, 1, 2, 3), 70), [1.7, 4.0, 0.8, 5.6], 9.5, 0.68)
    h, r = md_table(M, "5. 범위")
    d.text(sl, 0.6, 6.25, 12.1, 0.6, "제외(Out): " + " · ".join(x[1] for x in r), 10, False, BP.MUTED)
    sl = d.slide("⑤ 실행 계획 — WBS · 간트 차트", "실제 수행 일정 (Git 커밋 시각 기준)", notes="작업을 열한 개로 쪼개고 실제 날짜 위에 올렸습니다.")
    d.pic(sl, os.path.join(DG, "d_plan_gantt.png"), 0.6, 1.5, 12.1, 5.4)
    sl = d.slide("⑥ 리스크와 검증", "기획은 가설 — 틀릴 수 있다고 전제하고 확인", notes="가능성과 영향을 곱해 우선순위를 정했고, 실제로 일어난 위험은 확인 단계에서 찾아 고쳤습니다.")
    h, r = md_table(M, "9.1 리스크")
    d.table(sl, 0.6, 1.5, 12.1, ["ID", "위험", "점수", "대응", "실제"], clip(r, (0, 1, 4, 5, 6), 52), [0.9, 3.3, 0.8, 3.4, 3.7], 9.5, 0.58)
    sl = d.slide("기말 과제 관점 — 대시보드와 코드 관리", "강의 25쪽의 네 가지 질문", notes="대시보드는 질문에서 지표를 골랐고, 코드는 Git 브랜치와 커밋으로 관리했습니다.")
    h, r = md_table(M, "11. 대시보드")
    d.table(sl, 0.6, 1.5, 12.1, h, r, [2.8, 9.3], 11.5, 0.95)
    sl = d.slide("기획과 AI — 바이브 코딩과 R-C-T-F", "기획이 분명할수록 결과도 분명", notes="기획을 글로 정리해 AI에게 지시하고, 결과를 검증하고, 기획을 고쳐 다시 지시했습니다.")
    h, r = md_table(M, "12.2 R-C-T-F")
    d.table(sl, 0.6, 1.5, 12.1, h, r, [1.6, 3.2, 7.3], 11, 0.6)
    h, r = md_table(M, "12.3 사람과 AI")
    d.table(sl, 0.6, 4.75, 12.1, h, r, [6.05, 6.05], 10.5, 0.75)
    sl = d.slide("중간 과제를 기획서로 읽기", "강의 24쪽의 여섯 질문과 답이 있는 곳", notes="중간고사 대체 과제 문서에서 여섯 질문의 답이 어디 있는지 찾아 정리했습니다.")
    h, r = md_table(M, "13. 중간 과제")
    d.table(sl, 0.6, 1.5, 12.1, h, r, [3.4, 8.7], 11, 0.72)
    closing(d, "결론", ["증상(어떻게 넘기지?) → 원인 네 갈래(보기·판단·행동·근거) → 해결안 다섯 가지",
                       "KPI 7개 중 6개를 실제 결과로 확인, GA4 실제 수집은 측정 ID 발급 후",
                       "결과의 품질은 확인 단계에서 갈렸다 — AI 문구 오류·설치 결함·깨질 뻔한 링크",
                       "다음: 운영 1개월 지표(가동률·기준 이탈 시간·노동 시간) → 다음 기획의 As-Is"], "운영 이관 기획을 마칩니다.")
    return d.save("13_운영이관_기획서_v1.0.pptx")


if __name__ == "__main__":
    BP.OUTDIR = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(ROOT, ".."))
    print(manual_deck())
    print(install_deck())
    print(vibe_deck())
    print(plan_deck())
