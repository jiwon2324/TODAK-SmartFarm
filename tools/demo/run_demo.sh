#!/bin/sh
# 시연 영상: 가상 화면 + 브라우저 조작 (record_demo.py 설명 참고). 녹화는 내부 ffmpeg 또는 외부 캡처 컨테이너(record_4k.sh)
set -e
apt-get -qq update >/dev/null && apt-get -qq install -y fonts-nanum fonts-noto-cjk >/dev/null 2>&1
pip install -q playwright==1.48.0
OUT=${TODAK_DEMO_DIR:-/w/demo_out}; mkdir -p "$OUT"
Xvfb :99 -screen 0 3840x2400x24 -ac -nolisten tcp >/dev/null 2>&1 &
export DISPLAY=:99; sleep 2
python tools/demo/record_demo.py
[ "$TODAK_EXTERNAL_CAPTURE" = "1" ] || python tools/demo/cut_demo.py "$OUT"
