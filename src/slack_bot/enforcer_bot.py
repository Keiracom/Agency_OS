"""Slack enforcer bot — Socket Mode entrypoint (ENFORCER-BUILD-001).

Mirrors src/telegram_bot/enforcer_bot.py shape but reads from Slack via
slack_sdk.socket_mode.SocketModeClient instead of polling a filesystem inbox.
Same gpt-4o-mini rule check, same cooldown, same interjection write-to-bot-
inboxes for tmux visibility.

Per PR #672 ratified spec + 4 decision points (all YES):
  1. RULES_PROMPT etc. extracted to src/bot_common/enforcer_rules.py (DONE Phase A)
  2. R3 + R6 violations route to BOTH #execution AND #alerts
  3. Bot username 'Enforcer' + :rotating_light: icon
  4. Phase C smoke includes cross-device deliberate-violation test

Env (read from /home/elliotbot/.config/agency-os/.env):
  SLACK_ENFORCER_BOT_TOKEN  — xoxb-... bot token (chat:write + chat:write.customize)
  SLACK_ENFORCER_APP_TOKEN  — xapp-1-... Socket Mode app-level token (connections:write)
  OPENAI_API_KEY            — gpt-4o-mini
  SLACK_LISTEN_CHANNEL      — default #execution C0B3QB0K1GQ
  SLACK_ALERTS_CHANNEL      — default #alerts C0B2EJU53EK
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections import deque
from datetime import datetime, timezone

import httpx
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web import WebClient

from src.bot_common.enforcer_rules import (
    CHECK_MODEL,
    FLAG_COOLDOWN_SECONDS,
    HIGH_SEVERITY_RULES,
    MAX_WINDOW,
    RULES_PROMPT,
    should_check,
)
from src.slack_bot.enforcer_callsign_map import SHARED_BOT_ID, attribute

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("enforcer-slack")

BOT_TOKEN = os.environ.get("SLACK_ENFORCER_BOT_TOKEN") or os.environ.get("SLACK_BOT_TOKEN", "")
APP_TOKEN = os.environ.get("SLACK_ENFORCER_APP_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LISTEN_CHANNEL = os.environ.get("SLACK_LISTEN_CHANNEL", "C0B3QB0K1GQ")
ALERTS_CHANNEL = os.environ.get("SLACK_ALERTS_CHANNEL", "C0B2EJU53EK")
ENFORCER_USERNAME = "Enforcer"
ENFORCER_ICON = ":rotating_light:"

# In-process state (lost on restart; reconstitutes from next 20 messages)
message_window: deque = deque(maxlen=MAX_WINDOW)
last_flag_times: dict[str, float] = {}
governance_events: dict = {}

# Bot inboxes — same write pattern as TG enforcer; tmux watchers consume
BOT_INBOXES = (
    "/tmp/telegram-relay-elliot/inbox",
    "/tmp/telegram-relay-aiden/inbox",
    "/tmp/telegram-relay-max/inbox",
)


def check_with_llm(current_msg: str, recent_msgs: list[str]) -> dict | None:
    """Synchronous gpt-4o-mini call. Returns {violation, rule_number, ...} or None on failure."""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — rule check disabled")
        return None
    user_content = json.dumps(
        {
            "current_message": current_msg,
            "recent_messages": list(recent_msgs)[-MAX_WINDOW:],
            "governance_events": governance_events,
        },
        ensure_ascii=False,
    )
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": CHECK_MODEL,
                    "messages": [
                        {"role": "system", "content": RULES_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 300,
                },
            )
            resp.raise_for_status()
            return json.loads(resp.json()["choices"][0]["message"]["content"])
    except Exception as exc:
        logger.warning("LLM check failed: %s", exc)
        return None


def write_bot_inboxes(text: str) -> None:
    """Mirror enforcer interjection into each bot inbox (same JSON shape as TG)."""
    import uuid

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    for inbox in BOT_INBOXES:
        try:
            os.makedirs(inbox, exist_ok=True)
            fname = f"{ts}_{uuid.uuid4().hex[:8]}.json"
            payload = {
                "id": fname.replace(".json", ""),
                "type": "text",
                "text": f"[ENFORCER]: {text}",
                "sender": "enforcer",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "surface": "slack",
            }
            with open(os.path.join(inbox, fname), "w") as f:
                json.dump(payload, f)
        except Exception as exc:
            logger.warning("inbox write failed for %s: %s", inbox, exc)


def post_interjection(web: WebClient, text: str, rule_num: int) -> None:
    """Post enforcer interjection. R3+R6 → both #execution and #alerts; others → #alerts only."""
    targets = [ALERTS_CHANNEL]
    if rule_num in HIGH_SEVERITY_RULES:
        targets.append(LISTEN_CHANNEL)
    for ch in targets:
        try:
            web.chat_postMessage(channel=ch, text=text, username=ENFORCER_USERNAME, icon_emoji=ENFORCER_ICON)
        except Exception as exc:
            logger.warning("post to %s failed: %s", ch, exc)
    write_bot_inboxes(text)


def process_event(event: dict, web: WebClient) -> None:
    """Apply pre-filter + LLM rule check + interjection (with cooldown) to a single message."""
    if event.get("subtype") in ("message_changed", "message_deleted", "channel_join"):
        return
    if event.get("channel") != LISTEN_CHANNEL:
        return
    text = event.get("text") or ""
    if not text:
        return

    callsign = attribute(event)
    message_window.append(f"[{callsign.upper()}] {text}")

    # Skip own enforcer posts
    if callsign == "enforcer":
        return
    # Skip Dave (humans not subject to bot rules per RULES_PROMPT)
    if callsign == "dave":
        return
    if not should_check(text):
        return

    logger.info("CHECK msg from=%s text=%s", callsign, text[:80])
    result = check_with_llm(text, list(message_window))
    if not result or not result.get("violation"):
        return

    rule_num = result.get("rule_number")
    rule_name = result.get("rule_name", "unknown")
    detail = result.get("detail", "")
    should_have = result.get("should_have", "")

    flag_key = f"rule_{rule_num}"
    now = time.time()
    if flag_key in last_flag_times and (now - last_flag_times[flag_key]) < FLAG_COOLDOWN_SECONDS:
        logger.info("cooldown skip rule %s", rule_num)
        return
    last_flag_times[flag_key] = now

    interjection = f"Rule {rule_num} -- {rule_name}: {detail}. {should_have}."
    logger.info("VIOLATION: %s", interjection)
    post_interjection(web, interjection, rule_num if isinstance(rule_num, int) else 0)


def handle_request(client: SocketModeClient, req: SocketModeRequest) -> None:
    """Socket Mode dispatch — events_api carries channel messages."""
    client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))
    if req.type != "events_api":
        return
    event = req.payload.get("event") or {}
    if event.get("type") != "message":
        return
    try:
        process_event(event, client.web_client)
    except Exception as exc:
        logger.exception("process_event error: %s", exc)


def main() -> int:
    if not BOT_TOKEN:
        logger.error("SLACK_ENFORCER_BOT_TOKEN (or SLACK_BOT_TOKEN) not set")
        return 2
    if not APP_TOKEN:
        logger.error("SLACK_ENFORCER_APP_TOKEN not set (xapp-1- Socket Mode token)")
        return 2

    web = WebClient(token=BOT_TOKEN)
    sm = SocketModeClient(app_token=APP_TOKEN, web_client=web)
    sm.socket_mode_request_listeners.append(handle_request)

    logger.info("enforcer (slack) starting — listen=%s alerts=%s shared_bot_id=%s", LISTEN_CHANNEL, ALERTS_CHANNEL, SHARED_BOT_ID)
    sm.connect()
    # Block forever (sm.connect spins a background thread; main holds via sleep loop)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
