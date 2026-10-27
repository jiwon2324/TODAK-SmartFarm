"""녹화 원본에서 자동 제어를 기다린 구간만 잘라내고 4K 고화질 H.264(MP4)로 인코딩한다.
메모리를 아끼려고 앞·뒤 두 구간을 따로 같은 설정으로 인코딩한 뒤 이어 붙인다(재인코딩 없음)."""
import json
import os
import subprocess
import sys

out = sys.argv[1]
m = json.load(open(f"{out}/marks.json"))
a, b = m["wait_start"] + 3.0, m["wait_end"]  # 대기 카드는 3초만 남김
vf = f"crop=3840:2160:0:{m['crop_y']},format=yuv420p"
enc = ["-c:v", "libx264", "-preset", "slow", "-crf", os.environ.get("TODAK_CRF", "15"), "-profile:v", "high", "-level", "5.2",
       "-x264-params", "aq-mode=3:rc-lookahead=30", "-threads", "8", "-r", "50", "-an"]
parts = [(["-t", f"{a:.2f}"], f"{out}/part1.mp4"), (["-ss", f"{b:.2f}"], f"{out}/part2.mp4")]
for cut, path in parts:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *(cut if cut[0] == "-ss" else []), "-i", f"{out}/raw.mkv",
                    *(cut if cut[0] == "-t" else []), "-vf", vf, *enc, path], check=True)
with open(f"{out}/parts.txt", "w") as f:
    f.write("".join(f"file '{p}'\n" for _, p in parts))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{out}/parts.txt", "-c", "copy",
                "-movflags", "+faststart", f"{out}/TODAK_시연영상_4K.mp4"], check=True)
for _, p in parts:
    os.remove(p)
os.remove(f"{out}/parts.txt")
print("done", a, b)
