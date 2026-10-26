#!/bin/sh
# 백엔드 테스트 실행 (Docker 필요, docker compose up -d mysql 이후)
# 단위 테스트 + 실제 MySQL(todak_test) 통합 테스트. 결과 리포트: backend/build/reports/tests/test/index.html
set -e
cd "$(dirname "$0")/.."
NET=$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' "$(docker compose ps -q mysql)")
. ./.env
docker run --rm --network "$NET" \
  -e DB_HOST=mysql -e DB_USER="${DB_USER:-todak}" -e DB_PASSWORD="$DB_PASSWORD" -e TZ=Asia/Seoul \
  -v "$PWD/backend":/app -v todak-gradle-cache:/home/gradle/.gradle -w /app \
  gradle:8.10.2-jdk21 gradle test --console=plain "$@"
