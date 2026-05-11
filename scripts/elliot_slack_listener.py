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
# Comma-separated list of channel IDs to poll. Default: #execution + #ceo.
# Per Dave 2026-05-11: bot now joined #ceo (C0B2PM3TV0B) and should see those posts.
CHANNELS = [c.strip() for c in os.environ.get("SLACK_LISTEN_CHANNELS", "C0B3QB0K1GQ,C0B2PM3TV0B").split(",") if c.strip()]
# Backward-compat single-channel env (overrides the list if set)
_single = os.environ.get("SLACK_LISTEN_CHANNEL")
if _single:
    CHANNELS = [_single]
POLL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "8"))
OWN_BOT_ID = os.environ.get("OWN_BOT_ID", "B0B2W7VL7T4")
BACKOFF_INITIAL = 30.0
BACKOFF_MAX = 120.0
_backoff_until: float = 0.0
_backoff_current: float = BACKOFF_INITIAL


def read_last_seen() -> str:
    if LAST_SEEN_PATH.exists():
        return LAST_SEEN_PATH.read_text().strip()
    return str(time.time())  # boot: only consider messages from now forward


def write_last_seen(ts: str) -> None:
    LAST_SEEN_PATH.write_text(ts)


def fetch_history(channel: str, oldest: str) -> list[dict]:
    """Call conversations.history for one channel; return messages newer than `oldest` ts.

    Sets a global backoff window when Slack returns 429 / ratelimited. Subsequent
    calls during the window short-circuit (return []) so we stop hammering the API.
    Backoff doubles up to BACKOFF_MAX, resets to BACKOFF_INITIAL on first success.
    """
    global _backoff_until, _backoff_current
    if not BOT_TOKEN:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(2)
    if time.time() < _backoff_until:
        return []
    url = f"https://slack.com/api/conversations.history?channel={channel}&oldest={oldest}&limit=50"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {BOT_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry_after = float(e.headers.get("Retry-After") or _backoff_current)
            _backoff_until = time.time() + retry_after
            _backoff_current = min(_backoff_current * 2, BACKOFF_MAX)
            print(f"history fetch 429 [{channel}]: backoff {retry_after}s (next={_backoff_current})", file=sys.stderr, flush=True)
            return []
        print(f"history fetch failed [{channel}]: {e}", file=sys.stderr, flush=True)
        return []
    except urllib.error.URLError as e:
        print(f"history fetch failed [{channel}]: {e}", file=sys.stderr, flush=True)
        return []
    if not data.get("ok"):
        if data.get("error") == "ratelimited":
            _backoff_until = time.time() + _backoff_current
            _backoff_current = min(_backoff_current * 2, BACKOFF_MAX)
            print(f"history fetch ratelimited [{channel}]: backoff {_backoff_current}s", file=sys.stderr, flush=True)
        else:
            print(f"slack rejected [{channel}]: {data}", file=sys.stderr, flush=True)
        return []
    # Reset backoff on first successful response
    _backoff_current = BACKOFF_INITIAL
    msgs = data.get("messages", [])
    # Tag each with the source channel so write_inbox can record provenance
    for m in msgs:
        m.setdefault("_channel_id", channel)
    return msgs


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
    # Poll every configured channel, accumulate messages, dedupe + sort by ts
    all_msgs: list[dict] = []
    for ch in CHANNELS:
        all_msgs.extend(fetch_history(ch, last_seen))
    if not all_msgs:
        return
    # Sort chronological (oldest first) so last_seen advances monotonically
    all_msgs.sort(key=lambda m: m.get("ts", ""))
    new_max = last_seen
    for m in all_msgs:
        ts = m.get("ts", "")
        if not ts or ts <= last_seen:
            continue
        if m.get("bot_id") == OWN_BOT_ID:
            new_max = ts
            continue
        text = m.get("text") or ""
        # Inbox if EITHER: human message (Dave + anyone non-bot) OR callsign-mentioning bot post
        if is_human_message(m) or matches_callsign(text):
            write_inbox(m)
        new_max = ts
    # Persist on every successful tick (even when no new bot/human msgs matched)
    # so a flood of own-bot posts advances the pointer and the file always exists.
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
    print(f"slack listener up — channels={CHANNELS} interval={POLL_SECONDS}s own_bot={OWN_BOT_ID}", flush=True)
    while True:
        try:
            tick()
        except Exception as e:
            print(f"tick error: {e}", file=sys.stderr, flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
