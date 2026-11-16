"""
운영 단계 소프트웨어 아키텍처 → docs/Diagrams/d_software_architecture_ops.png
제출한 PPT(03 개발 보고서 7·10쪽, 04 완료 보고서 11쪽, 05 구축 보고서 21쪽)의 실제 구현 구성도를
계층(화면 → API → 서비스 → 영속성 → 데이터·통신 → 현장)으로 다시 그리고, 운영 이관에서 더한 부분(보라색)을 표시한다.
  python3 tools/diagrams_ops.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "plan_docs"))
import figs as F  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
F.OUT = os.path.join(ROOT, "docs", "Diagrams")
NEW = "#6A1B9A"
NEW_L = "#F3E5F5"


def band(ax, y, h, label, fc):
    ax.add_patch(Rectangle((1, y), 98, h, fc=fc, ec="none"))
    ax.text(2, y + h - 1.0, label, fontsize=8.2, fontweight="bold", va="top", color=F.INK)


def new(ax, x, y, w, h, text, fs=7.0):
    F.box(ax, x, y, w, h, text, fc=NEW_L, ec=NEW, fs=fs, tc=NEW, lw=1.4)


def main():
    fig, ax = F.canvas(11, 9.2, "TODAK 소프트웨어 아키텍처 (운영 단계 v1.2) — 제출 PPT의 실제 구현 구성도 + 운영 이관 추가분(보라색)")

    # 1. 사용자
    band(ax, 89, 10, "사용자", F.BLUE_L)
    F.box(ax, 14, 90.5, 15, 5.5, "농가 (FARMER)\n대시보드·제어·생육", fc="white", fs=7.2)
    F.box(ax, 32, 90.5, 15, 5.5, "관리자 (ADMIN)\n승인·장비·규칙", fc="white", fs=7.2)
    F.box(ax, 50, 90.5, 15, 5.5, "조회 전용 (VIEWER)\n/demo 둘러보기", fc="white", fs=7.2)
    new(ax, 68, 90.5, 28, 5.5, "운영팀 (신규)\n운영 매뉴얼 · 일일 점검 · 백업 · GA4 보고서", fs=7.2)

    # 2. 표현 계층 (frontend 컨테이너)
    band(ax, 70, 18, "표현 계층 (frontend 컨테이너: nginx + React 18)", F.GREEN_L)
    F.box(ax, 4, 72, 21, 11, "농가 화면 8개\nSCR-02~09\n대시보드·그래프·제어·이력\n알림·기준값·생육·수확", fc="white", ec=F.GREEN, fs=6.9)
    F.box(ax, 27, 72, 21, 11, "관리자 사이트 6개\nSCR-A1·10·A4·A5·A6\n현황·사용자·장비\n규칙·로그·기상", fc="white", ec=F.GREEN, fs=6.9)
    new(ax, 50, 72, 14, 11, "운영 점검\nSCR-A7 (신규)\n9개 항목 자동 판정\n점검표 CSV", fs=6.9)
    F.box(ax, 66, 72, 14.5, 11, "공통\napi/client: JWT 메모리\n+ Refresh 쿠키\nSSE 구독 · 권한 가드", fc="white", ec=F.GREEN, fs=6.7)
    new(ax, 82.5, 72, 13.5, 11, "analytics.ts (신규)\nGA4 page_view\n+ 기능 이벤트 7종\n개인정보 제외", fs=6.7)

    # 3. 애플리케이션 계층 (backend 컨테이너)
    band(ax, 31, 37, "애플리케이션 계층 (backend 컨테이너: Spring Boot 3.3 · Java 21)", F.GREEN_L)
    ax.text(3, 63.2, "API", fontsize=7.4, fontweight="bold", color=F.GRAY)
    F.box(ax, 8, 59.5, 13, 5, "auth\n로그인·가입·토큰", fc="white", ec=F.GREEN, fs=6.6)
    F.box(ax, 23, 59.5, 13, 5, "web\n농장·데이터·장치·알림", fc="white", ec=F.GREEN, fs=6.6)
    F.box(ax, 38, 59.5, 13, 5, "admin\n관리자 API 26개", fc="white", ec=F.GREEN, fs=6.6)
    new(ax, 53, 59.5, 13, 5, "OpsController\n/api/admin/ops (신규)", fs=6.6)
    F.box(ax, 68, 59.5, 13, 5, "ingest (HTTP)\n기기 토큰 대체 수집", fc="white", ec=F.GREEN, fs=6.6)
    F.box(ax, 83, 59.5, 13, 5, "stream\nSSE 실시간 발행", fc="white", ec=F.GREEN, fs=6.6)

    ax.text(3, 54.2, "서비스", fontsize=7.4, fontweight="bold", color=F.GRAY)
    F.box(ax, 8, 46, 14, 7.5, "규칙 엔진 (1분)\nCR-01~07\n히스테리시스·안전 한계", fc="white", ec=F.GREEN, fs=6.5)
    F.box(ax, 24, 46, 14, 7.5, "명령·ACK 추적\n요청 > 전송 > 확인\nTIMEOUT·중복 409", fc="white", ec=F.GREEN, fs=6.5)
    F.box(ax, 40, 46, 14, 7.5, "수집 검증\n형식·msgId 중복\n범위·급변 플래그", fc="white", ec=F.GREEN, fs=6.5)
    F.box(ax, 56, 46, 14, 7.5, "경보·감시\n중복 억제 30분\n무응답·단절 감지", fc="white", ec=F.GREEN, fs=6.5)
    F.box(ax, 72, 46, 11.5, 7.5, "분석\nGDD·시간 집계\n기상 CSV", fc="white", ec=F.GREEN, fs=6.5)
    F.box(ax, 85.5, 46, 10.5, 7.5, "배치\n보존 03:00\n(원시 3년)", fc="white", ec=F.GREEN, fs=6.5)

    ax.text(3, 41.2, "영속성\n·연동", fontsize=7.4, fontweight="bold", color=F.GRAY, va="top")
    F.box(ax, 8, 33.5, 30, 5, "JPA Repository 22개 · Flyway V1~V3\n(도메인 22개 테이블)", fc="white", ec=F.GREEN, fs=6.6)
    F.box(ax, 40, 33.5, 30, 5, "MQTT 어댑터 (Eclipse Paho)\n측정·ACK 구독 / 명령·기준값 발행", fc="white", ec=F.GREEN, fs=6.6)
    F.box(ax, 72, 33.5, 24, 5, "ErrorLog (최근 200건)\nActuator /actuator/health", fc="white", ec=F.GREEN, fs=6.6)

    # 4. 데이터·통신 계층
    band(ax, 15, 14.5, "데이터 · 통신 계층", F.ORANGE_L)
    F.box(ax, 8, 17, 20, 9, "mysql 컨테이너\nMySQL 8.4 · 22개 테이블\nFK 36개 · 볼륨 mysql-data", fc="white", ec=F.ORANGE, fs=6.7)
    F.box(ax, 30, 17, 20, 9, "mosquitto 컨테이너\nMQTT 2.0 · 1883\n계정·ACL·LWT", fc="white", ec=F.ORANGE, fs=6.7)
    F.box(ax, 52, 17, 18, 9, "기상청 ASOS\n양평(202) 일자료 CSV\n관리자 업로드", fc="white", ec=F.ORANGE, fs=6.7)
    new(ax, 72, 17, 24, 9, "backups/ (신규 연결)\ntools/backup-db.sh (cron 04:00)\nmysqldump > .sql.gz 7일 보관\n백엔드에 읽기 전용 마운트", fs=6.6)

    # 5. 현장·외부
    band(ax, 1, 12.5, "현장 · 외부 서비스", F.GRAY_L)
    F.box(ax, 8, 2.5, 42, 8, "simulator 컨테이너 (Python) = 가상 게이트웨이 GW-01\n센서 11채널 1분 송신 · 장치 11종 명령 실행·ACK\n단절 시 기준값 사본으로 안전 운전 · 복구 후 재전송", fc="#FFFDE7", ec="#F9A825", fs=6.7)
    new(ax, 75, 2.5, 21, 8, "Google Analytics 4 (신규)\n측정 ID: .env GA_MEASUREMENT_ID\n광고 신호 끔 · 보관 14개월", fs=6.6)
    F.box(ax, 52, 2.5, 21, 8, "미구현·확장\n실장비(A안) · 카메라 수확 판별\n운영 HTTPS·TLS", fc="white", ec=F.RED, tc=F.RED, fs=6.6)

    # 화살표
    F.arrow(ax, (40, 90.3), (40, 83.3), "HTTP 8088", color=F.BLUE, lw=1.1, loff=(5, -1.5))
    F.arrow(ax, (82, 90.3), (57, 83.3), color=NEW, lw=1.1)
    F.arrow(ax, (37, 71.8), (37, 64.8), "/api · SSE", both=True, lw=1.1, loff=(5, -0.5))
    F.arrow(ax, (57, 71.8), (59.5, 64.8), color=NEW, lw=1.1)
    # GA4: 오른쪽 가장자리를 따라 내려가 다른 상자를 가로지르지 않게
    ax.plot([96.3, 98.2, 98.2], [77.5, 77.5, 7], color=NEW, lw=1.0, ls=(0, (4, 3)))
    F.arrow(ax, (98.2, 7), (96.6, 7), color=NEW, lw=1.0)
    ax.text(98.0, 40, "gtag.js 이벤트", fontsize=6.6, color=NEW, rotation=90, ha="right", va="center", bbox=dict(fc="white", ec="none", pad=0.4))
    F.arrow(ax, (23, 33.3), (18, 26.3), "JPA", both=True, lw=1, loff=(-3, -1))
    F.arrow(ax, (55, 33.3), (40, 26.3), "MQTT", both=True, lw=1, loff=(2, -1))
    F.arrow(ax, (61, 26.3), (61, 33.3), "CSV", lw=1, loff=(3, -1))
    F.arrow(ax, (84.5, 26.3), (84.5, 33.3), "백업 확인", color=NEW, lw=1, loff=(5, -1))
    F.arrow(ax, (40, 16.8), (40, 10.8), "todak/farm1/...", both=True, color="#F9A825", lw=1.2, loff=(6, -1))
    print(F.save(fig, "d_software_architecture_ops"))


if __name__ == "__main__":
    main()
