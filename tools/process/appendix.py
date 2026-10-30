"""
01~04 보고서 공통 부록: 과제 진행 과정 · 프롬프트 스크립트 · 중간 산출물 · GitHub 이력
프롬프트 원문은 tools/process/extract_prompts.py가 과제 폴더에 만든 프롬프트_기록/prompts.json에서 읽는다.
  docx_appendix(d, "부록 D")      # Doc(docgen) 객체
  ppt_appendix(slide, table)
"""
import json
import os
import subprocess

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROMPTS = os.environ.get("TODAK_PROMPTS", os.path.join(os.path.dirname(ROOT), "프롬프트_기록", "prompts.json"))
GITHUB = os.environ.get("TODAK_GITHUB_URL")
LONG = 1500  # 이보다 긴 프롬프트(붙여 넣은 지시서)는 표에서 빼고 전문을 따로 싣는다

# 진행 단계: (단계, 시작 시각, 학생이 요청한 것, 나온 산출물)
STAGES = [
    ("1. 과제 이해·아이디어", "2026-10-26 10:12", "과제 안내 사진을 보여 주고 작성 순서, 쉬운 용어, 다이어그램 종류, 테이블 정의서, 프로젝트 이름을 물음",
     "개발 계획서 초안 · 시퀀스 다이어그램 · 이름(TODAK) 아이디어"),
    ("2. 계획서 초안 검토", "2026-10-26 11:32", "계획서 초안 문서 화면에 댓글로 확인·수정 요청", "계획서 초안 수정본"),
    ("3. 프로젝트 지시서", "2026-10-26 11:56", "직접 준비한 『프로젝트 지시서』와 기존 산출물(docx)을 붙여 넣고 실무 수준 산출물 요청",
     "00 기존산출물 검토결과서 · 02 개발 계획서 v2.0 · 다이어그램 · 테이블 정의서"),
    ("4. 후속 개발 지시서 · 구현", "2026-10-26 14:23", "『후속 개발 지시서』로 실제 실행되는 웹 시스템(DB·JWT·대시보드·GitHub)과 보고서 연계 요청",
     "백엔드 · 프런트엔드 · 시뮬레이터 · Docker · 03·04 보고서 v1.0"),
    ("5. GitHub 업로드", "2026-10-27 12:01", "터미널에서 docker·git 명령을 직접 실행하고 GitHub 계정으로 로그인", "공개 저장소 jiwon2324/TODAK-SmartFarm"),
    ("6. 실제 데이터 · 공개 접속", "2026-10-27 18:30", "가상 데이터를 실제 자료로 바꾸는 방법, 기상청 로그인 후 양평 실측 반영, 인터넷 주소와 고화질 시연 영상 요청",
     "기상청 ASOS 양평 실측 반영 · 로그인 없이 둘러보기 · 시연 영상"),
    ("7. 검증 · 완성도", "2026-10-27 21:18", "ERD·테이블 정의서 대조, 앱 로고, UI/UX 가이드 확인, PPT 안 링크, 영상 화질·자막 개선 요청",
     "실제 DB에서 만든 테이블 정의서·ERD · 앱 로고 · 4K 영상 · 아이콘 정리"),
    ("8. 제출 전 점검", "2026-10-27 23:17", "과제 항목별 대조, 생성형 AI 활용 표기, 영상을 GitHub Pages로", "01~04 과제 대조표 · 시연 영상 페이지"),
    ("9. 상시 데모 · 재제출", "2026-10-28 10:54", "맥북을 꺼도 교수님이 열 수 있는 사이트 요청", "GitHub Pages 스냅샷 데모"),
    ("10. 공지 반영", "2026-10-30 14:38", "프롬프트 스크립트와 중간 산출물을 보고서에 넣으라는 공지 반영 요청", "이 부록"),
]


def load():
    rows = json.load(open(PROMPTS, encoding="utf-8"))
    prompts = [r for r in rows if r["kind"] == "prompt"]
    for i, r in enumerate(prompts, 1):
        r["no"] = f"P{i:02d}"
    cmds, seen = [], set()
    for r in rows:
        if r["kind"] == "command" and r["text"] not in seen:
            seen.add(r["text"]); cmds.append(r)
    return prompts, cmds


def long_title(r):
    first = next((l.strip("# ").strip() for l in r["text"].splitlines() if l.startswith("#")), "붙여 넣은 지시서")
    return first


def shown(r, limit=None):
    """표에 넣을 프롬프트 문구 (긴 지시서는 제목과 글자 수만)"""
    t = r["text"]
    if len(t) > LONG:
        head = t[: t.find("#")].strip() if "#" in t else ""
        return (head + "\n" if head else "") + f"[붙여 넣은 지시서 『{long_title(r)}』 {len(t):,}자 — 전문은 아래 절]"
    if r.get("images"):
        t += f"  (사진 {r['images']}장 첨부)"
    if limit and len(t) > limit:
        t = t[:limit].rstrip() + "…"
    return t


def git_log():
    out = subprocess.run(["git", "-C", ROOT, "log", "--reverse", "--date=format:%m-%d %H:%M", "--format=%h|%ad|%s"],
                         capture_output=True, text=True, check=True).stdout
    return [tuple(l.split("|", 2)) for l in out.strip().splitlines()]


def count(rel):
    return sum(len(f) for _, _, f in os.walk(os.path.join(ROOT, rel)))


def artifacts():
    return [
        ("과제 문서", "00 기존산출물 검토결과서 · 01 시스템 제안서 v1.0 · 02 개발 계획서 v2.0 · 03 개발 보고서 v1.0 · 04 개발 완료 보고서 v1.0 (Word·PPT·PDF), 05 통합 구축 보고서(참고용)", "과제 폴더 · PDF 폴더"),
        ("요구사항 · 추적", "요구사항 25건(기능 18 · 비기능 7), 요구사항 추적표, 계획서 대비 구현 검토서", "docs/RTM.md · docs/Development_Plan"),
        ("설계 그림", f"시스템 구성도 · ERD · 시퀀스 · 유스케이스 · 화면 구조도 등 {count('docs/Diagrams')}개 파일", "docs/Diagrams"),
        ("데이터베이스", "테이블 정의서(실제 DB 22개 테이블), 스키마·시드·변경 SQL(Flyway V1~V3)", "docs/Database · backend/src/main/resources/db/migration"),
        ("소스 코드", "백엔드(Spring Boot·Java 21) · 프런트엔드(React·TypeScript) · 시뮬레이터(Python) · 인프라(Docker·MQTT)", "backend · frontend · simulator · infra"),
        ("시험 증빙", f"실행 화면 캡처 · E2E · 시나리오 · 성능 · DB 조회 결과 {count('docs/Test_Evidence')}개 파일", "docs/Test_Evidence"),
        ("디자인", "TODAK 앱 로고 · 아이콘 · 글자 로고", "docs/brand"),
        ("시연 영상 · 데모", "4K 시연 영상 페이지, 항상 열리는 스냅샷 데모 사이트", "docs/Demo · docs/app (GitHub Pages)"),
        ("만드는 도구", "보고서·PPT 생성, 증빙 수집, 화면 캡처, 영상 녹화, 스냅샷 기록 스크립트", "tools"),
        ("프롬프트 기록", "이 부록의 프롬프트 원문 (세션 기록에서 추출)", "과제 폴더 프롬프트_기록 (공개 저장소에는 올리지 않음)"),
    ]


def docx_appendix(d, label):
    prompts, cmds = load()
    log = git_log()
    d.h(f"{label}. 과제 진행 과정 · 프롬프트 스크립트 · 중간 산출물", 1)
    d.p(f"이 과제는 생성형 AI(Claude Code, Claude 데스크톱 앱)와 대화하며 진행했다. 학생이 요청(프롬프트)을 입력하면 AI가 문서·그림·소스 코드를 만들고, "
        f"학생이 결과를 열어 보고 다시 요청하는 과정을 반복했다. 기간은 {prompts[0]['time'][:10]} ~ {prompts[-1]['time'][:10]}이며, "
        f"학생이 입력한 프롬프트 {len(prompts)}건과 직접 실행한 터미널 명령 {len(cmds)}건, GitHub 커밋 {len(log)}건이 남아 있다.")
    d.h(f"{label}.1 진행 단계", 2)
    d.table(["단계", "시작", "학생이 요청한 것", "나온 산출물"], [(s[0], s[1][5:], s[2], s[3]) for s in STAGES], [3, 2.2, 6.4, 5],
            caption="과제 진행 단계", size=8, fixed=True)
    d.p("학생이 직접 한 일: 과제 조건·사진 제공, 지시서 작성, 결과 확인과 수정 요청, 기상청 로그인과 자료 선택, GitHub 계정 로그인·공개 결정, 터미널 명령 실행, 최종 제출 파일 선택.", size=9)

    d.h(f"{label}.2 프롬프트 스크립트 (입력 순서 그대로)", 2)
    d.p("세션 기록에서 학생이 입력한 문장만 뽑아 고치지 않고 그대로 실었다(오타 포함). '다시 시도해 주세요'는 응답이 끊겨 다시 요청한 것이고, [문서 댓글]은 AI가 만든 문서 화면에 단 댓글이다. 사용자 폴더 경로는 ~로 줄였다.", size=9)
    d.table(["번호", "시각", "프롬프트"], [(r["no"], r["time"][5:], shown(r)) for r in prompts], [1.3, 2.2, 13.1], caption="프롬프트 스크립트", size=8, fixed=True)

    longs = [r for r in prompts if len(r["text"]) > LONG]
    if longs:
        d.h(f"{label}.3 붙여 넣은 지시서 전문", 2)
        for r in longs:
            d.p(f"{r['no']} ({r['time']}) 『{long_title(r)}』", bold=True)
            for line in r["text"].splitlines():
                s = line.strip()
                if not s or s == "---":
                    continue
                if s.startswith("#"):
                    d.p(s.lstrip("# "), bold=True, size=9.5)
                else:
                    d.p(s.replace("**", ""), size=8.5)

    d.h(f"{label}.4 학생이 직접 실행한 터미널 명령", 2)
    d.table(["시각", "명령"], [(c["time"][5:], c["text"]) for c in cmds], [2.2, 14.4], caption="직접 실행한 명령 (같은 명령 반복은 한 번만)", size=7.5, fixed=True)

    d.h(f"{label}.5 중간 산출물", 2)
    d.table(["구분", "산출물", "위치"], artifacts(), [2.6, 8.6, 5.4], caption="중간 산출물 목록", size=8, first_col_bold=True, fixed=True)

    d.h(f"{label}.6 GitHub 소스 관리 이력", 2)
    d.p(f"저장소: {GITHUB}" if GITHUB else "저장소: 로컬 Git", size=9)
    d.p("소스 코드와 문서·그림·증빙을 한 저장소에서 관리했다. 작업 단위마다 커밋해 언제 무엇이 바뀌었는지 남겼다(커밋 메시지 그대로).", size=9)
    d.table(["커밋", "시각", "내용"], log, [1.7, 2.2, 12.7], caption=f"커밋 이력 ({len(log)}건)", size=7.5, fixed=True)


def ppt_appendix(slide, table):
    """slide(title, sub, notes) · table(sl, x, y, w, headers, rows, widths, size, rowh)"""
    prompts, cmds = load()
    log = git_log()
    sl = slide("부록 · 과제 진행 과정 (생성형 AI 활용)", f"프롬프트 {len(prompts)}건 · 직접 실행한 명령 {len(cmds)}건 · GitHub 커밋 {len(log)}건 · 전문은 Word 보고서 부록",
               "교수님 공지에 따라 과제를 어떤 과정으로 만들었는지, 입력한 프롬프트와 중간 산출물을 정리했습니다.")
    table(sl, 0.6, 1.55, 12.1, ["단계", "시작", "요청한 것", "나온 산출물"], [(s[0], s[1][5:], s[2], s[3]) for s in STAGES], [2.3, 1.4, 5, 3.4], 9, 0.47)
    per = 10
    chunks = [prompts[i:i + per] for i in range(0, len(prompts), per)]
    for k, ch in enumerate(chunks, 1):
        sl = slide(f"부록 · 프롬프트 스크립트 ({k}/{len(chunks)})", "입력한 문장 그대로 · 긴 문장은 줄임, 전문은 Word 부록", "학생이 입력한 프롬프트를 순서대로 실었습니다.")
        table(sl, 0.6, 1.55, 12.1, ["번호", "시각", "프롬프트"], [(r["no"], r["time"][5:], shown(r, 85).replace("\n", " ")) for r in ch], [0.8, 1.5, 9.8], 9, 0.4)
    sl = slide("부록 · 중간 산출물", "GitHub 저장소에서 버전 관리" + (f" · {GITHUB}" if GITHUB else ""), "과제를 하며 나온 중간 산출물과 위치입니다.")
    table(sl, 0.6, 1.55, 12.1, ["구분", "산출물", "위치"], artifacts(), [1.8, 6.4, 3.9], 9, 0.47)
    per = 11
    chunks = [log[i:i + per] for i in range(0, len(log), per)]
    for k, ch in enumerate(chunks, 1):
        sl = slide(f"부록 · GitHub 커밋 이력 ({k}/{len(chunks)})", "작업 단위마다 커밋 (메시지 그대로)", "GitHub에 남은 커밋 이력입니다.")
        table(sl, 0.6, 1.55, 12.1, ["커밋", "시각", "내용"], [(h, t, (m[:88] + "…") if len(m) > 88 else m) for h, t, m in ch], [1, 1.4, 9.7], 9, 0.37)
