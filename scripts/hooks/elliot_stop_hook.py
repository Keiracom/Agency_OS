#!/usr/bin/env python3
"""elliot_stop_hook.py — Stage 4 — Elliot's notification stop hook.

Fires when elliot's session goes idle. Reads the last assistant text from the
transcript, reads the notification policy, classifies the response, decides
whether to post to Slack #ceo per policy, applies cool-down + format rules.

Suppresses auto-post if I already called slack_relay.py manually this turn
(no double-post).

Fail-open: any error logs to stderr, exits 0.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

POLICY_PATH = Path("/home/elliotbot/clawd/Agency_OS/config/elliot_notification_policy.md")
STATE_PATH = Path("/tmp/elliot_notify_state.json")
RELAY_LOG_PROBE = Path("/tmp/elliot_last_slack_post.ts")
RELAY = "/home/elliotbot/clawd/Agency_OS/scripts/slack_relay.py"
PYTHON = "/home/elliotbot/clawd/Agency_OS/.venv/bin/python3"
ENV_FILE = "/home/elliotbot/.config/agency-os/.env"
COOL_DOWN_SECONDS = 60

COMPLETION_RE = re.compile(r"\b(shipped|completed|done|merged|landed|finished|live|deployed)\b", re.IGNORECASE)
BLOCKER_RE = re.compile(r"\b(blocked|blocker|cannot|stuck|need.{0,20}decision|need.{0,20}your)\b", re.IGNORECASE)
MERGE_READY_RE = re.compile(r"\b(merge.eligible|dual.concur|ready.to.merge|approved.by.both)\b", re.IGNORECASE)
INCIDENT_RE = re.compile(r"\b(down|crashed|stalled|incident|degraded|failing)\b", re.IGNORECASE)
ROUTINE_ACK_RE = re.compile(r"^(acknowledged|noted|got it|starting|running|checking|will|standing by|waiting)", re.IGNORECASE)
SLACK_POST_MARKER_RE = re.compile(r"sent to Slack #C0B2PM3TV0B|\[ELLIOT\] sent to Slack")


def load_policy() -> dict:
    """Parse the policy markdown for verbosity + cool-down. Tolerant defaults."""
    policy = {"verbosity": "balanced", "cool_down": COOL_DOWN_SECONDS}
    if not POLICY_PATH.exists():
        return policy
    try:
        text = POLICY_PATH.read_text()
        m = re.search(r"^VERBOSITY:\s*(\w+)", text, re.MULTILINE)
        if m:
            policy["verbosity"] = m.group(1).lower()
    except OSError:
        pass
    return policy


def read_state() -> dict:
    if not STATE_PATH.exists():
        return {"last_post_at": 0}
    try:
        return json.loads(STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {"last_post_at": 0}


def write_state(state: dict) -> None:
    try:
        STATE_PATH.write_text(json.dumps(state))
    except OSError:
        pass


def read_last_assistant_text(transcript_path: str) -> str:
    if not transcript_path or not Path(transcript_path).exists():
        return ""
    last = ""
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("type") != "assistant":
                    continue
                msg = d.get("message") or {}
                content = msg.get("content")
                if isinstance(content, list):
                    parts = [b.get("text","") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                    txt = "\n".join(p for p in parts if p)
                    if txt:
                        last = txt
                elif isinstance(content, str) and content:
                    last = content
    except OSError as e:
        sys.stderr.write(f"[elliot_stop_hook] read err: {e}\n")
    return last


def already_posted_this_turn(transcript_path: str, since_ts: float) -> bool:
    """Look at recent tool_result blocks for the slack_relay success marker."""
    if not transcript_path or not Path(transcript_path).exists():
        return False
    try:
        with open(transcript_path) as f:
            lines = f.readlines()
    except OSError:
        return False
    # scan last ~50 entries for slack_relay post markers
    for line in lines[-100:]:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        # tool_result content may indicate a slack post happened
        msg = d.get("message") or {}
        content = msg.get("content")
        if isinstance(content, list):
            for b in content:
                if not isinstance(b, dict):
                    continue
                tc = b.get("content")
                txt = ""
                if isinstance(tc, str):
                    txt = tc
                elif isinstance(tc, list):
                    for s in tc:
                        if isinstance(s, dict) and s.get("type") == "text":
                            txt += s.get("text","")
                if txt and SLACK_POST_MARKER_RE.search(txt):
                    return True
        elif isinstance(content, str):
            if SLACK_POST_MARKER_RE.search(content):
                return True
    return False


def classify(text: str, verbosity: str) -> tuple[str | None, str]:
    """Return (kind, summary) or (None, '') to suppress."""
    if not text or len(text.strip()) < 30:
        return None, ""
    # Skip routine acks
    first_line = text.strip().split("\n", 1)[0]
    if ROUTINE_ACK_RE.match(first_line) and len(text) < 300:
        return None, ""
    # Incident / blocker — highest priority, bypasses cool-down
    if INCIDENT_RE.search(text) and any(w in text.lower() for w in ("service", "indexer", "down", "stalled", "crashed")):
        return "incident", text
    if BLOCKER_RE.search(text):
        return "blocker", text
    if MERGE_READY_RE.search(text):
        return "merge_ready", text
    if COMPLETION_RE.search(text):
        return "completion", text
    # Verbosity decides whether to emit progress
    if verbosity == "chatty":
        return "progress", text
    return None, ""


def summarise_for_ceo(kind: str, raw: str, max_chars: int = 1200) -> str:
    """Build a #ceo-format-compliant summary. Bullets only, plain English."""
    # naive: lead with category, first 8 bullet-like lines or first paragraphs
    head = {
        "completion": "**Completion**",
        "blocker": "**Blocker — needs decision**",
        "merge_ready": "**Merge eligible**",
        "incident": "**Incident — critical state change**",
        "progress": "**Progress update**",
    }.get(kind, "**Update**")
    lines = raw.strip().split("\n")
    bullets = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        # already a bullet
        if s.startswith(("- ", "* ", "• ")):
            bullets.append(s.replace("* ", "- ").replace("• ", "- "))
        else:
            # convert prose line to a bullet, strip leading hash/asterisk markdown
            s_clean = re.sub(r"^[#*]+\s*", "", s).strip()
            if s_clean:
                bullets.append(f"- {s_clean}")
        if len(bullets) >= 10:
            break
    body = "\n".join(bullets)
    # strip technical tokens that trip the format gate
    body = re.sub(r"PR\s*#\d+", "the PR", body, flags=re.IGNORECASE)
    body = re.sub(r"\b[0-9a-f]{7,40}\b", "<sha>", body)  # commit SHAs
    body = re.sub(r"/home/\S+", "<path>", body)
    body = re.sub(r"`[^`]+`", "<code>", body)  # code spans
    body = re.sub(r"```[\s\S]+?```", "<code>", body)  # code fences
    out = f"{head}\n{body}"
    if len(out) > max_chars:
        out = out[:max_chars].rsplit("\n", 1)[0] + "\n- (truncated)"
    return out


def post_to_ceo(message: str) -> bool:
    try:
        env = os.environ.copy()
        # ensure token is loaded
        if "SLACK_BOT_TOKEN" not in env:
            try:
                for line in open(ENV_FILE):
                    if line.startswith("SLACK_BOT_TOKEN="):
                        env["SLACK_BOT_TOKEN"] = line.split("=",1)[1].strip()
                        break
            except OSError:
                pass
        env["CALLSIGN"] = "elliot"
        r = subprocess.run(
            [PYTHON, RELAY, message],
            capture_output=True, text=True, timeout=15, env=env, check=False,
        )
        if r.returncode == 0:
            return True
        sys.stderr.write(f"[elliot_stop_hook] relay failed rc={r.returncode}: {r.stderr[:200]}\n")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        sys.stderr.write(f"[elliot_stop_hook] relay err: {e}\n")
    return False


def main() -> int:
    cs = os.environ.get("CALLSIGN", "").strip().lower()
    if cs and cs != "elliot":
        return 0  # only fire for elliot
    try:
        payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except Exception:
        payload = {}
    transcript_path = payload.get("transcript_path") or ""
    text = read_last_assistant_text(transcript_path)
    if not text:
        return 0
    policy = load_policy()
    kind, summary_src = classify(text, policy["verbosity"])
    if kind is None:
        return 0  # not worth posting
    state = read_state()
    now = time.time()
    bypass_cooldown = kind in ("blocker", "incident")
    if not bypass_cooldown and (now - state.get("last_post_at", 0)) < policy["cool_down"]:
        sys.stderr.write(f"[elliot_stop_hook] cool-down active ({int(now - state.get('last_post_at',0))}s) — skipping {kind}\n")
        return 0
    if already_posted_this_turn(transcript_path, now - 120):
        sys.stderr.write(f"[elliot_stop_hook] manual slack post detected this turn — skipping {kind}\n")
        return 0
    msg = summarise_for_ceo(kind, summary_src)
    if post_to_ceo(msg):
        state["last_post_at"] = now
        write_state(state)
        sys.stderr.write(f"[elliot_stop_hook] posted {kind} to #ceo ({len(msg)}ch)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
