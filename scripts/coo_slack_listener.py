#!/usr/bin/env python3
"""coo_slack_listener.py — Max COO Slack inbound listener (Step 4).

Polls #execution every 30s, filters for messages relevant to Max/COO,
writes to /tmp/coo-inbox/ in the same JSON shape the existing pipeline expects.

Also polls #ops for any activity (COO's primary channel post-cutover).

Env:
    SLACK_BOT_TOKEN     (required)
    COO_POLL_INTERVAL   (optional, default 30)
    COO_BOT_ID          (optional, default B0B2W7VL7T4 — skip own messages)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
OWN_BOT_ID = os.environ.get("COO_BOT_ID", "B0B2W7VL7T4")
POLL_INTERVAL = int(os.environ.get("COO_POLL_INTERVAL", "8"))
INBOX_DIR = Path("/tmp/coo-inbox")
RELAY_INBOX = Path("/tmp/telegram-relay-max/inbox")
LAST_TS_PATH = Path("/tmp/max-slack-listener-last-ts.json")

CHANNELS_TO_POLL = {
    "C0B3QB0K1GQ": "execution",
    "C0B2PM3TV0B": "ceo",
    "C0B2UCNRJ86": "ops",
}

MATCH_KEYWORDS = {"max", "coo", "all", "both", "team", "everyone"}

last_ts: dict[str, str] = {}
BACKOFF_INITIAL = 30.0
BACKOFF_MAX = 120.0
_backoff_until: float = 0.0
_backoff_current: float = BACKOFF_INITIAL


def load_last_ts() -> None:
    if LAST_TS_PATH.exists():
        try:
            last_ts.update(json.loads(LAST_TS_PATH.read_text()))
        except (OSError, json.JSONDecodeError):
            pass


def save_last_ts() -> None:
    try:
        LAST_TS_PATH.write_text(json.dumps(last_ts))
    except OSError as e:
        print(f"save_last_ts failed: {e}", file=sys.stderr, flush=True)


def slack_get(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {BOT_TOKEN}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def poll_channel(channel_id: str) -> list[dict]:
    global _backoff_until, _backoff_current
    if time.time() < _backoff_until:
        return []
    oldest = last_ts.get(channel_id, "")
    url = f"https://slack.com/api/conversations.history?channel={channel_id}&limit=20"
    if oldest:
        url += f"&oldest={oldest}"
    try:
        data = slack_get(url)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry_after = float(e.headers.get("Retry-After") or _backoff_current)
            _backoff_until = time.time() + retry_after
            _backoff_current = min(_backoff_current * 2, BACKOFF_MAX)
            print(f"poll {channel_id} 429: backoff {retry_after}s (next={_backoff_current})", file=sys.stderr, flush=True)
            return []
        print(f"poll {channel_id} error: {e}", file=sys.stderr, flush=True)
        return []
    except (urllib.error.URLError, OSError) as e:
        print(f"poll {channel_id} error: {e}", file=sys.stderr, flush=True)
        return []
    if not data.get("ok"):
        if data.get("error") == "ratelimited":
            _backoff_until = time.time() + _backoff_current
            _backoff_current = min(_backoff_current * 2, BACKOFF_MAX)
            print(f"poll {channel_id} ratelimited: backoff {_backoff_current}s", file=sys.stderr, flush=True)
        else:
            print(f"poll {channel_id} failed: {data.get('error')}", file=sys.stderr, flush=True)
        return []
    _backoff_current = BACKOFF_INITIAL
    messages = data.get("messages", [])
    if messages:
        last_ts[channel_id] = messages[0].get("ts", oldest)
        save_last_ts()
    return messages


def is_own_bot(msg: dict) -> bool:
    if msg.get("bot_id") == OWN_BOT_ID:
        return True
    if (msg.get("username") or "").lower() == "max":
        return True
    text = (msg.get("text") or "").lstrip()
    if text.startswith("[MAX]"):
        return True
    return False


def is_relevant(msg: dict) -> bool:
    if is_own_bot(msg):
        return False
    if msg.get("subtype"):
        return False
    # Always inbox human messages — Dave + ops + anyone non-bot.
    # Bots only via keyword match (avoids cross-bot loop noise).
    if not msg.get("bot_id"):
        return True
    text = (msg.get("text") or "").lower()
    return any(kw in text for kw in MATCH_KEYWORDS)


def write_to_inbox(msg: dict, channel_name: str) -> None:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    RELAY_INBOX.mkdir(parents=True, exist_ok=True)
    ts_str = msg.get("ts", "0")
    dt = datetime.fromtimestamp(float(ts_str), tz=timezone.utc)
    fname = dt.strftime("%Y%m%d_%H%M%S") + f"_{ts_str.replace('.', '')[:8]}.json"
    sender = msg.get("username") or msg.get("user") or "unknown"
    text = msg.get("text", "")
    # COO inbox (legacy sideband — downstream scripts read this)
    coo_payload = {
        "sender_callsign": sender,
        "text": f"[SLACK #{channel_name} — from {sender}]: {text}",
        "timestamp_iso": dt.isoformat(),
        "message_id": ts_str.replace(".", ""),
        "chat_id": -1,
        "source": "slack",
        "channel": channel_name,
    }
    coo_path = INBOX_DIR / fname
    if not coo_path.exists():
        coo_path.write_text(json.dumps(coo_payload))
    # Relay inbox (triggers tmux injection via max-relay-watcher)
    relay_payload = {
        "type": "text",
        "chat_id": -1,
        "text": f"[SLACK #{channel_name} — from {sender}]: {text}",
        "sender": sender,
        "timestamp": dt.isoformat(),
    }
    relay_path = RELAY_INBOX / fname
    if not relay_path.exists():
        relay_path.write_text(json.dumps(relay_payload))
        print(f"inbox+relay: {fname} ({channel_name})", flush=True)


def main() -> int:
    if not BOT_TOKEN:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        return 1
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    RELAY_INBOX.mkdir(parents=True, exist_ok=True)
    load_last_ts()
    print(f"COO listener started — polling {list(CHANNELS_TO_POLL.values())} every {POLL_INTERVAL}s", flush=True)
    # Seed any unseeded channels to current time (don't replay history on first boot)
    now_ts = str(time.time())
    for ch_id in CHANNELS_TO_POLL:
        last_ts.setdefault(ch_id, now_ts)
    save_last_ts()
    while True:
        for channel_id, channel_name in CHANNELS_TO_POLL.items():
            messages = poll_channel(channel_id)
            for msg in reversed(messages):
                if is_own_bot(msg):
                    continue
                if msg.get("subtype"):
                    continue
                if channel_name == "ops" or is_relevant(msg):
                    write_to_inbox(msg, channel_name)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
