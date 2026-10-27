#!/bin/sh
# 4K(3840x2160) 50fps 시연 영상 녹화 — 브라우저 컨테이너와 캡처 컨테이너가 가상 화면(X 소켓)을 공유한다
#   TODAK_ADMIN_PW=... TODAK_FARMER_PW=... sh tools/demo/record_4k.sh
set -e
cd "$(dirname "$0")/../.."
docker build -q -t todak-ffmpeg tools/demo/ffmpeg >/dev/null
docker volume create todak-x11 >/dev/null
mkdir -p demo_out; rm -f demo_out/raw.mkv demo_out/marks.json
docker rm -f todak-cap >/dev/null 2>&1 || true
docker run -d --name todak-cap --ipc=shareable --shm-size=2g -v todak-x11:/tmp/.X11-unix -v "$PWD":/w todak-ffmpeg sh /w/tools/demo/ffmpeg/capture.sh /w/demo_out >/dev/null
docker run --rm --network todak_default --ipc=container:todak-cap -v todak-x11:/tmp/.X11-unix -v "$PWD":/w -w /w \
  -e TODAK_ADMIN_PW -e TODAK_FARMER_PW -e TODAK_DEMO_DIR=/w/demo_out -e TODAK_EXTERNAL_CAPTURE=1 \
  mcr.microsoft.com/playwright/python:v1.48.0-jammy sh tools/demo/run_demo.sh
docker wait todak-cap >/dev/null; docker logs todak-cap; docker rm todak-cap >/dev/null
docker run --rm -v "$PWD":/w todak-ffmpeg python3 /w/tools/demo/cut_demo.py /w/demo_out
ls -la demo_out/TODAK_시연영상_4K.mp4
