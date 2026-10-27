"""녹화 원본에서 자동 제어를 기다린 구간만 잘라내고 고화질 H.264(MP4)로 인코딩한다."""
import json
import subprocess
import sys

out = sys.argv[1]
m = json.load(open(f"{out}/marks.json"))
a, b = m["wait_start"] + 3.0, m["wait_end"]  # 대기 카드는 3초만 남김
flt = (f"[0:v]trim=0:{a:.2f},setpts=PTS-STARTPTS[v0];[0:v]trim=start={b:.2f},setpts=PTS-STARTPTS[v1];"
       f"[v0][v1]concat=n=2:v=1:a=0,crop=2560:1440:0:{m['crop_y']},format=yuv420p[v]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{out}/raw.mkv", "-filter_complex", flt, "-map", "[v]",
                "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high",
                "-movflags", "+faststart", "-r", "30", f"{out}/TODAK_시연영상_1440p.mp4"], check=True)
print("done", a, b)
