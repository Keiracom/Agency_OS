"""
Contract: src/telegram_bot/save_handler.py
Purpose: /save command — write typed memory rows via src.memory.store()
Layer: telegram_bot command handler
Consumers: chat_bot.py CommandHandler('save', cmd_save)

Delegates all Supabase writes to src.memory.store() — enforces rate limiting,
type validation, and the agreed interface contract.
"""

import logging
import os
import sys

from telegram import Update
from telegram.ext import ContextTypes

# sys.path injection so src.memory resolves from the telegram_bot runtime context
_src_root = os.path.join(os.path.dirname(__file__), "..", "..")
if _src_root not in sys.path:
    sys.path.insert(0, _src_root)

from src.memory import store  # noqa: E402
from src.memory.types import VALID_SOURCE_TYPES  # noqa: E402

logger = logging.getLogger(__name__)

CALLSIGN: str = os.getenv("CALLSIGN", "elliot")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_save_command(args: list[str]) -> tuple[str, str]:
    """Return (source_type, content) from the args list after /save.

    Rules:
    - /save pattern <text>  -> ('pattern', '<text>')
    - /save <text>          -> ('daily_log', '<text>')  if first word not a valid type
    - /save                 -> ('daily_log', '')         empty (handler rejects)
    """
    if not args:
        return ("daily_log", "")

    first = args[0].lower()
    if first in VALID_SOURCE_TYPES:
        content = " ".join(args[1:]).strip()
        return (first, content)

    # First word is not a valid type — treat entire text as daily_log content
    content = " ".join(args).strip()
    return ("daily_log", content)


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------


async def cmd_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/save [type] <content> — save typed memory via src.memory.store()."""
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
            "/save daily_log <text>\n"
            "/save <text>  (saves as daily_log)\n\n"
            f"Valid types: {', '.join(sorted(VALID_SOURCE_TYPES))}"
        )
        return

    try:
        row = await store(
            callsign=CALLSIGN,
            source_type=source_type,
            content=content,
            tags=[source_type],
        )
        preview = content[:50] + ("..." if len(content) > 50 else "")
        row_id = row.get("id", "?")
        await update.message.reply_text(
            f"Saved [{source_type}]: {preview}\nid={row_id}"
        )
        logger.info(f"[save] callsign={CALLSIGN} type={source_type} id={row_id}")
    except ValueError as exc:
        logger.error(f"[save] validation error: {exc}")
        await update.message.reply_text(f"Invalid type: {exc}")
    except Exception as exc:
        logger.error(f"[save] unexpected error: {exc}")
        await update.message.reply_text(f"Failed to save: {exc}")
