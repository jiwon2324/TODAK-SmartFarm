#!/bin/sh
# 환경 변수로 받은 계정으로 비밀번호 파일을 만들고 브로커를 띄운다 (비밀번호는 저장소에 넣지 않는다)
set -e
mkdir -p /mosquitto/config /mosquitto/data
cp /todak/mosquitto.conf /mosquitto/config/mosquitto.conf
cp /todak/acl /mosquitto/config/acl
rm -f /mosquitto/config/passwd
touch /mosquitto/config/passwd
mosquitto_passwd -b /mosquitto/config/passwd todak-server "$MQTT_SERVER_PASSWORD"
mosquitto_passwd -b /mosquitto/config/passwd gw-01 "$MQTT_GW_PASSWORD"
chown -R mosquitto:mosquitto /mosquitto/config /mosquitto/data
chmod 0700 /mosquitto/config/passwd /mosquitto/config/acl
exec mosquitto -c /mosquitto/config/mosquitto.conf
