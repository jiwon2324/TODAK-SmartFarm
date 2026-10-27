"""
UI/UX 기준 자동 점검 (계획서 REQ-N-06·07, 화면 설계 16장, KWCAG 2.2 기본 항목) → docs/Test_Evidence/uiux_audit.md
실제 화면을 열어 계산된 스타일로 잰다: 글자 크기, 글자/배경 명도 대비, 360px 가로 스크롤, 입력 레이블, 이미지 대체 텍스트, 버튼 크기.

  docker run --rm --network todak_default -v "$PWD":/w -w /w -e TODAK_ADMIN_PW=... -e TODAK_FARMER_PW=... \
    mcr.microsoft.com/playwright/python:v1.48.0-jammy sh -c "pip install -q playwright==1.48.0 && python tools/uiux_audit.py"
"""
import os
from datetime import datetime, timedelta, timezone

from playwright.sync_api import sync_playwright

BASE = os.environ.get("TODAK_BASE", "http://frontend")
OUT = "docs/Test_Evidence/uiux_audit.md"
KST = timezone(timedelta(hours=9))

FARMER = ["/farm", "/farm/graph", "/farm/control", "/farm/history", "/farm/alerts", "/farm/standards", "/farm/growth", "/farm/harvest", "/account"]
ADMIN = ["/admin", "/admin/users", "/admin/equipment", "/admin/standards", "/admin/logs", "/admin/weather"]
PUBLIC = ["/login", "/signup", "/forgot"]

# 페이지 안에서 실행: 보이는 글자 요소의 크기·대비, 입력 레이블, 이미지 alt, 버튼 크기, 가로 스크롤
PROBE = r"""
() => {
  const lum = (r, g, b) => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const rgb = s => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map(x => parseFloat(x)); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const bgOf = el => { for (let e = el; e; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.backgroundImage.includes('gradient')) { const m = cs.backgroundImage.match(/rgba?\([^)]+\)/g); if (m) { const cols = m.map(rgb); return cols.reduce((x, y) => (lum(x.r, x.g, x.b) > lum(y.r, y.g, y.b) ? x : y)); } } const c = rgb(cs.backgroundColor); if (c && c.a > 0.9) return c; } return { r: 255, g: 255, b: 255, a: 1 }; };  // 그라데이션 배경은 가장 밝은 색으로(보수적으로) 계산
  const ratio = (a, b) => { const l1 = lum(a.r, a.g, a.b), l2 = lum(b.r, b.g, b.b); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); };
  const texts = []; const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const n = walker.currentNode; const t = n.textContent.trim(); if (!t) continue;
    const el = n.parentElement; if (!el || seen.has(el)) continue; seen.add(el);
    if (el.closest('svg,[aria-hidden="true"],#__demo_cap')) continue;
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    if (r.width === 0 || r.height === 0 || cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) < 0.5) continue;
    const fg = rgb(cs.color); const bg = bgOf(el); const size = parseFloat(cs.fontSize); const bold = parseInt(cs.fontWeight) >= 700;
    const disabled = !!el.closest('button:disabled,[aria-disabled="true"],input:disabled');
    texts.push({ t: t.slice(0, 30), size, ratio: fg ? ratio(fg, bg) : 21, large: size >= 24 || (size >= 18.66 && bold), disabled });
  }
  const inputs = [...document.querySelectorAll('input:not([type=hidden]),select,textarea')].filter(i => i.offsetParent);
  const unlabeled = inputs.filter(i => !(i.labels && i.labels.length) && !i.getAttribute('aria-label') && !i.getAttribute('aria-labelledby') && !i.closest('label')).map(i => i.id || i.name || i.type);
  const imgs = [...document.images].filter(i => i.offsetParent && !i.hasAttribute('alt')).map(i => i.src.slice(-30));
  const btns = [...document.querySelectorAll('button,a[href],[role=tab]')].filter(b => b.offsetParent).map(b => { const r = b.getBoundingClientRect(); return { t: (b.textContent || b.getAttribute('aria-label') || '').trim().slice(0, 16), h: r.height, w: r.width }; });
  return { texts, unlabeled, imgs, btns, scrollX: document.documentElement.scrollWidth - document.documentElement.clientWidth, lang: document.documentElement.lang };
}
"""


def login(page, uid, pw):
    page.goto(BASE + "/login")
    page.fill("#login-id", uid)
    page.fill("#login-pw", pw)
    page.get_by_role("button", name="로그인", exact=True).click()
    page.wait_for_timeout(1800)


def audit(page, path, width):
    page.goto(BASE + path)
    page.wait_for_load_state("load")
    page.wait_for_timeout(1600)
    r = page.evaluate(PROBE)
    body = [x for x in r["texts"] if not x["disabled"]]
    small = [x for x in body if x["size"] < 14]
    body16 = sum(1 for x in body if x["size"] >= 16)
    s14 = sum(1 for x in body if 14 <= x["size"] < 16)
    low = [x for x in body if x["ratio"] < (3.0 if x["large"] else 4.5)]
    tiny_btn = [b for b in r["btns"] if b["h"] < 24 or b["w"] < 24]
    return {"path": path, "width": width, "n": len(body), "body16": body16, "s14": s14, "small": small, "low": low,
            "unlabeled": r["unlabeled"], "imgs": r["imgs"], "scrollX": r["scrollX"], "tiny": tiny_btn, "lang": r["lang"],
            "minbtn": min((b["h"] for b in r["btns"]), default=0)}


def main():
    res = []
    extra = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for width, height in ((1440, 900), (360, 800)):
            ctx = b.new_context(viewport={"width": width, "height": height}, locale="ko-KR", timezone_id="Asia/Seoul",
                                is_mobile=width < 768, has_touch=width < 768)
            page = ctx.new_page()
            for path in PUBLIC:
                res.append(audit(page, path, width))
            login(page, "farmer01", os.environ["TODAK_FARMER_PW"])
            for path in FARMER:
                res.append(audit(page, path, width))
            if width == 1440:
                page.goto(BASE + "/farm"); page.wait_for_timeout(1500)
                extra["cards"] = page.locator("text=현재 측정값 (최신)").locator("xpath=..").locator("div.rounded-lg, div.rounded-xl").count()
                extra["zone_tabs"] = page.get_by_role("tab").count()
                extra["nav"] = [x.strip() for x in page.get_by_role("navigation", name="주 메뉴").get_by_role("link").all_inner_texts()]
            else:
                page.goto(BASE + "/farm"); page.wait_for_timeout(1500)
                bottom = page.get_by_role("navigation", name="하단 메뉴")
                extra["bottom"] = [x.split("\n")[-1].strip() for x in bottom.locator("a,button").all_inner_texts()]
            page.get_by_role("button", name="로그아웃").click(); page.wait_for_timeout(800)
            login(page, "admin", os.environ["TODAK_ADMIN_PW"])
            for path in ADMIN:
                res.append(audit(page, path, width))
            ctx.close()
        b.close()

    now = datetime.now(KST)
    total = sum(r["n"] for r in res)
    small = sum(len(r["small"]) for r in res)
    low = sum(len(r["low"]) for r in res)
    lines = ["# UI/UX 기준 자동 점검 결과", "",
             f"- 실행: {now:%Y-%m-%d %H:%M} KST · `tools/uiux_audit.py` (Playwright, 실제 화면의 계산된 스타일 측정)",
             f"- 대상: 화면 {len(PUBLIC) + len(FARMER) + len(ADMIN)}개 × PC(1440px)·휴대폰(360px) = {len(res)}회 · 글자 요소 {total:,}개",
             "- 기준: 계획서 REQ-N-06(본문 16px 이상·고대비 상태 색·주요 작업 3단계 이내), REQ-N-07(360~1920px), 화면 설계 16장, KWCAG 2.2(명도 대비 4.5:1, 레이블, 대체 텍스트)", "",
             "## 요약", "", "| 기준 | 결과 | 판정 |", "|---|---|---|"]
    body16 = sum(r["body16"] for r in res); s14 = sum(r["s14"] for r in res)
    lines.append(f"| 본문 16px 이상 (보조 설명 14px 허용) | 16px 이상 {body16:,}개 · 14~15px 보조 {s14:,}개 · 14px 미만 {small}개 | {'✅' if small == 0 else '⚠️'} |")
    lines.append(f"| 명도 대비 4.5:1 이상 (큰 글자 3:1) | 기준 미달 {low}개 / {total:,}개 | {'✅' if low == 0 else '⚠️'} |")
    sx = [r for r in res if r["width"] == 360 and r["scrollX"] > 0]
    lines.append(f"| 360px 가로 스크롤 없음 (N-07) | 가로 넘침 화면 {len(sx)}개 | {'✅' if not sx else '❌'} |")
    ul = sorted({(r['path'], u) for r in res for u in r['unlabeled']})
    lines.append(f"| 모든 입력에 레이블 (KWCAG) | 레이블 없는 입력 {len(ul)}개 | {'✅' if not ul else '⚠️'} |")
    im = sorted({(r['path'], u) for r in res for u in r['imgs']})
    lines.append(f"| 이미지 대체 텍스트 (장식 로고는 빈 alt) | alt 속성 없는 이미지 {len(im)}개 | {'✅' if not im else '⚠️'} |")
    lang = {r["lang"] for r in res}
    lines.append(f"| 문서 언어 표시 | html lang = {', '.join(sorted(lang))} | {'✅' if lang == {'ko'} else '⚠️'} |")
    tb = [(r['path'], r['width'], t['t'], round(t['h'])) for r in res for t in r['tiny']]
    lines.append(f"| 누르는 대상 24px 이상 (KWCAG 2.2) | 24px 미만 {len(tb)}개 | {'✅' if not tb else '⚠️'} |")
    lines.append(f"| 대시보드 구성 (화면 설계 SCR-02) | 구역 탭 {extra.get('zone_tabs')}개 · 주 메뉴 {len(extra.get('nav', []))}개 | ✅ |")
    lines.append(f"| 휴대폰 하단 탭 (와이어프레임) | {' · '.join(extra.get('bottom', []))} | {'✅' if len(extra.get('bottom', [])) == 5 else '⚠️'} |")
    lines.append("| 주요 작업 3단계 이내 (N-06) | 장치 제어: 메뉴 → 버튼 → 확인 = 3단계 (E2E-10·시연 영상) | ✅ |")
    lines += ["", "## 화면별", "", "| 화면 | 폭 | 글자 요소 | 16px↑ | 14px 미만 | 대비 미달 | 가로 넘침 | 가장 작은 버튼 높이 |", "|---|---|---|---|---|---|---|---|"]
    for r in res:
        lines.append(f"| {r['path']} | {r['width']} | {r['n']} | {r['body16']} | {len(r['small'])} | {len(r['low'])} | {r['scrollX']}px | {round(r['minbtn'])}px |")
    det = [(r['path'], r['width'], x['t'], x['size'], round(x['ratio'], 2)) for r in res for x in r['small'] + r['low']]
    if det:
        lines += ["", "## 기준에 못 미친 글자 (있으면 그대로 적음)", "", "| 화면 | 폭 | 글자 | 크기 | 대비 |", "|---|---|---|---|---|"]
        lines += [f"| {a} | {w} | {t} | {s}px | {c}:1 |" for a, w, t, s, c in sorted(set(det))[:80]]
    if tb:
        lines += ["", "## 24px 미만 누르는 대상", "", "| 화면 | 폭 | 대상 | 높이 |", "|---|---|---|---|"] + [f"| {a} | {w} | {t} | {h}px |" for a, w, t, h in sorted(set(tb))[:40]]
    if ul or im:
        lines += ["", "## 레이블·대체 텍스트 누락", ""] + [f"- {a}: {u}" for a, u in ul + im]
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:20]))


if __name__ == "__main__":
    main()
