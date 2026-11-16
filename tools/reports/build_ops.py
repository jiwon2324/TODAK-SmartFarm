# -*- coding: utf-8 -*-
"""운영 이관 문서 Word 생성: 운영 매뉴얼·설치 보고서.
원본은 docs/Operations/*.md 이고, 이 스크립트는 마크다운을 그대로 Word 서식(docgen.Doc)으로 옮긴다 — 내용은 md에서만 고친다.
  python3 tools/reports/build_ops.py [출력 폴더]   (기본: 저장소 바깥 과제 폴더)
"""
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
import docgen  # noqa: E402
from docgen import Doc  # noqa: E402
from docx.shared import Cm, Pt  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPS = os.path.join(ROOT, "docs", "Operations")
OUTDIR = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(ROOT, ".."))
TODAY = datetime.now().strftime("%Y.%m.%d")
# 교수님 안내(2026-11): 운영 이관 산출물은 기말고사 대체과제로 제출
docgen.COURSE = "데이터 기획 및 분석 · 1학기 기말고사 대체과제"

IMG_RE = re.compile(r"^!\[(.*?)\]\((.*?)\)\s*$")


def plain(t):
    """인라인 코드 표시(`)만 걷어낸다. 굵게(**)는 docgen이 처리한다."""
    return t.replace("`", "")


def table_rows(lines):
    rows = [[plain(c.strip()) for c in ln.strip().strip("|").split("|")] for ln in lines]
    return rows[0], [r for r in rows[2:]]


def widths(headers, rows):
    """칸 너비: 글자 수에 비례하되 너무 좁거나 넓지 않게"""
    n = len(headers)
    lens = [max([len(headers[i])] + [len(r[i]) if i < len(r) else 0 for r in rows]) for i in range(n)]
    return [min(max(l, 4), 40) for l in lens]


def render(d, md_path, skip_title=True):
    base = os.path.dirname(md_path)
    lines = open(md_path, encoding="utf-8").read().split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
            continue
        if s.startswith("# "):
            if not skip_title:
                d.h(s[2:], 1)
            i += 1
            continue
        if s.startswith("## "):
            d.h(plain(s[3:]), 1)
        elif s.startswith("### "):
            d.h(plain(s[4:]), 2)
        elif s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(plain(lines[i].strip()[1:].strip()))
                i += 1
            for b in buf:
                d.p(b, size=9, color=docgen.GRAY)
            continue
        elif s.startswith("```"):
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            d.code("\n".join(buf))
        elif s.startswith("|"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                buf.append(lines[i])
                i += 1
            h, rows = table_rows(buf)
            d.table(h, rows, widths(h, rows), size=8)
            continue
        elif IMG_RE.match(s):
            cap, path = IMG_RE.match(s).groups()
            d.image(os.path.normpath(os.path.join(base, path)), cap, width_cm=16)
        elif s.startswith("- [ ] "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- [ ] "):
                items.append("☐ " + plain(lines[i].strip()[6:]))
                i += 1
            for it in items:
                d.p(it)
            continue
        elif s.startswith("- "):
            items = []
            while i < len(lines) and (lines[i].strip().startswith("- ") or (lines[i].startswith("   ") and lines[i].strip().startswith("- "))):
                items.append(plain(lines[i].strip()[2:]))
                i += 1
            d.bullets(items)
            continue
        elif re.match(r"^\d+\. ", s):
            # Word의 자동 번호(List Number)는 문서 전체에서 이어지므로, 목록마다 번호를 직접 쓴다
            n = 0
            while i < len(lines) and (re.match(r"^\d+\. ", lines[i].strip()) or lines[i].startswith("   - ")):
                t = lines[i].strip()
                if t.startswith("- "):
                    par = d.p("· " + plain(t[2:]))
                    par.paragraph_format.left_indent = Cm(1.2)
                else:
                    n += 1
                    par = d.p(f"{n}. " + plain(re.sub(r"^\d+\. ", "", t)))
                    par.paragraph_format.left_indent = Cm(0.6)
                    par.paragraph_format.first_line_indent = Cm(-0.5)
                par.paragraph_format.space_after = Pt(2)
                i += 1
            continue
        else:
            d.p(plain(s))
        i += 1


def build(md, title, subtitle, doc_id, history, out_name):
    d = Doc(title, subtitle, doc_id, "v1.0", "운영 이관 · 인수 확인 요청")
    d.cover(date=TODAY)
    d.doc_control(history)
    d.toc()
    render(d, os.path.join(OPS, md))
    return d.save(os.path.join(OUTDIR, out_name))


if __name__ == "__main__":
    print(build("운영_매뉴얼.md", "운영 매뉴얼", "일일 점검 · 백업·복구 · 장애 대응 · 사용자 관리 · GA4 이용 통계",
                "TODAK-OPS-001", [("v1.0", "2026.11.16", "최초 작성 (운영팀 이관, 운영 점검 화면 SCR-A7·GA4 반영)", "양지원")],
                "08_운영_매뉴얼_v1.0.docx"))
    print(build("설치_보고서.md", "설치 보고서", "깨끗한 환경에 v1.2.0 설치 · 설치 결과 확인 15항목 · 발견 사항과 조치",
                "TODAK-INS-001", [("v1.0", "2026.11.16", "최초 작성 (개발 PC 새 설치 기록, 운영 서버 설치 전)", "양지원")],
                "09_설치_보고서_v1.0.docx"))
    print(build("바이브코딩_관제_소프트웨어.md", "바이브 코딩 기록", "스마트팜 관제 소프트웨어 만들기 · 어떤 Framework을 쓰는가",
                "TODAK-VIB-001", [("v1.0", "2026.11.16", "최초 작성 (통합 관제 SCR-M1 개발 과정과 프레임워크 정리)", "양지원")],
                "11_바이브코딩_관제소프트웨어_v1.0.docx"))
