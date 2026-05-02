"""COO Bot (Max) — Dave's COO proxy for Agency OS.

Phase 2 build (Tier 0 starting authority). Reads supergroup + governance_events,
DMs Dave summaries on hourly cadence + on-demand /status, accepts Dave's DMs
as conversational + /post group-relay instructions.

LLM: Claude Opus via `claude -p` subprocess on Dave's Max plan ($0/call).

Environment:
  COO_BOT_TOKEN          — Telegram bot token for @MaxCOO_Bot
  COO_DAVE_CHAT_ID       — Dave's chat ID for DM (default: 7267788033)
  COO_DIGEST_INTERVAL_MINUTES — digest poll cadence (default: 60)
  COO_APPROVAL_TIER      — 0..3, default 0 (tier-gated autonomy)
  DATABASE_URL or SUPABASE_DB_URL — asyncpg DSN
  MEMORY_RECALL_BACKEND  — 'supabase' | 'mem0' | 'hybrid' for context retriever
  OPENAI_API_KEY         — DEPRECATED for primary path; kept as legacy fallback
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
from telegram import Bot, Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.coo_bot.config import COOConfig
from src.coo_bot.dm_handler import handle_dm
from src.coo_bot.group_handler import handle_group_message
from src.coo_bot.opus_client import opus_call
from src.coo_bot.persona import get_system_prompt

logger = logging.getLogger(__name__)

# Group chat ID for the Agency OS supergroup (used to filter MessageHandlers).
_GROUP_CHAT_ID = -1003926592540


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


async def generate_summary(events: list[dict[str, Any]], window_hours: int = 1) -> str:
    """Generate a plain-English digest of recent governance events via Opus CLI.

    Uses Claude Opus subprocess (Max plan, $0/call). Returns an empty string
    on failure so the caller can skip the DM gracefully.
    """
    event_lines = "\n".join(
        f"- [{e.get('event_type', 'unknown')}] {e.get('event_data', {})} "
        f"(callsign={e.get('callsign', '?')}, ts={e.get('timestamp', '')})"
        for e in events[:30]  # cap at 30 to stay under prompt budget
    )
    user_msg = (
        f"Last {window_hours}h governance events ({len(events)} total):\n"
        f"{event_lines}\n\n"
        "Summarize for Dave: 3-5 bullet points, flag anything unusual."
    )
    return await opus_call(get_system_prompt("dm"), user_msg, timeout=60)


async def fetch_recent_events(
    database_url: str, hours: int = 1
) -> list[dict[str, Any]]:
    """Fetch governance_events created in the last *hours* hours via asyncpg.

    Returns an empty list on connection failure so the digest loop continues.
    """
    if not database_url:
        logger.warning("No DATABASE_URL configured — skipping event fetch")
        return []

    since: datetime = datetime.now(UTC) - timedelta(hours=hours)
    query = """
        SELECT event_type, event_data, callsign, timestamp, tool_name, directive_id
        FROM public.governance_events
        WHERE timestamp > $1
        ORDER BY timestamp DESC
        LIMIT 500
    """
    try:
        conn: asyncpg.Connection = await asyncpg.connect(database_url, statement_cache_size=0)
        try:
            rows = await conn.fetch(query, since)
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    except Exception as exc:
        logger.error("Event fetch failed: %s", exc)
        return []


async def send_dm(bot_token: str, chat_id: int, text: str) -> bool:
    """Send *text* to *chat_id* using the COO bot token.

    Returns True on success, False on TelegramError (logged, not raised).
    """
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except TelegramError as exc:
        logger.error("Telegram DM failed (chat_id=%s): %s", chat_id, exc)
        return False


async def digest_loop(cfg: COOConfig) -> None:
    """Main event loop — poll, summarise, DM Dave on cadence."""
    interval_seconds = cfg.digest_interval_minutes * 60
    logger.info(
        "COO digest loop started — interval=%dm, dave_chat_id=%s",
        cfg.digest_interval_minutes,
        cfg.dave_chat_id,
    )

    while True:
        try:
            events = await fetch_recent_events(
                cfg.database_url, hours=cfg.digest_interval_minutes // 60 or 1
            )
            if not events:
                logger.info("No governance events in window — skipping DM")
            else:
                summary = await generate_summary(
                    events, window_hours=cfg.digest_interval_minutes // 60 or 1
                )
                if summary:
                    ok = await send_dm(cfg.bot_token, cfg.dave_chat_id, summary)
                    logger.info("DM sent=%s (%d events)", ok, len(events))
                else:
                    logger.warning("Empty summary from OpenAI — skipping DM")
        except Exception as exc:
            logger.error("Unhandled digest error (will retry next cycle): %s", exc)

        await asyncio.sleep(interval_seconds)


# ---------------------------------------------------------------------------
# /status command handler
# ---------------------------------------------------------------------------


async def _check_opa() -> str:
    """Return OPA health string without raising."""
    try:
        import urllib.request
        req = urllib.request.urlopen("http://localhost:8181/health", timeout=2)
        return "up" if req.status == 200 else f"degraded ({req.status})"
    except Exception:
        return "unavailable"


async def _recorder_status() -> str:
    """Return recorder freshness based on log mtime."""
    log_path = "/tmp/agency-os-recorder/recorder.log"
    try:
        mtime = os.path.getmtime(log_path)
        age_minutes = (datetime.now().timestamp() - mtime) / 60
        return f"up (last write {age_minutes:.0f}m ago)"
    except FileNotFoundError:
        return "unavailable (log not found)"
    except Exception:
        return "unavailable"


async def _last_governance_event(database_url: str) -> str:
    """Return timestamp of most recent governance_event."""
    if not database_url:
        return "unavailable (no DB URL)"
    try:
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        try:
            row = await conn.fetchrow(
                "SELECT timestamp FROM public.governance_events ORDER BY timestamp DESC LIMIT 1"
            )
            if row:
                return str(row["timestamp"])
            return "none recorded"
        finally:
            await conn.close()
    except Exception as exc:
        logger.error("last_governance_event query failed: %s", exc)
        return "unavailable"


async def _today_event_count(database_url: str) -> str:
    """Return count of governance_events since midnight UTC today."""
    if not database_url:
        return "unavailable (no DB URL)"
    try:
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        try:
            row = await conn.fetchrow(
                "SELECT COUNT(*) AS cnt FROM public.governance_events "
                "WHERE timestamp > current_date"
            )
            return str(row["cnt"]) if row else "0"
        finally:
            await conn.close()
    except Exception as exc:
        logger.error("today_event_count query failed: %s", exc)
        return "unavailable"


async def _open_pr_count() -> str:
    """Return count of open PRs via gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--json", "number"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            import json
            prs = json.loads(result.stdout or "[]")
            return str(len(prs))
        return "unavailable"
    except Exception as exc:
        logger.error("open_pr_count failed: %s", exc)
        return "unavailable"


async def _memory_count(database_url: str) -> str:
    """Return total agent_memories row count."""
    if not database_url:
        return "unavailable (no DB URL)"
    try:
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        try:
            row = await conn.fetchrow("SELECT COUNT(*) AS cnt FROM public.agent_memories")
            return str(row["cnt"]) if row else "0"
        finally:
            await conn.close()
    except Exception as exc:
        logger.error("memory_count query failed: %s", exc)
        return "unavailable"


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command — return system health snapshot."""
    cfg = COOConfig()

    opa, recorder, last_event, today_count, open_prs, mem_count = await asyncio.gather(
        _check_opa(),
        _recorder_status(),
        _last_governance_event(cfg.database_url),
        _today_event_count(cfg.database_url),
        _open_pr_count(),
        _memory_count(cfg.database_url),
    )

    lines = [
        "Agency OS — system status",
        f"OPA: {opa}",
        f"Max (COO bot): up",
        f"Recorder: {recorder}",
        f"Last governance event: {last_event}",
        f"Governance events today: {today_count}",
        f"Open PRs: {open_prs}",
        f"Agent memories: {mem_count}",
    ]
    text = "\n".join(lines)

    if update.message:
        await update.message.reply_text(text)


# ---------------------------------------------------------------------------
# Entry point — Application with job_queue + command handler
# ---------------------------------------------------------------------------


def _make_digest_job(cfg: COOConfig):
    """Return a job_queue callback that runs one digest cycle."""
    async def _digest_job(context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            hours = cfg.digest_interval_minutes // 60 or 1
            events = await fetch_recent_events(cfg.database_url, hours=hours)
            if not events:
                logger.info("No governance events in window — skipping DM")
                return
            summary = await generate_summary(events, window_hours=hours)
            if summary:
                ok = await send_dm(cfg.bot_token, cfg.dave_chat_id, summary)
                logger.info("DM sent=%s (%d events)", ok, len(events))
            else:
                logger.warning("Empty summary from OpenAI — skipping DM")
        except Exception as exc:
            logger.error("Unhandled digest error: %s", exc)

    return _digest_job


def main() -> None:
    """Entry point. Loads config, builds Application, registers handlers."""
    logging.basicConfig(
        level=logging.INFO,
        format="[coo-bot] %(asctime)s %(levelname)s: %(message)s",
        stream=sys.stdout,
    )

    cfg = COOConfig()

    app = (
        Application.builder()
        .token(cfg.bot_token)
        .concurrent_updates(True)
        .build()
    )

    app.add_handler(CommandHandler("status", cmd_status))

    # Group reader — store messages from supergroup in rolling buffer.
    app.add_handler(
        MessageHandler(
            filters.Chat(chat_id=_GROUP_CHAT_ID) & filters.TEXT,
            handle_group_message,
        )
    )

    # Dave's DM — bidirectional conversation + /post relay + STOP MAX kill.
    app.add_handler(
        MessageHandler(
            filters.Chat(chat_id=cfg.dave_chat_id) & filters.TEXT,
            handle_dm,
        )
    )

    interval_seconds = cfg.digest_interval_minutes * 60
    app.job_queue.run_repeating(
        _make_digest_job(cfg),
        interval=interval_seconds,
        first=interval_seconds,
        name="digest",
    )

    tier = int(os.environ.get("COO_APPROVAL_TIER", "0"))
    logger.info(
        "Max COO bot starting — digest interval=%dm, dave_chat_id=%s, tier=%d",
        cfg.digest_interval_minutes, cfg.dave_chat_id, tier,
    )
    app.run_polling(drop_pending_updates=True)
