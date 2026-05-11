"""Enforcer Bot — Slack Socket Mode governance enforcement daemon.

Provenance:
  Source bot:  src/telegram_bot/enforcer_bot.py (571 LOC, TG getUpdates polling)
  Spec:        docs/enforcer_redesign_spec.md (ENFORCER-REDESIGN-001 / ENFORCER-BUILD-001)

Preserved helpers (ported nearly verbatim):
  - TRIGGER_PATTERNS / should_check()     — enforcer_bot.py:100-142
  - enforce_events state tracker logic    — enforcer_bot.py:261-301
  - stage0_active deterministic check     — enforcer_bot.py:317-329
  - max_outbox_watcher()                  — enforcer_bot.py:407-550
  - PR_CLAIM_RE regex                     — enforcer_bot.py:202-206

New in this module:
  - Slack Socket Mode (slack_sdk.socket_mode.aiohttp.SocketModeClient)
  - Per-channel message windows and per-(rule,channel) rate limiting
  - Slack chat.postMessage with threading (thread_ts)
  - asyncpg pool for governance_events persistence
  - ENFORCER_OBSERVE_ONLY phase-A mode
  - housekeeping() with auth.test health probe (3 consecutive failures → exit)
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import sys
import time
import traceback
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger("enforcer_slack")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

# ---------------------------------------------------------------------------
# Config / constants
# ---------------------------------------------------------------------------

SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")   # xapp-1- for Socket Mode
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")   # xoxb- for API calls
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_URL", "")   # asyncpg DSN

CHECK_MODEL = "gpt-4o-mini"
MAX_WINDOW = 20
FLAG_COOLDOWN_SECONDS = 300
OBSERVE_ONLY = os.environ.get("ENFORCER_OBSERVE_ONLY", "0") == "1"

# Slack channel IDs from spec §1 (resolved at runtime via conversations.info;
# these are fallback human-readable names used in scoping logic).
EXECUTION_CHANNEL_NAME = "#execution"
ALERTS_CHANNEL_NAME = "#alerts"

# Filesystem inboxes — parity with enforcer_bot.py:192-196
BOT_INBOXES = [
    "/tmp/telegram-relay-elliot/inbox",
    "/tmp/telegram-relay-aiden/inbox",
    "/tmp/telegram-relay-max/inbox",
]

MAX_OUTBOX = "/tmp/telegram-relay-max/outbox"

# asyncpg pool — initialised lazily in _get_pool()
_pg_pool: Any = None  # asyncpg.Pool | None
_PG_POOL_SIZE = 4
_PG_IDLE_TIMEOUT = 60.0

# In-process retry queue for failed governance_events inserts (housekeeping drains it)
_insert_retry_queue: list[dict] = []
_INSERT_MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# Per-channel state
# ---------------------------------------------------------------------------

# message_windows[channel_name] = deque(maxlen=20)
message_windows: dict[str, deque] = {}

# enforce_events: same keys as TG version — last_concur_elliot, last_concur_aiden,
#                 last_step0, last_stage0_request.  Shared across channels (global tracker).
enforce_events: dict[str, dict] = {}

# last_flag_times[(rule_number, channel_name)] = float (time.time())
# Per-rule AND per-channel — upgraded from the global per-rule dict in enforcer_bot.py:34
last_flag_times: dict[tuple, float] = {}

# channel_name_cache[channel_id] = "#channel-name"
channel_name_cache: dict[str, str] = {}

# Health probe state
_health_fail_count = 0

# ---------------------------------------------------------------------------
# Trigger patterns — ported verbatim from enforcer_bot.py:100-136
# ---------------------------------------------------------------------------

TRIGGER_PATTERNS = [
    "dave —",
    "dave,",
    "your call",
    "here's the plan",
    "here's what",
    "commit",
    "pushed",
    "pr #",
    "merged",
    "deployed",
    "triggered",
    "complete",
    "done",
    "all stores written",
    "4-store",
    "git push origin main",
    "memory_listener.py",
    "chat_bot.py",
    "store.py",
    "listener_discernment.py",
    "claude.md",
    "state saved",
    "ceo_memory updated",
    "manual updated",
    "drive mirror",
    "daily_log written",
    "stores written",
    "store save complete",
    "session closed",
    "[atlas]",
    "[orion]",
    # Dual-concur governance (2026-04-22): [FINAL CONCUR:*] is peer-Step-0 signal for Rule 2
    "[final concur",
    "final concur:elliot",
    "final concur:aiden",
]

# PR claim regex — ported verbatim from enforcer_bot.py:202-206
PR_CLAIM_RE = re.compile(
    r"#?(\d+).{0,80}?(merged|approved(?:\s+by\s+both)?|complete|passed?|green|all\s+tests|ci\s+pass|ship)"
    r"|(merged|approved(?:\s+by\s+both)?|complete|passed?|green|all\s+tests|ci\s+pass).{0,80}?#?(\d+)",
    re.IGNORECASE,
)


def should_check(text: str) -> bool:
    """Pre-filter: only proceed if any TRIGGER_PATTERN substring hits."""
    lower = text.lower()
    return any(p in lower for p in TRIGGER_PATTERNS)


# ---------------------------------------------------------------------------
# Callsign extraction — spec §7.3
# ---------------------------------------------------------------------------

_USERNAME_TO_CALLSIGN: dict[str, str] = {
    "elliot":   "elliot",
    "aiden":    "aiden",
    "max":      "max",
    "atlas":    "atlas",
    "orion":    "orion",
    "scout":    "scout",
    "enforcer": "enforcer",
}


def callsign_from_username(username: str) -> str:
    """Map Slack username override → callsign per spec §7.3.

    Lowercase, strip.  Fallback to 'dave' for real Slack users (no override),
    or 'unknown' for unrecognised values.
    """
    if not username:
        return "dave"
    key = username.strip().lower()
    return _USERNAME_TO_CALLSIGN.get(key, "dave" if key else "unknown")


# ---------------------------------------------------------------------------
# asyncpg pool
# ---------------------------------------------------------------------------

async def _get_pool() -> Any:
    """Return (or lazily initialise) the asyncpg connection pool."""
    global _pg_pool
    if _pg_pool is not None:
        return _pg_pool
    try:
        import asyncpg  # type: ignore[import]
        _pg_pool = await asyncpg.create_pool(
            dsn=SUPABASE_DB_URL,
            min_size=1,
            max_size=_PG_POOL_SIZE,
            max_inactive_connection_lifetime=_PG_IDLE_TIMEOUT,
        )
        logger.info("asyncpg pool created (size=%d)", _PG_POOL_SIZE)
    except Exception as exc:
        logger.warning("asyncpg pool init failed: %s", exc)
        _pg_pool = None
    return _pg_pool


async def _insert_governance_event(row: dict) -> bool:
    """Insert one row into public.governance_events via asyncpg.

    On failure: enqueue in _insert_retry_queue for housekeeping() retry.
    Returns True on success, False on failure.
    """
    pool = await _get_pool()
    if pool is None:
        logger.warning("governance_events insert skipped — no asyncpg pool")
        row["_retries"] = row.get("_retries", 0)
        _insert_retry_queue.append(row)
        return False
    sql = """
        INSERT INTO public.governance_events
            (timestamp, source, rule_id, rule_name, channel, callsign,
             interjection_text, current_message, recent_window_json, llm_model)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                sql,
                row.get("timestamp", datetime.now(UTC)),
                row.get("source", "enforcer"),
                row.get("rule_id"),
                row.get("rule_name"),
                row.get("channel"),
                row.get("callsign"),
                row.get("interjection_text"),
                row.get("current_message"),
                json.dumps(row.get("recent_window_json", [])),
                row.get("llm_model", CHECK_MODEL),
            )
        return True
    except Exception as exc:
        logger.warning("governance_events insert failed: %s", exc)
        row["_retries"] = row.get("_retries", 0)
        _insert_retry_queue.append(row)
        return False


# ---------------------------------------------------------------------------
# LLM check — ported from enforcer_bot.py:151-189, uses build_prompt()
# ---------------------------------------------------------------------------

async def check_with_llm(
    channel: str,
    current_msg: str,
    recent_msgs: list[str],
) -> dict | None:
    """Call gpt-4o-mini to check for rule violations.

    Uses build_prompt(channel) as system message (channel-aware rule filtering).
    Fail-open: returns None on any error.
    """
    from src.bot_common.enforcer_rules import build_prompt

    if not OPENAI_API_KEY:
        logger.warning("No OPENAI_API_KEY — skipping LLM check")
        return None

    system_prompt = build_prompt(channel)
    user_content = json.dumps(
        {
            "current_message": current_msg,
            "recent_messages": recent_msgs[-MAX_WINDOW:],
            "governance_events": enforce_events,
        },
        ensure_ascii=False,
    )

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": CHECK_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 300,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception as exc:
        logger.warning("LLM check failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Interjection delivery
# ---------------------------------------------------------------------------

async def _write_filesystem_inboxes(text: str, ts: str) -> None:
    """Write interjection to bot filesystem inboxes — parity with enforcer_bot.py:225-244."""
    for inbox in BOT_INBOXES:
        try:
            os.makedirs(inbox, exist_ok=True)
            fname = f"{ts}_{uuid.uuid4().hex[:8]}.json"
            payload = {
                "id": fname.replace(".json", ""),
                "type": "text",
                "chat_id": -1003926592540,
                "text": f"[ENFORCER]: {text}",
                "sender": "enforcer",
                "timestamp": datetime.now(UTC).isoformat(),
            }
            with open(os.path.join(inbox, fname), "w") as f:
                json.dump(payload, f)
        except Exception as exc:
            logger.error("Failed to write inbox %s: %s", inbox, exc)


async def _post_to_slack(
    channel_id: str,
    text: str,
    thread_ts: str | None,
) -> bool:
    """Post interjection via Slack chat.postMessage. Retry once on 5xx."""
    if not SLACK_BOT_TOKEN:
        logger.warning("No SLACK_BOT_TOKEN — cannot post interjection")
        return False
    payload: dict = {
        "channel": channel_id,
        "text": text,
        "username": "Enforcer",
        "icon_emoji": ":rotating_light:",
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                    json=payload,
                )
            data = resp.json()
            if data.get("ok"):
                return True
            logger.warning("chat.postMessage not ok (attempt %d): %s", attempt + 1, data.get("error"))
            if attempt == 0:
                await asyncio.sleep(1)
        except Exception as exc:
            logger.warning("chat.postMessage error (attempt %d): %s", attempt + 1, exc)
            if attempt == 0:
                await asyncio.sleep(1)
    return False


# ---------------------------------------------------------------------------
# Message processing pipeline — spec §4
# ---------------------------------------------------------------------------

async def process_message(event: dict) -> None:
    """Full message-processing pipeline per spec §4.

    Fail-open: any unhandled exception is logged (with traceback) and swallowed.
    Surfaces internal errors as a governance_events row with rule_id='internal_error'.
    """
    try:
        await _process_message_inner(event)
    except Exception:
        logger.error("Unhandled exception in process_message:\n%s", traceback.format_exc())
        # Surface as governance_events internal_error row — best-effort
        with contextlib.suppress(Exception):
            await _insert_governance_event({
                "source": "enforcer",
                "rule_id": "internal_error",
                "rule_name": "internal_error",
                "channel": event.get("_channel_name", "unknown"),
                "callsign": "enforcer",
                "interjection_text": "INTERNAL ERROR: " + traceback.format_exc()[:500],
                "current_message": event.get("text", "")[:500],
                "recent_window_json": [],
                "llm_model": CHECK_MODEL,
            })


async def _process_message_inner(event: dict) -> None:
    """Inner pipeline — called by process_message(); exceptions propagate up."""
    text = event.get("text", "")
    if not text:
        return

    channel_id: str = event.get("channel", "")
    channel_name: str = event.get("_channel_name", channel_id)  # resolved by socket_loop
    event_ts: str = event.get("ts", "")
    thread_ts: str | None = event.get("thread_ts") or event_ts or None

    # Step 1 — Filter own bot messages (bot_id present) and Enforcer username
    bot_id = event.get("bot_id")
    username_override = event.get("username", "")
    if bot_id and username_override.lower() == "enforcer":
        logger.debug("Skipped (own Enforcer message): ts=%s", event_ts)
        return

    # Dave messages pass through to state tracker but skip violation checks
    is_dave = not bot_id and not username_override

    # Step 2 — Update sliding window
    if channel_name not in message_windows:
        message_windows[channel_name] = deque(maxlen=MAX_WINDOW)
    sender_label = username_override or "Dave"
    window_entry = f"[{sender_label}]: {text[:500]}"
    message_windows[channel_name].append(window_entry)

    # Step 3 — Update enforce_events state tracker (verbatim logic from enforcer_bot.py:261-301)
    now_iso = datetime.now(UTC).isoformat()
    text_lower = text.lower()

    if is_dave and (
        text.strip().endswith("/stage0") or text.strip().endswith("/stage 0")
    ):
        enforce_events["last_stage0_request"] = {
            "timestamp": now_iso,
            "text_snippet": text[:100],
            "topic_hint": text[:60],
        }
        logger.info("EVENT: last_stage0_request updated")

    if bot_id and "concur" in text_lower:
        callsign = callsign_from_username(username_override)
        if callsign == "elliot":
            enforce_events["last_concur_elliot"] = {
                "timestamp": now_iso,
                "text_snippet": text[:100],
                "topic_hint": text[:60],
            }
            logger.info("EVENT: last_concur_elliot updated")
        elif callsign == "aiden":
            enforce_events["last_concur_aiden"] = {
                "timestamp": now_iso,
                "text_snippet": text[:100],
                "topic_hint": text[:60],
            }
            logger.info("EVENT: last_concur_aiden updated")

    if "step 0" in text_lower or "restate" in text_lower:
        enforce_events["last_step0"] = {
            "timestamp": now_iso,
            "text_snippet": text[:100],
            "topic_hint": text[:60],
        }
        logger.info("EVENT: last_step0 updated")

    # Dave messages don't trigger violation checks
    if is_dave:
        logger.debug("Skipped violation check (Dave): ts=%s", event_ts)
        return

    # Step 4 — Pre-filter
    if not should_check(text):
        logger.debug("Skipped (no trigger): %s", text[:60])
        return

    logger.info("CHECKING message in %s ts=%s", channel_name, event_ts)

    # Step 5 — stage0_active (deterministic, not LLM) — enforcer_bot.py:317-329
    stage0_active = False
    last_stage0 = enforce_events.get("last_stage0_request", {})
    if last_stage0:
        stage0_ts = last_stage0.get("timestamp", "")
        if stage0_ts:
            try:
                ts_dt = datetime.fromisoformat(stage0_ts)
                age_minutes = (datetime.now(UTC) - ts_dt).total_seconds() / 60
                stage0_active = age_minutes < 30
            except Exception:
                pass
    logger.info("/stage0 gate: active=%s", stage0_active)

    # Step 6 — LLM check
    recent_window = list(message_windows[channel_name])
    result = await check_with_llm(channel_name, text, recent_window)

    if not result or not result.get("violation"):
        return

    rule_num = result.get("rule_number")
    rule_name = result.get("rule_name", "unknown")
    detail = result.get("detail", "")
    should_have = result.get("should_have", "")

    # Step 7a — Rules 1 and 2 require stage0_active — enforcer_bot.py:341-343
    if rule_num in (1, 2) and not stage0_active:
        logger.info("Rule %s violation suppressed — /stage0 not active", rule_num)
        return

    # Step 7b — Per-(rule, channel) cooldown — upgraded from per-rule global
    flag_key = (rule_num, channel_name)
    now = time.time()
    if (
        flag_key in last_flag_times
        and (now - last_flag_times[flag_key]) < FLAG_COOLDOWN_SECONDS
    ):
        logger.info("Skipping re-flag rule=%s channel=%s (cooldown)", rule_num, channel_name)
        return
    last_flag_times[flag_key] = now

    # Step 8 — Interjection text — identical format to enforcer_bot.py:357
    interjection = f"[ENFORCER] Rule {rule_num} -- {rule_name}: {detail}. {should_have}."
    logger.info("VIOLATION: %s", interjection)

    # Step 9 — Deliver
    ts_label = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    callsign = callsign_from_username(username_override)

    if OBSERVE_ONLY:
        observe_text = "OBSERVE: " + interjection
        logger.info("[OBSERVE-ONLY] Would post: %s", interjection)
        await _write_filesystem_inboxes(observe_text, ts_label)
        await _insert_governance_event({
            "timestamp": datetime.now(UTC),
            "source": "enforcer",
            "rule_id": f"R{rule_num}",
            "rule_name": rule_name,
            "channel": channel_name,
            "callsign": callsign,
            "interjection_text": observe_text,
            "current_message": text[:1000],
            "recent_window_json": recent_window,
            "llm_model": CHECK_MODEL,
        })
        return

    # Live mode: Slack post + filesystem inboxes
    slack_ok = await _post_to_slack(channel_id, interjection, thread_ts)
    if not slack_ok:
        logger.warning("Slack post failed — writing filesystem inbox only")
    await _write_filesystem_inboxes(interjection, ts_label)

    # Step 10 — Persist governance_events row
    await _insert_governance_event({
        "timestamp": datetime.now(UTC),
        "source": "enforcer",
        "rule_id": f"R{rule_num}",
        "rule_name": rule_name,
        "channel": channel_name,
        "callsign": callsign,
        "interjection_text": interjection,
        "current_message": text[:1000],
        "recent_window_json": recent_window,
        "llm_model": CHECK_MODEL,
    })


# ---------------------------------------------------------------------------
# Channel name resolution
# ---------------------------------------------------------------------------

async def _resolve_channel_name(channel_id: str) -> str:
    """Resolve Slack channel ID → '#name' via conversations.info (cached)."""
    if channel_id in channel_name_cache:
        return channel_name_cache[channel_id]
    if not SLACK_BOT_TOKEN:
        return channel_id
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://slack.com/api/conversations.info",
                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                params={"channel": channel_id},
            )
        data = resp.json()
        if data.get("ok"):
            name = "#" + data["channel"]["name"]
            channel_name_cache[channel_id] = name
            return name
    except Exception as exc:
        logger.warning("conversations.info failed for %s: %s", channel_id, exc)
    return channel_id


def _channel_in_scope(channel_name: str) -> bool:
    """True if this channel carries any enforcer rule."""
    from src.bot_common.enforcer_rules import RULES
    all_channels: set[str] = set()
    for r in RULES:
        all_channels.update(r["channels"])
    return channel_name in all_channels


# ---------------------------------------------------------------------------
# socket_loop — Slack Socket Mode consumer
# ---------------------------------------------------------------------------

async def socket_loop() -> None:
    """Receive Slack message.channels events via Socket Mode.

    Uses SLACK_APP_TOKEN (xapp-1-) for socket auth.
    Resolves channel ID → name; skips channels not in any rule's scope.
    """
    if not SLACK_APP_TOKEN:
        logger.error("SLACK_APP_TOKEN not set — socket_loop cannot start")
        return

    from slack_sdk.socket_mode.aiohttp import SocketModeClient  # type: ignore[import]
    from slack_sdk.web.async_client import AsyncWebClient  # type: ignore[import]

    web_client = AsyncWebClient(token=SLACK_BOT_TOKEN)
    client = SocketModeClient(app_token=SLACK_APP_TOKEN, web_client=web_client)

    async def _handle(client_ref: Any, req: Any) -> None:  # noqa: ANN401
        """Handle one Socket Mode request payload."""
        try:
            payload = req.payload
            if isinstance(payload, str):
                payload = json.loads(payload)
            if payload.get("type") != "event_callback":
                await client_ref.send_socket_mode_response(
                    __import__("slack_sdk.socket_mode.response", fromlist=["SocketModeResponse"]).SocketModeResponse(
                        envelope_id=req.envelope_id
                    )
                )
                return
            ev = payload.get("event", {})
            if ev.get("type") != "message":
                await client_ref.send_socket_mode_response(
                    __import__("slack_sdk.socket_mode.response", fromlist=["SocketModeResponse"]).SocketModeResponse(
                        envelope_id=req.envelope_id
                    )
                )
                return

            channel_id = ev.get("channel", "")
            channel_name = await _resolve_channel_name(channel_id)

            # ACK immediately — Slack requires <3s
            from slack_sdk.socket_mode.response import SocketModeResponse
            await client_ref.send_socket_mode_response(
                SocketModeResponse(envelope_id=req.envelope_id)
            )

            if not _channel_in_scope(channel_name):
                logger.debug("Skipping channel not in scope: %s", channel_name)
                return

            ev["_channel_name"] = channel_name
            await process_message(ev)

        except Exception:
            logger.error("socket_loop handler error:\n%s", traceback.format_exc())

    client.socket_mode_request_listeners.append(_handle)
    logger.info("Connecting Socket Mode client...")
    await client.connect()
    logger.info("Socket Mode client connected")

    # Keep running until cancelled
    while True:
        await asyncio.sleep(10)


# ---------------------------------------------------------------------------
# max_outbox_watcher — ported nearly verbatim from enforcer_bot.py:407-550
# ---------------------------------------------------------------------------

async def max_outbox_watcher() -> None:
    """Watch MAX's outbox for PR/completion claims and mechanically verify them.

    Applies regex pre-filter (cheap) before running verify_pr.sh (slightly heavier).
    Fail-open: errors in verification log a warning and continue — never crash the watcher.

    Ported nearly verbatim from src/telegram_bot/enforcer_bot.py:407-550.
    Keeps verify_pr.sh subprocess call and PR_CLAIM_RE regex unchanged.
    """
    os.makedirs(MAX_OUTBOX, exist_ok=True)
    logger.info("Enforcer watching MAX outbox: %s", MAX_OUTBOX)

    while True:
        try:
            files = sorted(f for f in os.listdir(MAX_OUTBOX) if f.endswith(".json"))
            for fname in files:
                fpath = os.path.join(MAX_OUTBOX, fname)
                try:
                    with open(fpath) as f:
                        msg = json.load(f)
                    os.unlink(fpath)

                    text = msg.get("text", "")
                    if not text:
                        continue

                    # Cheap regex pre-filter — skip if no PR claim detected
                    match = PR_CLAIM_RE.search(text)
                    if not match:
                        logger.debug("MAX outbox: no PR claim in %s", fname)
                        continue

                    # Extract PR number from first numeric capture group
                    pr_num_str = match.group(1) or match.group(4)
                    if not pr_num_str:
                        logger.debug("MAX outbox: regex matched but no PR number in %s", fname)
                        continue
                    pr_num = int(pr_num_str)

                    # Determine which claim keyword triggered the match
                    claim_kw = (match.group(2) or match.group(3) or "").lower().strip()

                    logger.info(
                        "MAX outbox: PR claim detected — PR #%d keyword=%r in %s",
                        pr_num,
                        claim_kw,
                        fname,
                    )

                    # Mechanical verification via verify_pr.sh
                    try:
                        script_path = os.path.join(
                            os.path.dirname(
                                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                            ),
                            "scripts",
                            "verify_pr.sh",
                        )
                        proc = await asyncio.create_subprocess_exec(
                            "bash",
                            script_path,
                            str(pr_num),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        try:
                            stdout_b, stderr_b = await asyncio.wait_for(
                                proc.communicate(), timeout=15
                            )
                        except TimeoutError:
                            proc.kill()
                            await proc.wait()
                            logger.warning("verify_pr.sh timed out for PR #%d — skipping", pr_num)
                            continue
                        stdout = stdout_b.decode()
                        stderr = stderr_b.decode()
                        if not stdout.strip():
                            logger.warning(
                                "verify_pr.sh returned no output for PR #%d (exit %d): %s",
                                pr_num,
                                proc.returncode,
                                stderr[:200],
                            )
                            continue

                        verify = json.loads(stdout)
                    except json.JSONDecodeError as exc:
                        logger.warning(
                            "verify_pr.sh output not valid JSON for PR #%d: %s", pr_num, exc
                        )
                        continue
                    except Exception as exc:
                        logger.warning("verify_pr.sh error for PR #%d: %s", pr_num, exc)
                        continue

                    # Mechanical comparison against verify_pr.sh output.
                    mismatch_reason = None

                    if claim_kw in ("merged", "complete", "ship") and not verify.get("merged"):
                        mismatch_reason = (
                            f"claimed '{claim_kw}' but merged=false (state={verify.get('state')})"
                        )
                    elif claim_kw in (
                        "passed",
                        "pass",
                        "green",
                        "all tests",
                        "ci pass",
                    ) and not verify.get("ci_passing"):
                        mismatch_reason = f"claimed '{claim_kw}' but ci_passing=false"
                    elif re.match(r"approved", claim_kw, re.IGNORECASE):
                        review_state = verify.get("review_state", "unknown")
                        if review_state != "APPROVED":
                            mismatch_reason = (
                                f"claimed '{claim_kw}' but review_state={review_state}"
                            )

                    if mismatch_reason:
                        failed = verify.get("failed_checks", [])
                        source_excerpt = text[:100].replace("\n", " ")
                        interjection = (
                            f"[ENFORCER] Rule 3 — COMPLETION-REQUIRES-VERIFICATION:\n"
                            f"MAX claimed PR #{pr_num} {mismatch_reason}. "
                            f"state={verify.get('state')} ci_passing={verify.get('ci_passing')} "
                            f"review_state={verify.get('review_state')}. "
                            f"Failed checks: {failed}. "
                            f"Source: {source_excerpt}"
                        )
                        logger.info("MISMATCH: %s", interjection)

                        ts_label = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                        if not OBSERVE_ONLY:
                            # Post to #alerts if we have a channel ID configured
                            alerts_id = os.environ.get("SLACK_ALERTS_CHANNEL_ID", "")
                            if alerts_id:
                                await _post_to_slack(alerts_id, interjection, None)
                        await _write_filesystem_inboxes(interjection, ts_label)
                        await _insert_governance_event({
                            "timestamp": datetime.now(UTC),
                            "source": "enforcer",
                            "rule_id": "R3",
                            "rule_name": "COMPLETION-REQUIRES-VERIFICATION",
                            "channel": ALERTS_CHANNEL_NAME,
                            "callsign": "max",
                            "interjection_text": (
                                "OBSERVE: " + interjection if OBSERVE_ONLY else interjection
                            ),
                            "current_message": text[:1000],
                            "recent_window_json": [],
                            "llm_model": "mechanical",
                        })
                    else:
                        logger.debug(
                            "MAX PR #%d claim verified OK (merged=%s ci_passing=%s)",
                            pr_num,
                            verify.get("merged"),
                            verify.get("ci_passing"),
                        )

                except Exception as exc:
                    logger.error("Error processing MAX outbox %s: %s", fname, exc)
                    with contextlib.suppress(OSError):
                        os.unlink(fpath)

        except Exception as exc:
            logger.error("MAX outbox watch error: %s", exc)

        await asyncio.sleep(1)


# ---------------------------------------------------------------------------
# housekeeping — health probe + retry queue drain
# ---------------------------------------------------------------------------

async def housekeeping() -> None:
    """Periodic maintenance: health probe, state flush, insert retry drain.

    health probe: auth.test every 60s.
    3 consecutive failures → process exits non-zero (systemd restarts).
    """
    global _health_fail_count

    while True:
        await asyncio.sleep(60)

        # --- Health probe ---
        if SLACK_BOT_TOKEN:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        "https://slack.com/api/auth.test",
                        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                    )
                data = resp.json()
                if data.get("ok"):
                    _health_fail_count = 0
                    logger.debug("auth.test OK")
                else:
                    _health_fail_count += 1
                    logger.warning("auth.test not ok: %s (fail_count=%d)", data.get("error"), _health_fail_count)
            except Exception as exc:
                _health_fail_count += 1
                logger.warning("auth.test failed: %s (fail_count=%d)", exc, _health_fail_count)

            if _health_fail_count >= 3:
                logger.error("3 consecutive auth.test failures — exiting for systemd restart")
                sys.exit(1)

        # --- Flush stale enforce_events keys (>24h) ---
        cutoff = datetime.now(UTC)
        stale_keys = []
        for key, val in enforce_events.items():
            ts_str = val.get("timestamp", "")
            if ts_str:
                try:
                    age_h = (cutoff - datetime.fromisoformat(ts_str)).total_seconds() / 3600
                    if age_h > 24:
                        stale_keys.append(key)
                except Exception:
                    pass
        for k in stale_keys:
            enforce_events.pop(k, None)
            logger.info("housekeeping: flushed stale enforce_events key %s", k)

        # --- Retry failed governance_events inserts ---
        retry_items = list(_insert_retry_queue)
        _insert_retry_queue.clear()
        for item in retry_items:
            retries = item.get("_retries", 0)
            if retries >= _INSERT_MAX_RETRIES:
                logger.warning("governance_events insert dropped after %d retries: %s", retries, item.get("rule_id"))
                continue
            item["_retries"] = retries + 1
            success = await _insert_governance_event(item)
            if success:
                logger.info("housekeeping: retried governance_events insert OK")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point — gather socket_loop, max_outbox_watcher, housekeeping."""
    if not SLACK_APP_TOKEN:
        logger.error("SLACK_APP_TOKEN not set — cannot start Socket Mode client")
        sys.exit(1)
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — LLM enforcement checks will be skipped")

    observe_str = " [OBSERVE-ONLY MODE]" if OBSERVE_ONLY else ""
    logger.info("Enforcer Slack bot starting%s", observe_str)

    async def _main() -> None:
        await asyncio.gather(
            socket_loop(),
            max_outbox_watcher(),
            housekeeping(),
        )

    asyncio.run(_main())


if __name__ == "__main__":
    main()
