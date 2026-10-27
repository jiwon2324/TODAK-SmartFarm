"""
최종 테이블 정의서를 실제 MySQL(information_schema)에서 뽑는다 — 컬럼 순서·타입·NULL·기본값·PK/FK/UQ·주석이 DB와 똑같다.
결과: docs/Database/table_dictionary.json (보고서 생성기가 읽음), docs/Database/테이블_정의서.md
실행: python3 tools/db_dictionary.py   (docker compose의 mysql이 떠 있어야 함)
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import collect_evidence as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "Database")
V3 = os.path.join(ROOT, "backend/src/main/resources/db/migration/V3__plan_alignment.sql")


def query(sql, e):
    cmd = ["docker", "compose", "exec", "-T", "-e", f"MYSQL_PWD={e['DB_PASSWORD']}", "mysql", "mysql", "-u", e.get("DB_USER", "todak"),
           "-N", "-B", "--raw", "--default-character-set=utf8mb4", e.get("DB_NAME", "todak"), "-e", sql]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=60)
    return [line.split("\t") for line in r.stdout.decode("utf-8").splitlines() if line]


def main():
    e = C.env() if callable(C.env) else C.env
    tables = query("SELECT table_name, table_comment FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name LIKE 'TB\\_%' ORDER BY create_time, table_name", e)
    cols = query("SELECT table_name, column_name, column_type, is_nullable, IFNULL(column_default,'\\N'), extra, column_comment "
                 "FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name LIKE 'TB\\_%' ORDER BY table_name, ordinal_position", e)
    keys = query("SELECT table_name, index_name, non_unique, GROUP_CONCAT(column_name ORDER BY seq_in_index) FROM information_schema.statistics "
                 "WHERE table_schema=DATABASE() AND table_name LIKE 'TB\\_%' GROUP BY table_name, index_name, non_unique", e)
    fks = query("SELECT table_name, column_name, referenced_table_name, referenced_column_name FROM information_schema.key_column_usage "
                "WHERE table_schema=DATABASE() AND referenced_table_name IS NOT NULL", e)
    v3 = open(V3, encoding="utf-8").read()
    v3_cols = {(t, c) for t, body in re.findall(r"ALTER TABLE (\w+)\s+(.*?);", v3, re.S) for c in re.findall(r"ADD COLUMN (\w+)", body)}

    pk, uq = {}, {}
    for t, idx, non_unique, colist in keys:
        cl = colist.split(",")
        if idx == "PRIMARY":
            pk[t] = cl
        elif non_unique == "0":
            for c in cl:
                uq.setdefault((t, c), []).append("UQ" if len(cl) == 1 else "UQ(복합)")
    fk = {(t, c): f"{rt}({rc})" for t, c, rt, rc in fks}

    # 표 순서는 설계 문서와 같게 V1 DDL의 CREATE TABLE 순서, 그 뒤에 V2 이후 추가 테이블
    v1 = open(V3.replace("V3__plan_alignment.sql", "V1__schema.sql"), encoding="utf-8").read()
    order = re.findall(r"CREATE TABLE (\w+)", v1)
    tables.sort(key=lambda x: (order.index(x[0]) if x[0] in order else len(order), x[0]))
    out = []
    for t, comment in tables:
        rows = []
        for tt, c, ty, nl, dflt, extra, cm in cols:
            if tt != t:
                continue
            k = []
            if c in pk.get(t, []):
                k.append("PK")
            if (t, c) in fk:
                k.append("FK")
            k += sorted(set(uq.get((t, c), [])))
            d = "" if dflt == "\\N" else dflt
            if "auto_increment" in extra:
                d = "자동 증가"
            desc = cm
            if (t, c) in fk:
                desc = (desc + " → " + fk[(t, c)]).strip()
            if (t, c) in v3_cols:
                desc = (desc + " [V3]").strip()
            rows.append({"column": c, "type": ty.upper(), "key": ", ".join(k), "nn": "Y" if nl == "NO" else "N", "default": d, "desc": desc})
        out.append({"table": t, "comment": comment, "columns": rows})
    os.makedirs(OUT, exist_ok=True)
    json.dump({"source": "MySQL information_schema (실제 DB)", "tables": out, "fk_count": len(fks),
               "fks": sorted([{"table": t, "column": c, "ref_table": rt, "ref_column": rc} for t, c, rt, rc in fks], key=lambda x: (x["table"], x["column"]))}, open(os.path.join(OUT, "table_dictionary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    md = ["# 최종 테이블 정의서 (실제 DB 기준)", "",
          f"- 출처: 실행 중인 MySQL의 information_schema에서 자동 추출 (`tools/db_dictionary.py`) · 테이블 {len(out)}개 · 컬럼 {sum(len(x['columns']) for x in out)}개 · 외래키 {len(fks)}개",
          "- 키: PK 기본키 · FK 외래키 · UQ 유일 · UQ(복합) 여러 컬럼 유일 · [V3] 구현 단계에서 추가된 컬럼", ""]
    for x in out:
        md += [f"## {x['table']} — {x['comment']}", "", "| 컬럼 | 타입 | 키 | NN | 기본값 | 설명 |", "|---|---|---|---|---|---|"]
        md += [f"| {r['column']} | {r['type']} | {r['key']} | {r['nn']} | {r['default']} | {r['desc']} |" for r in x["columns"]]
        md.append("")
    open(os.path.join(OUT, "테이블_정의서.md"), "w", encoding="utf-8").write("\n".join(md))
    print(len(out), "tables", sum(len(x["columns"]) for x in out), "columns", len(fks), "FKs")


if __name__ == "__main__":
    main()
