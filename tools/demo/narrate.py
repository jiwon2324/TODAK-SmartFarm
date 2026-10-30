"""
시연 영상에 한국어 내레이션(macOS 음성 합성)을 입힌다. 영상은 다시 인코딩하지 않고 음성 트랙만 더한다.
  TODAK_VOICE="Yuna (프리미엄)" python3 tools/demo/narrate.py <입력 mp4> <출력 mp4>
narration.json: [시작초, 끝나야 할 초, 문장] — 문장이 구간보다 길면 말 속도를 조금 올린다(최대 1.06배, 빠르면 발음이 뭉개짐).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
VOICE = os.environ.get("TODAK_VOICE", "Yuna")
BASE_RATE = int(os.environ.get("TODAK_RATE", "165"))  # 분당 단어 수 (say 기본 약 175)


def dur(path):
    out = subprocess.run(["afinfo", path], capture_output=True, text=True, check=True).stdout
    return float(re.search(r"estimated duration: ([\d.]+)", out).group(1))


def main(src, dst):
    lines = json.load(open(os.path.join(HERE, "narration.json"), encoding="utf-8"))
    tmp = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
    segs = []
    for i, (start, end, text) in enumerate(lines):
        path = os.path.join(tmp, f"n{i:02d}.wav")
        rate = BASE_RATE
        while True:
            subprocess.run(["say", "-v", VOICE, "-r", str(rate), "--file-format=WAVE", "--data-format=LEI16@48000", "-o", path, text], check=True)
            d = dur(path)
            if start + d <= end or rate >= BASE_RATE * 1.06:
                break
            rate = int(rate * 1.03)
        over = start + d - end
        print(f"{i:02d} {start:6.1f}+{d:4.1f}s rate {rate}" + (f"  !! {over:.1f}s 넘침" if over > 0 else ""))
        segs.append((start, path))
    # 음성 구간을 시작 시각에 맞춰 놓고 합친 뒤 음량을 맞춘다 (ffmpeg은 Docker 이미지 사용)
    inputs, filt = [], []
    for k, (start, path) in enumerate(segs):
        inputs += ["-i", f"/t/{os.path.basename(path)}"]
        ms = int(start * 1000)
        # 앞뒤를 아주 짧게 페이드해 문장 시작·끝에서 소리가 툭 끊기지 않게
        filt.append(f"[{k + 1}:a]afade=t=in:d=0.03,areverse,afade=t=in:d=0.08,areverse,adelay={ms}|{ms}[a{k}]")
    mix = "".join(f"[a{k}]" for k in range(len(segs)))
    filt.append(f"{mix}amix=inputs={len(segs)}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[out]")
    sd, sf = os.path.split(os.path.realpath(src))
    dd, df = os.path.split(os.path.realpath(dst))
    subprocess.run(["docker", "run", "--rm", "--entrypoint", "ffmpeg", "-v", f"{sd}:/s:ro", "-v", f"{dd}:/d", "-v", f"{tmp}:/t:ro", "todak-ffmpeg",
                    "-loglevel", "error", "-y", "-i", f"/s/{sf}", *inputs, "-filter_complex", ";".join(filt),
                    "-map", "0:v", "-map", "[out]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2",
                    "-movflags", "+faststart", f"/d/{df}"], check=True)
    print("done", dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
