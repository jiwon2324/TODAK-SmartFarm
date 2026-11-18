#!/bin/sh
# 시연 영상에 통합 관제 장면을 끼워 넣는다: 원본 0~219.0초 + 관제 장면(기다린 구간 제외) + 원본 219.0초~끝(마무리 카드)
# 4K를 한꺼번에 처리하면 Docker 메모리(8GB)가 모자라서, 네 조각을 같은 설정으로 하나씩 인코딩한 뒤 다시 인코딩 없이 이어 붙인다.
# 소리는 넣지 않는다 (내레이션은 narrate_clips.py가 따로 입힘).
#   sh tools/demo/splice_monitor.sh <원본 mp4> <출력 mp4>
set -e
cd "$(dirname "$0")/../.."
SRC=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); DST=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
M=demo_out/monitor/marks_monitor.json
v() { python3 -c "import json;m=json.load(open('$M'));print($1)"; }
A0=$(v "m['s_card']"); AD=$(v "m['wait_start']+1.5-m['s_card']"); B0=$(v "m['wait_end']"); BD=$(v "m['end']-m['wait_end']"); CY=$(v "m['crop_y']")
CUT=219.0
W=demo_out/monitor/parts; mkdir -p $W
ENC="-c:v libx264 -preset medium -crf 16 -profile:v high -level 5.2 -x264-params aq-mode=3 -threads 4 -r 50 -pix_fmt yuv420p -an"
run() { docker run --rm --memory=6g -v "$(dirname "$SRC")":/s:ro -v "$PWD/demo_out/monitor":/m todak-ffmpeg sh -c "$1"; }
run "ffmpeg -y -loglevel error -i '/s/$(basename "$SRC")' -t $CUT $ENC /m/parts/p1.mp4"
run "ffmpeg -y -loglevel error -ss $A0 -i /m/raw.mkv -t $AD -vf crop=3840:2160:0:$CY $ENC /m/parts/p2.mp4"
run "ffmpeg -y -loglevel error -ss $B0 -i /m/raw.mkv -t $BD -vf crop=3840:2160:0:$CY $ENC /m/parts/p3.mp4"
run "ffmpeg -y -loglevel error -ss $CUT -i '/s/$(basename "$SRC")' $ENC /m/parts/p4.mp4"
printf "file 'p1.mp4'\nfile 'p2.mp4'\nfile 'p3.mp4'\nfile 'p4.mp4'\n" > $W/list.txt
docker run --rm -v "$PWD/demo_out/monitor":/m -v "$(dirname "$DST")":/d todak-ffmpeg \
  ffmpeg -y -loglevel error -f concat -safe 0 -i /m/parts/list.txt -c copy -movflags +faststart "/d/$(basename "$DST")"
echo "segment A $A0 +$AD, B $B0 +$BD"
