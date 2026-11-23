"""
운영 이관 기획서 그림 3장 → docs/Diagrams/
  d_plan_logic_tree.png  문제 로직 트리 (MECE: 보기·판단·행동·근거)
  d_plan_asis_tobe.png   As-Is → Gap → To-Be
  d_plan_gantt.png       실제 수행 일정 WBS·간트 (Git 커밋 시각 기준)
  python3 tools/diagrams_plan.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "plan_docs"))
import figs as F  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
F.OUT = os.path.join(ROOT, "docs", "Diagrams")
NEW = "#6A1B9A"
NEW_L = "#F3E5F5"


def logic_tree():
    fig, ax = F.canvas(11, 5.6, "운영 이관 문제 로직 트리 — 원인을 빠짐없이, 겹치지 않게(MECE) 네 갈래로")
    F.box(ax, 2, 40, 17, 20, "운영팀이\n넘겨받기 어렵다\n(증상)", fc=F.RED_L, ec=F.RED, fs=10, bold=True)
    rows = [("보기", "상태가 화면 여러 곳에 흩어짐\n하우스 위치와 연결 안 됨", "통합 관제 화면 (SCR-M1)"),
            ("판단", "정상·이상 기준이 화면에 없음\n매일 볼 항목이 정해지지 않음", "서버 판정 5단계 · 운영 점검 9항목"),
            ("행동", "장애 대응·백업·사용자 관리\n절차가 없음", "운영 매뉴얼 + 화면의 절차 번호"),
            ("근거", "새 환경 설치 재현 미확인\n실제 사용 현황을 모름", "설치 보고서 (새 환경 설치) · GA4")]
    for i, (k, why, sol) in enumerate(rows):
        y = 78 - i * 24
        F.box(ax, 26, y, 11, 14, k, fc="white", ec=F.GREEN, fs=11, bold=True)
        F.box(ax, 41, y, 27, 14, why, fc="white", ec="#9E9E9E", fs=8.6)
        F.box(ax, 72, y, 25, 14, sol, fc=NEW_L, ec=NEW, fs=8.6, tc=NEW)
        F.arrow(ax, (19.5, 50), (25.6, y + 7), lw=1)
        F.arrow(ax, (37.4, y + 7), (40.6, y + 7), lw=1)
        F.arrow(ax, (68.4, y + 7), (71.6, y + 7), color=NEW, lw=1.2)
    ax.text(31.5, 96, "원인 갈래", ha="center", fontsize=9, color=F.GRAY, fontweight="bold")
    ax.text(54.5, 96, "세부 원인 (5 Whys)", ha="center", fontsize=9, color=F.GRAY, fontweight="bold")
    ax.text(84.5, 96, "해결안", ha="center", fontsize=9, color=NEW, fontweight="bold")
    return F.save(fig, "d_plan_logic_tree")


def asis_tobe():
    fig, ax = F.canvas(11, 5.2, "As-Is → Gap → To-Be — 현재를 데이터로 알고, 목표를 정하고, 사이를 메우는 안을 설계한다")
    F.box(ax, 2, 10, 28, 78, "As-Is (이관 전)\n\n관리 화면 6개를 오가며 확인\n사람이 숫자를 보고 판단\n운영 절차 문서 없음\n개발 PC에서만 실행\n백업 확인 화면 없음\n사용 현황 모름",
          fc=F.GRAY_L, ec="#9E9E9E", fs=9.5)
    F.box(ax, 36, 10, 28, 78, "Gap을 메우는 안 (기획)\n\n통합 관제 화면\n운영 점검 9항목 자동 판정\n운영 매뉴얼 (절차 번호)\n새 환경 설치 · 설치 보고서\n백업 표시 · 복구 시험\nGA4 이용 통계",
          fc=NEW_L, ec=NEW, fs=9.5, tc=NEW)
    F.box(ax, 70, 10, 28, 78, "To-Be (이관 후)\n\n한 화면에서 하우스 전체 상황\n서버가 같은 기준으로 판정\n증상별 절차를 따라 조치\n명령 1회 설치, 15항목 확인\n복구까지 검증된 백업\n데이터로 화면·기능 개선",
          fc=F.GREEN_L, ec=F.GREEN, fs=9.5)
    F.arrow(ax, (30.6, 49), (35.4, 49), lw=1.6)
    F.arrow(ax, (64.6, 49), (69.4, 49), lw=1.6, color=NEW)
    F.note(fig, "As-Is 기준: 2026-11-16 아침 (커밋 366feb1). To-Be 확인: 2026-11-18 main 병합 (커밋 80d40df).")
    return F.save(fig, "d_plan_asis_tobe")


def gantt():
    # 실제 수행 일정 (Git 커밋 시각 기준, 일 단위). 11-19~11-22는 작업 없음
    days = ["11-16", "11-17", "11-18", "11-23"]
    wbs = [("1", "범위 확인 (메모 사진)", 0, 0, F.GRAY), ("2", "아키텍처 정리 (제출 PPT)", 0, 0, F.BLUE),
           ("3", "운영 점검·GA4 구현", 0, 0, F.GREEN), ("4", "새 환경 설치·결함 수정", 0, 0, F.ORANGE),
           ("5", "운영 매뉴얼·설치 보고서", 0, 0, F.GRAY), ("6", "통합 관제 화면·API·시험", 0, 0, F.GREEN),
           ("7", "바이브 코딩 기록", 0, 0, F.GRAY), ("8", "보고서 양식 정비·발표 자료", 1, 1, F.GRAY),
           ("9", "시연 영상 내레이션 교체", 1, 1, F.BLUE), ("10", "관제 장면 영상·공개 데모·병합", 1, 2, F.GREEN),
           ("11", "기획서 정리 (12주차 강의)", 3, 3, NEW)]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    for i, (wid, name, s, e, col) in enumerate(wbs):
        ax.barh(i, e - s + 1, left=s - 0.5, color=col, alpha=0.85, height=0.55)
        ax.text(-0.62, i, f"{wid}  {name}", va="center", ha="right", fontsize=8.5)
    ax.axvline(2.5, color=F.RED, lw=1, ls="--")
    ax.text(2.55, -1.0, "main 병합 (11-18)", color=F.RED, fontsize=7.5)
    ax.set_xlim(-0.5, 3.5); ax.set_ylim(len(wbs) - 0.4, -1.6)
    ax.set_xticks(range(4)); ax.set_xticklabels(days, fontsize=8.5)
    ax.set_yticks([])
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE"); ax.set_axisbelow(True)
    ax.set_title("운영 이관 WBS · 간트 차트 (실제 수행 일정)", loc="left", fontsize=11, fontweight="bold")
    F.note(fig, "Git 커밋 시각 기준. 11-19~11-22는 작업 없음(가로축 생략). 초록 구현 · 주황 설치·검증 · 파랑 설계·영상 · 회색 문서 · 보라 기획서.")
    return F.save(fig, "d_plan_gantt")


if __name__ == "__main__":
    print(logic_tree())
    print(asis_tobe())
    print(gantt())
