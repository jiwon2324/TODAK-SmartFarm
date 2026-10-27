"""로고 SVG → PNG (투명 배경, 고해상도). docker playwright 이미지에서 실행"""
from playwright.sync_api import sync_playwright

ITEMS = [("todak_mark.svg", 68, 66, 8, "todak_mark.png"), ("todak_logo.svg", 300, 72, 6, "todak_logo.png"),
         ("todak_logo_white.svg", 300, 72, 6, "todak_logo_white.png")]
with sync_playwright() as p:
    b = p.chromium.launch()
    for src, w, h, s, out in ITEMS:
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=s)
        svg = open(f"docs/brand/{src}", encoding="utf-8").read()
        sized = svg.replace("<svg ", f'<svg width="{w}" height="{h}" ', 1)
        pg.set_content("<html><body style='margin:0;background:transparent'>" + sized + "</body></html>")
        pg.wait_for_timeout(300)
        pg.screenshot(path=f"docs/brand/{out}", omit_background=True, clip={"x": 0, "y": 0, "width": w, "height": h})
        print(out)
    b.close()
