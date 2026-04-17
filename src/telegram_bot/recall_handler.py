"""
FILE: src/telegram_bot/recall_handler.py
PURPOSE: Telegram /recall command — surfaces agent memories grouped by source_type.
CONSUMERS: src/telegram_bot/chat_bot.py (registers handle_recall)
"""

import logging
import uuid
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

import src.memory as memory

logger = logging.getLogger(__name__)

_MAX_INLINE_CHARS = 3800  # Telegram message limit is ~4096; leave headroom
_CONTENT_PREVIEW = 120


def _format_memory_line(m: memory.Memory) -> str:
    preview = m.content[:_CONTENT_PREVIEW].replace("\n", " ")
    if len(m.content) > _CONTENT_PREVIEW:
        preview += "..."
    tag_str = f" [{', '.join(m.tags)}]" if m.tags else ""
    return f"• {preview}{tag_str}"


def _format_grouped(grouped: dict[str, list[memory.Memory]]) -> str:
    if not grouped:
        return "No memories found."
    lines = []
    for source_type, mems in sorted(grouped.items()):
        lines.append(f"\n**{source_type.upper()}** ({len(mems)})")
        for m in mems:
            lines.append(_format_memory_line(m))
    return "\n".join(lines).strip()


async def handle_recall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recall [topic] command."""
    if update.message is None:
        return

    args = context.args or []
    topic = " ".join(args).strip() if args else None

    try:
        grouped = memory.recall(topic=topic)
        body = _format_grouped(grouped)
    except Exception as exc:
        logger.exception("recall failed")
        await update.message.reply_text(f"recall error: {exc}")
        return

    header = f"**/recall** {'`' + topic + '`' if topic else '(recent high-value)'}\n\n"
    full_text = header + body

    if len(full_text) <= _MAX_INLINE_CHARS:
        await update.message.reply_text(full_text)
    else:
        # Write to temp file and send summary
        tmp_path = Path(f"/tmp/recall-{uuid.uuid4()}.md")
        tmp_path.write_text(full_text)
        total = sum(len(v) for v in grouped.values())
        summary = (
            f"**/recall** returned {total} memories across {len(grouped)} type(s). "
            f"Full output saved to:\n`{tmp_path}`"
        )
        await update.message.reply_text(summary)
        logger.info(f"recall output written to {tmp_path}")
