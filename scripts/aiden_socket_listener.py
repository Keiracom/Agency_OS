#!/usr/bin/env python3
"""aiden_socket_listener.py — Slack Socket Mode replacement for the polling listener.

WebSocket push subscription to message.channels + message.groups. Replaces
scripts/aiden_slack_listener.py (poll conversations.history every 8s).

Same filter logic + same inbox-write path:
  - Drop messages whose text starts with `[AIDEN]` (self-loop guard; shared bot_id)
  - Keep messages containing callsign tokens: aiden/all/both/team
  - Keep messages tagged `[ELLIOT]` / `[MAX]` / `[ENFORCER]` / `[DAVE]`
  - Keep non-bot messages (Dave/human posts)
  - Channel allowlist: #execution + #alerts + #completed_directives

Latency: ~50-500ms (WebSocket push) vs 0.5-8s (poll). Zero polling pressure
on conversations.history Tier 3 rate limits.

Env (read from /home/elliotbot/.config/agency-os/.env):
  SLACK_BOT_TOKEN              xoxb-... (chat:write / channels:history scopes — same shared bot)
  SLACK_ENFORCER_APP_TOKEN     xapp-1-... (reuse — same Slack app supports multiple sockets)
  SLACK_LISTENER_CHANNELS      comma-separated allowlist (default = execution/alerts/completed_directives)

Revert: systemctl --user stop aiden-slack-listener.service (after pointing the
unit back at aiden_slack_listener.py).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path

from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web import WebClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("aiden-socket-listener")

BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
APP_TOKEN = os.environ.get("SLACK_ENFORCER_APP_TOKEN", "")
CHANNELS = {c.strip() for c in os.environ.get(
    "SLACK_LISTENER_CHANNELS", "C0B3QB0K1GQ,C0B2EJU53EK,C0B2U15PSEA"
).split(",") if c.strip()}
INBOX = Path("/tmp/telegram-relay-aiden/inbox")
GROUP_CHAT_ID = -1003926592540

CALLSIGN_TRIGGERS = ("aiden", "all", "both", "team")
KEEP_TAGS = ("[ELLIOT]", "[MAX]", "[ENFORCER]", "[DAVE]")
SELF_TAG = "[AIDEN]"


def should_keep(text: str, has_bot_id: bool) -> bool:
    if text.startswith(SELF_TAG):
        return False
    low = text.lower()
    if any(t in low for t in CALLSIGN_TRIGGERS):
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
    payload = {"type": "text", "chat_id": GROUP_CHAT_ID, "text": text, "sender": sender}
    fname = f"slack_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
    (INBOX / fname).write_text(json.dumps(payload))


def process_event(event: dict) -> None:
    if event.get("type") != "message":
        return
    if event.get("subtype") in ("message_changed", "message_deleted", "channel_join"):
        return
    channel = event.get("channel", "")
    if channel not in CHANNELS:
        return
    text = event.get("text", "")
    if not text:
        return
    has_bot = bool(event.get("bot_id"))
    if not should_keep(text, has_bot):
        return
    write_inbox(text, sender_from(event))
    logger.info("inbox <- %s %s (%dch)", channel, event.get("ts", "?"), len(text))


def handle_request(client: SocketModeClient, req: SocketModeRequest) -> None:
    client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))
    if req.type != "events_api":
        return
    event = req.payload.get("event") or {}
    try:
        process_event(event)
    except Exception as exc:
        logger.exception("process_event error: %s", exc)


def main() -> int:
    if not BOT_TOKEN:
        logger.error("SLACK_BOT_TOKEN not set")
        return 2
    if not APP_TOKEN:
        logger.error("SLACK_ENFORCER_APP_TOKEN not set (xapp-1- Socket Mode token)")
        return 2
    web = WebClient(token=BOT_TOKEN)
    sm = SocketModeClient(app_token=APP_TOKEN, web_client=web)
    sm.socket_mode_request_listeners.append(handle_request)
    logger.info("aiden-socket-listener starting — channels=%s", sorted(CHANNELS))
    sm.connect()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
