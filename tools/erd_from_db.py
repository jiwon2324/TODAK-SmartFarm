"""
ERD(Mermaid)를 실제 DB에서 뽑은 테이블 정의서(docs/Database/table_dictionary.json)로 만든다 → docs/Diagrams/erd.mmd, erd.png
  python3 tools/db_dictionary.py && python3 tools/erd_from_db.py
"""
import json
import os
import re
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIAG = os.path.join(ROOT, "docs", "Diagrams")


def main():
    dd = json.load(open(os.path.join(ROOT, "docs", "Database", "table_dictionary.json"), encoding="utf-8"))
    lines = ["erDiagram"]
    for t in dd["tables"]:
        lines.append(f"  {t['table']} {{")
        for c in t["columns"]:
            ty = re.sub(r"\(.*", "", c["type"]).lower()
            keys = [k for k in ("PK", "FK") if k in c["key"]] + (["UK"] if "UQ" in c["key"] else [])
            lines.append(f"    {ty} {c['column']}" + (" " + ",".join(keys) if keys else ""))
        lines.append("  }")
    nullable = {(t["table"], c["column"]): c["nn"] == "N" for t in dd["tables"] for c in t["columns"]}
    for f in dd["fks"]:
        rel = "|o--o{" if nullable[(f["table"], f["column"])] else "||--o{"
        lines.append(f"  {f['ref_table']} {rel} {f['table']} : \"{f['column']}\"")
    open(os.path.join(DIAG, "erd.mmd"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    subprocess.run(["docker", "run", "--rm", "-u", f"{os.getuid()}:{os.getgid()}", "-v", f"{DIAG}:/data", "minlag/mermaid-cli:11.4.0",
                    "-i", "/data/erd.mmd", "-o", "/data/erd.png", "-w", "3600", "-s", "2", "-b", "white"], check=True)
    print(len(dd["tables"]), "tables", len(dd["fks"]), "relations")


if __name__ == "__main__":
    main()
