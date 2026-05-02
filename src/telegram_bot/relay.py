"""
Relay utilities for tmux session ↔ Telegram communication.
Used by Elliottbot in the tmux Claude session to send/receive messages from Dave.
"""

import contextlib
import json
import os
import uuid
from datetime import UTC, datetime

from src.relay.redis_relay import outbox_queue
from src.relay.redis_relay import push_sync as redis_push_sync

RELAY_DIR = "/tmp/telegram-relay"
INBOX_DIR = f"{RELAY_DIR}/inbox"
OUTBOX_DIR = f"{RELAY_DIR}/outbox"
CHAT_ID = 7267788033


def send_text(text: str, chat_id: int = CHAT_ID) -> str:
    """Send a text message to Telegram via the relay outbox."""
    os.makedirs(OUTBOX_DIR, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    msg_id = f"{ts}_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": msg_id,
        "type": "text",
        "chat_id": chat_id,
        "text": text,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    path = os.path.join(OUTBOX_DIR, f"{msg_id}.json")
    with open(path, "w") as f:
        json.dump(payload, f)
    # Phase 1b dual-write: also push to Redis (fail-open)
    with contextlib.suppress(Exception):
        redis_push_sync(outbox_queue(os.environ.get("CALLSIGN", "elliot")), payload)
    return msg_id


def send_file(file_path: str, caption: str = "", chat_id: int = CHAT_ID) -> str:
    """Send a file to Telegram via the relay outbox."""
    os.makedirs(OUTBOX_DIR, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    msg_id = f"{ts}_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": msg_id,
        "type": "file",
        "chat_id": chat_id,
        "file_path": os.path.abspath(file_path),
        "caption": caption,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    path = os.path.join(OUTBOX_DIR, f"{msg_id}.json")
    with open(path, "w") as f:
        json.dump(payload, f)
    # Phase 1b dual-write: also push to Redis (fail-open)
    with contextlib.suppress(Exception):
        redis_push_sync(outbox_queue(os.environ.get("CALLSIGN", "elliot")), payload)
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
