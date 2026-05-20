#!/usr/bin/env python3
"""agent_stop_hook.py — Stop hook for every agent. Publishes completion to NATS.

Fires when an agent's Claude session goes idle (end of a turn). Reads the
last assistant text response from the session transcript, classifies what
happened, publishes a typed envelope to the appropriate NATS subject so
the rest of the fleet sees the event in real-time.

Claude Code passes a JSON payload on stdin with:
  - session_id, transcript_path, stop_hook_active, cwd, hook_event_name

Classification (simple keyword/marker rules; refined per role):
  - "[SHIPPED:" or "PR #<n>" + opened → completion + review
  - "[REVIEW:approve:" or "[REVIEW:HOLD" → review verdict
  - "[CONCUR:" → deliberation response
  - "BLOCKED" / "[BLOCKED:" → blocker
  - "DELIBERATION-RESPONSE" → deliberation response
  - default → status update

Routing (publish to one or more subjects):
  - Worker (atlas/orion/scout/nova): completion → keiracom.elliot.inbox.
    PR shipped → also keiracom.review.<pr>
  - Reviewer (aiden/max): review verdict → keiracom.review.<pr>.
    Deliberation response → keiracom.deliberation.<topic_id_or_thread>.
  - Elliot: handled by a separate stage-4 hook (notifications to Slack).

Fail-open: any error logs to stderr and exits 0 — never blocks a session.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

WORKER_CALLSIGNS = {"atlas", "orion", "scout", "nova"}
REVIEWER_CALLSIGNS = {"aiden", "max"}

PR_OPEN_RE = re.compile(r"\bPR\s*#?(\d+)\b", re.IGNORECASE)
SHIPPED_RE = re.compile(r"\[SHIPPED:([a-z]+)\s+([A-Za-z_0-9-]+)\]", re.IGNORECASE)
REVIEW_RE = re.compile(r"\[REVIEW:(approve|hold|concur)[\-_]?([A-Z\-]*)?:?([a-z]+)\]", re.IGNORECASE)
CONCUR_RE = re.compile(r"\[CONCUR:([a-z]+)\]", re.IGNORECASE)
BLOCKER_RE = re.compile(r"\[BLOCKED:([a-z]+)\]|BLOCKER:", re.IGNORECASE)
DELIB_RE = re.compile(r"DELIBERATION[\-:][A-Z\-]+", re.IGNORECASE)


def callsign() -> str:
    cs = os.environ.get("CALLSIGN", "").strip().lower()
    if cs:
        return cs
    # Fallback: infer from cwd
    cwd = os.getcwd()
    if cwd.endswith("Agency_OS"):
        return "elliot"
    for c in WORKER_CALLSIGNS | REVIEWER_CALLSIGNS:
        if cwd.endswith(f"Agency_OS-{c}"):
            return c
    return "unknown"


def read_last_assistant_text(transcript_path: str) -> str:
    if not transcript_path or not Path(transcript_path).exists():
        return ""
    last_text = ""
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
                    parts = []
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "text":
                            parts.append(b.get("text", ""))
                    txt = "\n".join(p for p in parts if p)
                    if txt:
                        last_text = txt
                elif isinstance(content, str) and content:
                    last_text = content
    except OSError as e:
        sys.stderr.write(f"[agent_stop_hook] transcript read err: {e}\n")
    return last_text


NOISE_RE = re.compile(
    r"^\s*(?:\[?\w+@nats.*\]?\s*)?NATS echo[es]*[, ]|"
    r"^\s*Standing\.?\s*$|"
    r"^\s*(?:NATS echo[es]*|relay reflection)[\s,.;:]*(?:no action[\s.,;:]*)?(?:Standing\.?\s*)?$",
    re.IGNORECASE | re.MULTILINE,
)


def is_noise_filler(text: str) -> bool:
    """Suppress hook emit on NATS-echo / Standing-filler self-replies (Elliot 2026-05-19)."""
    if not text or not text.strip():
        return True
    stripped = text.strip()
    if NOISE_RE.search(stripped):
        return True
    low = stripped.lower()
    if low in {"standing.", "standing", "no action. standing.", "nats echo, no action. standing."}:
        return True
    if len(stripped) < 120 and re.search(r"\bstanding\.?\s*$", low) and re.search(r"\b(echo|no action|acknowledged|holding|no change)\b", low):
        return True
    return False


def classify(text: str) -> dict:
    cls = {"kind": "status", "pr_number": None, "topic_id": None}
    if not text:
        return cls
    m_blocker = BLOCKER_RE.search(text)
    if m_blocker:
        cls["kind"] = "blocker"
        return cls
    m_shipped = SHIPPED_RE.search(text)
    m_pr = PR_OPEN_RE.search(text)
    if m_shipped:
        cls["kind"] = "shipped"
        if m_pr:
            cls["pr_number"] = m_pr.group(1)
        return cls
    m_review = REVIEW_RE.search(text)
    if m_review:
        cls["kind"] = "review"
        if m_pr:
            cls["pr_number"] = m_pr.group(1)
        return cls
    if CONCUR_RE.search(text) or DELIB_RE.search(text):
        cls["kind"] = "deliberation"
        return cls
    return cls


def publish_nats(subject: str, envelope: dict) -> None:
    payload = json.dumps(envelope, default=str)
    try:
        subprocess.run(
            ["/usr/local/bin/nats", "pub", subject, payload],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        sys.stderr.write(f"[agent_stop_hook] nats pub err: {e}\n")


def summarize(text: str, max_chars: int = 600) -> str:
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 10].rsplit("\n", 1)[0] + "\n…[truncated]"


def main() -> int:
    cs = callsign()
    # Skip elliot — handled by a different hook (stage 4 notification policy)
    if cs == "elliot":
        return 0
    if cs == "unknown":
        sys.stderr.write("[agent_stop_hook] unknown callsign — skipping\n")
        return 0
    try:
        payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except Exception:
        payload = {}
    transcript_path = payload.get("transcript_path") or ""
    text = read_last_assistant_text(transcript_path)
    if is_noise_filler(text):
        sys.stderr.write(f"[agent_stop_hook] {cs} noise-filler suppressed\n")
        return 0
    cls = classify(text)
    envelope = {
        "from": cs,
        "kind": cls["kind"],
        "summary": summarize(text),
        "ts": time.time(),
        "session_id": payload.get("session_id", ""),
    }
    if cls["pr_number"]:
        envelope["pr_number"] = cls["pr_number"]

    # Routing by role + kind
    targets: list[str] = []
    if cs in WORKER_CALLSIGNS:
        # Always tell elliot what happened
        targets.append("keiracom.elliot.inbox")
        if cls["kind"] == "shipped" and cls["pr_number"]:
            targets.append(f"keiracom.review.{cls['pr_number']}")
    elif cs in REVIEWER_CALLSIGNS:
        if cls["kind"] == "review" and cls["pr_number"]:
            targets.append(f"keiracom.review.{cls['pr_number']}")
            targets.append("keiracom.elliot.inbox")
        elif cls["kind"] == "deliberation":
            # Route to elliot inbox; future: extract topic_id and post to deliberation.<id>
            targets.append("keiracom.elliot.inbox")
        elif cls["kind"] == "blocker":
            targets.append("keiracom.elliot.inbox")
        else:
            targets.append("keiracom.elliot.inbox")

    if not targets:
        return 0
    for subj in targets:
        publish_nats(subj, envelope)
    sys.stderr.write(f"[agent_stop_hook] {cs}/{cls['kind']} → {targets}\n")
    # Next-work prompter: closes the "agent idle after turn-end" gap
    # (Dave directive 2026-05-20). Fires for workers + reviewers; fail-open.
    try:
        subprocess.run(
            ["/home/elliotbot/clawd/Agency_OS/.venv/bin/python3",
             "/home/elliotbot/clawd/Agency_OS/scripts/orchestrator/next_work_prompter.py",
             "--callsign", cs],
            capture_output=True, text=True, timeout=20, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        sys.stderr.write(f"[agent_stop_hook] next_work_prompter err: {e}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
