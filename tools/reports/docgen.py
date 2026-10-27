# -*- coding: utf-8 -*-
"""python-docx 공통 서식: 표지, 목차, 머리글·바닥글, 표·그림 번호, 코드 블록."""
import os
import re
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, RGBColor, Emu

FONT = "맑은 고딕"
MONO = "Consolas"
GREEN = RGBColor(0x2E, 0x7D, 0x32)
GRAY = RGBColor(0x5F, 0x63, 0x68)
FIG = os.path.join(os.path.dirname(__file__), "fig")


def _font(run, name=FONT, size=None, bold=None, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def _field(par, instr, placeholder="1"):
    r = par.add_run(); f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin"); r._element.append(f1)
    r = par.add_run(); it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = f" {instr} "; r._element.append(it)
    r = par.add_run(); f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "separate"); r._element.append(f2)
    r = par.add_run(placeholder); _font(r)
    r = par.add_run(); f3 = OxmlElement("w:fldChar"); f3.set(qn("w:fldCharType"), "end"); r._element.append(f3)


def _shade(cell, hexcolor):
    tcPr = cell._element.get_or_add_tcPr()
    sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexcolor)
    tcPr.append(sh)


def _borders(table, color="BDBDBD"):
    tblPr = table._element.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{e}"); el.set(qn("w:val"), "single"); el.set(qn("w:sz"), "4"); el.set(qn("w:color"), color)
        b.append(el)
    tblPr.append(b)


def _repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); trPr.append(h)


# 제출자 정보 (표지)
STUDENT = ("작성자", "한양여자대학교 · 학번 2402180 · 양지원")
COURSE = "데이터 기획 및 분석 · 1학기 중간고사 대체과제"


URL_RE = re.compile(r"(https?://[^\s()<>]+[^\s()<>.,·])")


def _hyperlink(par, run, url):
    """이미 만든 글자(run)를 눌러서 열리는 외부 링크로 감싼다 (파란 밑줄)"""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    rid = par.part.relate_to(url, RT.HYPERLINK, is_external=True)
    run.font.color.rgb = RGBColor(0x15, 0x65, 0xC0)
    run.font.underline = True
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), rid)
    run._r.addprevious(h)
    h.append(run._r)


class Doc:
    def __init__(self, title, subtitle, doc_id, version, status):
        self.d = Document()
        self.title, self.doc_id, self.version, self.status = title, doc_id, version, status
        self.subtitle = subtitle
        self.tab_no = 0; self.fig_no = 0
        sec = self.d.sections[0]
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        sec.left_margin = sec.right_margin = Cm(2.2); sec.top_margin = Cm(2.3); sec.bottom_margin = Cm(2.0)
        self.width_cm = 21.0 - 4.4
        st = self.d.styles
        normal = st["Normal"]; normal.font.name = FONT; normal.font.size = Pt(10)
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        normal.paragraph_format.space_after = Pt(4); normal.paragraph_format.line_spacing = 1.25
        for lvl, size, col in ((1, 16, GREEN), (2, 13, RGBColor(0x20, 0x21, 0x24)), (3, 11, RGBColor(0x20, 0x21, 0x24))):
            hs = st[f"Heading {lvl}"]
            hs.font.name = FONT; hs.font.size = Pt(size); hs.font.bold = True; hs.font.color.rgb = col
            hs.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
            hs.paragraph_format.space_before = Pt(14 if lvl == 1 else 10); hs.paragraph_format.space_after = Pt(6)
            hs.paragraph_format.keep_with_next = True
        for name in ("List Bullet", "List Number"):
            s = st[name]; s.font.name = FONT; s.font.size = Pt(10)

    # ---------- 표지·관리 ----------
    def cover(self, client="방울토마토 재배 농가 (가상 발주처, 경기도 양평군)", author="TODAK 프로젝트팀", date="2026.10.26"):
        d = self.d
        # 학교 로고 (한양여자대학교 공식 UI 페이지의 로고, docs/brand/)
        logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "brand", "hywoman_logo.png")
        if os.path.exists(logo):
            d.add_picture(logo, width=Cm(7.0))
        for _ in range(3):
            d.add_paragraph()
        todak = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "brand", "todak_logo.png")
        if os.path.exists(todak):
            d.add_picture(todak, width=Cm(6.0))  # TODAK 로고 (docs/brand)
        else:
            p = d.add_paragraph(); r = p.add_run("TODAK"); _font(r, size=14, bold=True, color=GREEN)
        p = d.add_paragraph(); r = p.add_run(self.title); _font(r, size=26, bold=True)
        p = d.add_paragraph(); r = p.add_run(self.subtitle); _font(r, size=13, color=GRAY)
        for _ in range(5):
            d.add_paragraph()
        rows = [("문서 번호", self.doc_id), ("버전", self.version), ("작성일", date), ("문서 상태", self.status),
                ("발주처", client), ("수행", author),
                (STUDENT[0], STUDENT[1]), ("과목", COURSE)]
        self.table(["항목", "내용"], rows, [4, 12.6], header=False, first_col_bold=True)
        self.page_break()

    def doc_control(self, history, approvals=True):
        self.h("문서 관리 정보", 1, numbered=False)
        self.table(["버전", "일자", "변경 내용", "작성자"], history, [2, 2.6, 9, 3], caption="개정 이력")
        if approvals:
            self.table(["구분", "성명", "소속·역할", "서명", "일자"],
                       [("작성", "양지원 (2402180)", "한양여자대학교 · 작성자", "", ""), ("검토", "(검토자)", "수행사 QA", "", ""),
                        ("승인", "(승인자)", "발주처 대표", "", "")], [2.2, 3, 4.6, 3.4, 3.4], caption="검토·승인")
        self.page_break()

    def toc(self):
        self.h("목차", 1, numbered=False)
        p = self.d.add_paragraph()
        _field(p, 'TOC \\o "1-3" \\h \\z \\u', "Word에서 문서를 열고 이 목차를 마우스 오른쪽 버튼 → '필드 업데이트'로 갱신하세요.")
        self.page_break()

    def header_footer(self):
        for sec in self.d.sections:
            sec.different_first_page_header_footer = True
            hp = sec.header.paragraphs[0]; hp.text = ""
            r = hp.add_run(f"TODAK  |  {self.title}  {self.version}"); _font(r, size=8, color=GRAY)
            hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = fp.add_run(f"{self.doc_id}   -  "); _font(r, size=8, color=GRAY)
            _field(fp, "PAGE", "1")
            r = fp.add_run("  -"); _font(r, size=8, color=GRAY)

    # ---------- 본문 ----------
    def h(self, text, level=1, numbered=True):
        self.d.add_heading(text, level)

    def p(self, text, bold=False, color=None, size=None, italic=False, align=None):
        par = self.d.add_paragraph()
        self._rich(par, text, bold, color, size)
        if italic:
            for r in par.runs:
                r.italic = True
        if align == "center":
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return par

    def _rich(self, par, text, bold=False, color=None, size=None):
        parts = text.split("**")
        for i, seg in enumerate(parts):
            for t in URL_RE.split(seg):
                if not t:
                    continue
                r = par.add_run(t); _font(r, size=size, bold=(bold or i % 2 == 1), color=color)
                if URL_RE.fullmatch(t):
                    _hyperlink(par, r, t)

    def note(self, text):
        return self.p(text, color=GRAY, size=8.5)

    def bullets(self, items, style="List Bullet"):
        for it in items:
            par = self.d.add_paragraph(style=style)
            self._rich(par, it)
            par.paragraph_format.space_after = Pt(2)

    def numbered(self, items):
        self.bullets(items, "List Number")

    def page_break(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def caption(self, kind, text):
        par = self.d.add_paragraph()
        if kind == "표":
            self.tab_no += 1; n = self.tab_no; seq = "Table"
        else:
            self.fig_no += 1; n = self.fig_no; seq = "Figure"
        r = par.add_run(f"{kind} "); _font(r, size=9, bold=True)
        _field(par, f"SEQ {seq} \\* ARABIC", str(n))
        for rr in par.runs[-2:]:
            pass
        r = par.add_run(f". {text}"); _font(r, size=9, bold=True)
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER if kind == "그림" else WD_ALIGN_PARAGRAPH.LEFT
        par.paragraph_format.keep_with_next = (kind == "표")
        return n

    def table(self, headers, rows, widths_cm=None, caption=None, header=True, first_col_bold=False, size=8.5, source=None):
        if caption:
            self.caption("표", caption)
        ncol = len(headers)
        t = self.d.add_table(rows=0, cols=ncol)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        _borders(t)
        if widths_cm is None:
            widths_cm = [self.width_cm / ncol] * ncol
        scale = self.width_cm / sum(widths_cm)
        widths_cm = [w * scale for w in widths_cm]
        if header:
            cells = t.add_row().cells
            _repeat_header(t.rows[0])
            for i, h in enumerate(headers):
                cells[i].text = ""
                r = cells[i].paragraphs[0].add_run(str(h)); _font(r, size=size, bold=True)
                _shade(cells[i], "E8F5E9")
        for row in rows:
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = ""
                lines = str(v).split("\n")
                for li, line in enumerate(lines):
                    par = cells[i].paragraphs[0] if li == 0 else cells[i].add_paragraph()
                    par.paragraph_format.space_after = Pt(0)
                    self._rich(par, line, bold=(first_col_bold and i == 0), size=size)
        for row in t.rows:
            for i, c in enumerate(row.cells):
                c.width = Cm(widths_cm[i])
                c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        if source:
            self.note(source)
        else:
            self.d.add_paragraph().paragraph_format.space_after = Pt(2)
        return t

    def figure(self, name, caption, explain=None, source=None, width_cm=None):
        path = os.path.join(FIG, name + ".png")
        par = self.d.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.add_run().add_picture(path, width=Cm(width_cm or self.width_cm))
        par.paragraph_format.keep_with_next = True
        self.caption("그림", caption)
        if explain:
            self.p(explain, size=9)
        if source:
            self.note(source)

    def image(self, path, caption, explain=None, width_cm=None, source=None):
        """임의 경로의 그림 (실행 화면 등). 파일이 없으면 '증빙 없음'을 적는다 — 그리지 않는다."""
        if not path or not os.path.exists(path):
            self.p(f"[증빙 파일 없음: {caption}]", color=GRAY)
            return
        from PIL import Image
        im = Image.open(path)
        w = width_cm or self.width_cm
        # 세로로 아주 긴 화면은 한 쪽에 들어가게 폭을 줄인다
        max_h = 21.0
        if im.height / im.width * w > max_h:
            w = max_h * im.width / im.height
        par = self.d.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.add_run().add_picture(path, width=Cm(w))
        par.paragraph_format.keep_with_next = True
        self.caption("그림", caption)
        if explain:
            self.p(explain, size=9)
        if source:
            self.note(source)

    def code(self, text, title=None):
        if title:
            self.p(title, bold=True, size=9)
        t = self.d.add_table(rows=1, cols=1); _borders(t, "E0E0E0")
        c = t.rows[0].cells[0]; _shade(c, "F6F8FA"); c.width = Cm(self.width_cm)
        c.text = ""
        for i, line in enumerate(text.rstrip("\n").split("\n")):
            par = c.paragraphs[0] if i == 0 else c.add_paragraph()
            par.paragraph_format.space_after = Pt(0); par.paragraph_format.line_spacing = 1.0
            r = par.add_run(line if line else " "); _font(r, name=MONO, size=8)
        self.d.add_paragraph().paragraph_format.space_after = Pt(2)

    def save(self, path):
        self.header_footer()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.d.save(path)
        return path
