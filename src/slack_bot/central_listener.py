"""central_listener.py — single Socket Mode subscriber: fanout + enforcer check.

Fixes Phase 2 architecture flaw: multiple Socket Mode connections sharing the
same app-level token cause Slack to round-robin events. Per-connection drops
lead to silent event loss (Dave's #ceo posts lost when assigned to enforcer
connection that filtered them).

This module owns the ONLY Socket Mode connection for the shared agency_os
bot. It does BOTH jobs the old split architecture did:
  1. FANOUT: writes per-callsign JSON to each agent's inbox dir based on
     channel→callsign routing matrix.
  2. ENFORCER: runs the gpt-4o-mini rule check on #execution events and
     posts interjections to bot inboxes (same write_bot_inboxes pattern as
     the old enforcer_bot.py).

Enforcer service (agency-os-enforcer-slack-bot) is decommissioned in the
same change — its functionality folded in here.

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
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

import httpx
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web import WebClient

from src.bot_common.enforcer_deterministic import check_r2, check_r3, check_r4, check_r6, check_r8
from src.bot_common.enforcer_rules import (
    CHECK_MODEL,
    FLAG_COOLDOWN_SECONDS,
    HIGH_SEVERITY_RULES,
    MAX_WINDOW,
    RULES_PROMPT,
    should_check,
)
from src.slack_bot.enforcer_callsign_map import attribute

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("slack-central-listener")

BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
APP_TOKEN = os.environ.get("SLACK_ENFORCER_APP_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ENFORCER_DETERMINISTIC = os.environ.get("ENFORCER_DETERMINISTIC", "1") == "1"
LISTEN_CHANNEL = os.environ.get("SLACK_LISTEN_CHANNEL", "C0B3QB0K1GQ")  # enforcer scope
ALERTS_CHANNEL = os.environ.get("SLACK_ALERTS_CHANNEL", "C0B2EJU53EK")
ENFORCER_USERNAME = "Enforcer"
ENFORCER_ICON = ":rotating_light:"

# Enforcer in-process state (lost on restart; reconstitutes from next 20 messages)
message_window: deque = deque(maxlen=MAX_WINDOW)
last_flag_times: dict[str, float] = {}
governance_events: dict = {}

CHANNEL_ROUTES: dict[str, list[str]] = {
    "C0B2PM3TV0B": ["elliot"],  # #ceo
    "C0B3QB0K1GQ": ["elliot", "aiden", "max"],  # #execution
    "C0B2EJU53EK": ["aiden"],  # #alerts
    "C0B2U15PSEA": ["aiden"],  # #completed_directives
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
    payload = json.dumps(
        {
            "type": "text",
            "chat_id": GROUP_CHAT_ID,
            "text": text,
            "sender": sender,
        }
    )
    fname = f"slack_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
    for inbox in CALLSIGN_TO_INBOX.get(callsign, []):
        inbox.mkdir(parents=True, exist_ok=True)
        (inbox / fname).write_text(payload)


def check_with_llm(current_msg: str, recent_msgs: list[str], channel_id: str = "") -> dict | None:
    """gpt-4o-mini call. Returns {violation, rule_number, ...} or None on failure."""
    if not OPENAI_API_KEY:
        return None
    user_content = json.dumps(
        {
            "current_message": current_msg,
            "current_channel_id": channel_id,
            "recent_messages": list(recent_msgs)[-MAX_WINDOW:],
            "governance_events": governance_events,
        },
        ensure_ascii=False,
    )
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
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


def post_interjection(web: WebClient, text: str, rule_num: int) -> None:
    """R3+R6 → both #execution and #alerts; others → #alerts only. Also write_bot_inboxes."""
    targets = [ALERTS_CHANNEL]
    if rule_num in HIGH_SEVERITY_RULES:
        targets.append(LISTEN_CHANNEL)
    for ch in targets:
        try:
            web.chat_postMessage(
                channel=ch, text=text, username=ENFORCER_USERNAME, icon_emoji=ENFORCER_ICON
            )
        except Exception as exc:
            logger.warning("interjection post to %s failed: %s", ch, exc)
    # Mirror into each bot inbox (tmux delivery) — same shape as old enforcer
    ts_now = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    for inbox_list in CALLSIGN_TO_INBOX.values():
        for inbox in inbox_list:
            try:
                inbox.mkdir(parents=True, exist_ok=True)
                fname = f"{ts_now}_{uuid.uuid4().hex[:8]}.json"
                payload = {
                    "id": fname.replace(".json", ""),
                    "type": "text",
                    "text": f"[ENFORCER]: {text}",
                    "sender": "enforcer",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "surface": "slack",
                }
                (inbox / fname).write_text(json.dumps(payload))
            except Exception as exc:
                logger.warning("enforcer inbox write failed %s: %s", inbox, exc)


def _fire_violation(result: dict, web: WebClient) -> None:
    """Post an enforcer interjection if not in cooldown."""
    rule_num = result.get("rule_number")
    flag_key = f"rule_{rule_num}"
    now = time.time()
    if flag_key in last_flag_times and (now - last_flag_times[flag_key]) < FLAG_COOLDOWN_SECONDS:
        return
    last_flag_times[flag_key] = now
    rule_name = result.get("rule_name", "unknown")
    detail = result.get("detail", "")
    should_have = result.get("should_have", "")
    interjection = f"Rule {rule_num} -- {rule_name}: {detail}. {should_have}."
    logger.info("VIOLATION: %s", interjection)
    post_interjection(web, interjection, rule_num if isinstance(rule_num, int) else 0)


def run_enforcer(event: dict, text: str, web: WebClient) -> None:
    """Deterministic-first enforcer pipeline.

    1. Deterministic loop: R4, R2, R8 — violation fires immediately.
    2. Hybrid: R3, R6 — evidence regex pre-filter; STRICT resolved, SOFT falls through.
    3. LLM fallback: R3 SOFT "done" + R9 (semantic).
    Set ENFORCER_DETERMINISTIC=0 to revert to LLM-only path.
    """
    if event.get("channel") != LISTEN_CHANNEL:
        return
    callsign = attribute(event)
    message_window.append(f"[{callsign.upper()}] {text}")
    if callsign == "enforcer":
        return
    if callsign == "dave":
        return
    if not should_check(text):
        return
    logger.info("ENFORCER CHECK from=%s text=%s", callsign, text[:80])

    if ENFORCER_DETERMINISTIC:
        recent = list(message_window)
        for check_fn, check_args in (
            (check_r4, (text,)),
            (check_r2, (text, recent)),
            (check_r8, (text, recent)),
        ):
            result = check_fn(*check_args)
            if result:
                _fire_violation(result, web)
                return

        r3_result, r3_skip = check_r3(text)
        if r3_result:
            _fire_violation(r3_result, web)
            return

        r6_result, r6_skip = check_r6(text)
        if r6_result:
            _fire_violation(r6_result, web)
            return

    result = check_with_llm(text, list(message_window), channel_id=event.get("channel", ""))
    if not result or not result.get("violation"):
        return
    _fire_violation(result, web)


def process_event(event: dict, web: WebClient | None = None) -> None:
    if event.get("type") != "message":
        return
    if event.get("subtype") in ("message_changed", "message_deleted", "channel_join"):
        return
    channel = event.get("channel", "")
    routes = CHANNEL_ROUTES.get(channel)
    text = event.get("text") or ""
    if not text:
        return
    # FANOUT
    if routes:
        sender = sender_from(event)
        for callsign in routes:
            self_tag = SELF_TAG_BY_CALLSIGN.get(callsign, "")
            if self_tag and text.startswith(self_tag):
                continue
            write_inbox(callsign, text, sender)
        logger.info(
            "fanout %s ts=%s -> %s (%dch)", channel, event.get("ts", "?"), routes, len(text)
        )
    # ENFORCER (only on #execution)
    if web is not None:
        try:
            run_enforcer(event, text, web)
        except Exception as exc:
            logger.exception("enforcer error: %s", exc)


def handle_request(client: SocketModeClient, req: SocketModeRequest) -> None:
    client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))
    if req.type != "events_api":
        return
    event = req.payload.get("event") or {}
    try:
        process_event(event, client.web_client)
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
