"""Max COO bot — DM handler (Dave ↔ Max private channel).

Handles bidirectional DM conversation with Dave:
- Dave sends message → intent classifier (Opus) decides relay vs private
- relay: posts to group via group_writer, confirms in DM
- private: loads full context + responds via Opus
- Dave sends STOP MAX → Max drops to relay-only (Tier 0 emergency)

Public API:
    handle_dm(update, context) — registered as MessageHandler for Dave's DM chat
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import ContextTypes

from src.coo_bot.config import COOConfig
from src.coo_bot.opus_client import opus_call

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_COO_SYSTEM_PROMPT = (
    "You are Max, COO of Agency OS. You are Dave's private strategic advisor. "
    "You have access to the full history of agent activity via governance_events "
    "and agent_memories. You watch the group chat in real-time. "
    "Respond concisely and directly. Dave is the CEO — be useful, not verbose. "
    "If Dave asks what's happening, summarise recent group activity. "
    "If Dave asks for your opinion, give it honestly — you are his COO, not a yes-man."
)


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

    # Classify intent: relay to group or private response
    try:
        from src.coo_bot.group_handler import get_recent_messages

        recent_msgs = get_recent_messages(limit=10)
    except Exception:
        recent_msgs = []
    recent_group = "\n".join(
        f"[{m.get('sender', '?')}] {m.get('text', '')[:100]}" for m in recent_msgs
    )

    intent = await _classify_intent(text, recent_group)

    if intent.get("intent") == "relay":
        relay_text = intent.get("relay_text") or text
        try:
            from src.coo_bot.group_writer import post_to_group

            ok = await post_to_group(
                cfg.bot_token, relay_text, dave_dm_id=update.message.message_id
            )
            if ok:
                await update.message.reply_text(f"Posted to group: {relay_text}")
            else:
                await update.message.reply_text("Failed to post to group.")
        except Exception as exc:
            await update.message.reply_text(f"Post failed: {exc}")
        return

    # Private response — Haiku tier for routine, Opus only for deep/tools.
    # Mirrors group_handler latency strategy (commit 6823670e).
    memory_context = await _load_context()
    user_msg = f"[Recent context]\n{memory_context}\n\n[Dave's message]\n{text}"

    lowered = text.lower()
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
    model = "claude-opus-4-6" if needs_deep else "claude-haiku-4-5"
    timeout = 120 if needs_tools else (90 if needs_deep else 20)

    response = await opus_call(
        _COO_SYSTEM_PROMPT,
        user_msg,
        timeout=timeout,
        model=model,
        with_tools=needs_tools,
    )

    if response:
        await update.message.reply_text(response)
    else:
        await update.message.reply_text(
            "I couldn't generate a response right now. Try again in a moment."
        )


async def _classify_intent(text: str, recent_group: str) -> dict:
    """Classify Dave's DM intent: 'relay' or 'private'.

    Returns: {"intent": "relay"|"private", "relay_text": "..." or None}
    """
    import json

    prompt = (
        "You are Max's intent classifier. Dave DM'd you this message. "
        "Based on the message content + recent group context, decide:\n"
        "- 'relay': Dave wants this posted to the group (e.g. 'tell them X', "
        "'approve that', 'merge it', direct instructions for agents)\n"
        "- 'private': Dave wants a response from you in DM (questions, "
        "'what do you think', 'summarise', opinions)\n\n"
        "If relay: extract the exact text to post (clean it up for group "
        "consumption but keep Dave's voice/intent).\n\n"
        'Respond with ONLY valid JSON: {"intent": "relay"|"private", '
        '"relay_text": "text to post" or null}\n\n'
        f"Recent group context:\n{recent_group}\n\n"
        f"Dave's DM: {text}"
    )
    raw = await opus_call("You are a JSON-only intent classifier.", prompt, timeout=30)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError, AttributeError):
        return {"intent": "private", "relay_text": None}


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
