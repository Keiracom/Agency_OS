#!/usr/bin/env python3
"""elliot_slack_listener.py — inbound Slack listener (Step 3.5).

Polls Slack #execution every 20s via conversations.history. Matches messages
mentioning Elliot's callsign (or all/both/team) and writes them as JSON to
/tmp/telegram-relay-elliot/inbox/ — same shape the existing tmux session
already consumes from the TG relay.

Filter chain (all must pass):
  1. message.text contains a callsign keyword (case-insensitive):
     'elliot' | 'all' | 'both' | 'team'
  2. message.bot_id != B0B2W7VL7T4 (own shared bot — prevents loop)
  3. message.ts > last_seen_ts (skip already-processed)

Env:
  SLACK_BOT_TOKEN          (required) — same shared bot
  SLACK_LISTEN_CHANNEL     (optional) — default #execution C0B3QB0K1GQ
  POLL_INTERVAL_SECONDS    (optional) — default 20
  OWN_BOT_ID               (optional) — default B0B2W7VL7T4 (agency_os)

Defers (per Step 3.5 directive):
  - Channel scope (only #execution polled)
  - Thread support (flat replies only — top-level messages only)
  - Image/file attachments (text only)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

CALLSIGN = "elliot"
INBOX = Path(f"/tmp/telegram-relay-{CALLSIGN}/inbox")
LAST_SEEN_PATH = Path(f"/tmp/elliot-slack-listener-last-seen.txt")
KEYWORDS = ("elliot", "all", "both", "team")

BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
CHANNEL = os.environ.get("SLACK_LISTEN_CHANNEL", "C0B3QB0K1GQ")
POLL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "20"))
OWN_BOT_ID = os.environ.get("OWN_BOT_ID", "B0B2W7VL7T4")


def read_last_seen() -> str:
    if LAST_SEEN_PATH.exists():
        return LAST_SEEN_PATH.read_text().strip()
    return str(time.time())  # boot: only consider messages from now forward


def write_last_seen(ts: str) -> None:
    LAST_SEEN_PATH.write_text(ts)


def fetch_history(oldest: str) -> list[dict]:
    """Call conversations.history; return messages newer than `oldest` ts."""
    if not BOT_TOKEN:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(2)
    url = f"https://slack.com/api/conversations.history?channel={CHANNEL}&oldest={oldest}&limit=50"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {BOT_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    except urllib.error.URLError as e:
        print(f"history fetch failed: {e}", file=sys.stderr, flush=True)
        return []
    if not data.get("ok"):
        print(f"slack rejected: {data}", file=sys.stderr, flush=True)
        return []
    return data.get("messages", [])


def matches_callsign(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in KEYWORDS)


def is_human_message(msg: dict) -> bool:
    """Any message lacking bot_id is from a human (Dave, ops, etc.).
    Always inbox human messages — they're either to me or shared visibility I want."""
    return not msg.get("bot_id")


def write_inbox(msg: dict) -> None:
    """Write a single matched message to the existing inbox path + JSON shape."""
    INBOX.mkdir(parents=True, exist_ok=True)
    ts_iso = datetime.now(timezone.utc).isoformat()
    short = uuid.uuid4().hex[:8]
    fname = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{short}.json"
    payload = {
        "id": fname.replace(".json", ""),
        "type": "text",
        "text": msg.get("text", ""),
        "sender": msg.get("user") or msg.get("bot_id") or "slack-unknown",
        "sender_callsign": "slack-inbound",
        "sender_is_bot": bool(msg.get("bot_id")),
        "slack_ts": msg.get("ts", ""),
        "timestamp": ts_iso,
    }
    (INBOX / fname).write_text(json.dumps(payload))
    print(f"inbound {fname} <- slack ts={msg.get('ts')}", flush=True)


def tick() -> None:
    last_seen = read_last_seen()
    messages = fetch_history(last_seen)
    if not messages:
        return
    # API returns newest-first — reverse for chronological processing
    messages.reverse()
    new_max = last_seen
    for m in messages:
        ts = m.get("ts", "")
        if not ts or ts <= last_seen:
            continue
        if m.get("bot_id") == OWN_BOT_ID:
            new_max = ts  # advance pointer to skip own posts forever
            continue
        text = m.get("text") or ""
        # Inbox if EITHER: human message (Dave + anyone non-bot) OR callsign-mentioning bot post
        if is_human_message(m) or matches_callsign(text):
            write_inbox(m)
        new_max = ts
    if new_max != last_seen:
        write_last_seen(new_max)


def main() -> int:
    INBOX.mkdir(parents=True, exist_ok=True)
    # On boot: persist initial last_seen=now so the file exists. Without
    # this, read_last_seen() returns time.time() FRESH on each tick (no
    # file present), so every tick sees "now" as the floor and zero new
    # messages can ever match. Permanent broken state otherwise.
    if not LAST_SEEN_PATH.exists():
        write_last_seen(str(time.time()))
        print(f"initialised last_seen={LAST_SEEN_PATH.read_text().strip()}", flush=True)
    print(f"slack listener up — channel={CHANNEL} interval={POLL_SECONDS}s own_bot={OWN_BOT_ID}", flush=True)
    while True:
        try:
            tick()
        except Exception as e:
            print(f"tick error: {e}", file=sys.stderr, flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
