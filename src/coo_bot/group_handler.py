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
from datetime import datetime, timezone
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Group chat ID for the Agency OS supergroup
_GROUP_CHAT_ID = -1003926592540

# Rolling buffer — capped at 50 entries
_MAX_BUFFER = 50
_buffer: deque[dict[str, Any]] = deque(maxlen=_MAX_BUFFER)


async def handle_group_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
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

    ts = datetime.now(tz=timezone.utc).isoformat()
    if update.message.date:
        ts = update.message.date.astimezone(timezone.utc).isoformat()

    entry: dict[str, Any] = {
        "sender": sender_name,
        "text": text,
        "timestamp": ts,
        "message_id": update.message.message_id,
    }
    _buffer.append(entry)
    logger.debug("group_handler: buffered message from %s (buffer=%d)", sender_name, len(_buffer))

    # If Dave addresses Max in group, respond IN the group
    dave_id = 7267788033
    if sender_id == dave_id:
        await _respond_to_dave_in_group(update, text)


async def _respond_to_dave_in_group(update: Update, text: str) -> None:
    """When Dave messages in the group, Max responds in-group like a COO would.

    Uses Opus to generate a contextual response based on recent group activity.
    Only responds if the message seems directed at Max or is a question/instruction.
    """
    try:
        from src.coo_bot.opus_client import opus_call
        from src.coo_bot.persona import get_system_prompt

        # Build context from recent buffer
        recent = "\n".join(
            f"[{m.get('sender', '?')}] {m.get('text', '')[:100]}"
            for m in list(_buffer)[-10:]
        )

        classifier_prompt = (
            "Dave just posted in the group. Decide: does this need a Max response?\n"
            "- If Dave is asking Max something, giving an instruction, or saying something "
            "that warrants a COO response → respond with the actual response text.\n"
            "- If Dave is addressing Elliot/Aiden specifically (not Max) → respond with exactly: SKIP\n"
            "- If it's a general statement not needing Max input → respond with: SKIP\n\n"
            f"Recent group:\n{recent}\n\nDave's message: {text}"
        )

        response = await opus_call(
            get_system_prompt("dm"), classifier_prompt, timeout=60
        )

        if response and response.strip() != "SKIP":
            # Post Max's response to group
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
