"""GOV-PHASE2 Track C2 / M2 — /recall TG command handler.

Surfaces the existing src.memory.recall.recall() function as a TG slash
command. Output groups results by source_type with brief previews.

Hybrid Mem0 retrieval is M3 territory and lives in
src.telegram_bot.memory_listener.recall_via_mem0; this handler uses the
canonical Supabase-backed recall() for now.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.memory.recall import recall

logger = logging.getLogger(__name__)

_PREVIEW_LEN = 80
_MAX_RESULTS_PER_TYPE = 3
_DEFAULT_N = 20


async def cmd_recall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/recall [topic] — surface high-value memories grouped by type."""
    args: list[str] = context.args or []
    topic = " ".join(args).strip() or None

    try:
        grouped = recall(topic=topic, n=_DEFAULT_N)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("[recall] retrieval failed: %s", exc)
        await update.message.reply_text(f"Recall failed: {exc}")
        return

    if not grouped:
        msg = "No memories found." if topic is None else f"No memories matching '{topic}'."
        await update.message.reply_text(msg)
        return

    lines: list[str] = []
    header = f"Recall: '{topic}'" if topic else "Recall: high-value memories"
    lines.append(header)
    for source_type in sorted(grouped):
        memories = grouped[source_type][:_MAX_RESULTS_PER_TYPE]
        lines.append(f"\n[{source_type}] ({len(grouped[source_type])} total)")
        for m in memories:
            preview = m.content[:_PREVIEW_LEN] + ("..." if len(m.content) > _PREVIEW_LEN else "")
            lines.append(f"  - {preview}")

    await update.message.reply_text("\n".join(lines))
    logger.info(
        "[recall] topic=%r returned %d types, %d total memories",
        topic, len(grouped), sum(len(v) for v in grouped.values()),
    )
