"""미리보기 이미지들을 한 장에 모은다: python3 sheet.py <접두사> <열> <출력접두사>"""
import glob
import sys

from PIL import Image

pre, cols, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
fs = sorted(glob.glob(pre + "-*.jpg"), key=lambda f: int(f.rsplit("-", 1)[1].split(".")[0]))
ims = [Image.open(f) for f in fs]
w, h = ims[0].size
per = cols * 3
for k in range(0, len(ims), per):
    chunk = ims[k:k + per]
    rows = (len(chunk) + cols - 1) // cols
    m = Image.new("RGB", (w * cols, h * rows), "white")
    for i, im in enumerate(chunk):
        m.paste(im.resize((w, h)), ((i % cols) * w, (i // cols) * h))
    m.save(f"{out}{k // per}.jpg", quality=82)
    print(f"{out}{k // per}.jpg", k + 1, "-", k + len(chunk))
