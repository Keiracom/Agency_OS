#!/usr/bin/env python3
"""aiden_slack_listener.py — Slack inbound bridge for AIDEN callsign.

Polls Slack `#execution` `conversations.history` every 20s, filters messages
the AIDEN agent should see, writes them to /tmp/telegram-relay-aiden/inbox/
in the JSON shape relay_watcher.sh expects so tmux injection still works.

Filter logic (per AIDEN-SLACK-MIGRATION-001 step 3.5 directive):
    - Skip messages whose text starts with `[AIDEN]` (self-loop guard;
      shared bot_id means we can't distinguish self vs Elliot via bot_id)
    - Keep messages matching callsign tokens: aiden, all, both, team
      (case-insensitive, substring)
    - Keep messages from non-bot users (Dave/Max-as-human posts)
    - Keep messages tagged `[ELLIOT]`, `[MAX]`, `[ENFORCER]`, `[DAVE]`

State cursor in /tmp/aiden-slack-listener-state (epoch float of last seen ts).
On first run, starts from "now" — does not replay history.

Env:
    SLACK_BOT_TOKEN          (required)
    SLACK_LISTENER_CHANNEL   (optional, default #execution = C0B3QB0K1GQ)
    LISTENER_POLL_SECONDS    (optional, default 20)

Required OAuth scopes (per Elliot's PR #675 finding 2026-05-11):
    channels:history (public) OR groups:history (private). Without them,
    conversations.history returns missing_scope error.

Revert: systemctl --user stop aiden-slack-listener.service.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CHANNELS = [c.strip() for c in os.environ.get("SLACK_LISTENER_CHANNELS", "C0B3QB0K1GQ").split(",") if c.strip()]
POLL = float(os.environ.get("LISTENER_POLL_SECONDS", "8"))
TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
INBOX = Path("/tmp/telegram-relay-aiden/inbox")
STATE_DIR = Path("/tmp/aiden-slack-listener-state.d")
GROUP_CHAT_ID = -1003926592540  # preserved so relay_watcher's last_chat_id still works for any legacy tg reply paths

CALLSIGN_TRIGGERS = ("aiden", "all", "both", "team")
KEEP_TAGS = ("[ELLIOT]", "[MAX]", "[ENFORCER]", "[DAVE]")
SELF_TAG = "[AIDEN]"

BACKOFF_INITIAL = 30.0
BACKOFF_MAX = 120.0
_backoff_until: float = 0.0
_backoff_current: float = BACKOFF_INITIAL


def slack_get(method: str, params: dict) -> dict:
    url = f"https://slack.com/api/{method}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _state_path(channel: str) -> Path:
    return STATE_DIR / f"{channel}.cursor"


def load_cursor(channel: str) -> str:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    p = _state_path(channel)
    if p.exists():
        return p.read_text().strip()
    cursor = f"{time.time():.6f}"
    p.write_text(cursor)
    return cursor


def save_cursor(channel: str, ts: str) -> None:
    _state_path(channel).write_text(ts)


def should_keep(text: str, has_bot_id: bool) -> bool:
    if text.startswith(SELF_TAG):
        return False
    low = text.lower()
    if any(t.lower() in low for t in CALLSIGN_TRIGGERS):
        return True
    if any(tag in text for tag in KEEP_TAGS):
        return True
    return not has_bot_id


def sender_from(msg: dict) -> str:
    text = msg.get("text", "")
    for tag in KEEP_TAGS:
        if tag in text:
            return tag.strip("[]").lower() + "bot"
    if msg.get("bot_id"):
        return "slackbot"
    return msg.get("user", "human") or "human"


def write_inbox(text: str, sender: str) -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": "text",
        "chat_id": GROUP_CHAT_ID,
        "text": text,
        "sender": sender,
    }
    fname = f"slack_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
    (INBOX / fname).write_text(json.dumps(payload))


def poll_once(channel: str, cursor: str) -> str:
    global _backoff_until, _backoff_current
    if time.time() < _backoff_until:
        return cursor
    try:
        result = slack_get("conversations.history", {"channel": channel, "oldest": cursor, "inclusive": "false", "limit": "100"})
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry_after = float(e.headers.get("Retry-After") or _backoff_current)
            _backoff_until = time.time() + retry_after
            _backoff_current = min(_backoff_current * 2, BACKOFF_MAX)
            print(f"history fetch 429 ({channel}): backoff {retry_after}s (next={_backoff_current})", file=sys.stderr, flush=True)
            return cursor
        print(f"slack history fetch failed ({channel}): {e}", file=sys.stderr, flush=True)
        return cursor
    except urllib.error.URLError as e:
        print(f"slack history fetch failed ({channel}): {e}", file=sys.stderr, flush=True)
        return cursor
    if not result.get("ok"):
        if result.get("error") == "ratelimited":
            _backoff_until = time.time() + _backoff_current
            _backoff_current = min(_backoff_current * 2, BACKOFF_MAX)
            print(f"history fetch ratelimited ({channel}): backoff {_backoff_current}s", file=sys.stderr, flush=True)
        else:
            print(f"slack rejected ({channel}): {result}", file=sys.stderr, flush=True)
        return cursor
    _backoff_current = BACKOFF_INITIAL
    messages = result.get("messages", [])
    if not messages:
        return cursor
    messages.sort(key=lambda m: float(m.get("ts", "0")))
    new_cursor = cursor
    for msg in messages:
        text = msg.get("text", "")
        if not text:
            continue
        has_bot = bool(msg.get("bot_id"))
        if should_keep(text, has_bot):
            write_inbox(text, sender_from(msg))
            print(f"inbox <- {channel} {msg.get('ts')} ({len(text)}ch)", flush=True)
        new_cursor = msg.get("ts", new_cursor)
    return new_cursor


def main() -> int:
    if not TOKEN:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        return 2
    cursors = {ch: load_cursor(ch) for ch in CHANNELS}
    print(f"aiden_slack_listener: channels={CHANNELS} poll={POLL}s", flush=True)
    while True:
        for ch in CHANNELS:
            cursors[ch] = poll_once(ch, cursors[ch])
            save_cursor(ch, cursors[ch])
        time.sleep(POLL)


if __name__ == "__main__":
    sys.exit(main())
