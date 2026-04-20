"""
Contract: src/telegram_bot/save_handler.py
Purpose: /save command — write typed memory rows via src.memory.store()
Layer: telegram_bot command handler
Consumers: chat_bot.py CommandHandler('save', cmd_save)

Delegates all Supabase writes to src.memory.store() — enforces rate limiting,
type validation, and the agreed interface contract.

store() is SYNC (returns uuid.UUID). cmd_save is async (Telegram handler) —
sync functions may be called from async context.

Dual-path extraction:
- /save <valid_type> <text>  → structured path (no OpenAI call)
- /save <free text>          → OpenAI GPT-4o-mini extraction path
"""

import json
import logging
import os
import sys
import uuid

import openai
from telegram import Update
from telegram.ext import ContextTypes

# sys.path injection so src.memory resolves from the telegram_bot runtime context
_src_root = os.path.join(os.path.dirname(__file__), "..", "..")
if _src_root not in sys.path:
    sys.path.insert(0, _src_root)

from src.memory.store import store  # noqa: E402
from src.memory.types import VALID_SOURCE_TYPES  # noqa: E402

logger = logging.getLogger(__name__)

CALLSIGN: str = os.getenv("CALLSIGN", "elliot")

# ---------------------------------------------------------------------------
# OpenAI extraction
# ---------------------------------------------------------------------------

_VALID_TYPES_LIST = ", ".join(sorted(VALID_SOURCE_TYPES))

EXTRACTION_PROMPT = f"""You extract structured memory fields from free-form text.

Return ONLY a JSON object with these exact keys:
- "source_type": one of [{_VALID_TYPES_LIST}]
- "content": cleaned, concise version of the core fact or decision (max 200 chars)
- "tags": list of 1-5 relevant lowercase single-word or hyphenated tags

Rules:
- source_type must be exactly one of the listed values
- If unsure of type, use "daily_log"
- content must be a standalone sentence, not a command or question
- tags must be lowercase strings, no spaces"""


def extract_memory_fields(raw_text: str) -> dict:
    """Use GPT-4o-mini to extract structured memory fields from free text."""
    client = openai.OpenAI()  # reads OPENAI_API_KEY from env

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=500,
    )
    try:
        from src.telegram_bot.openai_cost_logger import log_openai_call
        log_openai_call(
            callsign=os.getenv("CALLSIGN", "unknown"),
            use_case="save_extraction",
            model="gpt-4o-mini",
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )
    except Exception:
        pass
    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_save_command(args: list[str]) -> tuple[str, str, bool]:
    """Return (source_type, content, needs_extraction) from the args list.

    Rules:
    - /save <valid_type> <text>  -> (type, text, False)  structured, skip OpenAI
    - /save <free text>          -> ('daily_log', full_text, True)  send to OpenAI
    - /save                      -> ('daily_log', '', False)  empty, handler rejects
    """
    if not args:
        return ("daily_log", "", False)

    first = args[0].lower()
    if first in VALID_SOURCE_TYPES:
        content = " ".join(args[1:]).strip()
        return (first, content, False)

    # First word is not a valid type — send full text to OpenAI
    content = " ".join(args).strip()
    return ("daily_log", content, True)


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------


async def cmd_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/save [type] <content> — save typed memory via src.memory.store()."""
    args: list[str] = context.args or []
    source_type, content, needs_extraction = parse_save_command(args)

    if not content:
        await update.message.reply_text(
            "Usage:\n"
            "/save pattern <text>\n"
            "/save decision <text>\n"
            "/save skill <text>\n"
            "/save reasoning <text>\n"
            "/save test_result <text>\n"
            "/save daily_log <text>\n"
            "/save <text>  (smart extraction via GPT-4o-mini)\n\n"
            f"Valid types: {', '.join(sorted(VALID_SOURCE_TYPES))}"
        )
        return

    tags = [source_type]

    if needs_extraction:
        try:
            extracted = extract_memory_fields(content)
            source_type = extracted.get("source_type", "daily_log")
            if source_type not in VALID_SOURCE_TYPES:
                source_type = "daily_log"
            content = extracted.get("content", content)
            tags = extracted.get("tags", [source_type])
        except Exception as exc:
            logger.error(f"[save] OpenAI extraction failed, falling back to daily_log: {exc}")
            source_type = "daily_log"
            tags = ["daily_log"]

    try:
        memory_id: uuid.UUID = store(
            callsign=CALLSIGN,
            source_type=source_type,
            content=content,
            tags=tags,
            state="confirmed",  # /save is Dave-driven explicit capture → confirmed
        )
        preview = content[:50] + ("..." if len(content) > 50 else "")
        await update.message.reply_text(
            f"Saved [{source_type}]: {preview}\nid={memory_id}"
        )
        logger.info(f"[save] callsign={CALLSIGN} type={source_type} id={memory_id}")
    except ValueError as exc:
        logger.error(f"[save] validation error: {exc}")
        await update.message.reply_text(f"Invalid type: {exc}")
    except Exception as exc:
        logger.error(f"[save] unexpected error: {exc}")
        await update.message.reply_text(f"Failed to save: {exc}")
