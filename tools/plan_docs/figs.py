# -*- coding: utf-8 -*-
"""TODAK 산출물 그림 생성. 모든 수치는 data.py에서 읽는다."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon, Ellipse
import data as D

FONT = os.path.expanduser("~/Library/Fonts/NanumGothic.ttf")
font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=FONT).get_name()
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 10

OUT = os.path.join(os.path.dirname(__file__), "fig")
os.makedirs(OUT, exist_ok=True)

GREEN = "#2E7D32"; GREEN_L = "#E8F5E9"; GREEN_M = "#A5D6A7"
GRAY = "#5F6368"; GRAY_L = "#F1F3F4"; INK = "#202124"
ORANGE = "#E65100"; ORANGE_L = "#FFF3E0"; BLUE = "#1565C0"; BLUE_L = "#E3F2FD"
RED = "#C62828"; RED_L = "#FFEBEE"


def save(fig, name):
    path = os.path.join(OUT, name + ".png")
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def clean(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#BDBDBD"); ax.spines["bottom"].set_color("#BDBDBD")
    ax.tick_params(colors=GRAY)
    ax.grid(axis="y", color="#EEEEEE", linewidth=0.8)
    ax.set_axisbelow(True)


def note(fig, text, y=-0.02):
    fig.text(0.01, y, text, fontsize=8, color=GRAY, ha="left", va="top")


# ---------------- 차트 ----------------
def climate_temp():
    c = D.CLIMATE; x = range(12)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.fill_between(x, c["tmin"], c["tmax"], color=GREEN_M, alpha=0.45, label="평균 최저~최고")
    ax.plot(x, c["tavg"], color=GREEN, lw=2.2, marker="o", ms=4, label="평균기온")
    ax.plot(x, c["rec_max"], color=ORANGE, lw=1, ls="--", label="역대 최고")
    ax.plot(x, c["rec_min"], color=BLUE, lw=1, ls="--", label="역대 최저")
    ax.axhline(15, color=GRAY, lw=0.8, ls=":")
    ax.text(11.2, 15.6, "야간 최저 관리선 15℃", fontsize=8, color=GRAY, ha="right")
    for i in (0, 7):
        ax.annotate(f"{c['tavg'][i]}℃", (i, c["tavg"][i]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8, color=GREEN)
    ax.set_xticks(list(x)); ax.set_xticklabels(D.MONTHS); ax.set_ylabel("기온 (℃)")
    ax.set_title("양평 외부 기온은 11~3월 평균 최저가 영하라 하우스 난방 감시가 필수", loc="left", fontsize=11, fontweight="bold")
    ax.legend(ncol=4, fontsize=8, frameon=False, loc="upper left", bbox_to_anchor=(0, -0.12))
    clean(ax)
    note(fig, "출처: 기상청 평년값(1991~2020), 양평관측소 [S1]. 외부 기온이며 하우스 내부 온도가 아님.", y=-0.1)
    return save(fig, "f_climate_temp")


def climate_rain():
    c = D.CLIMATE
    fig, ax = plt.subplots(figsize=(8, 3.4))
    colors = [ORANGE if v >= 300 else GREEN for v in c["rain"]]
    b = ax.bar(D.MONTHS, c["rain"], color=colors, width=0.65)
    for r, v in zip(b, c["rain"]):
        ax.text(r.get_x() + r.get_width() / 2, v + 6, f"{v:g}", ha="center", fontsize=7.5, color=INK)
    ax.set_ylabel("강수량 (mm)")
    ax.set_title("연 강수량 1,383.6mm 중 53%가 7~8월에 집중", loc="left", fontsize=11, fontweight="bold")
    clean(ax)
    note(fig, "출처: 기상청 평년값(1991~2020), 양평관측소 [S1]. 주황 = 월 300mm 이상.")
    return save(fig, "f_climate_rain")


def climate_sun_rh():
    c = D.CLIMATE
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.2))
    a1.bar(D.MONTHS, c["sun"], color=[ORANGE if v < 160 else GREEN for v in c["sun"]], width=0.65)
    a1.set_title("월 일조시간 (시간)", loc="left", fontsize=10, fontweight="bold")
    a1.tick_params(axis="x", labelsize=7); clean(a1)
    a2.plot(D.MONTHS, c["rh"], color=BLUE, marker="o", ms=3)
    a2.axhspan(70, 80, color=GREEN_L, zorder=0)
    a2.text(0, 80.8, "하우스 권장 70~80% (내부 기준)", fontsize=7.5, color=GREEN)
    a2.set_title("외부 평균 상대습도 (%)", loc="left", fontsize=10, fontweight="bold")
    a2.set_ylim(50, 85); a2.tick_params(axis="x", labelsize=7); clean(a2)
    fig.suptitle("7월은 일조가 가장 적고(150.3시간) 습도가 가장 높다(79.3%)", x=0.01, ha="left", fontsize=11, fontweight="bold", y=1.04)
    note(fig, "출처: 기상청 평년값(1991~2020) [S1], 권장 습도 [S4]. 주황 = 160시간 미만.")
    return save(fig, "f_climate_sun_rh")


def climate_diurnal():
    d = D.diurnal()
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.bar(D.MONTHS, d, color=[ORANGE if v >= 13 else GREEN_M for v in d], width=0.65)
    for i, v in enumerate(d):
        ax.text(i, v + 0.2, f"{v}", ha="center", fontsize=7.5)
    ax.set_ylabel("일교차 (℃)")
    ax.set_title("봄(4~5월)·가을(10월) 일교차 13℃ 이상 → 새벽 저온·한낮 고온이 하루에 함께 온다", loc="left", fontsize=10.5, fontweight="bold")
    clean(ax)
    note(fig, "산출: 평균 최고기온 - 평균 최저기온 (기상청 평년값 [S1]).")
    return save(fig, "f_climate_diurnal")


def gdd_external():
    g = D.monthly_gdd_from_normals()
    cum = []; s = 0
    for v in g:
        s += v; cum.append(round(s, 1))
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.bar(D.MONTHS, g, color=GREEN_M, width=0.65, label="월 GDD")
    ax2 = ax.twinx()
    ax2.plot(D.MONTHS, cum, color=GREEN, marker="o", ms=3, label="누적 GDD")
    ax2.set_ylabel("누적 GDD (℃·일)", color=GREEN)
    ax.set_ylabel("월 GDD (℃·일)")
    ax.set_title(f"외부 기온만으로는 4~10월에만 열량이 쌓인다 (연 개략 {cum[-1]:,.0f}℃·일)", loc="left", fontsize=10.5, fontweight="bold")
    clean(ax); ax2.spines["top"].set_visible(False)
    note(fig, f"개략 계산: max(0, 월평균기온 - {D.GDD_BASE:g}℃) × 일수, 평년값 [S1], Tbase [S7]. 일자료로 계산하는 실제 값과 다르며 하우스 내부 GDD가 아님.")
    return save(fig, "f_gdd_external")


def season_risk():
    c = D.CLIMATE
    rows = ["저온", "고온", "다습", "일조 부족", "집중호우"]
    def lv(v, hi, mid, lo=None, rev=False):
        if rev:
            return 3 if v < hi else 2 if v < mid else (1 if lo is not None and v < lo else 0)
        return 3 if v >= hi else 2 if v >= mid else (1 if lo is not None and v >= lo else 0)
    M = [
        [lv(t, -5, 0, 10, rev=True) for t in c["tmin"]],
        [lv(t, 30, 28, 25) for t in c["tmax"]],
        [lv(h, 77, 70) for h in c["rh"]],
        [lv(s, 160, 180, rev=True) for s in c["sun"]],
        [lv(r, 300, 130) for r in c["rain"]],
    ]
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(["#F5F5F5", "#FFE0B2", "#FFB74D", "#E65100"])
    fig, ax = plt.subplots(figsize=(8.5, 2.9))
    ax.imshow(M, cmap=cmap, vmin=0, vmax=3, aspect="auto")
    ax.set_xticks(range(12)); ax.set_xticklabels(D.MONTHS, fontsize=8)
    ax.set_yticks(range(5)); ax.set_yticklabels(rows)
    lab = {0: "", 1: "낮음", 2: "중간", 3: "높음"}
    for i in range(5):
        for j in range(12):
            ax.text(j, i, lab[M[i][j]], ha="center", va="center", fontsize=7, color="white" if M[i][j] == 3 else INK)
    ax.set_title("계절별 재배 환경 위험: 겨울 저온과 7~8월 고온·다습·호우가 핵심", loc="left", fontsize=10.5, fontweight="bold")
    for s in ax.spines.values():
        s.set_visible(False)
    note(fig, "판정 규칙(개발팀 설정): 저온 최저<-5 높음, <0 중간, <10 낮음 / 고온 최고≥30 높음, ≥28 중간, ≥25 낮음 / 다습 ≥77% 높음, ≥70% 중간 /\n일조 <160h 높음, <180h 중간 / 호우 ≥300mm 높음, ≥130mm 중간. 자료: 기상청 평년값 [S1].")
    return save(fig, "f_season_risk")


def grow_setpoints():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.2), gridspec_kw={"width_ratios": [1.1, 1]})
    items = [("주간 환기\n(ON 28 / OFF 26)", 26, 28, ORANGE), ("야간 난방\n(ON 14 / OFF 16)", 14, 16, BLUE),
             ("안전 고온", 32, 35, RED), ("안전 저온", 5, 8, RED)]
    for i, (n, lo, hi, col) in enumerate(items):
        a1.barh(i, hi - lo, left=lo, color=col, alpha=0.75, height=0.5)
        a1.text(hi + 0.4, i, f"{lo}~{hi}℃", va="center", fontsize=8)
    a1.set_yticks(range(len(items))); a1.set_yticklabels([x[0] for x in items], fontsize=8)
    a1.set_xlim(0, 40); a1.invert_yaxis()
    a1.set_title("온도 제어 히스테리시스 구간", loc="left", fontsize=10, fontweight="bold"); clean(a1)
    st = [("초기", 1.0, 2.0), ("최성기", 2.0, 2.5), ("말기", 1.8, 2.2)]
    for i, (n, lo, hi) in enumerate(st):
        a2.bar(i, hi - lo, bottom=lo, color=GREEN, alpha=0.8, width=0.5)
        a2.text(i, hi + 0.05, f"{lo}~{hi}", ha="center", fontsize=8)
    a2.set_xticks(range(3)); a2.set_xticklabels([s[0] for s in st]); a2.set_ylim(0, 3); a2.set_ylabel("EC (dS/m)")
    a2.set_title("생육 단계별 양액 EC 관리 범위", loc="left", fontsize=10, fontweight="bold"); clean(a2)
    note(fig, "온도 설정값: 문헌 [S4][S6][S9]을 근거로 개발팀이 정한 초기값(시범운영 중 조정). EC: [S5] 생육 초기 1.0~2.0, 최성기 2.0~2.5, 말기 2.0(±0.2는 설정 허용폭).")
    return save(fig, "f_grow_setpoints")


def budget():
    items = D.BUDGET; tot = sum(v for _, _, v in items)
    fig, ax = plt.subplots(figsize=(8, 3.4))
    names = [n for n, _, _ in items][::-1]; vals = [v / 1e6 for _, _, v in items][::-1]
    ax.barh(names, vals, color=[GREEN if n == "인건비" else GREEN_M for n in names], height=0.6)
    for i, v in enumerate(vals):
        ax.text(v + 0.3, i, f"{v:,.1f}백만 원 ({v * 1e6 / tot * 100:.0f}%)", va="center", fontsize=8.5)
    ax.set_xlim(0, 32); ax.set_xlabel("백만 원")
    ax.set_title(f"총사업비 {tot / 1e6:,.0f}백만 원: 인건비 50%, 현장 장비·설치 34%", loc="left", fontsize=11, fontweight="bold")
    clean(ax); ax.grid(axis="x", color="#EEEEEE"); ax.grid(axis="y", visible=False)
    note(fig, "모든 금액은 견적 미확보 추정치. 기존 설비(난방기·양액기·측창 모터·환기팬)는 농가 보유를 가정하고 연동 비용만 반영.")
    return save(fig, "f_budget")


def gantt():
    fig, ax = plt.subplots(figsize=(9, 4.6))
    n = len(D.WBS)
    for i, (wid, name, s, e, who, out) in enumerate(D.WBS):
        col = GREEN if wid.startswith("4") else (BLUE if wid.startswith("3") else (ORANGE if wid.startswith("5") else GRAY))
        ax.barh(i, e - s + 1, left=s - 0.5, color=col, alpha=0.8, height=0.55)
        ax.text(0.2 - 0.5, i, f"{wid} {name}", va="center", ha="right", fontsize=8.5)
        ax.text(e + 0.6, i, who, va="center", fontsize=7.5, color=GRAY)
    for w, g in D.GATES:
        ax.axvline(w + 0.5, color=RED, lw=1, ls="--")
        ax.text(w + 0.6, -1.0, g, color=RED, fontsize=7.5, ha="left")
    ax.set_xlim(-0.3, 13.8); ax.set_ylim(n - 0.4, -1.6)
    ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{w}주" for w in range(1, 13)], fontsize=8)
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE"); ax.set_axisbelow(True)
    ax.set_title("12주 WBS: 구현(5~9주)과 현장 설치(7~9주)가 겹치고, 관문 4개에서 승인", loc="left", fontsize=11, fontweight="bold")
    note(fig, "1주 = 2026.11.02~11.06, 12주 = 2027.01.18~01.22 (문서상 가상 사업 기간). 회색 착수·운영, 파랑 설계, 초록 구현, 주황 테스트.")
    return save(fig, "f_gantt")


def req_matrix():
    diff = {"하": 0, "중": 1, "상": 2}
    grp = {"MVP": 0, "MVP(웹) / 확장(SMS)": 0, "MVP(시뮬레이터) / HW": 1, "확장": 2}
    cells = {}
    for r in D.REQ_F:
        key = (grp.get(r[8], 0), diff[r[9]])
        cells.setdefault(key, []).append(r[0].replace("REQ-F-", "F"))
    fig, ax = plt.subplots(figsize=(8, 3.6))
    cols = ["MVP (시뮬레이터로 완결)", "MVP + 하드웨어 확보 시 실증", "확장 기능"]
    rows = ["난이도 하", "난이도 중", "난이도 상"]
    for gx in range(3):
        for dy in range(3):
            fc = GREEN_L if gx == 0 else (BLUE_L if gx == 1 else GRAY_L)
            ax.add_patch(Rectangle((gx, dy), 1, 1, fc=fc, ec="white", lw=2))
            ids = cells.get((gx, dy), [])
            ax.text(gx + 0.5, dy + 0.5, "\n".join([", ".join(ids[k:k + 3]) for k in range(0, len(ids), 3)]), ha="center", va="center", fontsize=9)
    ax.set_xlim(0, 3); ax.set_ylim(0, 3)
    ax.set_xticks([0.5, 1.5, 2.5]); ax.set_xticklabels(cols, fontsize=8.5)
    ax.set_yticks([0.5, 1.5, 2.5]); ax.set_yticklabels(rows, fontsize=8.5)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("기능 요구사항 18건 중 16건이 시뮬레이터만으로 개발·검증 가능", loc="left", fontsize=11, fontweight="bold")
    note(fig, "F = REQ-F-. 구분과 난이도는 요구사항 정의서(표 11-1)와 동일.")
    return save(fig, "f_req_matrix")


def risk_matrix():
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    for i in range(1, 6):
        for j in range(1, 6):
            sc = i * j
            fc = "#FFCDD2" if sc >= 12 else ("#FFE0B2" if sc >= 6 else "#F1F8E9")
            ax.add_patch(Rectangle((i - 0.5, j - 0.5), 1, 1, fc=fc, ec="white", lw=2))
    pos = {}
    for rid, name, l, im, _ in D.RISKS:
        k = (l, im); off = pos.get(k, 0); pos[k] = off + 1
        ax.text(l, im + 0.22 - off * 0.25, rid, ha="center", va="center", fontsize=8.5, fontweight="bold")
    ax.set_xlim(0.5, 5.5); ax.set_ylim(0.5, 5.5)
    ax.set_xticks(range(1, 6)); ax.set_yticks(range(1, 6))
    ax.set_xlabel("발생 가능성 (1 낮음 ~ 5 높음)"); ax.set_ylabel("영향도 (1 ~ 5)")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("최우선 위험: R-01 기존 설비 연동 (가능성 3 × 영향 4)", loc="left", fontsize=10.5, fontweight="bold")
    note(fig, "빨강 = 점수 12 이상, 주황 = 6~11, 연두 = 5 이하. 점수 = 가능성 × 영향 (개발팀 평가).")
    return save(fig, "f_risk_matrix")


# ---------------- 도식 헬퍼 ----------------
def canvas(w, h, title):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 0.93])
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    fig.text(0.01, 0.975, title, fontsize=11, fontweight="bold", va="top")
    return fig, ax


def box(ax, x, y, w, h, text, fc=GRAY_L, ec="#9E9E9E", fs=8.5, bold=False, tc=INK, lw=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2", fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc, fontweight="bold" if bold else "normal", linespacing=1.35)


def arrow(ax, p1, p2, label=None, color=GRAY, ls="-", lw=1.2, fs=7.5, lpos=0.5, loff=(0, 1.5), both=False, rad=0.0):
    ax.annotate("", xy=p2, xytext=p1, arrowprops=dict(arrowstyle="<|-|>" if both else "-|>", color=color, lw=lw, ls=ls,
                                                       shrinkA=0, shrinkB=0, mutation_scale=10, connectionstyle=f"arc3,rad={rad}"))
    if label:
        mx = p1[0] + (p2[0] - p1[0]) * lpos + loff[0]; my = p1[1] + (p2[1] - p1[1]) * lpos + loff[1]
        ax.text(mx, my, label, fontsize=fs, color=color, ha="center", va="bottom",
                bbox=dict(fc="white", ec="none", pad=0.6))


def as_is_to_be():
    fig, ax = canvas(10, 4.6, "AS-IS 사람의 감각과 기억 → TO-BE 측정·기록·자동 제어·알림")
    box(ax, 1, 82, 44, 9, "AS-IS 수작업 관리", fc="#ECEFF1", bold=True, fs=10)
    box(ax, 55, 82, 44, 9, "TO-BE TODAK 시스템", fc=GREEN_L, ec=GREEN, bold=True, fs=10)
    rows = [("온도", "새벽·한낮 직접 측창 개폐", "히스테리시스 자동 환기·난방 + 안전 운전"),
            ("빛", "날씨를 보고 커튼 판단", "일사량 기준 차광, 일부 보광, DLI 표시"),
            ("물·양액", "타이머 관수, EC·pH 가끔 측정", "배지수분 기준 구역 관수, EC·pH 경보"),
            ("수정", "벌통 교체 시기 기억", "벌통 등록·교체 알림 (사람이 교체)"),
            ("수확", "매일 눈으로 확인", "착색도 분석 후 수확 후보 알림 (사람이 수확)"),
            ("기록", "기록 없음, 경험 의존", "1분 데이터 3년, 그래프·CSV·GDD")]
    for i, (k, a, b) in enumerate(rows):
        y = 70 - i * 12.5
        box(ax, 1, y, 9, 9, k, fc="white", bold=True)
        box(ax, 11.5, y, 33.5, 9, a, fc="#ECEFF1")
        arrow(ax, (46, y + 4.5), (54, y + 4.5), color=GREEN, lw=1.6)
        box(ax, 55, y, 44, 9, b, fc=GREEN_L, ec=GREEN)
    return save(fig, "d_asis_tobe")


def architecture():
    fig, ax = canvas(10, 5.8, "전체 아키텍처: 서버가 판단하고, 현장 게이트웨이는 실행과 안전 운전을 맡는다")
    for (y0, y1, n, c) in [(80, 98, "사용자", BLUE_L), (56, 77, "서버 (Docker)", GREEN_L), (34, 53, "통신", ORANGE_L), (2, 31, "현장 (A안 실장비 / B안 시뮬레이터)", GRAY_L)]:
        ax.add_patch(Rectangle((0.5, y0), 99, y1 - y0, fc=c, ec="none", alpha=0.55))
        ax.text(1.5, y1 - 2.5, n, fontsize=8.5, fontweight="bold", color=INK, va="center")
    box(ax, 14, 83, 22, 9, "농가 (FARMER)\nPC·스마트폰 브라우저", fc="white")
    box(ax, 40, 83, 22, 9, "관리자 (ADMIN)\n검수자 (VIEWER)", fc="white")
    box(ax, 68, 83, 28, 9, "React + TypeScript\n반응형 웹 대시보드", fc="white", ec=BLUE)
    box(ax, 4, 59, 20, 11, "Spring Boot API\nREST · SSE\nSpring Security(JWT)", fc="white", ec=GREEN)
    box(ax, 27, 59, 19, 11, "제어 규칙 엔진\n스케줄러(1분)\n명령 관리", fc="white", ec=GREEN)
    box(ax, 49, 59, 16, 11, "MQTT 수집기\n(Spring\nIntegration)", fc="white", ec=GREEN)
    box(ax, 68, 59, 13, 11, "MySQL 8\n20개 테이블", fc="white", ec=GREEN)
    box(ax, 84, 59, 14, 11, "Python 분석\nOpenCV 착색도\nGDD 배치", fc="white", ec=GREEN)
    box(ax, 10, 37, 34, 9, "HTTPS 443 (웹·API·이미지 업로드)", fc="white", ec=ORANGE)
    box(ax, 52, 37, 44, 9, "MQTT 브로커 Mosquitto (TLS 8883, 계정 인증)", fc="white", ec=ORANGE)
    box(ax, 4, 5, 20, 22, "게이트웨이 GW-01\n\n수집·명령 실행\n안전 운전\n24시간 버퍼", fc="white", ec=GRAY, bold=True)
    box(ax, 30, 20.5, 20, 6, "센서 11채널 (RS-485)", fc="white", fs=8)
    box(ax, 30, 12.5, 20, 6, "장치 11대 (릴레이·접점)", fc="white", fs=8)
    box(ax, 30, 4.5, 20, 6, "카메라 2대 (10시·14시)", fc="white", fs=8)
    box(ax, 56, 5, 41, 21.5, "B안 시뮬레이터 (Python)\n\nGW-01과 같은 MQTT 토픽·JSON으로\n센서값을 만들고 명령에 ACK를 보낸다\n→ 서버·DB·웹 코드는 A안과 동일", fc="#FFFDE7", ec="#FBC02D", fs=8)
    arrow(ax, (82, 83), (82, 70.5), "REST·SSE", both=True, loff=(5, -6))
    arrow(ax, (16, 59), (16, 46.5), both=True)
    arrow(ax, (57, 59), (66, 46.5), both=True)
    arrow(ax, (24.5, 64.5), (26.5, 64.5)); arrow(ax, (46.5, 64.5), (48.5, 64.5), both=True); arrow(ax, (65.5, 64.5), (67.5, 64.5))
    arrow(ax, (14, 27.5), (20, 36.5), "이미지 업로드", loff=(-7, -2))
    arrow(ax, (22, 27.5), (62, 36.5), "MQTT todak/…", both=True, lpos=0.6, loff=(0, -1.5))
    for yy in (23.5, 15.5, 7.5):
        arrow(ax, (24.5, yy), (29.5, yy), both=True)
    return save(fig, "d_architecture")


def comm_structure():
    fig, ax = canvas(11, 5.4, "통신·데이터 수집 구조도: 위로는 측정값, 아래로는 명령이 흐른다")
    xs = [1, 15, 30, 45, 60, 75, 88]
    names = ["센서·장치", "게이트웨이\nGW-01", "LTE 라우터\nRT-01", "MQTT 브로커", "Spring Boot\n수집기·규칙 엔진", "MySQL", "React 웹\n농가·관리자"]
    for x, n in zip(xs, names):
        box(ax, x, 62, 11.5, 13, n, fc=GREEN_L if x in (60, 75) else (BLUE_L if x == 88 else GRAY_L), ec=GREEN if x in (60, 75) else GRAY, fs=8.5, bold=True)
    up = ["RS-485\n10초 샘플", "MQTT pub\n1분 평균 JSON", "LTE / TLS", "구독\nQoS 1", "INSERT\n중복 무시", "SSE 푸시\n3초 내"]
    for i in range(6):
        arrow(ax, (xs[i] + 11.5, 72), (xs[i + 1], 72), up[i], color=GREEN, lw=1.4, loff=(0, 1.2), fs=7)
    dn = ["접점 ON/OFF", "cmd 토픽 수신\nACK 발행", "LTE / TLS", "pub cmd\nQoS 1", "명령 저장\nREQUESTED/SENT", "POST\n/devices/{id}/commands"]
    for i in range(6):
        arrow(ax, (xs[i + 1], 65), (xs[i] + 11.5, 65), dn[i], color=ORANGE, lw=1.4, loff=(0, -8.5), fs=7)
    ax.text(1, 90, "▲ 측정값 (초록)   ▼ 제어 명령 (주황)", fontsize=8.5, color=GRAY)
    rows = [("주기", "10초 샘플 → 1분 평균 / 하트비트 30초 / 카메라 하루 2회 / GDD 매일 00:30"),
            ("저장", "원시 TB_SENSOR_DATA · 시간 집계 TB_SENSOR_DATA_HOURLY · 명령 TB_CONTROL_COMMAND · 상태 TB_CONTROL_LOG · 알림 TB_ALERT"),
            ("장애", "서버·LTE 단절 → GW가 마지막 기준값으로 안전 운전 + 24시간 버퍼 → 복구 시 is_buffered=1로 재전송 (msgId로 중복 제거)"),
            ("보안", "웹·API HTTPS + JWT / MQTT 계정·ACL·TLS(A안) / 이미지 업로드 기기 토큰 / 비밀번호 BCrypt"),
            ("B안", "시뮬레이터가 GW-01 대신 같은 토픽을 사용 → 서버·DB·웹 코드는 A안과 동일")]
    for i, (k, v) in enumerate(rows):
        y = 40 - i * 8.2
        box(ax, 1, y, 8, 6.5, k, fc="white", bold=True, fs=8.5)
        ax.text(11, y + 3.25, v, fontsize=8.2, va="center")
    return save(fig, "d_comm_structure")


def flow_collect():
    fig, ax = canvas(10, 2.9, "데이터 수집 흐름: 온도센서 S-T01 → MySQL → 대시보드")
    steps = ["S-T01\n10초마다 측정", "GW-01\n1분 평균·min·max\nmsgId 부여", "MQTT\ntodak/farm1/Z1/\nsensor/S-T01", "수집기\n형식·범위·급변 검사\n품질 플래그", "MySQL\nTB_SENSOR_DATA\n(uk msg_id)", "규칙 엔진·SSE\n기준 비교, 화면 갱신"]
    for i, s in enumerate(steps):
        box(ax, 1 + i * 16.6, 25, 14.6, 45, s, fc=GREEN_L if i in (3, 4) else GRAY_L, ec=GREEN if i in (3, 4) else GRAY, fs=8)
        if i < 5:
            arrow(ax, (15.6 + i * 16.6, 47.5), (17.6 + i * 16.6, 47.5), color=GREEN, lw=1.6)
    ax.text(1, 8, "이상치(급변 > spike_limit) → quality=SPIKE로 저장하고 제어 판단에서 제외 · 3분 무수신 → SENSOR_FAIL 경보 · 같은 msgId 재수신 → 무시", fontsize=8, color=GRAY)
    return save(fig, "d_flow_collect")


def flow_command():
    fig, ax = canvas(10, 3.1, "제어 명령 흐름: 웹 요청 → 환풍기 ON → ACK → 화면 (목표 p95 5초)")
    steps = ["웹 대시보드\n'환풍기1 켜기'", "POST /api/v1/\ndevices/{id}/\ncommands", "명령 저장\nREQUESTED\n수동 모드 설정", "MQTT pub\n…/D-FAN01/cmd\n→ SENT", "GW-01\n릴레이 ON\nACK 발행", "ACKED 저장\nTB_CONTROL_LOG\nSSE 푸시"]
    for i, s in enumerate(steps):
        box(ax, 1 + i * 16.6, 30, 14.6, 42, s, fc=ORANGE_L if i in (2, 3, 5) else GRAY_L, ec=ORANGE if i in (2, 3, 5) else GRAY, fs=8)
        if i < 5:
            arrow(ax, (15.6 + i * 16.6, 51), (17.6 + i * 16.6, 51), color=ORANGE, lw=1.6)
    ax.text(1, 12, "10초 내 ACK 없음 → 1회 재전송 → 실패 시 TIMEOUT + DEVICE_NOACK 경보 · 같은 idempotencyKey는 기존 명령을 반환(중복 실행 방지)", fontsize=8, color=GRAY)
    return save(fig, "d_flow_command")


def control_authority():
    fig, ax = canvas(10, 3.4, "제어 주체: 평상시 서버 판단, 단절 시 게이트웨이 안전 운전")
    box(ax, 1, 52, 47, 34, "평상시 (서버 연결)\n\n• 판단: 서버 규칙 엔진 (1분마다)\n• 실행: GW-01이 명령 수행 후 ACK\n• 기준값: DB가 원본, GW는 사본 보유\n• 수동 명령이 자동보다 우선 (안전 한계 제외)", fc=GREEN_L, ec=GREEN, fs=8.5)
    box(ax, 52, 52, 47, 34, "단절 시 (서버·LTE 90초 무응답)\n\n• 판단: GW-01 로컬 안전 로직\n• 범위: 고온 환기·저온 난방·관수 중지\n• 기록: 측정·상태 변화 24시간 버퍼\n• 복구: 버퍼 재전송 → 서버가 상태 재동기화", fc=ORANGE_L, ec=ORANGE, fs=8.5)
    arrow(ax, (48.5, 74), (51.5, 74), color=GRAY, both=True)
    ax.text(1, 34, "우선순위: ① 안전 한계 CR-05·06 (SAFETY)  ② 수동 명령 (MANUAL, manual_until까지)  ③ 자동 규칙 (AUTO)  ④ 단절 시 안전 운전 (FAILSAFE)", fontsize=8.5)
    ax.text(1, 22, "기준값 동기화: 기준값 저장 → MQTT retained 토픽 todak/farm1/gw/GW-01/config 발행 → GW가 버전 번호로 적용 확인", fontsize=8.5)
    ax.text(1, 10, "근거: 기존 문서는 '현장 제어기 판단'과 '서버 규칙 엔진'이 함께 적혀 모순 → 위와 같이 역할을 나눠 통일", fontsize=8, color=GRAY)
    return save(fig, "d_control_authority")


# ---------------- 배치도 ----------------
L, W = 41.5, 8.0


def house_base(title, show_beds=True):
    fig = plt.figure(figsize=(11, 3.9))
    ax = fig.add_axes([0.04, 0.12, 0.94, 0.72])
    ax.set_xlim(-4.5, 44); ax.set_ylim(-1.6, 9.6); ax.set_aspect("equal"); ax.axis("off")
    fig.text(0.01, 0.97, title, fontsize=11, fontweight="bold", va="top")
    ax.add_patch(Rectangle((0, 0), L, W, fc="white", ec=INK, lw=1.5))
    ax.add_patch(Rectangle((0, 0), L / 2, W, fc=GREEN_L, ec="none", alpha=0.5))
    ax.add_patch(Rectangle((L / 2, 0), L / 2, W, fc=BLUE_L, ec="none", alpha=0.5))
    ax.plot([L / 2, L / 2], [0, W], color=GRAY, ls="--", lw=1)
    ax.text(L / 4, W + 0.35, "Z1 입구측 구역 (약 166㎡)", ha="center", fontsize=8.5, color=GREEN, fontweight="bold")
    ax.text(3 * L / 4, W + 0.35, "Z2 안쪽 구역 (약 166㎡)", ha="center", fontsize=8.5, color=BLUE, fontweight="bold")
    if show_beds:
        for yb in (1.0, 2.9, 4.8, 6.7):
            ax.add_patch(Rectangle((3.5, yb), 35.5, 0.45, fc="#C8E6C9", ec="#81C784", lw=0.6))
    ax.add_patch(Rectangle((-0.15, 3.2), 0.3, 1.6, fc=ORANGE, ec="none"))
    ax.text(-0.5, 4.0, "출입구\n(남)", ha="right", va="center", fontsize=7.5)
    ax.text(43.3, -1.2, f"길이 {L}m × 폭 {W:g}m ≈ 332㎡ (가정 A-01)", fontsize=7.5, color=GRAY, ha="right")
    ax.text(0, -1.2, "베드 4열(코이어 배지, 길이 35.5m), 베드 사이 통로 약 1.4m, 양끝 작업공간", fontsize=7.5, color=GRAY)
    return fig, ax


def layout_plan():
    fig, ax = house_base("① 비닐하우스 평면·구역 배치도: 100평을 2개 관리 구역으로 나눈다")
    ax.add_patch(Rectangle((0.2, 0.2), 3.0, 7.6, fc="none", ec=GRAY, ls=":", lw=1))
    ax.text(1.7, 7.3, "작업·양액·제어반 공간", ha="center", fontsize=7, color=GRAY)
    ax.add_patch(Rectangle((39.3, 0.2), 2.0, 7.6, fc="none", ec=GRAY, ls=":", lw=1))
    ax.text(40.3, 7.3, "환기팬 공간", ha="center", fontsize=7, color=GRAY)
    ax.text(20.75, 3.85, "관수 1계통 (Z1)  |  관수 2계통 (Z2)", ha="center", fontsize=8, color=INK, bbox=dict(fc="white", ec="none"))
    return save(fig, "l_plan")


def mark(ax, x, y, code, shape, color, dy=0.55):
    if shape == "c":
        ax.add_patch(Circle((x, y), 0.32, fc=color, ec="white", lw=0.8, zorder=5))
    elif shape == "s":
        ax.add_patch(Rectangle((x - 0.32, y - 0.32), 0.64, 0.64, fc=color, ec="white", lw=0.8, zorder=5))
    else:
        ax.add_patch(Polygon([(x, y + 0.38), (x - 0.36, y - 0.3), (x + 0.36, y - 0.3)], fc=color, ec="white", lw=0.8, zorder=5))
    ax.text(x, y + dy, code, ha="center", va="bottom", fontsize=6.4, zorder=6, bbox=dict(fc="white", ec="none", pad=0.3, alpha=0.85))


def layout_sensors():
    fig, ax = house_base("② 센서 배치도: 구역별 온습도·배지수분 1세트, 공용 CO₂·일사, 양액부 EC·pH, 외부 온도")
    seen = set()
    for sid, name, z, (x, y), *_ in D.SENSORS:
        if sid.startswith("S-H"):
            continue
        col = BLUE if sid.startswith("CAM") else (ORANGE if sid in ("S-EC01", "S-PH01") else GREEN)
        shape = "t" if sid.startswith("CAM") else "c"
        label = sid + ("/H0" + sid[-1] if sid.startswith("S-T0") and sid != "S-TO01" else "")
        mark(ax, x, y, label, shape, col)
    ax.text(-4.4, 9.2, "● 환경 센서(초록)   ● 양액 센서(주황)   ▲ 카메라(파랑)   S-T01/H01 = 온습도 일체형, S-TO01 = 외부 온도", fontsize=7.5, color=GRAY)
    return save(fig, "l_sensors")


def layout_devices():
    fig, ax = house_base("③ 제어장치·통신 배치도: 제어반(CP-01)에 게이트웨이·라우터·UPS를 모으고 RS-485 간선을 길이 방향으로 배선")
    ax.plot([0.8, 40.5], [4.0, 4.0], color=ORANGE, lw=1.2, ls="--", zorder=2)
    ax.text(30, 3.55, "RS-485·전원 간선", fontsize=7, color=ORANGE, va="top")
    for did, name, z, (x, y), *_ in D.DEVICES:
        if did in ("GW-01", "RT-01", "UPS-01"):
            continue
        col = RED if did.startswith("CP") else (GRAY if did.startswith("D-NUT") else INK)
        mark(ax, x, y, did, "s", col if did != "CP-01" else RED)
    ax.text(-4.4, 9.2, "■ 제어 장치(검정)   ■ 제어반 CP-01(빨강, 내부에 GW-01·RT-01·UPS-01)   ■ 기존 양액기(회색)", fontsize=7.5, color=GRAY)
    return save(fig, "l_devices")


# ---------------- UML ----------------
def stick(ax, x, y, name):
    ax.add_patch(Circle((x, y + 9), 1.6, fc="white", ec=INK))
    ax.plot([x, x], [y + 7.4, y + 2], color=INK); ax.plot([x - 3, x + 3], [y + 5.5, y + 5.5], color=INK)
    ax.plot([x, x - 2.4], [y + 2, y - 2], color=INK); ax.plot([x, x + 2.4], [y + 2, y - 2], color=INK)
    ax.text(x, y - 5, name, ha="center", fontsize=8.5, fontweight="bold")


def usecase():
    fig, ax = canvas(10, 6, "유스케이스: 농가 7개, 관리자 4개, 시스템 액터(게이트웨이·스케줄러) 4개")
    ax.add_patch(FancyBboxPatch((16, 2), 66, 86, boxstyle="round,pad=0.3,rounding_size=2", fc="white", ec=GRAY))
    ax.text(18, 85, "TODAK 웹 시스템", fontsize=9, fontweight="bold")
    left = [("UC-01 대시보드 조회", 78), ("UC-02 환경 그래프·CSV", 68), ("UC-03 장치 원격 제어", 58), ("UC-04 자동/수동 모드 전환", 48),
            ("UC-05 재배 기준값 설정", 38), ("UC-06 알림 확인·처리", 28), ("UC-07 생육(GDD)·수확 분석 조회", 18)]
    right = [("UC-08 사용자·권한 관리", 78), ("UC-09 구역·센서·장치 등록", 68), ("UC-10 제어 규칙 관리", 58), ("UC-11 기상 CSV 가져오기", 48),
             ("UC-12 센서 데이터 수신", 34), ("UC-13 자동 제어 실행", 24), ("UC-14 이상 감지·경보", 14), ("UC-15 일 배치(GDD·집계)", 5)]
    for t, y in left:
        ax.add_patch(Ellipse((34, y + 2.5), 30, 7, fc=GREEN_L, ec=GREEN)); ax.text(34, y + 2.5, t, ha="center", va="center", fontsize=7.8)
        ax.plot([8, 19], [50, y + 2.5], color="#9E9E9E", lw=0.7)
    for i, (t, y) in enumerate(right):
        fc = BLUE_L if i < 4 else ORANGE_L
        ax.add_patch(Ellipse((65, y + 2.5), 30, 7, fc=fc, ec=BLUE if i < 4 else ORANGE)); ax.text(65, y + 2.5, t, ha="center", va="center", fontsize=7.8)
        ax.plot([80, 91], [y + 2.5, 70 if i < 4 else 22], color="#9E9E9E", lw=0.7)
    stick(ax, 6, 46, "농가\n(FARMER)")
    stick(ax, 93, 66, "관리자\n(ADMIN)")
    box(ax, 87, 14, 12, 12, "≪시스템≫\n게이트웨이·\n스케줄러", fc="white", fs=7.5)
    ax.annotate("", xy=(49, 59.5), xytext=(50, 26), arrowprops=dict(arrowstyle="-|>", ls="--", color=GRAY, lw=0.8))
    ax.text(51.5, 42, "≪extend≫\n안전 한계", fontsize=7, color=GRAY)
    ax.text(18, -2, "VIEWER(검수자)는 UC-01·02·07 조회만 가능", fontsize=7.5, color=GRAY)
    return save(fig, "u_usecase")


def sequence(name, title, parts, msgs, notes=None, h=5.2):
    fig, ax = canvas(10, h, title)
    n = len(parts); xs = [8 + i * (84 / (n - 1)) for i in range(n)]
    for x, p in zip(xs, parts):
        box(ax, x - 7, 88, 14, 7, p, fc=GRAY_L, fs=8, bold=True)
        ax.plot([x, x], [88, 2], color="#BDBDBD", ls="--", lw=0.8)
    y = 82
    nrow = sum(1 for m in msgs if m[0] != "frame") + 0.6 * sum(1 for m in msgs if m[0] == "frame")
    step = min(7.0, 78.0 / nrow)
    for m in msgs:
        if m[0] == "frame":
            _, a, b, lab, rows = m
            ax.add_patch(Rectangle((xs[a] - 6, y - rows * step - step * 0.6 + 3), xs[b] - xs[a] + 12, rows * step + step * 0.6 + 1.5, fc="none", ec=ORANGE, lw=1))
            ax.text(xs[a] - 5.5, y + 2.6, lab, fontsize=7.5, color=ORANGE, va="top", fontweight="bold")
            y -= step * 0.6
            continue
        a, b, txt, kind = m
        if a == b:
            ax.annotate("", xy=(xs[a] + 0.5, y - 3), xytext=(xs[a] + 0.5, y),
                        arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9, connectionstyle="arc3,rad=-1.4"))
            ax.text(xs[a] + 4, y - 1.5, txt, fontsize=7.6, va="center")
            y -= step
            continue
        ls = "--" if kind == "r" else "-"
        ax.annotate("", xy=(xs[b], y), xytext=(xs[a], y), arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9, ls=ls, mutation_scale=9))
        ax.text((xs[a] + xs[b]) / 2, y + 0.6, txt, fontsize=7.6, ha="center", va="bottom", color=GRAY if kind == "r" else INK,
                bbox=dict(fc="white", ec="none", pad=0.3))
        y -= step
    if notes:
        ax.text(1, 0, notes, fontsize=7.5, color=GRAY, va="bottom")
    return save(fig, name)


def sequences():
    out = []
    out.append(sequence("u_seq01", "SD-01 수집·자동 환기: 서버가 판단하고 게이트웨이가 실행",
        ["S-T01", "GW-01", "MQTT 브로커", "Spring Boot", "MySQL", "웹(SSE)"],
        [(0, 1, "1. 10초 샘플", "c"), (1, 2, "2. pub S-T01 (1분 평균 28.4℃)", "c"), (2, 3, "3. 전달 (QoS 1)", "c"),
         (3, 4, "4. INSERT TB_SENSOR_DATA", "c"), (3, 5, "5. SSE 측정값", "c"), (3, 3, "6. CR-01 평가: 28.4 ≥ 28.0, 최소시간 OK", "c"),
         (3, 4, "7. INSERT 명령 REQUESTED", "c"), (3, 2, "8. pub D-VENT01/cmd OPEN", "c"), (2, 1, "9. 전달", "c"),
         (1, 1, "10. 릴레이 동작", "c"), (1, 2, "11. pub ack (OPEN)", "r"), (2, 3, "12. 전달", "r"), (3, 4, "13. ACKED + TB_CONTROL_LOG", "c"), (3, 5, "14. SSE 장치 상태", "c")],
        "26.0℃ 이하로 내려가면 같은 흐름으로 CLOSE (히스테리시스).", h=6.0))
    out.append(sequence("u_seq02", "SD-02 수동 제어: 웹 버튼 → ACK까지 목표 p95 5초",
        ["농가(웹)", "Spring Boot", "MySQL", "MQTT 브로커", "GW-01"],
        [(0, 1, "1. POST /devices/7/commands {ON, 60분}", "c"), (1, 1, "2. JWT·권한·멱등키 확인", "c"),
         (1, 2, "3. 명령 REQUESTED, mode=MANUAL", "c"), (1, 0, "4. 202 Accepted {commandId}", "r"), (1, 3, "5. pub cmd (SENT)", "c"),
         (3, 4, "6. 전달", "c"), ("frame", 1, 4, "alt [10초 내 ACK]", 2), (4, 3, "7a. ack ON", "r"), (1, 2, "8a. ACKED·로그", "c"),
         ("frame", 1, 4, "else [ACK 없음]", 2), (1, 3, "7b. 1회 재전송", "c"), (1, 2, "8b. TIMEOUT + 경보", "c"), (1, 0, "9. SSE 결과", "r")],
        "manual_until이 지나면 장치는 AUTO로 복귀. 안전 한계(CR-05·06)는 수동 모드에도 동작.", h=5.8))
    out.append(sequence("u_seq03", "SD-03 통신 단절·복구: 게이트웨이 안전 운전 후 재동기화",
        ["GW-01", "MQTT 브로커", "Spring Boot", "MySQL", "웹"],
        [(1, 2, "1. GW-01 LWT 'offline' (90초 무응답)", "c"), (2, 3, "2. gateway OFFLINE", "c"), (2, 4, "3. GW_OFFLINE 경보", "c"),
         (0, 0, "4. 로컬 안전 운전 (CR-05·06 사본)", "c"), (0, 0, "5. 측정·상태 24h 버퍼", "c"), (0, 1, "6. 재연결, status online", "c"),
         (0, 1, "7. 버퍼 재전송 (is_buffered=1)", "c"), (1, 2, "8. 전달", "c"), (2, 3, "9. INSERT (msg_id 중복 무시)", "c"),
         (2, 1, "10. config 버전 확인", "c"), (2, 4, "11. 경보 RESOLVED", "c")],
        "GW가 단절 중 바꾼 장치 상태는 TB_CONTROL_LOG.changed_by=FAILSAFE로 기록.", h=5.6))
    out.append(sequence("u_seq04", "SD-04 GDD 일 배치: 내부·외부를 따로 계산해 저장",
        ["스케줄러 00:30", "GDD 서비스", "MySQL", "웹"],
        [(0, 1, "1. 전일 계산 시작", "c"), (1, 2, "2. 내부 온도 시간 집계 조회", "c"), (1, 1, "3. 시간 평균 24개 → 일평균, 결측률", "c"),
         (1, 2, "4. INSERT GDD (INTERNAL)", "c"), (1, 2, "5. 외부 기상 일자료 조회", "c"), (1, 1, "6. (최고+최저)/2 → GDD", "c"),
         (1, 2, "7. INSERT GDD (EXTERNAL)", "c"), (3, 2, "8. GET /crop-cycles/1/gdd", "c")],
        "GDD = max(0, min(Tavg, Tupper) - Tbase). 결측률 20% 초과일은 is_complete=0.", h=4.8))
    return out


def activity():
    fig, ax = canvas(10, 5.8, "액티비티: 자동 제어 규칙 평가 (1분마다, 구역·규칙별)")
    def node(x, y, t, kind="a", w=22):
        if kind == "d":
            ax.add_patch(Polygon([(x, y + 4), (x + w / 2, y), (x, y - 4), (x - w / 2, y)], fc=ORANGE_L, ec=ORANGE))
            ax.text(x, y, t, ha="center", va="center", fontsize=7.6)
        else:
            box(ax, x - w / 2, y - 3.2, w, 6.4, t, fc=GREEN_L if kind == "a" else GRAY_L, ec=GREEN if kind == "a" else GRAY, fs=7.8)
    ax.add_patch(Circle((50, 92), 1.5, fc=INK))
    node(50, 84, "구역 대표값 계산 (OK 품질 센서 평균)")
    node(50, 72, "유효 센서 있음?", "d", 26)
    node(84, 72, "자동 중지 + SENSOR_FAIL 경보", "e", 28)
    node(50, 60, "안전 한계 초과?", "d", 26)
    node(84, 60, "SAFETY 명령 (모드 무시)", "a", 28)
    node(50, 48, "장치 MANUAL 이고 manual_until 전?", "d", 34)
    node(84, 48, "건너뜀 (수동 우선)", "e", 28)
    node(50, 36, "ON 조건 / OFF 조건 충족?", "d", 30)
    node(16, 36, "상태 유지", "e", 20)
    node(50, 24, "최소 작동시간·일 상한·중복 명령 검사", "a", 36)
    node(50, 12, "명령 생성 (idempotencyKey) → MQTT", "a", 34)
    ax.add_patch(Circle((50, 3), 1.5, fc="white", ec=INK)); ax.add_patch(Circle((50, 3), 0.9, fc=INK))
    for a, b in [((50, 90.5), (50, 87.2)), ((50, 80.8), (50, 76)), ((50, 68), (50, 64)), ((50, 56), (50, 52)), ((50, 44), (50, 40)),
                 ((50, 32), (50, 27.2)), ((50, 20.8), (50, 15.2)), ((50, 8.8), (50, 4.5))]:
        arrow(ax, a, b, color=GRAY)
    arrow(ax, (63, 72), (70, 72), "아니오", loff=(0, 0.6)); arrow(ax, (63, 60), (70, 60), "예", loff=(0, 0.6))
    arrow(ax, (67, 48), (70, 48), "예", loff=(0, 0.6)); arrow(ax, (35, 36), (26, 36), "아니오", loff=(0, 0.6))
    ax.text(51, 65, "예", fontsize=7.5, color=GRAY); ax.text(51, 53, "아니오", fontsize=7.5, color=GRAY)
    ax.text(51, 41, "아니오", fontsize=7.5, color=GRAY); ax.text(51, 29, "예", fontsize=7.5, color=GRAY)
    return save(fig, "u_activity")


def erd():
    fig, ax = canvas(11, 7.6, "ERD: 기존 9개 테이블 보완 + 11개 신규 (총 20개)")
    T = {
        "TB_USER": (2, 80, ["PK user_id", "login_id UQ", "role"]),
        "TB_FARM": (24, 80, ["PK farm_id", "FK owner_user_id", "region, area_m2"]),
        "TB_ZONE*": (46, 80, ["PK zone_id", "FK farm_id", "UQ farm_id+zone_code"]),
        "TB_CROP_CYCLE*": (68, 80, ["PK cycle_id", "FK farm_id", "gdd_base/upper"]),
        "TB_GATEWAY*": (2, 58, ["PK gateway_id", "FK farm_id", "status, synced_ver"]),
        "TB_SENSOR": (24, 58, ["PK sensor_id", "FK farm_id, zone_id, gateway_id", "metric, valid_min/max"]),
        "TB_DEVICE": (46, 58, ["PK device_id", "FK farm_id, zone_id, gateway_id", "mode, manual_until"]),
        "TB_CROP_STD": (68, 58, ["PK std_id", "FK farm_id, zone_id, created_by", "stage, version_no"]),
        "TB_SENSOR_DATA": (2, 36, ["PK data_id", "FK sensor_id", "UQ msg_id, quality"]),
        "TB_SENSOR_DATA_HOURLY*": (24, 36, ["PK sensor_id+hour_at", "FK sensor_id", "avg/min/max"]),
        "TB_CONTROL_RULE*": (46, 36, ["PK rule_id", "FK farm_id, zone_id", "on/off_threshold"]),
        "TB_CONTROL_COMMAND*": (68, 36, ["PK command_id", "FK device_id, rule_id, requested_by", "UQ idempotency_key"]),
        "TB_CONTROL_LOG": (68, 14, ["PK log_id", "FK device_id, command_id", "prev/new_state"]),
        "TB_ALERT": (2, 14, ["PK alert_id", "FK farm_id, zone_id, acked_by", "dedupe_key, status"]),
        "TB_ALERT_DELIVERY*": (24, 14, ["PK delivery_id", "FK alert_id, user_id", "channel"]),
        "TB_IMAGE_RESULT": (46, 14, ["PK image_id", "FK zone_id", "ripeness_stage"]),
        "TB_GDD_DAILY*": (90, 80, ["PK cycle+date+source", "FK cycle_id", "gdd, cum_gdd"]),
        "TB_BEEHIVE*": (90, 58, ["PK hive_id", "FK cycle_id, zone_id"]),
        "TB_WEATHER_DAILY*": (90, 36, ["PK station+date", "tavg/max/min"]),
        "TB_SETTING_HISTORY*": (90, 14, ["PK history_id", "FK changed_by"]),
    }
    W_, H_ = 19.5, 15
    for n, (x, y, cols) in T.items():
        new = n.endswith("*")
        xw = W_ if x < 90 else 9.5
        ax.add_patch(Rectangle((x, y), xw, H_, fc="white", ec=GREEN if new else GRAY, lw=1.2))
        ax.add_patch(Rectangle((x, y + H_ - 4), xw, 4, fc=GREEN_L if new else GRAY_L, ec=GREEN if new else GRAY, lw=1.2))
        ax.text(x + 0.6, y + H_ - 2, n.rstrip("*"), fontsize=6.6 if x >= 90 else 7.6, va="center", fontweight="bold")
        for i, c in enumerate(cols):
            ax.text(x + 0.6, y + H_ - 6.5 - i * 3.2, c, fontsize=6 if x >= 90 else (6.0 if len(c) > 26 else 6.8), va="center", color=INK if i < 2 else GRAY)
    def rel(a, b, lab="1:N"):
        arrow(ax, a, b, lab, color="#78909C", lw=0.8, fs=6.5, loff=(0, 0.3))
    rel((21.5, 87), (24, 87)); rel((43.5, 87), (46, 87))
    rel((33, 80), (33, 73)); rel((55, 80), (55, 73)); rel((21.5, 65), (24, 65))
    rel((27, 58), (17, 51)); rel((40, 58), (40, 51)); rel((60, 58), (75, 51)); rel((77, 36), (77, 29)); rel((21.5, 21), (24, 21))
    rel((87.5, 87), (90, 87))
    ax.text(1, 3, "초록 = 신규 테이블. 선은 주요 1:N 관계만 표시, 각 상자에는 FK를 모두 적음. TB_WEATHER_DAILY는 FK 없이 station_id로 TB_FARM.kma_station_id와 연결.", fontsize=7.5, color=GRAY)
    return save(fig, "u_erd")


def sitemap():
    fig, ax = canvas(10, 4.4, "화면 구조도: 로그인 후 7개 메뉴, 관리자 전용 설정 1개")
    box(ax, 41, 82, 18, 8, "로그인", fc="white", bold=True)
    box(ax, 38, 64, 24, 9, "대시보드 (구역 Z1·Z2 탭)", fc=GREEN_L, ec=GREEN, bold=True)
    arrow(ax, (50, 82), (50, 73.5))
    menus = ["환경 그래프\n·CSV", "장치 제어\n·모드", "제어 이력", "알림", "재배 기준값\n·제어 규칙", "생육 분석\nGDD·기상", "수확 판별", "설정(ADMIN)\n사용자·구역\n센서·장치"]
    for i, m in enumerate(menus):
        x = 1 + i * 12.4
        box(ax, x, 32, 11, 16, m, fc=BLUE_L if i < 7 else ORANGE_L, ec=BLUE if i < 7 else ORANGE, fs=7.8)
        ax.plot([50, x + 5.5], [64, 48], color="#BDBDBD", lw=0.8)
    ax.text(1, 18, "대시보드 카드: 구역 온도·습도·CO₂·일사·배지수분·EC·pH, 장치 상태, 미처리 알림, 오늘 DLI·누적 GDD", fontsize=8)
    ax.text(1, 9, "모바일(360px): 카드 1열, 하단 탭 5개(대시보드·그래프·제어·알림·더보기)", fontsize=8, color=GRAY)
    return save(fig, "u_sitemap")


def wireframe():
    fig, ax = canvas(10.5, 5, "와이어프레임: 대시보드 (데스크톱 / 모바일)")
    ax.add_patch(Rectangle((1, 4), 68, 84, fc="white", ec=GRAY))
    ax.add_patch(Rectangle((1, 80), 68, 8, fc=GRAY_L, ec=GRAY)); ax.text(3, 84, "TODAK   양평 방울토마토 1동    [Z1] [Z2]          알림 2   사용자", fontsize=7.6, va="center")
    ax.add_patch(Rectangle((1, 4), 11, 76, fc="#FAFAFA", ec=GRAY))
    for i, m in enumerate(["대시보드", "그래프", "장치 제어", "이력", "알림", "기준값", "생육 분석", "수확", "설정"]):
        ax.text(2.5, 74 - i * 7, m, fontsize=7.2, color=GREEN if i == 0 else INK)
    cards = [("온도", "24.6℃", "목표 20~28"), ("습도", "72%", "70~80"), ("CO₂", "520ppm", ""), ("일사", "640W/㎡", "DLI 12.4"),
             ("배지수분", "61%", "관수 55%↓"), ("EC", "2.1", "2.0~2.5"), ("pH", "6.1", "5.5~6.8"), ("GDD 누적", "412", "정식 후 38일")]
    for i, (k, v, s) in enumerate(cards):
        cx = 14 + (i % 4) * 13.5; cy = 60 - (i // 4) * 17
        ax.add_patch(FancyBboxPatch((cx, cy), 12, 14, boxstyle="round,pad=0.2,rounding_size=1", fc=GREEN_L if i < 4 else BLUE_L, ec="#BDBDBD"))
        ax.text(cx + 1, cy + 11, k, fontsize=7); ax.text(cx + 1, cy + 6, v, fontsize=10, fontweight="bold"); ax.text(cx + 1, cy + 2, s, fontsize=6.3, color=GRAY)
    ax.add_patch(Rectangle((14, 8), 34, 24, fc="white", ec="#BDBDBD")); ax.text(15, 29, "24시간 온도·습도 그래프", fontsize=7.2)
    xs = [15 + i * 1.4 for i in range(23)]; import math; ys = [17 - 5 * math.cos(2 * math.pi * (i - 3) / 22) for i in range(23)]
    ax.plot(xs, ys, color=GREEN, lw=1)
    ax.add_patch(Rectangle((50, 8), 18, 24, fc="white", ec="#BDBDBD")); ax.text(51, 29, "장치 상태", fontsize=7.2)
    for i, d in enumerate(["측창 좌  OPEN", "환기팬1  OFF", "난방기  OFF", "관수 Z1  OFF"]):
        ax.text(51, 24 - i * 4.5, d, fontsize=6.6)
    ax.text(1, 0.5, "카드 값은 화면 예시이며 측정값이 아님", fontsize=7, color=GRAY)
    ax.add_patch(FancyBboxPatch((76, 4), 22, 84, boxstyle="round,pad=0.3,rounding_size=2", fc="white", ec=GRAY))
    ax.text(77.5, 83, "TODAK  Z1 ▼      알림", fontsize=7.2)
    for i, (k, v, _) in enumerate(cards[:5]):
        ax.add_patch(Rectangle((77.5, 70 - i * 11), 19, 9, fc=GREEN_L, ec="#BDBDBD"))
        ax.text(78.5, 74.5 - i * 11, f"{k}   {v}", fontsize=7.4, va="center")
    ax.add_patch(Rectangle((76.3, 5), 21.4, 7, fc=GRAY_L, ec="none")); ax.text(77, 8.5, "대시보드 그래프 제어 알림 더보기", fontsize=6.4, va="center")
    return save(fig, "u_wireframe")


def build_all():
    paths = {}
    for f in (climate_temp, climate_rain, climate_sun_rh, climate_diurnal, gdd_external, season_risk, grow_setpoints, budget, gantt,
              req_matrix, risk_matrix, as_is_to_be, architecture, comm_structure, flow_collect, flow_command, control_authority,
              layout_plan, layout_sensors, layout_devices, usecase, activity, erd, sitemap, wireframe):
        p = f(); paths[os.path.basename(p)[:-4]] = p
    for p in sequences():
        paths[os.path.basename(p)[:-4]] = p
    return paths


if __name__ == "__main__":
    ps = build_all()
    print(len(ps), "figures")
