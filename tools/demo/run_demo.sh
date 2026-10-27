#!/bin/sh
# 시연 영상: 가상 화면 + 녹화 + 후처리 (record_demo.py 설명 참고)
set -e
apt-get -qq update >/dev/null && apt-get -qq install -y fonts-nanum fonts-noto-cjk >/dev/null 2>&1
pip install -q playwright==1.48.0
OUT=${TODAK_DEMO_DIR:-/w/demo_out}; mkdir -p "$OUT"
Xvfb :99 -screen 0 2560x1600x24 -nolisten tcp >/dev/null 2>&1 &
export DISPLAY=:99; sleep 2
python tools/demo/record_demo.py
python tools/demo/cut_demo.py "$OUT"
