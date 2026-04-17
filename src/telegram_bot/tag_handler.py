"""
FILE: src/telegram_bot/tag_handler.py
PURPOSE: Telegram /tag command handler — natural-language lead rejection tagging.
         Dave sends /tag <free text>; Haiku parses to structured fields;
         Dave confirms yes/no; on yes, a row is persisted to lead_tags.
CONSUMERS: src/telegram_bot/chat_bot.py (registers handle_tag + handle_tag_confirmation)
"""

import asyncio
import json
import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from src.pipeline.lead_tag_categories import (
    REASON_CATEGORIES,
    STAGE_CHOICES,
    is_valid_category,
    is_valid_stage,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HAIKU_MODEL = "claude-haiku-4-5"
TAG_TIMEOUT_SECONDS = 300  # 5 minutes

# ---------------------------------------------------------------------------
# In-memory pending tag store  {chat_id: PendingTag}
# ---------------------------------------------------------------------------

_pending_tags: dict[int, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Helpers — imported lazily to avoid circular imports with chat_bot
# ---------------------------------------------------------------------------

def _get_bot_config() -> tuple[str, str, dict[str, str], str, int]:
    """Return (SUPABASE_URL, SUPABASE_KEY, SUPABASE_HEADERS, CALLSIGN, DAVE_USER_ID).

    Reads from environment so tests can patch os.environ without importing chat_bot.
    """
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    callsign = os.environ.get("CALLSIGN", "elliot")
    dave_user_id = int(os.environ.get("DAVE_USER_ID", "7267788033"))
    return supabase_url, supabase_key, headers, callsign, dave_user_id


def _classify_sender_local(update: Update) -> str:
    """Lightweight sender check — returns 'dave' or the callsign."""
    _, _, _, callsign, dave_user_id = _get_bot_config()
    user = update.effective_user
    if user and not user.is_bot and user.id == dave_user_id:
        return "dave"
    return callsign


# ---------------------------------------------------------------------------
# Haiku extraction
# ---------------------------------------------------------------------------

_EXTRACT_PROMPT = (
    "Extract lead rejection tag fields from the user text. "
    "Return ONLY valid JSON with these keys: "
    "domain (string, required), stage (string, required), reason_category (string, required), "
    "detail (string, required), criteria (object or null, optional). "
    f"stage must be one of: {STAGE_CHOICES}. "
    f"reason_category must be one of: {REASON_CATEGORIES}. "
    "Map numeric stage references (e.g. 'stage 2') to their canonical name (e.g. 'stage2_abn'). "
    "Return no other text — only the JSON object."
)


async def _haiku_extract(free_text: str) -> dict[str, Any]:
    """Call Haiku to parse free_text into structured tag fields. Returns parsed dict."""
    import anthropic  # local import — keeps module importable without anthropic installed in CI mocks

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.AsyncAnthropic(api_key=api_key)

    response = await client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=300,
        temperature=0,
        system=_EXTRACT_PROMPT,
        messages=[{"role": "user", "content": free_text}],
    )
    raw = response.content[0].text
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Timeout cleanup
# ---------------------------------------------------------------------------

async def _schedule_timeout(chat_id: int, message_id: int) -> None:
    await asyncio.sleep(TAG_TIMEOUT_SECONDS)
    pending = _pending_tags.get(chat_id)
    if pending and pending.get("message_id") == message_id:
        _pending_tags.pop(chat_id, None)
        logger.info(f"[tag] Pending tag for chat={chat_id} timed out and cleared.")


# ---------------------------------------------------------------------------
# Public handler: /tag
# ---------------------------------------------------------------------------

async def handle_tag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """CommandHandler callback for /tag <free text>."""
    if not update.message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    free_text = " ".join(context.args) if context.args else ""

    if not free_text.strip():
        await update.message.reply_text(
            "Usage: /tag <free text>\n"
            "Example: /tag plumbermate.com.au dropped from stage 2 enterprise 200+ employees"
        )
        return

    # Guard: one pending tag per chat at a time
    if chat_id in _pending_tags:
        await update.message.reply_text(
            "Finish your previous tag first (reply yes/no)"
        )
        return

    # Call Haiku
    try:
        parsed = await _haiku_extract(free_text)
    except Exception as exc:
        logger.error(f"[tag] Haiku extraction failed: {exc}")
        await update.message.reply_text(f"Parse failed — {exc}. Tag not created.")
        return

    # Validate
    stage = parsed.get("stage", "")
    category = parsed.get("reason_category", "")
    domain = parsed.get("domain", "")
    detail = parsed.get("detail", "")
    criteria = parsed.get("criteria")

    errors: list[str] = []
    if not domain:
        errors.append("domain missing")
    if not is_valid_stage(stage):
        errors.append(f"invalid stage={stage!r}")
    if not is_valid_category(category):
        errors.append(f"invalid reason_category={category!r}")
    if not detail:
        errors.append("detail missing")

    if errors:
        await update.message.reply_text(
            f"Parse error: {', '.join(errors)}.\n"
            f"Raw parsed: domain={domain!r} stage={stage!r} category={category!r} detail={detail!r}"
        )
        return

    # Store pending
    tagged_by = _classify_sender_local(update)
    _pending_tags[chat_id] = {
        "domain": domain,
        "stage": stage,
        "reason_category": category,
        "detail": detail,
        "criteria": criteria,
        "tagged_by": tagged_by,
        "message_id": message_id,
    }

    # Schedule timeout cleanup
    asyncio.create_task(_schedule_timeout(chat_id, message_id))

    # Build confirmation
    criteria_line = f"\ncriteria={json.dumps(criteria)}" if criteria else ""
    confirm_text = (
        f"Tag {domain} — stage={stage}, category={category}, detail={detail}"
        f"{criteria_line}. Confirm? (reply yes/no)"
    )
    await update.message.reply_text(confirm_text)


# ---------------------------------------------------------------------------
# Public handler: yes/no confirmation
# ---------------------------------------------------------------------------

async def handle_tag_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    MessageHandler observer. Returns True if the message was consumed (yes/no reply).
    Returns False if no pending tag exists or message is not yes/no — caller passes through.
    """
    if not update.message or not update.effective_chat:
        return False

    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip().lower()

    if chat_id not in _pending_tags:
        return False

    if text not in ("yes", "no"):
        return False

    pending = _pending_tags.pop(chat_id)

    if text == "no":
        await update.message.reply_text("Cancelled.")
        return True

    # Persist to Supabase
    supabase_url, _, headers, _, _ = _get_bot_config()
    payload: dict[str, Any] = {
        "domain": pending["domain"],
        "stage": pending["stage"],
        "reason_category": pending["reason_category"],
        "detail": pending["detail"],
        "tagged_by": pending["tagged_by"],
        "tagged_at": datetime.now(timezone.utc).isoformat(),
    }
    if pending.get("criteria") is not None:
        payload["criteria"] = pending["criteria"]

    try:
        url = f"{supabase_url}/rest/v1/lead_tags"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        await update.message.reply_text("✅ Tagged.")
        logger.info(f"[tag] Persisted lead_tag for domain={pending['domain']}")
    except Exception as exc:
        logger.error(f"[tag] Supabase write failed: {traceback.format_exc()}")
        short = str(exc)[:120]
        await update.message.reply_text(f"Tag failed — {short}. Not saved.")

    return True
