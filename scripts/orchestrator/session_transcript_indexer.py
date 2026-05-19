#!/usr/bin/env python3
"""session_transcript_indexer.py — Claude session jsonl → Weaviate (SessionTranscripts + SessionFacts).

Filters tool-call noise and hook output from ~/.claude/projects/-home-elliotbot-clawd-Agency-OS-<cs>/*.jsonl,
chunks the cleaned user+assistant text, uploads to SessionTranscripts (raw chunks), then runs
an LLM fact-extraction per session and uploads structured facts to SessionFacts.

Deterministic UUIDs make re-runs idempotent. Mtime cursor at /tmp/session_indexer_cursor.json
skips unchanged files for fast incremental polling.

Modes:
    --once                 : sync all callsigns once then exit
    --daemon N             : poll every N seconds
    --callsign CS          : only process one callsign (default: all 7)
    --skip-facts           : skip LLM fact extraction (chunks only)
    --since-mtime SEC      : only process files modified in last N seconds
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

WEAVIATE_BASE = f"http://{os.environ.get('WEAVIATE_HOST','127.0.0.1')}:{os.environ.get('WEAVIATE_PORT','8090')}"
PROJECTS_ROOT = Path(os.path.expanduser("~/.claude/projects"))
CURSOR_PATH = Path("/tmp/session_indexer_cursor.json")
NS = uuid.UUID("9b5b5d51-2a32-4b71-9c5f-7b6c1e3a4d11")
CHUNK_CHARS = 4000
MIN_TEXT_CHARS = 20
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"
LLM_PROVIDER = os.environ.get("SESSION_FACT_LLM", "openai").lower()

CALLSIGN_DIRS = {
    "elliot": "-home-elliotbot-clawd-Agency-OS",
    "aiden":  "-home-elliotbot-clawd-Agency-OS-aiden",
    "atlas":  "-home-elliotbot-clawd-Agency-OS-atlas",
    "max":    "-home-elliotbot-clawd-Agency-OS-max",
    "orion":  "-home-elliotbot-clawd-Agency-OS-orion",
    "scout":  "-home-elliotbot-clawd-Agency-OS-scout",
    "nova":   "-home-elliotbot-clawd-Agency-OS-nova",
}

SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
COMMAND_NAME_RE = re.compile(r"<command-name>.*?</command-name>", re.DOTALL)
COMMAND_STDOUT_RE = re.compile(r"<command-(stdout|message|args)>.*?</command-(stdout|message|args)>", re.DOTALL)
LOCAL_CMD_RE = re.compile(r"<local-command-stdout>.*?</local-command-stdout>", re.DOTALL)
KEI_REF_RE = re.compile(r"\bKEI-\d+\b", re.IGNORECASE)
PR_REF_RE = re.compile(r"PR\s*#(\d+)", re.IGNORECASE)
MARKER_RE = re.compile(r"\[(STARTING|REVIEW|SHIPPED|DISPATCH|HOLD|CONCUR|BLOCKED|READY|FINAL|MERGE-READY):", re.IGNORECASE)
DIRECTIVE_HINTS = ("STEP 0", "Directive #", "check agents", "stop all work", "ratify", "approve")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("session_transcript_indexer")


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = SYSTEM_REMINDER_RE.sub("", s)
    s = COMMAND_NAME_RE.sub("", s)
    s = COMMAND_STDOUT_RE.sub("", s)
    s = LOCAL_CMD_RE.sub("", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s


def extract_turn_text(line: dict) -> tuple[str | None, str, int]:
    t = line.get("type")
    if t not in ("user", "assistant"):
        return None, "", 0
    msg = line.get("message") or {}
    role = msg.get("role") or t
    content = msg.get("content")
    if isinstance(content, str):
        return role, clean_text(content), 0
    if not isinstance(content, list):
        return None, "", 0
    text_parts = []
    tool_count = 0
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            text_parts.append(block.get("text", ""))
        elif btype == "tool_use":
            tool_count += 1
        elif btype == "tool_result":
            tc = block.get("content")
            if isinstance(tc, str):
                preview = tc[:120].replace("\n", " ")
                text_parts.append(f"[tool_result: {preview}]")
            elif isinstance(tc, list):
                for sub in tc:
                    if isinstance(sub, dict) and sub.get("type") == "text":
                        preview = (sub.get("text") or "")[:120].replace("\n", " ")
                        text_parts.append(f"[tool_result: {preview}]")
    combined = "\n".join(p for p in text_parts if p)
    return role, clean_text(combined), tool_count


def chunk_text(text: str, size: int = CHUNK_CHARS) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks = []
    pos = 0
    while pos < len(text):
        end = min(pos + size, len(text))
        if end < len(text):
            for breaker in ("\n\n", "\n", ". ", " "):
                idx = text.rfind(breaker, pos + size // 2, end)
                if idx > pos:
                    end = idx + len(breaker)
                    break
        chunks.append(text[pos:end].strip())
        pos = end
    return [c for c in chunks if c]


def tag_text(text: str) -> list[str]:
    tags = []
    for kei in set(KEI_REF_RE.findall(text)):
        tags.append(f"kei:{kei.upper()}")
    for pr in set(PR_REF_RE.findall(text)):
        tags.append(f"pr:{pr}")
    if MARKER_RE.search(text):
        tags.append("marker")
    if any(h.lower() in text.lower() for h in DIRECTIVE_HINTS):
        tags.append("directive")
    return tags[:20]


def stable_uuid(*parts: str) -> str:
    return str(uuid.uuid5(NS, "|".join(parts)))


def weaviate_request(method: str, path: str, body: dict | None = None, timeout: int = 30):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urlrequest.Request(f"{WEAVIATE_BASE}{path}", data=data, method=method, headers=headers)
    try:
        return urlrequest.urlopen(req, timeout=timeout).read()
    except urlerror.HTTPError as e:
        return f"HTTP_{e.code}:{e.read().decode()[:200]}"


def upsert_object(cls: str, obj_id: str, props: dict) -> str:
    payload = {"class": cls, "id": obj_id, "properties": props}
    r = weaviate_request("POST", "/v1/objects", payload)
    if isinstance(r, str) and r.startswith("HTTP_"):
        if "422" in r or "409" in r:
            r2 = weaviate_request("PUT", f"/v1/objects/{cls}/{obj_id}", payload)
            return "upserted" if not (isinstance(r2, str) and r2.startswith("HTTP_")) else f"err_put:{r2[:100]}"
        return f"err_post:{r[:100]}"
    return "created"


def load_cursor() -> dict:
    if CURSOR_PATH.exists():
        try:
            return json.loads(CURSOR_PATH.read_text())
        except Exception:
            pass
    return {}


def save_cursor(cur: dict) -> None:
    CURSOR_PATH.write_text(json.dumps(cur, indent=2))


def parse_ts(s: str) -> str | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return None


def process_jsonl(jsonl_path: Path, callsign: str) -> dict:
    session_id = jsonl_path.stem
    stats = {"turns_seen": 0, "turns_indexed": 0, "chunks_upserted": 0, "errors": 0}
    first_ts = None
    last_ts = None
    all_turns = []
    turn_index = 0
    with jsonl_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                stats["errors"] += 1
                continue
            stats["turns_seen"] += 1
            role, text, tool_count = extract_turn_text(d)
            if role is None or len(text) < MIN_TEXT_CHARS:
                continue
            ts = parse_ts(d.get("timestamp") or (d.get("message") or {}).get("timestamp") or "")
            if ts and not first_ts:
                first_ts = ts
            if ts:
                last_ts = ts
            chunks = chunk_text(text)
            for ci, chunk in enumerate(chunks):
                obj_id = stable_uuid("st", session_id, str(turn_index), str(ci))
                props = {
                    "session_id": session_id,
                    "callsign": callsign,
                    "role": role,
                    "timestamp": ts,
                    "turn_index": turn_index,
                    "chunk_index": ci,
                    "text": chunk,
                    "text_chars": len(text),
                    "tool_calls": tool_count,
                    "tags": tag_text(chunk),
                }
                props = {k: v for k, v in props.items() if v is not None}
                r = upsert_object("SessionTranscripts", obj_id, props)
                if r in ("created", "upserted"):
                    stats["chunks_upserted"] += 1
                else:
                    stats["errors"] += 1
                    if stats["errors"] <= 3:
                        log.error("upsert err on %s turn=%s chunk=%s: %s", session_id, turn_index, ci, r)
            stats["turns_indexed"] += 1
            all_turns.append({"role": role, "text": text, "turn_index": turn_index, "ts": ts})
            turn_index += 1
    stats["session_start"] = first_ts
    stats["session_end"] = last_ts
    stats["all_turns"] = all_turns
    return stats


_SYSTEM_PROMPT = (
    "You are extracting structured facts from a Claude Code session transcript between Dave (CEO/user) "
    "and an AI agent. Output JSON only: an array of fact objects. Each object: "
    '{"type": "decision|discovery|directive|blocker|lesson|verdict|action_item", '
    '"text": "<one-sentence fact>", "context": "<surrounding context, max 200 chars>", '
    '"related_keis": ["KEI-XX"], "related_prs": ["1234"]}. '
    "Categories: decision = ratified architectural/governance choice; discovery = empirical finding (especially failed/verified paths); "
    "directive = explicit Dave instruction; blocker = problem surfaced that blocked work; lesson = pattern learned (often anchored 'feedback'); "
    "verdict = audit/review conclusion; action_item = pending follow-up. "
    "Skip routine status, acknowledgements, tool noise. Extract 5-30 facts per session. "
    "Output ONLY the JSON array, no preamble, no markdown fences."
)


def _build_transcript(turns: list[dict], max_chars: int = 80000) -> str:
    parts = []
    total = 0
    for t in turns:
        line = f"[{t['role']}] {t['text']}\n\n"
        if total + len(line) > max_chars:
            parts.append("\n[truncated]")
            break
        parts.append(line)
        total += len(line)
    return "".join(parts)


def _parse_json_array(text_out: str) -> tuple[list | None, str | None]:
    text_out = re.sub(r"^```(json)?\n|\n```$", "", text_out.strip(), flags=re.MULTILINE)
    try:
        facts = json.loads(text_out)
        if not isinstance(facts, list):
            return None, "not_list"
        return facts, None
    except json.JSONDecodeError as e:
        return None, f"parse_err: {e} | text: {text_out[:200]}"


def _call_openai(transcript: str, callsign: str, session_id: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"facts": [], "model": OPENAI_MODEL, "skipped": "no OPENAI_API_KEY"}
    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT + ' Wrap the array in {"facts": [...]} for JSON object output.'},
            {"role": "user", "content": f"Transcript ({callsign}, session {session_id}):\n\n{transcript}"},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 4000,
    }
    req = urlrequest.Request(OPENAI_API_URL, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type":"application/json", "Authorization": f"Bearer {api_key}"})
    try:
        raw = urlrequest.urlopen(req, timeout=180).read()
    except urlerror.HTTPError as e:
        return {"facts": [], "model": OPENAI_MODEL, "error": f"HTTP_{e.code}: {e.read().decode()[:300]}"}
    except Exception as e:
        return {"facts": [], "model": OPENAI_MODEL, "error": f"req_failed: {e}"}
    resp = json.loads(raw)
    text_out = (resp.get("choices",[{}])[0].get("message",{}).get("content") or "").strip()
    try:
        wrapper = json.loads(text_out)
        facts = wrapper.get("facts") if isinstance(wrapper, dict) else None
        if not isinstance(facts, list):
            return {"facts": [], "model": OPENAI_MODEL, "error": f"no_facts_key | text: {text_out[:200]}"}
    except json.JSONDecodeError as e:
        return {"facts": [], "model": OPENAI_MODEL, "error": f"parse_err: {e} | text: {text_out[:200]}"}
    return {"facts": facts, "model": OPENAI_MODEL, "usage": resp.get("usage", {})}


def _call_anthropic(transcript: str, callsign: str, session_id: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"facts": [], "model": ANTHROPIC_MODEL, "skipped": "no ANTHROPIC_API_KEY"}
    body = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 4000,
        "system": _SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": f"Transcript ({callsign}, session {session_id}):\n\n{transcript}"}],
    }
    req = urlrequest.Request(ANTHROPIC_API_URL, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type":"application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"})
    try:
        raw = urlrequest.urlopen(req, timeout=180).read()
    except urlerror.HTTPError as e:
        return {"facts": [], "model": ANTHROPIC_MODEL, "error": f"HTTP_{e.code}: {e.read().decode()[:300]}"}
    except Exception as e:
        return {"facts": [], "model": ANTHROPIC_MODEL, "error": f"req_failed: {e}"}
    resp = json.loads(raw)
    content_blocks = resp.get("content", [])
    text_out = "".join(b.get("text","") for b in content_blocks if b.get("type") == "text").strip()
    facts, err = _parse_json_array(text_out)
    if facts is None:
        return {"facts": [], "model": ANTHROPIC_MODEL, "error": err}
    return {"facts": facts, "model": ANTHROPIC_MODEL, "usage": resp.get("usage", {})}


def extract_facts_via_llm(session_id: str, callsign: str, turns: list[dict], session_start: str | None, session_end: str | None) -> dict:
    if not turns:
        return {"facts": [], "model": "n/a", "skipped": "no turns"}
    transcript = _build_transcript(turns)
    if LLM_PROVIDER == "anthropic":
        return _call_anthropic(transcript, callsign, session_id)
    out = _call_openai(transcript, callsign, session_id)
    if out.get("facts") or out.get("skipped"):
        return out
    log.warning("openai failed (%s), trying anthropic", out.get("error","?")[:80])
    return _call_anthropic(transcript, callsign, session_id)


def upload_facts(session_id: str, callsign: str, facts: list[dict], session_start: str | None, session_end: str | None, model: str) -> dict:
    stats = {"facts_total": len(facts), "upserted": 0, "errors": 0}
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    for i, fact in enumerate(facts):
        if not isinstance(fact, dict) or not fact.get("text"):
            continue
        obj_id = stable_uuid("sf", session_id, str(i), (fact.get("text") or "")[:80])
        props = {
            "session_id": session_id,
            "callsign": callsign,
            "session_start": session_start,
            "session_end": session_end,
            "fact_type": (fact.get("type") or "unknown")[:32],
            "fact_text": (fact.get("text") or "")[:2000],
            "context": (fact.get("context") or "")[:800],
            "related_keis": [str(k)[:32] for k in (fact.get("related_keis") or []) if k][:20],
            "related_prs": [str(p)[:16] for p in (fact.get("related_prs") or []) if p][:20],
            "extracted_at": now_iso,
            "extractor_model": model,
        }
        props = {k: v for k, v in props.items() if v is not None}
        r = upsert_object("SessionFacts", obj_id, props)
        if r in ("created", "upserted"):
            stats["upserted"] += 1
        else:
            stats["errors"] += 1
            if stats["errors"] <= 3:
                log.error("fact upsert err %s/%d: %s", session_id, i, r)
    return stats


def run_once(callsigns: list[str], skip_facts: bool, since_mtime: float | None) -> dict:
    cursor = load_cursor()
    cutoff = time.time() - since_mtime if since_mtime else 0
    grand = {"files": 0, "chunks": 0, "facts": 0, "errors": 0, "skipped_unchanged": 0, "skipped_facts": 0}
    for cs in callsigns:
        proj_dir = PROJECTS_ROOT / CALLSIGN_DIRS[cs]
        if not proj_dir.exists():
            continue
        jsonl_files = sorted(proj_dir.glob("*.jsonl"))
        log.info("callsign=%s files=%d", cs, len(jsonl_files))
        for jf in jsonl_files:
            mtime = jf.stat().st_mtime
            if mtime < cutoff:
                continue
            key = str(jf)
            if cursor.get(key, {}).get("mtime") == mtime and cursor.get(key, {}).get("done"):
                grand["skipped_unchanged"] += 1
                continue
            log.info("processing %s/%s (mtime=%s)", cs, jf.name, datetime.fromtimestamp(mtime).isoformat())
            try:
                stats = process_jsonl(jf, cs)
            except Exception as e:
                log.exception("process_jsonl failed: %s", e)
                grand["errors"] += 1
                continue
            grand["files"] += 1
            grand["chunks"] += stats["chunks_upserted"]
            grand["errors"] += stats["errors"]
            fact_stats = {"upserted": 0, "errors": 0}
            facts_done = False
            if not skip_facts and stats["all_turns"]:
                ex = extract_facts_via_llm(jf.stem, cs, stats["all_turns"], stats["session_start"], stats["session_end"])
                if ex.get("facts"):
                    fact_stats = upload_facts(jf.stem, cs, ex["facts"], stats["session_start"], stats["session_end"], ex["model"])
                    grand["facts"] += fact_stats["upserted"]
                    facts_done = True
                elif ex.get("error") or ex.get("skipped"):
                    log.warning("fact extract failed/skipped %s: %s", jf.name, ex.get("error") or ex.get("skipped"))
                    grand["skipped_facts"] += 1
            cursor[key] = {"mtime": mtime, "done": True, "facts_done": facts_done, "chunks": stats["chunks_upserted"]}
            save_cursor(cursor)
    log.info("run_once done: %s", grand)
    return grand


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true")
    p.add_argument("--daemon", type=int, metavar="SECONDS")
    p.add_argument("--callsign", choices=list(CALLSIGN_DIRS.keys()))
    p.add_argument("--skip-facts", action="store_true", help="skip LLM fact extraction (chunks only)")
    p.add_argument("--since-mtime", type=float, metavar="SECONDS", help="only files mtime in last N seconds")
    args = p.parse_args()
    callsigns = [args.callsign] if args.callsign else list(CALLSIGN_DIRS.keys())
    if args.once:
        run_once(callsigns, args.skip_facts, args.since_mtime)
        return 0
    if args.daemon:
        log.info("daemon mode: poll=%ss callsigns=%s skip_facts=%s", args.daemon, callsigns, args.skip_facts)
        while True:
            try:
                run_once(callsigns, args.skip_facts, args.since_mtime or args.daemon * 4)
            except Exception:
                log.exception("daemon iteration failed")
            time.sleep(args.daemon)
    p.error("--once or --daemon required")


if __name__ == "__main__":
    sys.exit(main())
