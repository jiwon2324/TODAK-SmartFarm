#!/bin/sh
# Oracle Cloud 무료 VM(Ubuntu 22.04/24.04, Ampere A1)에 TODAK 배포
#   sh tools/deploy/deploy_oracle.sh <공인 IP> [ssh 키]
# - 커밋된 소스만 올린다 (git archive). 서버 .env는 서버에서 무작위 값으로 처음 한 번 만들고 출력하지 않는다.
# - 주소: https://<IP의 점을 대시로>.sslip.io (Caddy가 인증서 자동 발급)
set -e
IP=$1; KEY=${2:-$HOME/.ssh/todak_oracle}
[ -n "$IP" ] || { echo "사용법: $0 <공인 IP> [ssh 키]"; exit 1; }
HOST="$(echo "$IP" | tr . -).sslip.io"
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new ubuntu@$IP"

git archive --format=tar HEAD | $SSH "mkdir -p ~/todak && tar -x -C ~/todak"
$SSH "SITE_HOST=$HOST sh -s" <<'REMOTE'
set -e
cd ~/todak
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker ubuntu
fi
# Oracle Ubuntu 이미지는 iptables가 22번만 열어 둔다 → 80·443 허용
for p in 80 443; do
  sudo iptables -C INPUT -p tcp --dport $p -j ACCEPT 2>/dev/null || sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport $p -j ACCEPT
done
sudo sh -c 'command -v netfilter-persistent >/dev/null && netfilter-persistent save' >/dev/null 2>&1 || true
if [ ! -f .env ]; then
  r() { openssl rand -base64 36 | tr -d '/+=' | cut -c1-32; }
  cat > .env <<ENV
MYSQL_ROOT_PASSWORD=$(r)
DB_NAME=todak
DB_USER=todak
DB_PASSWORD=$(r)
JWT_SECRET=$(r)$(r)
MQTT_SERVER_PASSWORD=$(r)
MQTT_GW_PASSWORD=$(r)
COOKIE_SECURE=true
CORS_ORIGINS=https://$SITE_HOST
SITE_HOST=$SITE_HOST
SIM_BACKFILL_DAYS=14
ENV
  chmod 600 .env
fi
sudo docker compose -f docker-compose.yml -f infra/deploy/docker-compose.prod.yml up -d --build
sudo docker compose -f docker-compose.yml -f infra/deploy/docker-compose.prod.yml ps --format '{{.Service}} {{.Status}}'
REMOTE
echo "주소: https://$HOST"
