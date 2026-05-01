"""Max COO bot — DM handler (Dave ↔ Max private channel).

Handles bidirectional DM conversation with Dave:
- Dave sends message → Max loads context (memories + recent group buffer) → responds via Opus
- Dave sends /post <text> → Max posts to group via group_writer
- Dave sends STOP MAX → Max drops to relay-only (Tier 0 emergency)

Public API:
    handle_dm(update, context) — registered as MessageHandler for Dave's DM chat
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import ContextTypes

from src.coo_bot.opus_client import opus_call
from src.coo_bot.config import COOConfig
from src.coo_bot.persona import get_system_prompt

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def handle_dm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a DM from Dave. Route to appropriate sub-handler."""
    if not update.message or not update.message.text:
        return

    cfg = COOConfig()
    text = update.message.text.strip()
    chat_id = update.message.chat_id

    # Only respond to Dave's DM
    if chat_id != cfg.dave_chat_id:
        return

    # Kill switch
    if text.upper() == "STOP MAX":
        await update.message.reply_text(
            "STOP MAX acknowledged. Dropping to relay-only. "
            "No autonomous posts. DM me 'RESUME MAX' to restore."
        )
        # Write stop state (tier_framework will read this)
        _write_stop_state(True)
        logger.warning("STOP MAX triggered by Dave")
        return

    if text.upper() == "RESUME MAX":
        _write_stop_state(False)
        await update.message.reply_text("Resumed. Back to normal operation.")
        logger.info("RESUME MAX triggered by Dave")
        return

    # /post command — relay to group
    if text.startswith("/post "):
        group_text = text[6:].strip()
        if group_text:
            # Import here to avoid circular — group_writer posts to group
            try:
                from src.coo_bot.group_writer import post_to_group
                ok = await post_to_group(cfg.bot_token, group_text)
                status = "Posted to group." if ok else "Failed to post."
                await update.message.reply_text(status)
            except Exception as exc:
                await update.message.reply_text(f"Post failed: {exc}")
        else:
            await update.message.reply_text("Usage: /post <message to post to group>")
        return

    # Regular conversation — call Opus with context
    memory_context = await _load_context()
    user_msg = f"[Recent context]\n{memory_context}\n\n[Dave's message]\n{text}"

    response = await opus_call(get_system_prompt("dm"), user_msg, timeout=30)

    if response:
        await update.message.reply_text(response)
    else:
        await update.message.reply_text(
            "I couldn't generate a response right now. Try again in a moment."
        )


async def _load_context() -> str:
    """Load recent group messages + relevant memories as context for Opus call."""
    lines = []
    # Load from working state buffer (populated by group_handler)
    try:
        from src.coo_bot.group_handler import get_recent_messages
        recent = get_recent_messages(limit=20)
        if recent:
            lines.append("Recent group messages:")
            for msg in recent:
                lines.append(f"  [{msg.get('sender', '?')}] {msg.get('text', '')[:150]}")
    except ImportError:
        lines.append("(group handler not loaded)")
    except Exception as exc:
        lines.append(f"(group context unavailable: {exc})")

    # Load from agent_memories
    try:
        from src.coo_bot.memory_retriever import get_relevant_memories
        memories = await get_relevant_memories(query="recent activity", limit=5)
        if memories:
            lines.append("\nRelevant memories:")
            for m in memories:
                lines.append(f"  [{m.get('source_type', '?')}] {m.get('content', '')[:100]}")
    except ImportError:
        pass
    except Exception:
        pass

    return "\n".join(lines) if lines else "(no context available)"


def _write_stop_state(stopped: bool) -> None:
    """Write STOP MAX state to a file that tier_framework reads."""
    import pathlib
    state_file = pathlib.Path("/tmp/max-coo-stopped")
    if stopped:
        state_file.write_text("STOPPED")
    else:
        state_file.unlink(missing_ok=True)
