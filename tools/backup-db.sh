#!/bin/sh
# MySQL 전체 백업 (계획서 표 68: 일 1회, 7일 보관). cron 예: 0 4 * * * /path/TODAK-SmartFarm/tools/backup-db.sh
set -e
cd "$(dirname "$0")/.."
. ./.env
mkdir -p backups
F="backups/todak_$(date +%Y%m%d_%H%M).sql.gz"
docker compose exec -T mysql sh -c "exec mysqldump -uroot -p\"\$MYSQL_ROOT_PASSWORD\" --single-transaction --routines --databases ${DB_NAME:-todak}" | gzip > "$F"
find backups -name 'todak_*.sql.gz' -mtime +7 -delete
echo "백업 완료: $F"
