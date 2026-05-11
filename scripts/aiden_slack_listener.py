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

CHANNEL = os.environ.get("SLACK_LISTENER_CHANNEL", "C0B3QB0K1GQ")
POLL = float(os.environ.get("LISTENER_POLL_SECONDS", "20"))
TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
INBOX = Path("/tmp/telegram-relay-aiden/inbox")
STATE_FILE = Path("/tmp/aiden-slack-listener-state")
GROUP_CHAT_ID = -1003926592540  # preserved so relay_watcher's last_chat_id still works for any legacy tg reply paths

CALLSIGN_TRIGGERS = ("aiden", "all", "both", "team")
KEEP_TAGS = ("[ELLIOT]", "[MAX]", "[ENFORCER]", "[DAVE]")
SELF_TAG = "[AIDEN]"


def slack_get(method: str, params: dict) -> dict:
    url = f"https://slack.com/api/{method}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def load_cursor() -> str:
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip()
    cursor = f"{time.time():.6f}"
    STATE_FILE.write_text(cursor)
    return cursor


def save_cursor(ts: str) -> None:
    STATE_FILE.write_text(ts)


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


def poll_once(cursor: str) -> str:
    try:
        result = slack_get("conversations.history", {"channel": CHANNEL, "oldest": cursor, "inclusive": "false", "limit": "100"})
    except urllib.error.URLError as e:
        print(f"slack history fetch failed: {e}", file=sys.stderr, flush=True)
        return cursor
    if not result.get("ok"):
        print(f"slack rejected: {result}", file=sys.stderr, flush=True)
        return cursor
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
            print(f"inbox <- {msg.get('ts')} ({len(text)}ch)", flush=True)
        new_cursor = msg.get("ts", new_cursor)
    return new_cursor


def main() -> int:
    if not TOKEN:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        return 2
    cursor = load_cursor()
    print(f"aiden_slack_listener: channel={CHANNEL} poll={POLL}s cursor={cursor}", flush=True)
    while True:
        cursor = poll_once(cursor)
        save_cursor(cursor)
        time.sleep(POLL)


if __name__ == "__main__":
    sys.exit(main())
