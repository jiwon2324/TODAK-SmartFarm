"""
미리 만든 문장별 음성 파일(nNN.wav 또는 nNN.mp3)을 시연 영상의 정해진 시각에 놓고, 영상의 기존 소리를 바꾼다. 영상은 다시 인코딩하지 않는다.
  python3 tools/demo/narrate_clips.py <음성 폴더> <입력 mp4> <출력 mp4>
현재 음성: Qwen Audio 3.0 TTS (Higgsfield 경유), language=ko, 말투 지시 '20대 한국인 여성 발표자, 편안한 대화체', speech_rate 1.1.
대본: narration_spoken.json (말하듯 다듬은 해요체, 29문장 — 시각은 narration.json과 같음).
처리: 문장 앞뒤 무음 제거 → (필요한 문장만) 속도 조정 → 시작 시각에 배치 → 저역 잡음 제거(80Hz) → 음량 -16 LUFS 정규화 → 피크 제한(찢어지는 소리 방지).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
SCRIPT = os.environ.get("TODAK_NARRATION", "narration_spoken.json")
# 다음 문장 시작과 겹치지 않도록: 시작 시각을 앞당긴 문장(초), 살짝 빠르게 읽힌 문장(배속, 1.06 이하라 귀로 구분 어려움)
START_OVERRIDE = {0: 0.3}
TEMPO = {0: 1.05}


def main(clips, src, dst):
    lines = json.load(open(os.path.join(HERE, SCRIPT), encoding="utf-8"))
    inputs, filt = [], []
    for k, (start, _end, _text) in enumerate(lines):
        name = next((f"n{k:02d}.{e}" for e in ("wav", "mp3") if os.path.exists(os.path.join(clips, f"n{k:02d}.{e}"))), None)
        if not name:
            sys.exit(f"음성 파일 없음: n{k:02d}")
        inputs += ["-i", f"/c/{name}"]
        ms = int(START_OVERRIDE.get(k, start) * 1000)
        tempo = f"atempo={TEMPO[k]}," if k in TEMPO else ""
        filt.append(f"[{k + 1}:a]aresample=48000,silenceremove=start_periods=1:start_threshold=-50dB,"
                    f"afade=t=in:d=0.02,areverse,silenceremove=start_periods=1:start_threshold=-50dB,afade=t=in:d=0.06,areverse,"
                    f"{tempo}adelay={ms}|{ms}[a{k}]")
    mix = "".join(f"[a{k}]" for k in range(len(lines)))
    filt.append(f"{mix}amix=inputs={len(lines)}:normalize=0,highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=9,"
                f"alimiter=limit=0.84,aresample=48000[out]")
    sd, sf = os.path.split(os.path.realpath(src))
    dd, df = os.path.split(os.path.realpath(dst))
    subprocess.run(["docker", "run", "--rm", "--entrypoint", "ffmpeg", "-v", f"{sd}:/s:ro", "-v", f"{dd}:/d", "-v", f"{os.path.realpath(clips)}:/c:ro",
                    "todak-ffmpeg", "-loglevel", "error", "-y", "-i", f"/s/{sf}", *inputs, "-filter_complex", ";".join(filt),
                    "-map", "0:v", "-map", "[out]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-t", "225.88",
                    "-movflags", "+faststart", f"/d/{df}"], check=True)
    print("done", dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
