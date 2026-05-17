"""central_listener.py — single Socket Mode subscriber: fanout only.

Fixes Phase 2 architecture flaw: multiple Socket Mode connections sharing the
same app-level token cause Slack to round-robin events. Per-connection drops
lead to silent event loss (Dave's #ceo posts lost when assigned to enforcer
connection that filtered them).

This module owns the ONLY Socket Mode connection for the shared agency_os
bot. It handles:
  1. FANOUT: writes per-callsign JSON to each agent's inbox dir based on
     channel→callsign routing matrix.
  2. AUTO-KEI: [CEO]-prefixed messages in #ceo trigger Linear issue creation
     (gated by AUTO_KEI_FROM_CEO=1).

ENFORCER removed: Dave 2026-05-17 KEI-151. Mechanical gates (phase-lock,
SKIP LOCKED, verification trigger, CI gate, Gate 2 evidence, Gate 4
heartbeat) now handle governance. Advisory LLM/deterministic enforcer was
dead code.

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
import re
import sys
import time
import uuid
from pathlib import Path

import httpx
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web import WebClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("slack-central-listener")

BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
APP_TOKEN = os.environ.get("SLACK_ENFORCER_APP_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Auto-KEI: #ceo channel id — messages starting with [CEO] trigger task creation.
CEO_CHANNEL = "C0B2PM3TV0B"
CEO_PREFIX = "[CEO]"

CHANNEL_ROUTES: dict[str, list[str]] = {
    "C0B2PM3TV0B": ["elliot"],  # #ceo
    # Per Dave 2026-05-12 (Option B): clones added to #execution routing with
    # tag-filtered fan-out via _is_clone_addressed(). Catches @atlas /
    # @orion / @scout / [ATLAS] / [ORION] / [SCOUT] references so explicit
    # dispatches reach clones; ambient team chatter does not.
    "C0B3QB0K1GQ": ["elliot", "aiden", "max", "atlas", "orion", "scout"],
    "C0B2EJU53EK": ["aiden"],  # #alerts
    "C0B2U15PSEA": ["aiden"],  # #completed_directives
}

# NOSONAR: /tmp/telegram-relay-<callsign>/inbox paths are the production contract
# with the per-callsign inbox-watcher systemd units (e.g. atlas-inbox-watcher.service).
# The listener writes INTO these dirs; the watcher services create them with
# restrictive modes. Migration to $XDG_STATE_HOME is a Phase 2 candidate per the
# 2026-05-12 memory audit (Pattern A — unclosed migrations). Don't migrate here
# without also updating watcher unit files in lockstep.
CALLSIGN_TO_INBOX: dict[str, list[Path]] = {
    "elliot": [Path("/tmp/telegram-relay-elliot/inbox")],  # NOSONAR S5443
    "aiden": [Path("/tmp/telegram-relay-aiden/inbox")],  # NOSONAR S5443
    "max": [Path("/tmp/telegram-relay-max/inbox"), Path("/tmp/coo-inbox")],  # NOSONAR S5443
    "atlas": [Path("/tmp/telegram-relay-atlas/inbox")],  # NOSONAR S5443
    "orion": [Path("/tmp/telegram-relay-orion/inbox")],  # NOSONAR S5443
    "scout": [Path("/tmp/telegram-relay-scout/inbox")],  # NOSONAR S5443
}

SELF_TAG_BY_CALLSIGN = {
    "elliot": "[ELLIOT]",
    "aiden": "[AIDEN]",
    "max": "[MAX]",
    "atlas": "[ATLAS]",
    "orion": "[ORION]",
    "scout": "[SCOUT]",
}

# Clones receive #execution messages only when explicitly addressed. Tag-filter
# keeps ambient team chatter out of clone inboxes (otherwise every message
# would spam every clone). Matches: @atlas / [ATLAS] / "Atlas — " / "Atlas:" /
# "Atlas," / case-insensitive on the bare word too if at sentence start.
CLONE_CALLSIGNS = frozenset({"atlas", "orion", "scout"})
_CLONE_ADDRESS_PATTERNS = {
    cs: re.compile(
        rf"@{cs}\b|\[{cs}\]|\b{cs}\s+(?:—|:|,|—)|^{cs}\b",
        re.IGNORECASE | re.MULTILINE,
    )
    for cs in CLONE_CALLSIGNS
}

KEEP_TAGS = (
    "[ELLIOT]",
    "[AIDEN]",
    "[MAX]",
    "[ATLAS]",
    "[ORION]",
    "[SCOUT]",
    "[ENFORCER]",
    "[DAVE]",
)
GROUP_CHAT_ID = -1003926592540


def sender_from(msg: dict) -> str:
    text = msg.get("text") or ""
    for tag in KEEP_TAGS:
        if tag in text:
            return tag.strip("[]").lower() + "bot"
    if msg.get("bot_id"):
        return "slackbot"
    return msg.get("user") or "human"


def _is_clone_addressed(callsign: str, text: str) -> bool:
    """Return True if a #execution message specifically addresses this clone.

    Tag-filter for clone fan-out (Option B per Dave 2026-05-12). Catches:
      - @atlas / @orion / @scout (Slack-style mention without lookup)
      - [ATLAS] / [ORION] / [SCOUT] (callsign tag prefix or inline)
      - "Atlas — ..." / "Atlas: ..." / "Atlas, ..." (direct address forms)
      - "atlas " at the start of a line (case-insensitive)

    Returns False for any message that does not specifically reference the
    clone — keeps ambient team chatter out of clone inboxes.
    """
    pattern = _CLONE_ADDRESS_PATTERNS.get(callsign)
    if pattern is None:
        return False
    return bool(pattern.search(text))


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


def _fanout_to_routes(routes: list[str], text: str, sender: str) -> None:
    """Fan out a #execution-channel message to each callsign's inbox.

    Skips self-tagged messages (e.g. [ELLIOT] prefix → elliot's inbox).
    Skips ambient messages for clones (atlas/orion/scout) unless explicitly
    addressed via _is_clone_addressed(). Primes always receive.
    """
    for callsign in routes:
        self_tag = SELF_TAG_BY_CALLSIGN.get(callsign, "")
        if self_tag and text.startswith(self_tag):
            continue
        if callsign in CLONE_CALLSIGNS and not _is_clone_addressed(callsign, text):
            continue
        write_inbox(callsign, text, sender)


def _extract_ceo_title(text: str) -> str | None:
    """Strip [CEO] prefix and return the first non-empty line (max 200 chars).

    Returns None if the body is empty after stripping — e.g. bare '[CEO]' post.
    """
    body = text
    if body.upper().startswith(CEO_PREFIX.upper()):
        body = body[len(CEO_PREFIX) :]
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return None


_LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"


def _create_kei_via_linear(title: str) -> str | None:
    """Create a new KEI issue in Linear and return the assigned identifier (e.g. "KEI-85").

    Phase 1 of the two-phase create (Max Note 2):
      (a) POST issueCreate with title — Linear assigns the identifier.
      (b) Optionally update title to "{identifier}: {title}" if convention requires prefix.
          The Part-3 webhook title-guard expects plain titles (no KEI-prefix) on fresh creates,
          so we skip the prefix-update: the title stays unprefixed here.

    Eventual-consistency note (Max review note 1): this function returns as soon
    as Linear's issueCreate succeeds. The corresponding public.tasks row lands
    asynchronously via the Linear webhook (~1-3s typical). Auto-KEI has no
    immediate consumer of the Supabase row (the confirmation post uses the
    returned Linear identifier directly), so this is acceptable. Any caller
    that needs to read the Supabase row should poll with a short timeout.

    The Linear webhook (src/api/webhooks/linear.py) handles the Supabase upsert
    when it receives the Issue.create event from Linear — we do NOT insert directly.

    Returns None on any failure so the caller can log-and-skip gracefully.
    """
    # Import locally to avoid top-of-module import cycles (webhook imports
    # FastAPI which we don't want loaded at listener startup if not needed).
    from src.api.webhooks.linear import LINEAR_TEAM_ID_DEFAULT

    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        logger.warning("auto-KEI: LINEAR_API_KEY not set — cannot create Linear issue")
        return None
    team_id = os.environ.get("LINEAR_TEAM_ID", LINEAR_TEAM_ID_DEFAULT)
    mutation = (
        "mutation($input:IssueCreateInput!){"
        "issueCreate(input:$input){success issue{id identifier url}}}"
    )
    body = json.dumps(
        {"query": mutation, "variables": {"input": {"teamId": team_id, "title": title}}}
    ).encode()
    req = httpx.Request(
        "POST",
        _LINEAR_GRAPHQL_URL,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        content=body,
    )
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.send(req)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        logger.warning("auto-KEI: Linear GraphQL request failed: %s", exc)
        return None
    issue = (((payload or {}).get("data") or {}).get("issueCreate") or {}).get("issue")
    if not issue:
        errors = (payload or {}).get("errors")
        logger.warning("auto-KEI: issueCreate returned no issue; errors=%s", errors)
        return None
    identifier: str = issue.get("identifier", "")
    if not identifier:
        logger.warning("auto-KEI: issueCreate returned issue with no identifier: %s", issue)
        return None
    logger.info("auto-KEI: Linear issue %s created — %s", identifier, title)
    return identifier


def _maybe_auto_create_kei(event: dict, web: WebClient | None) -> None:
    """Auto-KEI intercept for [CEO]-prefixed messages in #ceo channel.

    Fires BEFORE the normal fanout so it runs regardless of fanout outcome.
    Best-effort: any failure is logged but never blocks the fanout relay.
    """
    if os.environ.get("AUTO_KEI_FROM_CEO", "0") != "1":
        return
    channel = event.get("channel", "")
    text = (event.get("text") or "").strip()
    if channel != CEO_CHANNEL:
        return
    if not text.upper().startswith(CEO_PREFIX.upper()):
        return
    title = _extract_ceo_title(text)
    if not title:
        logger.info("auto-KEI: [CEO] post has empty body after strip — skip")
        return
    kei_id = _create_kei_via_linear(title)
    if kei_id is None:
        return
    if web is not None:
        try:
            web.chat_postMessage(
                channel=CEO_CHANNEL,
                text=f"[System] {kei_id} created — {title}",
            )
        except Exception as exc:
            logger.warning("auto-KEI: confirmation post failed: %s", exc)


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
    # Auto-KEI intercept: fires BEFORE fanout; best-effort; does not block relay.
    try:
        _maybe_auto_create_kei(event, web)
    except Exception as exc:
        logger.exception("auto-KEI error (non-blocking): %s", exc)

    if routes:
        _fanout_to_routes(routes, text, sender_from(event))
        logger.info(
            "fanout %s ts=%s -> %s (%dch)", channel, event.get("ts", "?"), routes, len(text)
        )


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
