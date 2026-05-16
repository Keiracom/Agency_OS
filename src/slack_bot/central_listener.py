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
import re
import sys
import time
import uuid
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psycopg
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web import WebClient

from src.bot_common.enforcer_deterministic import (
    _R3_EVIDENCE_RE,
    check_r2,
    check_r3,
    check_r4,
    check_r6,
    check_r8,
)
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
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Auto-KEI: #ceo channel id — messages starting with [CEO] trigger task creation.
CEO_CHANNEL = "C0B2PM3TV0B"
CEO_PREFIX = "[CEO]"
ENFORCER_USERNAME = "Enforcer"
ENFORCER_ICON = ":rotating_light:"

# Enforcer in-process state (lost on restart; reconstitutes from next MAX_WINDOW messages)
message_window: deque = deque(maxlen=MAX_WINDOW)

# R9 (DIRECTIVE-INITIATIVE) post-LLM exempt patterns. FP-tuning 2026-05-11:
# LLM mis-fires R9 on dispatches that already name concrete next-action subjects
# ([PROPOSE:], [READY:], [BUSY:], [CONCUR-REQUEST], [FP-LOG:], [DISPATCH],
# "I'll/will <verb>", "@<name> ships/drops/owns <X>"). Suppress R9 fires
# when any of these structured protocol tags are present.
_R9_EXEMPT_RE = re.compile(
    r"\[(?:propose|ready|busy|concur-request|concur|fp-log|valid-fire|dispatch)[\w:-]*\]"
    r"|\b(?:i'?ll|i will|aiden will|elliot will|max will|orion will|atlas will|scout will)\b"
    r"|@\w+\s+(?:ships?|drops?|owns?|takes?|opens?|merges?|files?|pushes?)\b"
    r"|@\w+\s+—\s+(?:roll-?up|audit|review|own|next)"
    # Track 5+7: status terminators that LLM mis-classifies as agenda-setting.
    r"|\b(?:standing\s+(?:ready|by|down|firm)|standing\.?$)"
    r"|\bcontinuing\s+standby\b"
    r"|\bwakeup\s+(?:at\s+)?\d{2}:\d{2}\b"
    r"|\bholding\s+(?:posture|position)\b"
    r"|\bawaiting\s+(?:concur|your\s+(?:concur|pr))\b",
    re.IGNORECASE | re.MULTILINE,
)

# Track 5 (2026-05-11): universal protocol-tag exempt. Per Max's architectural
# insight after [FP-LOG:R8] fired on his OWN R8 FP-analysis tally post — the
# message contained 'COO clone dispatch' inside [FP-LOG:R8] context, which
# triggered R8's dispatch regex. Per-rule protocol-tag exempts don't cover R4
# or R8. Solution: universal exempt at top of run_enforcer that skips ALL
# deterministic + LLM checks when message is a governance protocol artifact
# (status post, FP tally, concur ack, propose, etc.).
_UNIVERSAL_PROTOCOL_TAG_RE = re.compile(
    r"\[(?:propose|summary-draft|concur-request|concur|ready|busy|fp-log|valid-fire|dispatch|dispatch-proposal|dispatch-complete|state|complete)[\w:-]*\]",
    re.IGNORECASE,
)

# R3 (COMPLETION-REQUIRES-VERIFICATION) post-LLM exempt — Track 4 (FP-tuning
# 2026-05-11). Suppresses LLM-hallucinated R3 fires on messages with substantial
# evidence. Pre-LLM `_R3_EVIDENCE_RE` (imported from enforcer_deterministic)
# already covers commit hashes, JSON state, MERGEABLE/MERGED/SUCCESS/FAILURE,
# pytest counts, terminal $ prefix, etc. This module adds the small set of
# LLM-stage extras that the pre-LLM regex deliberately omits (bare `PR #N`
# without prose-state suffix, gh+git CLI invocations) — patterns most useful
# only when correcting LLM hallucinations on output that's already verbatim
# CLI rather than completion prose.
_R3_LLM_EVIDENCE_EXTRAS_RE = re.compile(
    r"PR\s*#\d+"  # PR reference (any form — pre-LLM regex requires prose state suffix)
    r"|\bgh\s+pr\s+(?:view|merge|create)\b"  # gh CLI invocation
    r"|\bgit\s+(?:log|cat-file)\b",  # git CLI invocation
    re.IGNORECASE,
)

last_flag_times: dict[str, float] = {}
governance_events: dict = {}

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
    # Track 5 universal exempt: governance protocol tags ([PROPOSE:],
    # [CONCUR:], [READY:], [BUSY:], [FP-LOG:], etc.) skip ALL rule checks.
    # These are status/governance artifacts, not execution-action messages.
    # Per Max's architectural fix 2026-05-11 (self-referential R8 FP).
    if _UNIVERSAL_PROTOCOL_TAG_RE.search(text):
        logger.info(
            "ENFORCER skipped by universal protocol-tag exempt: %s",
            text[:80],
        )
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

        if r3_skip and r6_skip:
            return

    result = check_with_llm(text, list(message_window), channel_id=event.get("channel", ""))
    if not result or not result.get("violation"):
        return
    # R9 post-LLM exempt — suppress DIRECTIVE-INITIATIVE fires when the message
    # already contains a [PROPOSE:] block or names an explicit next-action subject.
    if result.get("rule_number") == 9 and _R9_EXEMPT_RE.search(text):
        logger.info(
            "ENFORCER R9 suppressed by post-LLM exempt regex (text contained [PROPOSE:] or next-action subject)"
        )
        return
    # R3 post-LLM exempt — Track 4. Suppress LLM-hallucinated R3 violations
    # when the message contains substantial evidence patterns. Re-uses the
    # pre-LLM `_R3_EVIDENCE_RE` (commit hashes, JSON, MERGEABLE/SUCCESS, pytest
    # counts, terminal $) plus a small set of LLM-stage extras (bare PR ref,
    # gh+git CLI invocations).
    if result.get("rule_number") == 3 and (
        _R3_EVIDENCE_RE.search(text) or _R3_LLM_EVIDENCE_EXTRAS_RE.search(text)
    ):
        logger.info(
            "ENFORCER R3 suppressed by post-LLM evidence regex (text contained commit/PR/CLI evidence)"
        )
        return
    # R3 post-LLM REPLAY-ON-CLAIM — Drevon PR-A.5 listener integration.
    # When REPLAY_ON_CLAIM_ENABLED=1, query turn_logs (PR-A schema) for actual
    # verify_pr.sh / gh pr view / git cat-file invocations matching PR#/commit
    # refs in the claim. If evidence found → suppress; otherwise fire.
    # Disabled by default — turn_logs needs accumulation post-#718 hook-wiring
    # before this check has reliable data. Activate after observation window.
    if result.get("rule_number") == 3 and os.environ.get("REPLAY_ON_CLAIM_ENABLED") == "1":
        try:
            from src.replay import verify_completion_claim

            verified, reason = verify_completion_claim(text, callsign=callsign)
            if verified:
                logger.info("ENFORCER R3 suppressed by replay-on-claim (PR-A.5): %s", reason)
                return
            logger.info("ENFORCER R3 confirmed by replay-on-claim (PR-A.5): %s", reason)
        except Exception as exc:
            logger.warning(
                "replay-on-claim raised — proceeding with LLM verdict (best-effort): %s",
                exc,
            )
    _fire_violation(result, web)


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


def _insert_kei_task(title: str) -> str | None:
    """Insert a new KEI task into public.tasks and return the new KEI id.

    Uses a single psycopg connection per call (listener is long-running; avoid
    holding a persistent connection across arbitrary idle periods).

    Returns None on any failure so the caller can log-and-skip gracefully.
    Idempotency: tasks.id has a UNIQUE constraint; duplicate inserts raise
    IntegrityError which is caught and treated as a skip (one winner).
    """
    db_url = DATABASE_URL.replace("+asyncpg", "")
    if not db_url:
        logger.warning("auto-KEI: DATABASE_URL not set — skipping insert")
        return None
    try:
        with psycopg.connect(db_url) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(MAX((substring(id FROM 'KEI-([0-9]+)'))::int), 0) + 1"
                " FROM public.tasks WHERE id ~ '^KEI-[0-9]+$'"
            )
            row = cur.fetchone()
            next_n: int = row[0] if row else 1
            kei_id = f"KEI-{next_n}"
            cur.execute(
                "INSERT INTO public.tasks (id, title, status, dependencies, required_persona)"
                " VALUES (%s, %s, %s, %s, %s)",
                (kei_id, title, "available", [], None),
            )
            conn.commit()
            logger.info("auto-KEI: inserted %s — %s", kei_id, title)
            return kei_id
    except psycopg.errors.UniqueViolation:
        logger.info("auto-KEI: duplicate insert skipped (race guard)")
        return None
    except Exception as exc:
        logger.warning("auto-KEI: DB insert failed: %s", exc)
        return None


def _maybe_auto_create_kei(event: dict, web: WebClient | None) -> None:
    """Auto-KEI intercept for [CEO]-prefixed messages in #ceo channel.

    Fires BEFORE the normal fanout so it runs regardless of fanout outcome.
    Best-effort: any failure is logged but never blocks the fanout relay.
    """
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
    kei_id = _insert_kei_task(title)
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
