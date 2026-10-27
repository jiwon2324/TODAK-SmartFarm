"""v2/mark.svg(방울토마토 송이) + 직접 그린 TODAK 글자 → 앱 아이콘·가로 로고(컬러/흰색/검정) SVG 생성. 이어서 render.py로 PNG."""
import os

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2")
mark = open(os.path.join(D, "mark.svg"), encoding="utf-8").read()
inner = mark[mark.index("<defs>"):mark.rindex("</svg>")]
WORD = """    <path d="M80 18 H104 M92 18 V52"/>
    <circle cx="127" cy="35" r="16.5"/>
    <path d="M152 18 V52 H158 A17 17 0 0 0 158 18 Z"/>
    <path d="M186 52 L200 18 L214 52 M191.5 40 H208.5"/>
    <path d="M226 18 V52 M247 18 L228.5 36.5 M233.5 32 L248 52"/>
"""


def uniq(s, p):  # 한 문서에 마크가 여러 번 들어가도 mask id가 겹치지 않게
    for k in ("m-l", "m-r", "m-f", "m-stem"):
        s = s.replace(f'id="{k}"', f'id="{p}{k}"').replace(f"url(#{k})", f"url(#{p}{k})")
    return s


def lockup(mc, tc, sc, p):
    s = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 262 78" role="img" aria-label="TODAK 토닥 방울토마토 스마트팜">\n'
    s += f'  <g color="{mc}">{uniq(inner, p)}</g>\n'
    s += f'  <g fill="none" stroke="{tc}" stroke-width="6.4" stroke-linecap="round" stroke-linejoin="round">\n{WORD}  </g>\n'
    s += (f'''  <text x="80" y="74" font-family="'Noto Sans CJK KR','Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif" '''
          f'''font-size="11.5" font-weight="500" letter-spacing="2.2" fill="{sc}">토닥 · 방울토마토 스마트팜</text>\n''')
    return s + "</svg>\n"


files = {
    "logo.svg": lockup("#1B4D32", "#14261A", "#4B5B50", "c"),
    "logo_white.svg": lockup("#FFFFFF", "#FFFFFF", "#CFE3D5", "w"),
    "logo_black.svg": lockup("#111111", "#111111", "#555555", "k"),
    "wordmark.svg": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="76 14 176 42" role="img" aria-label="TODAK"><g fill="none" stroke="currentColor" stroke-width="6.4" stroke-linecap="round" stroke-linejoin="round">\n{WORD}</g></svg>\n',
    "app_icon.svg": ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="TODAK">\n'
                     '  <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2E7D4F"/><stop offset="1" stop-color="#1B4D32"/></linearGradient></defs>\n'
                     '  <rect width="512" height="512" rx="115" fill="url(#bg)"/>\n'
                     f'  <g transform="translate(64 60) scale(6)" color="#FFFFFF">{uniq(inner, "i")}</g>\n</svg>\n'),
}
for k, v in files.items():
    open(os.path.join(D, k), "w", encoding="utf-8").write(v)
print(list(files))
