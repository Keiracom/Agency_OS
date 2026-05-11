"""central_listener.py — single Socket Mode subscriber that fans events out.

Fixes Phase 2 architecture flaw: multiple per-agent Socket Mode connections
sharing the same app-level token cause Slack to round-robin events across
connections. Per-listener channel allowlists then DROP events outside the
allowlist, leading to silent loss for channels only one listener subscribed
to (e.g. #ceo for Elliot).

This module owns the SINGLE Socket Mode connection for the shared agency_os
bot. It receives every event the bot is entitled to, then writes per-callsign
JSON to each agent's inbox dir based on a channel→callsign routing matrix.

ROUTING MATRIX (per Dave 2026-05-11 + role-swap):
  C0B2PM3TV0B (#ceo)                  → ['elliot']
  C0B3QB0K1GQ (#execution)            → ['elliot', 'aiden', 'max']
  C0B2EJU53EK (#alerts)               → ['aiden']
  C0B2U15PSEA (#completed_directives) → ['aiden']

Per-callsign filter is applied AFTER routing:
  - Skip if text starts with that callsign's SELF_TAG (loop guard).
  - Otherwise inbox unconditionally (relay-watcher delivers to tmux).

Env (read from /home/elliotbot/.config/agency-os/.env):
  SLACK_BOT_TOKEN              xoxb-... shared bot (chat:write / channels:history)
  SLACK_ENFORCER_APP_TOKEN     xapp-1-... Socket Mode token (reused — no second app needed)

Service entry point: python3 -m src.slack_bot.central_listener
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
logger = logging.getLogger("slack-central-listener")

BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
APP_TOKEN = os.environ.get("SLACK_ENFORCER_APP_TOKEN", "")

CHANNEL_ROUTES: dict[str, list[str]] = {
    "C0B2PM3TV0B": ["elliot"],                       # #ceo
    "C0B3QB0K1GQ": ["elliot", "aiden", "max"],       # #execution
    "C0B2EJU53EK": ["aiden"],                         # #alerts
    "C0B2U15PSEA": ["aiden"],                         # #completed_directives
}

CALLSIGN_TO_INBOX: dict[str, list[Path]] = {
    "elliot": [Path("/tmp/telegram-relay-elliot/inbox")],
    "aiden": [Path("/tmp/telegram-relay-aiden/inbox")],
    "max": [Path("/tmp/telegram-relay-max/inbox"), Path("/tmp/coo-inbox")],
}

SELF_TAG_BY_CALLSIGN = {
    "elliot": "[ELLIOT]",
    "aiden": "[AIDEN]",
    "max": "[MAX]",
}

KEEP_TAGS = ("[ELLIOT]", "[AIDEN]", "[MAX]", "[ENFORCER]", "[DAVE]")
GROUP_CHAT_ID = -1003926592540


def sender_from(msg: dict) -> str:
    text = msg.get("text") or ""
    for tag in KEEP_TAGS:
        if tag in text:
            return tag.strip("[]").lower() + "bot"
    if msg.get("bot_id"):
        return "slackbot"
    return msg.get("user") or "human"


def write_inbox(callsign: str, text: str, sender: str) -> None:
    payload = json.dumps({
        "type": "text",
        "chat_id": GROUP_CHAT_ID,
        "text": text,
        "sender": sender,
    })
    fname = f"slack_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
    for inbox in CALLSIGN_TO_INBOX.get(callsign, []):
        inbox.mkdir(parents=True, exist_ok=True)
        (inbox / fname).write_text(payload)


def process_event(event: dict) -> None:
    if event.get("type") != "message":
        return
    if event.get("subtype") in ("message_changed", "message_deleted", "channel_join"):
        return
    channel = event.get("channel", "")
    routes = CHANNEL_ROUTES.get(channel)
    if not routes:
        return
    text = event.get("text") or ""
    if not text:
        return
    sender = sender_from(event)
    for callsign in routes:
        self_tag = SELF_TAG_BY_CALLSIGN.get(callsign, "")
        if self_tag and text.startswith(self_tag):
            continue
        write_inbox(callsign, text, sender)
    logger.info("fanout %s ts=%s -> %s (%dch)", channel, event.get("ts", "?"), routes, len(text))


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
        logger.error("SLACK_ENFORCER_APP_TOKEN not set")
        return 2
    web = WebClient(token=BOT_TOKEN)
    sm = SocketModeClient(app_token=APP_TOKEN, web_client=web)
    sm.socket_mode_request_listeners.append(handle_request)
    logger.info("central-listener starting — routes=%s", CHANNEL_ROUTES)
    sm.connect()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
