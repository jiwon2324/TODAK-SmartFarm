"""
Claude Code 세션 기록(jsonl)에서 사용자가 입력한 프롬프트만 뽑아 과제 폴더의 프롬프트_기록/prompts.json 으로 저장한다.
프롬프트 원문은 제출 보고서 부록에만 싣고 공개 저장소에는 올리지 않는다.
  python3 tools/process/extract_prompts.py <세션.jsonl>
도구 결과·시스템 알림·자동 메시지는 빼고, 직접 친 터미널 명령(bash-input)은 kind=command로 따로 표시한다.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.environ.get("TODAK_PROMPTS", os.path.join(os.path.dirname(ROOT), "프롬프트_기록", "prompts.json"))
END = os.environ.get("TODAK_PROMPTS_END", "2026-10-30 14:40")  # 공지 반영 요청까지 (부록 자체에 대한 대화는 제외)
SKIP = ("This session is being continued", "<command-", "<local-command", "<task-notification", "[SYSTEM", "<artifact-view-context",
        "[Request interrupted", "I hit my usage limit")


def clean(t):
    m = re.search(r"=== BEGIN ARTIFACT COMMENT \w+ ===\n(.*?)\n=== END", t, re.S)
    if m:  # 문서 화면에 단 댓글은 댓글 본문만
        t = "[문서 댓글] " + "\n".join(x[2:] if x.startswith("> ") else x.lstrip(">") for x in m.group(1).splitlines()).replace("＠Claude", "").strip()
    t = re.sub(r"<system-reminder>.*?</system-reminder>", "", t, flags=re.S)
    t = re.sub(r"</?pasted_content[^>]*>", "", t)
    t = re.sub(r"<!-- reply \d+ -->\s*", "", t)
    t = t.replace("/Users/yangjiwon", "~")
    own = "\n".join(l for l in t.splitlines() if not l.startswith(">")).strip()
    if own:  # 답장할 때 인용한 AI 문장(> …)은 빼고 학생이 쓴 말만
        t = own
    return t.strip()


def main(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("type") != "user" or o.get("isMeta") or o.get("isCompactSummary"):
            continue
        c = o.get("message", {}).get("content")
        imgs = 0
        if isinstance(c, list):
            if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
                continue
            imgs = sum(1 for x in c if isinstance(x, dict) and x.get("type") == "image")
            c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
        raw = (c or "").strip()
        if not raw or any(s in raw[:400] for s in SKIP):
            continue
        t = clean(raw)
        if not t:
            continue
        ts = (datetime.fromisoformat(o["timestamp"][:19]) + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
        m = re.match(r"<bash-input>(.*?)</bash-input>", t, re.S)
        if m:
            rows.append({"time": ts, "kind": "command", "text": m.group(1).strip()})
            continue
        imgs += len(re.findall(r"\[Image[^\]]*\]", t))
        t = re.sub(r"\[Image[^\]]*\]", "", t).strip()
        rows.append({"time": ts, "kind": "prompt", "images": imgs, "text": t})
    # 작업 중에 보낸 메시지는 대기열(queue-operation enqueue)에만 원문이 남는다
    seen = {r["text"][:60] for r in rows}
    for line in open(path, encoding="utf-8"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("type") != "queue-operation" or o.get("operation") != "enqueue" or not isinstance(o.get("content"), str):
            continue
        raw = o["content"].strip()
        if not raw or any(x in raw[:400] for x in SKIP):
            continue
        t = clean(raw)
        imgs = len(re.findall(r"\[Image[^\]]*\]", t))
        t = re.sub(r"\[Image[^\]]*\]", "", t).strip()
        if not t or t[:60] in seen or t.startswith("<bash-"):
            continue
        seen.add(t[:60])
        ts = (datetime.fromisoformat(o["timestamp"][:19]) + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
        rows.append({"time": ts, "kind": "prompt", "images": imgs, "text": t})
    rows = sorted((r for r in rows if r["time"] <= END), key=lambda r: r["time"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(rows), "→", OUT)


if __name__ == "__main__":
    main(sys.argv[1])
