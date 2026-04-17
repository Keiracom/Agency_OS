"""
Contract: src/telegram_bot/save_handler.py
Purpose: /save command — write typed memory rows to agent_memories table
Layer: telegram_bot command handler
Imports: httpx (shared with chat_bot), python-telegram-bot
Consumers: chat_bot.py CommandHandler('save', cmd_save)

Schema (agent_memories):
    id              uuid PK
    callsign        text NOT NULL
    source_type     text NOT NULL  -- pattern/decision/test_result/reasoning/skill/dave_confirmed/general
    content         text NOT NULL
    typed_metadata  jsonb
    tags            text[]
    valid_from      timestamptz DEFAULT now()
    valid_to        timestamptz
    created_at      timestamptz NOT NULL DEFAULT now()
"""

import logging
import os

import httpx
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (mirrors chat_bot.py — same env, same headers pattern)
# ---------------------------------------------------------------------------

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
CALLSIGN: str = os.getenv("CALLSIGN", "elliot")

_SUPABASE_HEADERS: dict[str, str] = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

VALID_TYPES: frozenset[str] = frozenset({
    "pattern",
    "decision",
    "skill",
    "reasoning",
    "test_result",
    "dave_confirmed",
    "general",
})

AGENT_MEMORIES_TABLE = "agent_memories"

# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_save_command(args: list[str]) -> tuple[str, str]:
    """Return (source_type, content) from the args list after /save.

    Rules:
    - /save pattern <text>  -> ('pattern', '<text>')
    - /save <text>          -> ('general', '<text>')  if first word not a valid type
    - /save                 -> ('general', '')         empty content (handler will reject)
    """
    if not args:
        return ("general", "")

    first = args[0].lower()
    if first in VALID_TYPES:
        content = " ".join(args[1:]).strip()
        return (first, content)

    # First word is not a type — treat entire message as general content
    content = " ".join(args).strip()
    return ("general", content)


# ---------------------------------------------------------------------------
# Supabase write
# ---------------------------------------------------------------------------


async def write_agent_memory(
    source_type: str,
    content: str,
    callsign: str = CALLSIGN,
    typed_metadata: dict | None = None,
    tags: list[str] | None = None,
) -> dict:
    """POST one row to agent_memories. Returns the created row dict."""
    url = f"{SUPABASE_URL}/rest/v1/{AGENT_MEMORIES_TABLE}"
    payload: dict = {
        "callsign": callsign,
        "source_type": source_type,
        "content": content,
    }
    if typed_metadata is not None:
        payload["typed_metadata"] = typed_metadata
    if tags is not None:
        payload["tags"] = tags

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=_SUPABASE_HEADERS, json=payload, timeout=10)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else payload


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------


async def cmd_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/save [type] <content> — save typed memory to agent_memories."""
    args: list[str] = context.args or []
    source_type, content = parse_save_command(args)

    if not content:
        await update.message.reply_text(
            "Usage:\n"
            "/save pattern <text>\n"
            "/save decision <text>\n"
            "/save skill <text>\n"
            "/save reasoning <text>\n"
            "/save test_result <text>\n"
            "/save <text>  (saves as general)\n\n"
            f"Valid types: {', '.join(sorted(VALID_TYPES))}"
        )
        return

    try:
        row = await write_agent_memory(source_type=source_type, content=content)
        preview = content[:50] + ("..." if len(content) > 50 else "")
        row_id = row.get("id", "?")
        await update.message.reply_text(
            f"Saved [{source_type}]: {preview}\nid={row_id}"
        )
        logger.info(f"[save] callsign={CALLSIGN} type={source_type} id={row_id}")
    except httpx.HTTPStatusError as exc:
        logger.error(f"[save] Supabase error {exc.response.status_code}: {exc.response.text}")
        await update.message.reply_text(
            f"Failed to save: Supabase returned {exc.response.status_code}. Check logs."
        )
    except Exception as exc:
        logger.error(f"[save] unexpected error: {exc}")
        await update.message.reply_text(f"Failed to save: {exc}")
