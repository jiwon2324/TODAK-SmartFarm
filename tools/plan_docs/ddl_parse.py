# -*- coding: utf-8 -*-
"""01_schema.sql을 읽어 테이블 정의서(데이터 사전) 행을 만든다. DDL과 문서가 항상 일치하도록."""
import os
import re

SCHEMA = os.path.join(os.path.dirname(__file__), "..", "TODAK_산출물", "schema", "01_schema.sql")
NEW = {"TB_ZONE", "TB_CROP_CYCLE", "TB_GATEWAY", "TB_SENSOR_DATA_HOURLY", "TB_CONTROL_RULE", "TB_CONTROL_COMMAND",
       "TB_ALERT_DELIVERY", "TB_BEEHIVE", "TB_WEATHER_DAILY", "TB_GDD_DAILY", "TB_SETTING_HISTORY"}


def parse():
    sql = open(SCHEMA, encoding="utf-8").read()
    tables = []
    for m in re.finditer(r"CREATE TABLE (\w+) \((.*?)\n\) COMMENT='([^']*)';", sql, re.S):
        name, body, comment = m.group(1), m.group(2), m.group(3)
        cols, pk, uq, fk = [], set(), set(), {}
        lines = [l.strip().rstrip(",") for l in body.split("\n") if l.strip()]
        for l in lines:
            if l.startswith("PRIMARY KEY"):
                pk |= set(x.strip() for x in re.search(r"\((.*)\)", l).group(1).split(","))
            elif l.startswith("UNIQUE KEY"):
                uq |= set(x.strip() for x in re.search(r"\((.*)\)", l).group(1).split(","))
            elif l.startswith("CONSTRAINT") and "FOREIGN KEY" in l:
                fm = re.search(r"FOREIGN KEY \((\w+)\) REFERENCES (\w+)\((\w+)\)", l)
                fk[fm.group(1)] = f"{fm.group(2)}.{fm.group(3)}"
        for l in lines:
            if l.startswith(("PRIMARY", "UNIQUE", "KEY", "CONSTRAINT", "INDEX")):
                continue
            cm = re.match(r"(\w+)\s+([A-Z]+(?:\([\d,]+\))?)\s*(.*)", l)
            if not cm:
                continue
            col, typ, rest = cm.groups()
            nn = "Y" if "NOT NULL" in rest else "N"
            dm = re.search(r"DEFAULT ([^ ]+(?: ON UPDATE [A-Z_()0-9]+)?)", rest)
            default = dm.group(1).replace("CURRENT_TIMESTAMP", "현재시각") if dm else ""
            if "AUTO_INCREMENT" in rest:
                default = "자동 증가"
            com = re.search(r"COMMENT '([^']*)'", rest)
            keys = []
            if col in pk:
                keys.append("PK")
            if col in fk:
                keys.append("FK")
            if col in uq:
                keys.append("UQ")
            desc = com.group(1) if com else ""
            if col in fk:
                desc = (desc + " → " if desc else "→ ") + fk[col]
            cols.append((col, typ, ",".join(keys), nn, default, desc))
        tables.append({"name": name, "comment": comment, "cols": cols, "new": name in NEW})
    return tables


if __name__ == "__main__":
    t = parse()
    print(len(t), sum(len(x["cols"]) for x in t))
