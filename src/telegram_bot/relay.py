"""
Relay utilities for tmux session ↔ Telegram communication.
Used by both Elliot and Aiden in their respective tmux Claude sessions.
Callsign is auto-detected from the tmux session name so each session writes
to its own per-callsign inbox/outbox — this is what keeps Aiden's traffic
out of Elliot's pane and vice versa.
"""
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _detect_callsign() -> str:
    """Detect callsign from tmux session name first, env var second.
    tmux session "aiden" -> "aiden"; "elliottbot" -> "elliot"; else env
    CALLSIGN, else "elliot". tmux wins over env because the shell env may
    have a stale CALLSIGN inherited from a profile (observed: shell env
    defaults to CALLSIGN=elliot even in the aiden pane)."""
    try:
        s = subprocess.check_output(
            ["tmux", "display-message", "-p", "#{session_name}"],
            text=True, stderr=subprocess.DEVNULL, timeout=2,
        ).strip()
        if s == "aiden":
            return "aiden"
        if s == "elliottbot":
            return "elliot"
    except Exception:
        pass
    return os.environ.get("CALLSIGN", "elliot")


CALLSIGN = _detect_callsign()
# Path convention matches chat_bot.py: parent dir is per-callsign, inbox/outbox
# are subdirs. Previously this file used /tmp/telegram-relay/{inbox,outbox}-{callsign}
# which diverged from chat_bot.py and meant relay.py and chat_bot.py never saw
# each other's files. Aligned 2026-04-17 per PR #343 review.
RELAY_DIR = f"/tmp/telegram-relay-{CALLSIGN}"
INBOX_DIR = f"{RELAY_DIR}/inbox"
OUTBOX_DIR = f"{RELAY_DIR}/outbox"
CHAT_ID = 7267788033


def send_text(text: str, chat_id: int = CHAT_ID) -> str:
    """Send a text message to Telegram via the relay outbox."""
    os.makedirs(OUTBOX_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    msg_id = f"{ts}_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": msg_id,
        "type": "text",
        "chat_id": chat_id,
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    path = os.path.join(OUTBOX_DIR, f"{msg_id}.json")
    with open(path, "w") as f:
        json.dump(payload, f)
    return msg_id


def send_file(file_path: str, caption: str = "", chat_id: int = CHAT_ID) -> str:
    """Send a file to Telegram via the relay outbox."""
    os.makedirs(OUTBOX_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    msg_id = f"{ts}_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": msg_id,
        "type": "file",
        "chat_id": chat_id,
        "file_path": os.path.abspath(file_path),
        "caption": caption,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    path = os.path.join(OUTBOX_DIR, f"{msg_id}.json")
    with open(path, "w") as f:
        json.dump(payload, f)
    return msg_id


def check_inbox() -> list[dict]:
    """Check for new messages from Telegram. Returns list of message dicts, clears inbox."""
    os.makedirs(INBOX_DIR, exist_ok=True)
    messages = []
    for fname in sorted(os.listdir(INBOX_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(INBOX_DIR, fname)
        try:
            with open(fpath) as f:
                msg = json.load(f)
            messages.append(msg)
            os.unlink(fpath)
        except Exception:
            pass
    return messages


def peek_inbox() -> list[dict]:
    """Check for new messages WITHOUT removing them."""
    os.makedirs(INBOX_DIR, exist_ok=True)
    messages = []
    for fname in sorted(os.listdir(INBOX_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(INBOX_DIR, fname)
        try:
            with open(fpath) as f:
                messages.append(json.load(f))
        except Exception:
            pass
    return messages
