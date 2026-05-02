"""Max COO bot — Group message handler.

Reads supergroup messages, maintains a rolling buffer of recent activity.
Used by dm_handler to provide context when Dave asks 'what's happening?'

Public API:
    handle_group_message(update, context) — MessageHandler callback
    get_recent_messages(limit=20) -> list[dict]
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import UTC, datetime
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Group chat ID for the Agency OS supergroup
_GROUP_CHAT_ID = -1003926592540

# Rolling buffer — capped at 50 entries
_MAX_BUFFER = 50
_buffer: deque[dict[str, Any]] = deque(maxlen=_MAX_BUFFER)


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """MessageHandler callback for group chat messages.

    Filters out own messages and enforcer alerts, stores the rest in the
    rolling buffer for later retrieval via get_recent_messages().
    """
    if not update.message or not update.message.text:
        return

    # Only process messages from the configured group
    if update.message.chat_id != _GROUP_CHAT_ID:
        return

    bot_id: int | None = None
    try:
        if context.bot:
            bot_id = context.bot.id
    except Exception:
        pass

    sender_id = update.message.from_user.id if update.message.from_user else None

    # Skip own messages to avoid loops
    if bot_id is not None and sender_id == bot_id:
        logger.debug("group_handler: skipping own message")
        return

    text = update.message.text or ""

    # Skip enforcer alerts
    if text.startswith("[ENFORCER]"):
        logger.debug("group_handler: skipping enforcer alert")
        return

    sender_name = "unknown"
    if update.message.from_user:
        u = update.message.from_user
        sender_name = u.username or u.full_name or str(u.id)

    ts = datetime.now(tz=UTC).isoformat()
    if update.message.date:
        ts = update.message.date.astimezone(UTC).isoformat()

    entry: dict[str, Any] = {
        "sender": sender_name,
        "text": text,
        "timestamp": ts,
        "message_id": update.message.message_id,
    }
    _buffer.append(entry)
    logger.debug("group_handler: buffered message from %s (buffer=%d)", sender_name, len(_buffer))

    # Respond in group when addressed by anyone (Dave, Elliot, Aiden)
    # Max is a group participant — responds when relevant
    dave_id = 7267788033
    should_respond = (
        sender_id == dave_id  # Always respond to Dave
        or "max" in text.lower()  # Respond when @-mentioned or name-dropped
        or "@maxcoo_bot" in text.lower()
    )
    if should_respond:
        await _respond_in_group(update, text, sender_name)


async def _respond_in_group(update: Update, text: str, sender: str) -> None:
    """When someone addresses Max in group, respond in-group like a COO.

    Latency-optimised: keyword pre-filter → Haiku for routine → Opus for deep.
    """
    try:
        from src.coo_bot.opus_client import opus_call
        from src.coo_bot.persona import get_system_prompt

        # LAYER 1: Keyword pre-filter (instant, no LLM) — skip obvious non-Max chatter
        lowered = text.lower()
        skip_patterns = [
            "[concur:",
            "[agree:",
            "[release:",
            "[claim:",
            "[queue-board]",
            "[dispatch",
            "co-authored-by:",
            "commit ",
            "pushed to",
        ]
        if any(pat in lowered for pat in skip_patterns) and "max" not in lowered:
            logger.debug("group_handler: pre-filter SKIP (pattern match)")
            return

        # Build context from recent buffer
        recent = "\n".join(
            f"[{m.get('sender', '?')}] {m.get('text', '')[:100]}" for m in list(_buffer)[-10:]
        )

        # LAYER 2: Decide complexity — Haiku (fast) vs Opus (deep)
        needs_tools = any(
            kw in lowered
            for kw in [
                "read",
                "file",
                "check",
                "look at",
                "query",
                "show me",
                "what's in",
                "cat ",
                "grep",
                "find",
                "database",
                "supabase",
                "store",
                "manual",
                "claude.md",
                "architecture",
            ]
        )
        needs_deep = needs_tools or any(
            kw in lowered
            for kw in [
                "why",
                "diagnose",
                "explain",
                "analyse",
                "opinion",
                "think",
                "strategy",
                "plan",
                "recommend",
            ]
        )

        # Select model: Haiku for routine, Opus for deep
        model = "claude-opus-4-6" if needs_deep else "claude-haiku-4-5"
        timeout = 120 if needs_tools else (60 if needs_deep else 20)

        classifier_prompt = (
            f"{sender} just posted in the group. Decide: does this need a Max response?\n"
            "- If someone is asking Max something, addressing Max, or saying something "
            "that warrants a COO response → respond with the actual response text.\n"
            "- If they're talking to each other and Max isn't relevant → respond with exactly: SKIP\n"
            "- Keep responses under 5 lines. Be terse.\n\n"
            f"Recent group:\n{recent}\n\n{sender}'s message: {text}"
        )

        response = await opus_call(
            get_system_prompt("dm"),
            classifier_prompt,
            timeout=timeout,
            model=model,
            with_tools=needs_tools,
        )

        if not response:
            # Timeout or failure — give useful fallback, not generic error
            await update.message.reply_text(
                "[MAX] Response timed out. For file reads or data queries, "
                "ask Elliot/Aiden directly — I don't have tool access yet."
            )
            logger.warning("group_handler: opus_call timeout responding to Dave")
        elif response.strip() != "SKIP":
            await update.message.reply_text(f"[MAX] {response}")
            logger.info("group_handler: Max responded to Dave in group")
    except Exception as exc:
        logger.warning("group_handler: failed to respond to Dave: %s", exc)


def get_recent_messages(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent `limit` buffered group messages (newest last).

    Args:
        limit: Maximum number of messages to return (default 20, max 50).

    Returns:
        List of dicts with keys: sender, text, timestamp, message_id.
    """
    limit = min(limit, _MAX_BUFFER)
    items = list(_buffer)
    return items[-limit:]
