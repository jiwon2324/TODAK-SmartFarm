"""
실제 구현(as-built) 시스템 구성도 → docs/Diagrams/d_architecture_final.png
계획서 그림(d_architecture)은 계획 단계 그대로 두고, 개발·완료 보고서는 이 그림을 쓴다.
  python3 tools/diagrams_final.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "plan_docs"))
import figs as F  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
F.OUT = os.path.join(ROOT, "docs", "Diagrams")


def band(ax, y, h, label, fc):
    ax.add_patch(Rectangle((1, y), 98, h, fc=fc, ec="none"))
    ax.text(2, y + h - 1.6, label, fontsize=8.5, fontweight="bold", va="top", color=F.INK)


def dashed(ax, x, y, w, h, text):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2", fc="white", ec=F.RED, lw=1.1, ls=(0, (4, 3))))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.3, color=F.RED, linespacing=1.35)


def main():
    dd = json.load(open(os.path.join(ROOT, "docs", "Database", "table_dictionary.json"), encoding="utf-8"))
    nt, nfk = len(dd["tables"]), dd["fk_count"]
    fig, ax = F.canvas(11, 7.6, "실제 구현 시스템 구성도 (TODAK v1.1) — Docker Compose 5개 컨테이너 + 선택 공개 접속")

    band(ax, 84, 14, "사용자", F.BLUE_L)
    F.box(ax, 14, 86, 17, 7, "농가 (FARMER)\n대시보드·제어·생육 분석", fc="white", fs=7.6)
    F.box(ax, 34, 86, 17, 7, "관리자 (ADMIN)\n승인·장비·규칙·기상 자료", fc="white", fs=7.6)
    F.box(ax, 54, 86, 19, 7, "조회 전용 (VIEWER)\n/demo 로그인 없이 둘러보기", fc="white", fs=7.6)
    F.box(ax, 76, 86, 21, 7, "브라우저 (PC·휴대폰)\n반응형 360px~", fc="white", ec=F.BLUE, fs=7.6)

    band(ax, 40, 42, "서버 (Docker Compose)", F.GREEN_L)
    F.box(ax, 5, 45, 21, 32, "frontend 컨테이너\nnginx\n\nReact 18\nTypeScript\nTailwind · Recharts\n\n/api 프록시\nSSE 전달", fc="white", ec=F.GREEN, fs=7.4)
    ax.add_patch(FancyBboxPatch((30, 44.5), 66.5, 33, boxstyle="round,pad=0.3,rounding_size=1.2", fc="#F6FBF6", ec=F.GREEN, lw=1.3))
    ax.text(63.25, 74.5, "backend 컨테이너: Spring Boot 3.3 · Java 21", ha="center", va="center", fontsize=8, fontweight="bold", color=F.INK)
    ax.text(63.25, 70.3, "REST API · SSE 실시간 · Swagger · Spring Security · JWT 15분 + Refresh 회전(HttpOnly 쿠키)", ha="center", va="center", fontsize=7.1, color=F.INK)
    F.box(ax, 32, 46.5, 20, 19, "규칙 엔진 (1분)\nCR-01~07\n히스테리시스\n2단계 환기·지속\n횟수·간격 제한\n안전 한계 우선", fc="white", ec=F.GREEN, fs=7)
    F.box(ax, 54, 46.5, 20, 19, "명령·ACK 추적\n요청 > 전송 > 확인\n10초 재전송\nTIMEOUT 처리\n중복 요청 409\nMQTT: Eclipse Paho", fc="white", ec=F.GREEN, fs=7)
    F.box(ax, 76, 46.5, 19, 19, "경보·분석·배치\n중복 억제 30분\n무응답·단절 감지\nGDD 일 배치\n시간 집계\n원시 3년 보존", fc="white", ec=F.GREEN, fs=7)

    band(ax, 21, 17, "데이터 · 통신", F.ORANGE_L)
    F.box(ax, 5, 23, 21, 11, "공개 접속 (선택)\nCloudflare 임시 터널\n> Caddy > nginx", fc="white", ec="#9E9E9E", fs=7)
    F.box(ax, 32, 23, 20, 11, f"mysql 컨테이너\nMySQL 8.4\n{nt}개 테이블 · FK {nfk}개\nFlyway V1~V3", fc="white", ec=F.ORANGE, fs=7)
    F.box(ax, 54, 23, 20, 11, "mosquitto 컨테이너\nMQTT 2.0 · 1883\n계정·ACL · LWT", fc="white", ec=F.ORANGE, fs=7)
    F.box(ax, 76, 23, 19, 11, "기상청 ASOS 일자료\n양평(202) 실측 CSV\n관리자 업로드\n> 외부 GDD", fc="white", ec=F.ORANGE, fs=7)

    band(ax, 1, 18, "현장 (이번 구현은 B안 시뮬레이터)", F.GRAY_L)
    F.box(ax, 5, 3, 69, 12, "simulator 컨테이너 (Python) = 가상 게이트웨이 GW-01\n센서 11채널 1분 송신 · 장치 11종 명령 실행·ACK · 시나리오 9종\n통신 단절 시 마지막 기준값으로 안전 운전 · 복구 후 버퍼 재전송",
          fc="#FFFDE7", ec="#F9A825", fs=7.5)
    dashed(ax, 76, 3, 19, 12, "미구현 · 확장\n실장비(A안)\n카메라 수확 판별\n운영 HTTPS·TLS")

    F.arrow(ax, (80, 86), (17, 77.3), "HTTP 8088", color=F.BLUE, lw=1.1, lpos=0.75, loff=(0, 0.5))
    F.arrow(ax, (26.3, 61), (29.7, 61), both=True, lw=1.1)
    ax.text(28, 63.2, "/api", fontsize=7, color=F.GRAY, ha="center")
    F.arrow(ax, (42, 46.2), (42, 34.3), "JPA", both=True, lw=1, loff=(3, 0))
    F.arrow(ax, (64, 46.2), (64, 34.3), "명령·측정·ACK", both=True, lw=1, loff=(0, 0))
    F.arrow(ax, (85.5, 34.3), (85.5, 46.2), "CSV", lw=1, loff=(3, 0))
    F.arrow(ax, (15.5, 34.3), (15.5, 44.7), lw=1, color="#9E9E9E")
    F.arrow(ax, (64, 22.7), (64, 15.3), "todak/farm1/...", both=True, color="#F9A825", lw=1.2, loff=(6, 0))
    print(F.save(fig, "d_architecture_final"))


if __name__ == "__main__":
    main()
