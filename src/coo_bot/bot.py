"""COO Bot (Max) — Plain-English executive summaries for Dave.

Phase 2 roadmap component. Observe-only v1: reads governance_events +
ceo_memory, generates summaries, DMs Dave. Does NOT make decisions.

Environment:
  COO_BOT_TOKEN         — Telegram bot token for @MaxCOO_Bot
  OPENAI_API_KEY        — for summary generation
  SUPABASE_URL + SUPABASE_SERVICE_KEY — for reading events
  COO_DAVE_CHAT_ID      — Dave's chat ID for DM (default: 7267788033)
  COO_DIGEST_INTERVAL_MINUTES — poll cadence (default: 60)
  DATABASE_URL or SUPABASE_DB_URL — asyncpg DSN
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
import openai
from telegram import Bot
from telegram.error import TelegramError

from src.coo_bot.config import COOConfig

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are Max, COO of Agency OS. "
    "Summarize agent activity for Dave in 3-5 bullet points. "
    "Be concise, flag anything unusual."
)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


async def generate_summary(events: list[dict[str, Any]], window_hours: int = 1) -> str:
    """Generate a plain-English digest of recent governance events via OpenAI.

    Uses gpt-4o-mini to keep costs low. Returns an empty string on failure
    so the caller can skip the DM gracefully.
    """
    cfg = COOConfig()
    client = openai.AsyncOpenAI(api_key=cfg.openai_api_key)

    event_lines = "\n".join(
        f"- [{e.get('event_type', 'unknown')}] {e.get('message', '')} "
        f"(callsign={e.get('callsign', '?')}, ts={e.get('created_at', '')})"
        for e in events[:30]  # cap at 30 to stay under token budget
    )
    user_msg = (
        f"Last {window_hours}h governance events ({len(events)} total):\n{event_lines}"
    )

    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        logger.error("OpenAI summary failed: %s", exc)
        return ""


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
        SELECT event_type, message, callsign, created_at, metadata
        FROM public.governance_events
        WHERE created_at > $1
        ORDER BY created_at DESC
        LIMIT 200
    """
    try:
        conn: asyncpg.Connection = await asyncpg.connect(database_url)
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


def main() -> None:
    """Entry point. Loads config, wires signal handlers, runs digest loop."""
    logging.basicConfig(
        level=logging.INFO,
        format="[coo-bot] %(asctime)s %(levelname)s: %(message)s",
        stream=sys.stdout,
    )

    cfg = COOConfig()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _shutdown(sig: int, frame: Any) -> None:  # noqa: ANN401
        logger.info("Received signal %s — shutting down COO bot", sig)
        loop.stop()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        loop.run_until_complete(digest_loop(cfg))
    finally:
        loop.close()
        logger.info("COO bot stopped")
