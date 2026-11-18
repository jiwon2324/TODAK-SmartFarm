#!/bin/sh
# 시연 영상 추가 장면(통합 관제·운영 점검) 4K 50fps 녹화 — record_4k.sh와 같은 구성
#   TODAK_ADMIN_PW=... sh tools/demo/record_monitor.sh
set -e
cd "$(dirname "$0")/../.."
OUT=demo_out/monitor
mkdir -p $OUT; rm -f $OUT/raw.mkv $OUT/start.flag $OUT/started.txt $OUT/stop.flag
docker volume create todak-x11 >/dev/null
docker rm -f todak-cap >/dev/null 2>&1 || true
docker run -d --name todak-cap --ipc=shareable --shm-size=2g -v todak-x11:/tmp/.X11-unix -v "$PWD":/w todak-ffmpeg sh /w/tools/demo/ffmpeg/capture.sh /w/$OUT >/dev/null
docker run --rm --network todak_default --ipc=container:todak-cap -v todak-x11:/tmp/.X11-unix -v "$PWD":/w -w /w/tools/demo \
  -e TODAK_ADMIN_PW -e TODAK_DEMO_DIR=/w/$OUT \
  mcr.microsoft.com/playwright/python:v1.48.0-jammy sh -c "apt-get -qq update >/dev/null && apt-get -qq install -y fonts-nanum fonts-noto-cjk >/dev/null 2>&1; pip install -q playwright==1.48.0; Xvfb :99 -screen 0 3840x2400x24 -ac -nolisten tcp >/dev/null 2>&1 & export DISPLAY=:99; sleep 2; python record_monitor.py"
docker wait todak-cap >/dev/null; docker logs todak-cap; docker rm todak-cap >/dev/null
ls -la $OUT
