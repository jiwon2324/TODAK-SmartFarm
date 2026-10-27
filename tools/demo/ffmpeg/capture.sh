#!/bin/sh
# 녹화 신호(start.flag)를 기다렸다가 가상 화면(:99)을 4K 50fps(시각 무손실)로 녹화, stop.flag가 생기면 정상 종료
OUT=${1:-/w/demo_out}; W=${2:-3840}; H=${3:-2400}; FPS=${4:-50}
while [ ! -f "$OUT/start.flag" ]; do sleep 0.1; done
ffmpeg -y -loglevel error -f x11grab -draw_mouse 0 -framerate "$FPS" -video_size "${W}x${H}" -i :99 \
  -c:v libx264 -preset ultrafast -crf 6 -threads 0 "$OUT/raw.mkv" &
PID=$!
python3 -c "import time;open('$OUT/started.txt','w').write(str(time.time()))"
while [ ! -f "$OUT/stop.flag" ]; do sleep 0.2; done
kill -INT $PID; wait $PID
echo captured
