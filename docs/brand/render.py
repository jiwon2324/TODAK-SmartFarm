"""로고 SVG → PNG (투명 배경, 고해상도). 실행: docker playwright 이미지에서 python docs/brand/render.py"""
import os

from playwright.sync_api import sync_playwright

D = "docs/brand/v2"
ITEMS = [("app_icon.svg", 512, 512, 2, "todak_app_icon.png"), ("logo.svg", 262, 78, 8, "todak_logo.png"),
         ("logo_white.svg", 262, 78, 8, "todak_logo_white.png"), ("logo_black.svg", 262, 78, 8, "todak_logo_black.png")]
with sync_playwright() as p:
    b = p.chromium.launch()
    for src, w, h, s, out in ITEMS:
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=s)
        page = os.path.abspath(f"{D}/_render.html")
        open(page, "w", encoding="utf-8").write(f"<html><body style='margin:0;background:transparent'><img src='{src}' width='{w}' height='{h}'></body></html>")
        pg.goto("file://" + page)
        pg.wait_for_timeout(400)
        pg.screenshot(path=f"docs/brand/{out}", omit_background=True)
        print(out)
    b.close()
os.remove(os.path.abspath(f"{D}/_render.html"))
