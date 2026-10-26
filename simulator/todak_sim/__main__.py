# -*- coding: utf-8 -*-
"""가상 센서·장치 시뮬레이터 실행: python -m todak_sim"""
import logging
import os
import time
from datetime import datetime

from .gateway import KST, VirtualGateway


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    gw = VirtualGateway(
        host=os.getenv("MQTT_HOST", "localhost"), port=int(os.getenv("MQTT_PORT", "1883")),
        user=os.getenv("MQTT_USER", "gw-01"), password=os.getenv("MQTT_PASSWORD", ""),
        farm_id=int(os.getenv("FARM_ID", "1")), gw_code=os.getenv("GATEWAY_CODE", "GW-01"))
    gw.connect()
    gw.backfill(int(os.getenv("BACKFILL_DAYS", "0")))
    hb = 0
    while True:
        now = datetime.now(KST).replace(second=0, microsecond=0)
        gw.tick(now)
        # 다음 분 정각까지 대기, 그 사이 30초마다 하트비트
        while True:
            rest = 60 - datetime.now(KST).second
            if rest <= 0 or datetime.now(KST).replace(second=0, microsecond=0) > now:
                break
            time.sleep(min(rest, 5))
            hb += 1
            if hb % 6 == 0 and gw.connected:
                gw.heartbeat()


if __name__ == "__main__":
    main()
