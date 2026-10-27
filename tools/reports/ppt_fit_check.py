# -*- coding: utf-8 -*-
"""
PPT 넘침 검사: 그림·표·글상자가 슬라이드 밖이나 바닥글 영역으로 넘치는지 추정한다.
표는 글자 수·글자 크기·열 너비로 줄 수를 계산해 실제로 늘어날 높이를 추정한다 (PowerPoint는 표 행을 자동으로 늘린다).
실행: python3 tools/reports/ppt_fit_check.py deck.pptx [...]
"""
import math
import sys
import unicodedata

from pptx import Presentation
from pptx.util import Emu

LIMIT_IN = 7.08  # 바닥글(7.1인치) 위까지


def char_w(ch, pt):
    """글자 폭 추정(pt): 한글·전각은 글자 크기와 같고, 영문·숫자는 약 0.55배"""
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return pt * 1.0
    return pt * 0.56


def lines_for(text, pt, width_pt):
    n = 0
    for para in text.split("\n"):
        w = sum(char_w(c, pt) for c in para)
        n += max(1, math.ceil(w / max(width_pt, 1)))
    return n


def font_pt(tf, default=14):
    for p in tf.paragraphs:
        for r in p.runs:
            if r.font.size:
                return r.font.size.pt
    return default


def check(path):
    prs = Presentation(path)
    sw, sh = prs.slide_width, prs.slide_height
    issues = []
    for i, sl in enumerate(prs.slides, 1):
        for shp in sl.shapes:
            x, y, w, h = shp.left or 0, shp.top or 0, shp.width or 0, shp.height or 0
            name = shp.shape_type
            if x < 0 or y < 0 or x + w > sw + Emu(9525) or y + h > sh + Emu(9525):
                issues.append((i, f"{name} 슬라이드 밖으로 나감 ({Emu(x).inches:.2f},{Emu(y).inches:.2f},{Emu(w).inches:.2f}x{Emu(h).inches:.2f})"))
            if shp.has_table:
                tbl = shp.table
                total = 0
                for r in tbl.rows:
                    need = r.height
                    for ci, c in enumerate(r.cells):
                        pt = font_pt(c.text_frame, 11)
                        cw = tbl.columns[ci].width
                        lm = (c.margin_left or Emu(91440 * 0.1)) + (c.margin_right or Emu(91440 * 0.1))
                        width_pt = Emu(cw - lm).pt
                        n = lines_for(c.text_frame.text, pt, width_pt)
                        hh = Emu(int((n * pt * 1.2 + 6) * 12700))
                        need = max(need, hh)
                    total += need
                bottom = Emu(y + total).inches
                if bottom > LIMIT_IN and Emu(y).inches < LIMIT_IN:
                    issues.append((i, f"표가 아래로 넘칠 수 있음: 예상 바닥 {bottom:.2f}in (행 {len(tbl.rows)}개)"))
            elif shp.has_text_frame and shp.text_frame.text.strip() and shp.shape_type != 13:
                tf = shp.text_frame
                pt = font_pt(tf)
                width_pt = Emu(w).pt - 14
                n = sum(lines_for(p.text if p.text else " ", pt, width_pt) for p in tf.paragraphs)
                need_in = n * pt * 1.25 / 72
                bottom = Emu(y).inches + need_in
                if need_in > Emu(h).inches + 0.25 and bottom > LIMIT_IN:
                    issues.append((i, f"글상자 넘침 가능: '{tf.text[:24]}…' 필요 {need_in:.2f}in > 상자 {Emu(h).inches:.2f}in"))
    return issues


if __name__ == "__main__":
    bad = 0
    for p in sys.argv[1:]:
        iss = check(p)
        bad += len(iss)
        print(f"== {p.split('/')[-1]}: {len(iss)}건")
        for i, m in iss:
            print(f"  슬라이드 {i}: {m}")
    sys.exit(1 if bad else 0)
