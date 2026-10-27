# -*- coding: utf-8 -*-
"""개발 보고서·완료 보고서 발표 자료(.pptx). 실행: python3 tools/reports/build_ppt.py [출력 폴더]
계획서 발표 자료와 같은 디자인(짙은 초록 표지·마무리, 흰 본문). 수치·화면은 실제 증빙 파일에서 읽는다."""
import os
import re
import sys
from datetime import datetime

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

sys.path.insert(0, os.path.dirname(__file__))
import content as C  # noqa: E402
import evidence as E  # noqa: E402
from build_docs import ASSIGN, perf_rows, test_summary_rows, totals  # noqa: E402

OUTDIR = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(E.ROOT, ".."))
FONT = "맑은 고딕"
DARK = RGBColor(0x1B, 0x3D, 0x20); GREEN = RGBColor(0x2E, 0x7D, 0x32); MOSS = RGBColor(0xA5, 0xD6, 0xA7)
TINT = RGBColor(0xEE, 0xF6, 0xEE); INK = RGBColor(0x20, 0x21, 0x24); MUTED = RGBColor(0x5F, 0x63, 0x68)
WHITE = RGBColor(0xFF, 0xFF, 0xFF); RED = RGBColor(0xC6, 0x28, 0x28); AMBER = RGBColor(0xB2, 0x6A, 0x00)
TODAY = datetime.now().strftime("%Y.%m.%d")
GITHUB = os.environ.get("TODAK_GITHUB_URL")
SITE = os.environ.get("TODAK_SITE_URL")


from brand import student_badge, todak_logo  # noqa: E402

URL_RE = re.compile(r"(https?://[^\s()<>]+[^\s()<>.,·])")
LINK = RGBColor(0x15, 0x65, 0xC0)
LINK_ON_DARK = RGBColor(0xBB, 0xDE, 0xFB)


class Deck:
    def __init__(self, footer):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(13.333), Inches(7.5)
        self.footer = footer
        self.n = 0

    def tf(self, tf, text, size=14, bold=False, color=INK, align=None):
        tf.clear()
        lines = text if isinstance(text, list) else [text]
        for i, l in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            if align:
                p.alignment = align
            # **굵게** 구간을 나누고, 주소(http…)는 눌러서 바로 열리는 링크로
            parts = [(k % 2 == 1, t) for k, seg in enumerate(str(l).split("**")) for t in URL_RE.split(seg) if t]
            for strong, t in parts:
                r = p.add_run(); r.text = t
                r.font.name = FONT; r.font.size = Pt(size); r.font.bold = bold or strong; r.font.color.rgb = color
                if URL_RE.fullmatch(t):
                    r.hyperlink.address = t
                    r.font.underline = True
                    r.font.color.rgb = LINK_ON_DARK if color in (WHITE, MOSS) else LINK
                rpr = r._r.get_or_add_rPr(); rpr.set("lang", "ko-KR")
                ea = rpr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}ea")
                if ea is None:
                    ea = etree.SubElement(rpr, "{http://schemas.openxmlformats.org/drawingml/2006/main}ea")
                ea.set("typeface", FONT)
            p.space_after = Pt(6)

    def text(self, sl, x, y, w, h, t, size=14, bold=False, color=INK, align=None, anchor=MSO_ANCHOR.TOP):
        tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        f = tb.text_frame; f.word_wrap = True; f.vertical_anchor = anchor
        f.margin_left = f.margin_right = Inches(0.05); f.margin_top = f.margin_bottom = Inches(0.03)
        self.tf(f, t, size, bold, color, align)
        return tb

    def card(self, sl, x, y, w, h, fill=TINT):
        s = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        s.fill.solid(); s.fill.fore_color.rgb = fill; s.line.fill.background(); s.shadow.inherit = False
        s.adjustments[0] = 0.08
        return s

    def slide(self, title, sub=None, dark=False, notes=""):
        sl = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.n += 1
        bg = sl.background.fill; bg.solid(); bg.fore_color.rgb = DARK if dark else WHITE
        if not dark:
            self.text(sl, 0.6, 0.38, 12.1, 0.8, title, 28, True, INK)
            if sub:
                self.text(sl, 0.6, 1.1, 12.1, 0.45, sub, 14, False, MUTED)
            self.text(sl, 0.6, 7.02, 9, 0.3, self.footer, 10, False, MUTED)
            self.text(sl, 11.9, 7.02, 0.9, 0.3, str(self.n), 10, False, MUTED, PP_ALIGN.RIGHT)
        if notes:
            sl.notes_slide.notes_text_frame.text = notes
        return sl

    def pic(self, sl, path, x, y, maxw, maxh, caption=None):
        if not path or not os.path.exists(path):
            self.card(sl, x, y, maxw, maxh, fill=RGBColor(0xF5, 0xF5, 0xF5))
            self.text(sl, x, y + maxh / 2 - 0.2, maxw, 0.4, "증빙 화면 없음", 14, False, MUTED, PP_ALIGN.CENTER)
            return
        im = Image.open(path)
        # 그림은 자르지 않고 전부 보이게 넣는다. 세로로 긴 전체 화면 캡처는 위→아래 순서로 2~3조각 나눠 나란히 놓아
        # 글씨가 너무 작아지지 않게 한다 (원본 파일은 그대로, 조각은 임시 파일)
        gap = 0.18
        best = (0, 1)
        for k in (1, 2, 3):
            pw, ph = (maxw - gap * (k - 1)) / k, maxh
            r = im.width / (im.height / k)
            scale = min(pw / r, ph) * r / im.width  # 표시 폭 / 원본 폭
            if scale > best[0] * 1.15:
                best = (scale, k)
        k = best[1]
        import tempfile
        pw = (maxw - gap * (k - 1)) / k
        seg_h = im.height / k
        r = im.width / seg_h
        w, h = (pw, pw / r) if pw / r <= maxh else (maxh * r, maxh)
        x0 = x + (maxw - (w * k + gap * (k - 1))) / 2
        for i in range(k):
            part = path
            if k > 1:
                part = os.path.join(tempfile.gettempdir(), f"todak_part{i}_" + os.path.basename(path))
                im.crop((0, int(i * seg_h), im.width, int((i + 1) * seg_h))).save(part)
            pic = sl.shapes.add_picture(part, Inches(x0 + i * (w + gap)), Inches(y), width=Inches(w), height=Inches(h))
            pic.line.color.rgb = RGBColor(0xD6, 0xDB, 0xD6); pic.line.width = Pt(0.75)
            if k > 1:
                self.text(sl, x0 + i * (w + gap), y + h - 0.02, w, 0.26, f"({i + 1}/{k}) " + ("위" if i == 0 else "이어서"), 9, False, MUTED, PP_ALIGN.RIGHT)
        if caption:
            self.text(sl, x, y + h + 0.05, maxw, 0.3, caption, 10, False, MUTED, PP_ALIGN.CENTER)

    def table(self, sl, x, y, w, headers, rows, widths, size=11, rowh=0.34):
        nr, nc = len(rows) + 1, len(headers)
        gt = sl.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(rowh * nr)).table
        tot = sum(widths)
        for i, cw in enumerate(widths):
            gt.columns[i].width = Inches(w * cw / tot)
        for r in range(nr):
            gt.rows[r].height = Inches(rowh)
            for c in range(nc):
                cell = gt.cell(r, c)
                val = headers[c] if r == 0 else rows[r - 1][c]
                cell.margin_left = cell.margin_right = Inches(0.06); cell.margin_top = cell.margin_bottom = Inches(0.02)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                color = WHITE if r == 0 else (RED if str(val).startswith(("미구현", "실패", "미달", "측정 불가")) else INK)
                self.tf(cell.text_frame, str(val), size, r == 0, color)
                for p in cell.text_frame.paragraphs:
                    p.space_after = Pt(0)
                cell.fill.solid(); cell.fill.fore_color.rgb = GREEN if r == 0 else (TINT if r % 2 == 0 else WHITE)
        return gt

    def cover(self, title, sub, docid, notes):
        sl = self.slide("", dark=True, notes=notes)
        if not todak_logo(sl, 0.8, 1.05, 0.9):
            self.text(sl, 0.8, 1.5, 6, 0.5, "TODAK", 20, True, MOSS)
        self.text(sl, 0.8, 2.1, 11.5, 1.6, title, 40, True, WHITE)
        self.text(sl, 0.8, 4.3, 11.5, 0.9, sub, 18, False, MOSS)
        self.text(sl, 0.8, 6.3, 11.5, 0.4, f"{docid}  v1.0  |  {TODAY}  |  TODAK {E.VERSION}  |  하우스 센서·장치 값은 시뮬레이터(B안) 데이터", 12, False, MOSS)
        student_badge(sl)

    def stats(self, sl, items, y=1.6):
        w = 12.1 / len(items)
        for i, (n, l) in enumerate(items):
            self.card(sl, 0.6 + i * w, y, w - 0.25, 1.9)
            self.text(sl, 0.75 + i * w, y + 0.15, w - 0.5, 0.9, n, 34, True, GREEN)
            self.text(sl, 0.75 + i * w, y + 1.05, w - 0.5, 0.8, l, 12, False, MUTED)

    def save(self, name):
        p = os.path.join(OUTDIR, name)
        self.prs.save(p)
        return p


def evidence_slides(d, prefix):
    """지시서 14절 필수 증빙 12종: 화면마다 화면명·ID·요구사항·기능·작동·데이터·시험 결과를 함께 표시"""
    at = E.e2e()[1]
    for key, t, sid, req, f, how, data, res in C.EVIDENCE12:
        sl = d.slide(f"{prefix} · {t}", f"{sid} · {req} · 실행 {at} · 데이터: {data} · 시험: {res}",
                     notes=f"{t} 화면입니다. {f}. {how}. 실제 실행 화면이며 {data} 값입니다. 시험 결과는 {res}입니다.")
        d.pic(sl, E.shot(key), 0.6, 1.6, 8.6, 5.3)
        d.card(sl, 9.45, 1.6, 3.25, 5.3)
        d.text(sl, 9.6, 1.75, 3.0, 5.0, ["**구현 기능**", f, "", "**실제 작동**", how, "", "**시험 결과**", res], 12)


def code_slide(d, title, sub, path, start, end_marker, max_lines=22, notes=""):
    lines = open(os.path.join(E.ROOT, path), encoding="utf-8").read().split("\n")
    i = next(k for k, l in enumerate(lines) if start in l)
    out = []
    for l in lines[i:i + max_lines]:
        out.append(l)
        if end_marker and end_marker in l and len(out) > 1:
            break
    sl = d.slide(title, sub + f" · {path}", notes=notes)
    d.card(sl, 0.6, 1.6, 12.1, 5.3, fill=RGBColor(0xF6, 0xF8, 0xFA))
    tb = d.text(sl, 0.8, 1.7, 11.8, 5.1, out, 11, False, INK)
    for p in tb.text_frame.paragraphs:
        p.space_after = Pt(0)
        for r in p.runs:
            r.font.name = "Consolas"


def test_chart(d, sl, x, y, w, h):
    rows = [r for r in test_summary_rows() if isinstance(r[1], int)]
    cd = CategoryChartData(); cd.categories = [r[0].split(" (")[0] for r in rows]
    cd.add_series("통과", [r[2] for r in rows]); cd.add_series("실패", [r[3] for r in rows])
    ch = sl.shapes.add_chart(XL_CHART_TYPE.BAR_STACKED, Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
    ch.font.name = FONT; ch.font.size = Pt(11); ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
    ch.series[0].format.fill.solid(); ch.series[0].format.fill.fore_color.rgb = GREEN
    ch.series[1].format.fill.solid(); ch.series[1].format.fill.fore_color.rgb = RED
    pl = ch.plots[0]; pl.gap_width = 60; pl.has_data_labels = True
    pl.data_labels.font.size = Pt(10); pl.data_labels.position = XL_LABEL_POSITION.CENTER
    pl.data_labels.font.color.rgb = WHITE
    ch.value_axis.major_gridlines.format.line.color.rgb = RGBColor(0xEE, 0xEE, 0xEE)


def pct(v):
    """'100.000' → '100%', '99.950' → '99.95%' (큰 숫자 카드가 줄바꿈되지 않게)"""
    return (v.rstrip("0").rstrip(".") + "%") if v else "-"


VIDEO_URL = (os.environ.get("TODAK_VIDEO_URL") or "").split(" ")[0] or None


def link_button(d, sl, x, y, w, h, label, url):
    """누르면 바로 열리는 버튼 (도형 전체에 하이퍼링크)"""
    from pptx.enum.shapes import MSO_SHAPE
    b = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    b.fill.solid(); b.fill.fore_color.rgb = GREEN; b.line.fill.background()
    b.click_action.hyperlink.address = url
    f = b.text_frame; f.margin_left = f.margin_right = Inches(0.1)
    d.tf(f, label, 15, True, WHITE, PP_ALIGN.CENTER)  # 글자에는 링크를 걸지 않아 흰색 유지, 도형 전체가 링크
    f.vertical_anchor = MSO_ANCHOR.MIDDLE


def assignment_slide(d, here):
    """과제 공지 3개 항목이 01~04 중 어디에 있는지"""
    sl = d.slide("과제 요구와 이 문서의 위치", f"이 문서: {here}", notes="과제 공지의 세 가지 요구가 네 개 문서 중 어디에 있는지 정리했습니다.")
    d.table(sl, 0.6, 1.6, 12.1, ["과제 공지", "어디에 있나"], ASSIGN, [5.2, 6.9], 13, 0.85)


def tasks_slide(d, title):
    """과제 1번 손 농사 6가지 — 구현 결과"""
    sl = d.slide(title, "빨간 글자 = 미구현 (계획서에서도 범위 밖·확장으로 정한 항목)",
                 notes="여섯 가지 작업의 구현 결과입니다. 햇빛, 온도, 영양액은 자동 제어로 구현해 시뮬레이터로 검증했고, 벌 수정은 알림, 씨 뿌리기와 수확 판별은 계획대로 범위 밖과 확장입니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["작업", "결과", "구현 내용", "검증"], [(r[0], r[2], r[3], r[4]) for r in C.task_rows(True)], [1.6, 2.2, 6.3, 2.0], 10, 0.78)


def learned_slides(d):
    """과제 2번 시스템 설계·분석에서 배운 점"""
    sl = d.slide("", dark=True, notes="과제 2번, 시스템 설계·분석에서 배운 점입니다.")
    d.text(sl, 0.8, 2.6, 11.5, 1.5, ["과제 2번", "시스템 설계·분석에서 배운 점"], 40, True, WHITE)
    sl = d.slide("시스템 분석·설계 이론을 이번 과제에 적용한 것", notes="수업에서 배운 개념을 이번 과제에 어떻게 적용했는지 정리했습니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["개념", "이번 과제에 적용한 내용"], C.THEORY, [3.4, 8.7], 12.5, 0.6)
    for part, chunk in ((1, C.LEARNED[:4]), (2, C.LEARNED[4:])):
        sl = d.slide(f"배운 점 ({part}/2)", notes="이번 과제를 하며 실제로 겪은 일에서 배운 점입니다.")
        for i, (h, body) in enumerate(chunk):
            x = 0.6 + (i % 2) * 6.15
            y = 1.5 + (i // 2) * 2.7
            d.card(sl, x, y, 5.9, 2.5)
            d.text(sl, x + 0.2, y + 0.12, 5.5, 0.5, h, 15, True, GREEN)
            d.text(sl, x + 0.2, y + 0.65, 5.5, 1.8, body, 11)
    d.text(sl, 0.6, 6.75, 12.1, 0.35, C.AI_NOTE, 10, False, MUTED)


def access_slide(d):
    """바로 확인하기: 웹 주소·시연 영상·계정"""
    sl = d.slide("바로 확인하기 — 웹 주소 · 시연 영상", "아래 버튼을 누르면 로그인 없이 바로 열립니다 (슬라이드 쇼에서도 클릭 가능)", notes="실행 중인 시스템을 직접 확인하는 방법입니다.")
    rows = C.access_rows()
    btns = [(t, u) for t, u in (("▶  사이트 바로 열기 (로그인 없이)", SITE and SITE + "/demo"), ("▶  시연 영상 보기", VIDEO_URL), ("▶  GitHub 소스 보기", GITHUB)) if u]
    y = 1.55
    if btns:
        w = (12.1 - 0.25 * (len(btns) - 1)) / len(btns)
        for i, (label, url) in enumerate(btns):
            link_button(d, sl, 0.6 + i * (w + 0.25), y, w, 0.62, label, url)
        y += 0.85
    d.table(sl, 0.6, y, 12.1, ["항목", "주소·방법"], rows, [3.3, 8.8], 11, 0.5)
    d.text(sl, 0.6, min(y + 0.5 * (len(rows) + 1) + 0.12, 6.75), 12.1, 0.4, "하우스 센서·장치 값은 시뮬레이터(B안) 데이터 · 외부 기상(10월)은 기상청 양평 실측 · 파란 밑줄 글자와 버튼은 누르면 바로 열립니다", 11, False, MUTED)


def req_status_slides(d):
    """요구사항 25건 완료 현황 (개발 보고서·완료 보고서 공통)"""
    for part, rows in (("기능 요구사항 18건", [r for r in C.REQ_STATUS if r[0].startswith("REQ-F")]),
                       ("비기능 요구사항 7건", [r for r in C.REQ_STATUS if r[0].startswith("REQ-N")])):
        sl = d.slide(f"요구사항 완료 현황 · {part}", "빨간 글자 = 미구현 또는 측정 불가 · 화면·API·소스·시험·증빙 연결은 docs/RTM.md",
                     notes="요구사항별 상태입니다. 추적 매트릭스에는 화면, API, 소스, 시험, 증빙까지 이어서 적었습니다.")
        rh = 0.28 if len(rows) > 10 else 0.5
        d.table(sl, 0.6, 1.6, 12.1, ["ID", "요구사항", "상태", "검증"], [(a, b, c, e) for a, b, c, dd, e in rows], [1.6, 3.4, 2.6, 4.5], 11 if len(rows) > 10 else 13, rh)


def dev_deck():
    d = Deck(f"TODAK 시스템 개발 보고서 v1.0  |  실제 구현·시험 결과  |  {TODAY}")
    t, p = totals()
    d.cover("방울토마토 스마트 농업 정보시스템\n시스템 개발 보고서", "계획서대로 만든 것, 바꾼 것, 실제로 돌려 본 결과", "TODAK-DEV-001",
            "개발 계획서 v2.0을 바탕으로 실제로 실행되는 시스템을 만들었습니다. 오늘은 무엇을 만들었고 어떻게 시험했는지, 실제 실행 화면과 함께 보고드립니다.")
    assignment_slide(d, "03 시스템 개발 보고서 — 작업별 구현 결과 포함")
    access_slide(d)
    tasks_slide(d, "손 농사 6가지 작업 — 어떻게 구현했나 (과제 1번)")

    sl = d.slide("한 장 요약: 계획서의 시스템이 실제로 돌아간다", notes="숫자 네 개로 요약합니다. 테이블 22개, API 묶음 10개, 자동 시험 통과 수, 그리고 실행 화면을 자동으로 찍어 증빙으로 남겼습니다.")
    d.stats(sl, [("22", "MySQL 테이블\n(FK 36개, Flyway V1~V3)"), ("5", "Docker 컨테이너\n(DB·MQTT·API·시뮬레이터·웹)"),
                 (f"{p}/{t}", "자동 시험 통과\n(단위·통합·E2E·시나리오)"), ("7", "자동 제어 규칙\n(CR-01~07, 히스테리시스)")])
    d.text(sl, 0.6, 3.9, 12.1, 2.9, ["**무엇을**: 관리자·농가·조회 전용 화면, 1분 수집, 자동 제어, 경보, 원격 제어, GDD 분석, 회원가입·승인",
                                     "**어떻게**: React + Spring Boot + MySQL + MQTT, 실제 장비 대신 같은 규격의 가상 센서·장치 시뮬레이터",
                                     "**검증**: JUnit(실제 MySQL)·Vitest·Playwright E2E·시나리오·k6 성능 — 결과 파일과 화면을 docs/Test_Evidence에 보관",
                                     "**정직하게**: 측정값은 모두 시뮬레이션 데이터, 확장 기능(F-05·F-07)은 미구현" + (f", 소스는 {GITHUB} (공개)" if GITHUB else ", GitHub 업로드 전")], 15)

    sl = d.slide("계획서와 달라진 점", "모두 이유를 남겼다 · 항목별 대조는 docs/Development_Plan/계획서_대비_구현_검토.md", notes="계획서와 다르게 구현한 곳입니다. 대부분 후속 지시서를 따르거나 보안·안전을 강화하려고 바꿨습니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["항목", "계획서 v2.0", "실제 구현", "이유"], C.PLAN_CHANGES, [1.8, 2.6, 4.6, 3.1], 10, 0.46)

    sl = d.slide("최종 기술 스택과 구조", "계획서와 다른 곳은 이유를 남겼다", notes="계획서와 다르게 쓴 기술은 세 가지입니다. MUI 대신 Tailwind는 후속 지시서가 지정했고, Java는 21로, MQTT는 Paho를 직접 써서 단순하게 했습니다.")
    d.table(sl, 0.6, 1.7, 7.2, ["영역", "기술", "계획서 대비"], [
        ("웹", "React 18 · TS · Tailwind · Recharts", "MUI → Tailwind"), ("API", "Spring Boot 3.3 · Java 21 · JWT", "Java 17 → 21"),
        ("DB", "MySQL 8.4 · Flyway", "20 → 22 테이블"), ("IoT", "Mosquitto 2 · Paho · Python", "Spring Integration → Paho"),
        ("시험", "JUnit 5 · Vitest · Playwright · k6", "E2E 추가"), ("실행", "Docker Compose · nginx", "같음")], [1.2, 3.6, 2.4], 12, 0.5)
    d.pic(sl, os.path.join(E.DIAG, "d_architecture_final.png"), 8.1, 1.7, 4.6, 4.9)

    sl = d.slide("데이터베이스: 실제 DDL에서 그린 ERD", "22개 테이블, FK 36개 · V3에서 가입 승인·규칙 세부 조건·기기 토큰 추가", notes="ERD는 손으로 그리지 않고 실제 마이그레이션 파일에서 자동으로 뽑았습니다. 그래서 문서와 DB가 어긋나지 않습니다.")
    d.pic(sl, os.path.join(E.DIAG, "erd.png"), 0.6, 1.6, 12.1, 5.3)

    sl = d.slide("인증·권한: 메뉴를 숨기는 것으로 끝내지 않는다", notes="권한은 화면이 아니라 서버가 검사합니다. 농가가 주소창에 다른 농장 번호를 넣어도 403이 나옵니다. 리프레시 토큰은 쓸 때마다 바뀌고, 훔친 토큰을 다시 쓰면 그 계열 전체가 끊깁니다.")
    items = [("JWT 15분 + Refresh 회전", "HttpOnly 쿠키, 해시만 저장, 재사용 시 계열 전체 폐기"),
             ("가입 → 관리자 승인", "역할·농장 지정 후 사용, 첫 로그인 임시 비밀번호 변경"),
             ("역할 3종 + 농장 격리", "ADMIN·FARMER·VIEWER, 다른 농장 403"),
             ("비밀번호 정책·잠금", "영문·숫자·특수 8자+, 5회 실패 10분 잠금")]
    for i, (a, b) in enumerate(items):
        x = 0.6 + (i % 2) * 6.15; y = 1.6 + (i // 2) * 2.6
        d.card(sl, x, y, 5.9, 2.3)
        d.text(sl, x + 0.25, y + 0.2, 5.4, 0.6, a, 20, True, GREEN)
        d.text(sl, x + 0.25, y + 0.95, 5.4, 1.2, b, 15, False, INK)

    sl = d.slide("실제 프로젝트 구조", "백엔드·프런트·시뮬레이터·인프라·도구·문서를 한 저장소에", notes="저장소 하나에 서버, 웹, 시뮬레이터, 실행 설정, 시험 도구, 문서가 모두 들어 있습니다.")
    tb = d.text(sl, 0.6, 1.6, 12.1, 5.3, C.PROJECT_TREE.split("\n"), 12)
    for para in tb.text_frame.paragraphs:
        para.space_after = Pt(0)
        for r in para.runs:
            r.font.name = "Consolas"
    code_slide(d, "주요 소스 코드 ① 히스테리시스 판단", "작동값과 해제값 사이에서는 현재 상태 유지 → 켜졌다 꺼졌다 반복 방지",
               "backend/src/main/java/kr/todak/control/RuleDecision.java", "public static Want decide", "throw new IllegalArgumentException",
               notes="자동 제어의 핵심인 히스테리시스 판단 코드입니다.")
    code_slide(d, "주요 소스 코드 ② 유효적산온도(GDD) 계산", "GDD = max(0, min(일평균, 상한) − 기준), 수집률 80% 미만은 불완전",
               "backend/src/main/java/kr/todak/analytics/GddCalculator.java", "public static double gdd(", None, 24,
               notes="GDD 계산 코드입니다. 손으로 계산한 7일치와 오차 0.1 이하인지 단위 시험으로 확인했습니다.")
    code_slide(d, "주요 소스 코드 ③ Refresh Token 회전", "쓸 때마다 새 토큰, 이미 쓴 토큰이 다시 오면 같은 계열 전체 폐기",
               "backend/src/main/java/kr/todak/auth/AuthService.java", "public Tokens refresh(", "return new Tokens", 26,
               notes="로그인 유지 토큰을 쓸 때마다 바꾸고, 훔친 토큰을 다시 쓰면 모두 끊는 코드입니다.")

    rate = E.ingest_rate()
    sl = d.slide("통신 데이터 수집 결과", "시뮬레이터 → MQTT → 서버 → MySQL (센서 11채널, 1분 주기)", notes="서버가 받은 메시지는 하나도 버리지 않고 저장했습니다. 개발 PC가 절전에 들어간 동안은 측정값 자체가 만들어지지 않아 그 구간은 비어 있습니다.")
    cnt = rate["counts"] or ("-", "-", "-", "-")
    d.stats(sl, [(pct(rate["rate"]), "수신 대비 처리 성공률\n(저장+중복)/수신, 목표 99.9%"), (cnt[0], "수신 메시지 (백엔드 기동 후)"),
                 (cnt[3], "거부된 메시지"), ("0건", "중복 재전송 100건 시험\n추가 저장 (IngestIntegrationTest)")])
    d.text(sl, 0.6, 3.8, 12.1, 3.0, ["**검증**: 형식·필수 필드 → msgId 중복 제거 → 범위(OUT_RANGE)·급변(SPIKE) 플래그 → 저장 → SSE 발행",
                                     "**통신 단절**: 게이트웨이 LWT로 오프라인 경보, 현장 안전 운전, 복구 후 버퍼 재전송(누락 없음 — 시나리오 시험)",
                                     "**MQTT 장애 대비**: HTTP 대체 수집 API(기기 토큰)",
                                     "**주의**: PC 절전으로 컨테이너가 멈춘 시간에는 측정값이 없음 (실제 공백, 메우지 않음)"], 14)

    evidence_slides(d, "실행 화면")

    sl = d.slide("자동 제어: 계획서 표 39 그대로", "히스테리시스 · 최소 작동 · 지속 시간 · 간격 · 안전 한계 우선", notes="임계값 근처에서 켜졌다 꺼졌다 하지 않도록 켜는 값과 끄는 값을 다르게 두었습니다. 안전 한계 35도와 5도는 사람이 수동으로 조작 중이어도 개입합니다.")
    d.table(sl, 0.6, 1.7, 12.1, ["규칙", "작동 / 해제", "동작", "추가 조건"], [
        ("CR-01 주간 환기", "≥28 / ≤26℃", "측창 → 5분 뒤 ≥30이면 환기팬", "최소 3분"), ("CR-02 야간 난방", "≤14 / ≥16℃", "난방기", "최소 5분"),
        ("CR-03 차광", "≥800 / ≤500 W/㎡", "차광막", "10분 지속 · 시간당 2회"), ("CR-04 관수", "≤55 / ≥65 %", "구역별 밸브", "1회 5분 · 일 12회 · 30분 간격"),
        ("CR-05 고온 안전", "≥35 / ≤32℃", "측창·환기팬 강제 + 경보", "수동보다 우선"), ("CR-06 저온 안전", "≤5 / ≥8℃", "난방 + 측창 닫기 + 경보", "수동보다 우선"),
        ("CR-07 보광", "≤100 / ≥200 W/㎡", "보광등", "주간만")], [2.6, 2.6, 4.2, 2.7], 13, 0.5)

    sl = d.slide("시나리오 시험: 이상 상황을 일부러 만들어 확인", "관리자 화면의 시나리오 버튼과 같은 경로로 실행 (tools/scenario_test.py)", notes="고온, 저온, 습도, 관수 부족, 센서 무응답, 통신 단절을 차례로 일으키고 경보와 제어 명령이 실제로 생기는지 판정했습니다.")
    sc = E.scenarios()
    if sc:
        d.table(sl, 0.6, 1.7, 12.1, ["시나리오", "판정", "확인한 것"], [(r["name"], "통과" if r["pass"] else "미통과",
                                                                      " · ".join(("✓" if c["ok"] else "✗") + c["item"] for c in r["checks"])) for r in sc], [2.6, 1.2, 8.3], 11, 0.62)
    else:
        d.text(sl, 0.6, 2, 12, 1, "시나리오 결과 파일이 없다.", 16)

    sl = d.slide("개발 중 문제와 해결", notes="개발하면서 실제로 막혔던 문제들입니다. 특히 노트북이 절전에 들어갔다 깨어났을 때 밀린 메시지 때문에 연결이 계속 끊기는 문제가 있었고, 수신 처리를 별도 스레드로 옮겨 해결했습니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["문제", "해결"], [(a, c) for a, b, c in C.PROBLEMS], [4.5, 7.6], 11, 0.46)

    sl = d.slide(f"시험 결과: {p}/{t} 통과", "실패·미실행도 그대로 표시 · 상세는 docs/Test_Evidence", notes="자동 시험 결과입니다. 백엔드는 실제 MySQL에 붙여서 돌렸고, E2E는 실제 브라우저로 회원가입부터 승인, 로그인, 권한 차단, 모바일 화면까지 확인했습니다.")
    test_chart(d, sl, 0.6, 1.6, 7.4, 5.2)
    pr = perf_rows()
    d.table(sl, 8.3, 1.7, 4.4, ["성능 항목", "측정값"], [(a.split(" (")[0], c) for a, b, c, dd in pr], [2.4, 2], 11, 0.6)

    req_status_slides(d)

    sl = d.slide("", dark=True, notes="정리하면, 계획서의 MVP 요구사항은 시뮬레이터로 모두 동작을 확인했고, 확장 기능과 실제 장비 연결은 다음 단계입니다.")
    d.text(sl, 0.8, 1.6, 11.5, 0.8, "다음 단계", 32, True, WHITE)
    d.text(sl, 0.8, 2.6, 11.5, 3.8, [("1. GitHub Actions CI 실행 확인 (저장소 업로드 완료)" if GITHUB else "1. GitHub 업로드 후 CI 실행, 저장소 주소를 보고서에 기재"),
                                     "2. 기상청 자료 정기 갱신 (지금은 2026-10-01~26 실측 CSV를 가져와 외부 GDD 검증 완료)",
                                     "3. 실장비(A안) 연결 전 전기·설비 안전 검증, '알림만' 1주 시범",
                                     "4. 수확 판별(F-07)용 이미지 수집 시작"], 20, False, MOSS)
    return d.save("03_시스템_개발_보고서_v1.0.pptx")


def done_deck():
    d = Deck(f"TODAK 시스템 개발 완료 보고서 v1.0  |  계획 대비 실적  |  {TODAY}")
    t, p = totals()
    pf = E.perf()
    d.cover("방울토마토 스마트 농업 정보시스템\n개발 완료 보고서", "계획 대비 실적 · 시험·성능·보안 검증 · 남은 일", "TODAK-CMP-001",
            "개발을 마치고 계획 대비 실적을 보고드립니다. 결론부터 말씀드리면 MVP 16건은 모두 시뮬레이터로 동작을 확인했고, 확장 기능 2건과 운영 측정 항목은 남아 있습니다.")
    assignment_slide(d, "04 시스템 개발 완료 보고서 — 작업별 구현 결과 · 배운 점(뒤쪽) 포함")
    access_slide(d)
    tasks_slide(d, "손 농사 6가지 작업 — 구현 결과 (과제 1번)")

    sl = d.slide("결론: MVP 16건 완료, 확장 2건은 다음 단계", notes="요구사항 25건 중 확장 범위인 육묘 모니터링과 수확 판별은 계획서대로 미구현이고, 가용성은 운영 한 달이 지나야 잴 수 있습니다.")
    done = sum(1 for r in C.REQ_STATUS if r[2].startswith("완료") or r[2] == "측정 완료")
    d.stats(sl, [(f"{done}/25", "요구사항 완료\n(기능 18 · 비기능 7)"), (f"{p}/{t}", "자동 시험 통과"),
                 (f"{pf['ack_p95'] / 1000:.1f}초" if pf and pf.get("ack_p95") else "-", "제어 요청→실행 확인 p95\n(목표 5초)"),
                 (pct(E.ingest_rate()["rate"]), "수신 대비 저장 성공률\n(목표 99.9%)")])
    d.text(sl, 0.6, 3.9, 12.1, 2.8, ["**완료**: 수집·자동 제어·경보·원격 제어·GDD·기준값·구역·권한·가입 승인·시뮬레이터",
                                     "**미구현(확장)**: F-05 육묘 모니터링, F-07 수확 판별, 문자 알림",
                                     "**운영 단계**: 가용성 99.5%, HTTPS 배포, 농가 사용성 시험, 실장비(A안) 연결",
                                     "**주의**: 하우스 측정값은 시뮬레이션 데이터(외부 기상만 기상청 실측) · " + ("GitHub 저장소에 소스 업로드 완료" if GITHUB else "GitHub 업로드 전") + (" · 공개 웹 주소: " + SITE if SITE else " · 웹 배포 안 함")], 15)

    sl = d.slide("사업 개요와 목표", notes="양평 100평 하우스, 5천만 원, 12주 사업입니다. 목표는 수집, 자동 제어, 경보, 원격 제어, 생육 분석을 하나의 웹으로 제공하는 것이었습니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["항목", "내용"], [("사업명", "양평 방울토마토 스마트 농업 정보시스템(TODAK) 구축"), ("대상", "경기도 양평군 비닐하우스 1동 100평(330.58㎡), 관리 구역 2개"),
                                                ("사업비·기간", "50,000,000원(VAT 포함) · 12주 (2026.11.02~2027.01.22, 가상 사업 기간) · 폭포수"),
                                                ("목표", "환경 1분 수집 · 자동 제어 · 이상 알림 · 원격 제어 · 생육 분석(GDD)을 하나의 반응형 웹으로"),
                                                ("실행 방안", "B안 가상 센서 시뮬레이터로 전 과정 검증 (A안 실장비는 확보 후)")], [2.2, 9.9], 15, 0.65)

    sl = d.slide("계획 대비 실제 범위", notes="계획서와 다르게 구현한 곳은 검토서에 모두 적었습니다. 화면은 계획보다 늘었고, API 경로는 후속 지시서의 묶음에 맞췄습니다.")
    d.table(sl, 0.6, 1.6, 12.1, ["구분", "계획", "실제"], [("MVP 요구사항", "16건", "16건 완료 (시뮬레이터 검증)"), ("확장", "F-05 · F-07 · SMS", "미구현 (계획과 같음)"),
                                                        ("화면", "SCR-01~10", "SCR-01~08·10 + 회원가입·내 정보·관리자 6화면"),
                                                        ("API", "API-01~27", "확장 2개 제외 전부 + 계정·관리 API"), ("DB", "20 테이블", "22 테이블"),
                                                        ("사용자 요청 추가", "-", "회원가입·승인·비밀번호 찾기·내 정보")], [2.5, 3.5, 6.1], 14, 0.6)

    sl = d.slide("계획서와 달라진 점", "모두 이유를 남겼다 · 항목별 대조는 docs/Development_Plan/계획서_대비_구현_검토.md", notes="계획서와 다르게 구현한 곳입니다. 대부분 후속 지시서를 따르거나 보안·안전을 강화하려고 바꿨습니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["항목", "계획서 v2.0", "실제 구현", "이유"], C.PLAN_CHANGES, [1.8, 2.6, 4.6, 3.1], 10, 0.46)

    req_status_slides(d)

    sl = d.slide("최종 시스템 구성도", "React 웹 · Spring Boot · MySQL · MQTT(Mosquitto) · 시뮬레이터(GW-01 역할)", notes="최종 구성입니다. 실장비를 붙일 때는 시뮬레이터 자리에 같은 규격의 게이트웨이가 들어갑니다.")
    d.pic(sl, os.path.join(E.DIAG, "d_architecture_final.png"), 0.6, 1.55, 12.1, 5.35)
    sl = d.slide("최종 데이터베이스 구성", "MySQL 8.4 · 22개 테이블 · FK 36개 · 원시 3년 보존, 시간 집계 영구", notes="실제 DDL에서 자동으로 만든 ERD입니다.")
    d.pic(sl, os.path.join(E.DIAG, "erd.png"), 0.6, 1.6, 12.1, 5.3)
    sl = d.slide("인수 테스트 체크리스트 (18항목)", "결과는 증빙 파일에서 자동 판정 · docs/Test_Evidence/인수테스트_체크리스트.md", notes="인수 기준 18항목입니다. GitHub 업로드와 다른 PC 설치 시험은 사유를 적었습니다.")
    import checklist as CK
    d.table(sl, 0.6, 1.5, 12.1, ["#", "인수 기준", "결과"], [(a, b, c.replace("✅ ", "").replace("⚠️ ", "").replace("⏸ ", "")) for a, b, _, c, _ in CK.ROWS], [0.5, 9.4, 2.2], 10, 0.28)

    for key in ("12_viewer_control_readonly", "06a_admin_users_pending"):
        s = next(x for x in C.SCREENS if x[0] == key)
        sl = d.slide(f"구현 결과 · {s[1]}", f"{s[2]} · {s[3]}", notes=f"{s[1]} 실제 실행 화면입니다.")
        d.pic(sl, E.shot(key), 0.6, 1.6, 12.1, 5.3)

    sl = d.slide("성능 측정 (k6)", "개발 PC 1대 Docker Compose 기준 — 운영 서버 값 아님", notes="조회는 7일치 원시 데이터 약 만 건을 가져오는 요청으로 쟀고, 제어는 버튼을 누른 뒤 장치가 실행을 확인할 때까지의 시간입니다.")
    d.table(sl, 0.6, 1.7, 12.1, ["항목", "목표", "측정값", "판정"], perf_rows(), [5, 2.4, 3.2, 1.5], 14, 0.6)

    rows = E.uiux()
    if rows:
        sl = d.slide("UI/UX 기준 점검 — 18개 화면 × PC·휴대폰", "계획서 REQ-N-06·07, 화면 설계, KWCAG 2.2 · 실제 화면을 열어 계산된 스타일로 측정 (tools/uiux_audit.py)",
                     notes="화면을 사람 눈으로만 본 것이 아니라 글자 크기, 명도 대비, 360픽셀 가로 넘침, 입력 레이블, 누르는 대상 크기를 자동으로 쟀습니다. 처음 점검에서 나온 문제를 고친 뒤 다시 잰 결과입니다.")
        d.table(sl, 0.6, 1.55, 12.1, ["기준", "결과", "판정"], [(a, b.replace("\n", " "), c) for a, b, c in rows], [4.4, 6.7, 1.0], 11.5, 0.46)

    sl = d.slide("보안·인증 검증", notes="보안 항목은 자동 시험으로 확인했습니다. HTTPS는 운영 서버에 배포할 때 적용해야 합니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["항목", "결과"], [("BCrypt 저장 · 5회 실패 잠금 · 계정 존재 비노출", "통과"), ("Refresh 회전 · 재사용 탐지 · 로그아웃 무효화", "통과"),
                                                  ("HttpOnly·SameSite 쿠키 · CSRF 헤더", "통과"), ("관리자 API 이중 차단 · 농가 간 격리", "통과"),
                                                  ("조회 전용 제어 차단 · 가입 승인 전 로그인 차단", "통과"), ("비밀정보 저장소 제외 (.env)", "확인"),
                                                  ("HTTPS · MQTT TLS", "미적용 (운영 배포 시)")], [8.5, 3.6], 14, 0.55)

    sl = d.slide("구현되지 않은 것과 다음 단계", notes="안 된 것을 된 것처럼 적지 않았습니다. 다음 단계는 실장비 연결과 수확 판별입니다.")
    d.table(sl, 0.6, 1.5, 12.1, ["항목", "이유", "다음 단계"], C.NOT_DONE, [3.8, 3.8, 4.5], 11, 0.55)

    sl = d.slide("실제 시스템 활용 가능성과 유지보수·확장", notes="서버, DB, 웹은 실장비에서도 그대로 씁니다. 실장비 적용 전 검증 조건을 지키고, 이후 수확 판별과 운영 배포를 진행합니다.")
    d.card(sl, 0.6, 1.5, 5.9, 5.3)
    d.text(sl, 0.85, 1.7, 5.4, 5.0, ["**활용 가능성**", "서버·DB·웹·MQTT 규격은 실장비(A안)에서도 그대로 사용 — 게이트웨이만 같은 토픽·JSON으로 연결",
                                     "실장비 전 조건(계획서 14.1): 시나리오·규칙 시험(완료), 장치별 수동 ON/OFF·ACK 확인, 통신 차단 1시간, 농가 입회 임계값 확인, 첫 1주 '알림만'",
                                     "현재 성능은 개발 PC 1대 기준 — 운영 서버에서 다시 측정"], 13)
    d.card(sl, 6.8, 1.5, 5.9, 5.3)
    d.text(sl, 7.05, 1.7, 5.4, 5.0, ["**유지보수·확장 계획**", "1. A안 실장비 연동(Modbus 게이트웨이) + 전기·설비 안전 검증", "2. 수확 판별(F-07): 이미지 수집 → OpenCV → API-24·25",
                                     "3. HTTPS·TLS, 운영 배포, 가용성 모니터링", "4. 문자 알림, 기상청 API 자동 연동", "5. GitHub Actions CI 상시 실행, 의존성 보안 점검",
                                     "6. 일 백업(tools/backup-db.sh) cron 등록"], 13)

    evidence_slides(d, "최종 실행 증빙")

    learned_slides(d)

    sl = d.slide("", dark=True, notes=("소스는 GitHub 공개 저장소에 올라가 있습니다. 실행은 docker compose 한 줄로 합니다." if GITHUB else "소스는 로컬 Git에 커밋되어 있고, 업로드는 아직 하지 않았습니다."))
    d.text(sl, 0.8, 1.4, 11.5, 0.8, "인도물", 32, True, WHITE)
    d.text(sl, 0.8, 2.4, 11.5, 4.2, ["소스: " + (f"{GITHUB} (공개)" if GITHUB else "TODAK-SmartFarm (로컬 Git) · GitHub 업로드 전"),
                                     ("웹 주소: " + SITE + "/demo (로그인 없이 둘러보기)" if SITE else "실행: docker compose up -d --build → http://localhost:8088 (웹 배포 안 함)"),
                                     "문서: README · 계획서 대비 검토서 · RTM · 인수 시험 체크리스트",
                                     "증빙: docs/Test_Evidence (실행 화면 · E2E · 시나리오 · 성능 · MySQL 조회)"], 18, False, MOSS)
    return d.save("04_시스템_개발_완료보고서_v1.0.pptx")


if __name__ == "__main__":
    print(dev_deck())
    print(done_deck())
