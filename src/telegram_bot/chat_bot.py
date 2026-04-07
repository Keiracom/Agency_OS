"""
Contract: src/telegram_bot/chat_bot.py
Purpose: Telegram chat interface to Claude Code on VPS
Layer: standalone service (not part of Agency OS pipeline)
Imports: python-telegram-bot, httpx, subprocess, asyncio
Consumers: Dave via Telegram
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

load_dotenv("/home/elliotbot/.config/agency-os/.env")

BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
ALLOWED_CHAT_IDS: list[int] = [int(os.getenv("TELEGRAM_CHAT_ID", "7267788033"))]
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
CLAUDE_BIN: str = "/home/elliotbot/.local/bin/claude"
WORK_DIR: str = "/home/elliotbot/clawd/Agency_OS"
LOG_FILE: str = "/home/elliotbot/clawd/logs/telegram-chat-bot.log"

SUPABASE_HEADERS: dict[str, str] = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# In-memory process tracking: chat_id -> subprocess handle
running_processes: dict[int, asyncio.subprocess.Process] = {}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
# Also log to stderr so systemd/nohup captures it
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger().addHandler(console)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


async def auth_check(update: Update) -> bool:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id not in ALLOWED_CHAT_IDS:
        logger.warning(f"Rejected message from chat_id={chat_id}")
        return False
    return True


# ---------------------------------------------------------------------------
# Supabase helpers (REST, no direct SQL)
# ---------------------------------------------------------------------------


async def supabase_get_active_session(chat_id: int) -> dict | None:
    url = (
        f"{SUPABASE_URL}/rest/v1/telegram_sessions"
        f"?telegram_chat_id=eq.{chat_id}&is_active=eq.true"
        f"&order=created_at.desc&limit=1"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=SUPABASE_HEADERS, timeout=10)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


async def supabase_create_session(
    chat_id: int,
    session_id: str,
    model: str = "claude-sonnet-4-6",
) -> dict:
    url = f"{SUPABASE_URL}/rest/v1/telegram_sessions"
    payload = {
        "telegram_chat_id": chat_id,
        "claude_session_id": session_id,
        "current_model": model,
        "is_active": True,
        "message_count": 0,
        "total_tokens": 0,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=SUPABASE_HEADERS, json=payload, timeout=10)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else payload


async def supabase_deactivate_sessions(chat_id: int) -> None:
    url = (
        f"{SUPABASE_URL}/rest/v1/telegram_sessions"
        f"?telegram_chat_id=eq.{chat_id}&is_active=eq.true"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            url,
            headers=SUPABASE_HEADERS,
            json={"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()},
            timeout=10,
        )
    resp.raise_for_status()


async def supabase_update_session(session_id: str, **kwargs) -> None:
    url = f"{SUPABASE_URL}/rest/v1/telegram_sessions?id=eq.{session_id}"
    kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            url,
            headers=SUPABASE_HEADERS,
            json=kwargs,
            timeout=10,
        )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Claude subprocess
# ---------------------------------------------------------------------------


async def run_claude(
    session_id: str,
    model: str,
    message: str,
    chat_id: int,
) -> str:
    """Spawn claude -p --resume <session_id> and return text output."""
    cmd = [
        CLAUDE_BIN,
        "-p",
        "--resume", session_id,
        "--model", model,
        "--output-format", "text",
        message,
    ]
    logger.info(f"[chat={chat_id}] spawning claude session={session_id[:8]} model={model}")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=WORK_DIR,
        env={**os.environ},
    )
    running_processes[chat_id] = proc

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        if stderr:
            logger.debug(f"[chat={chat_id}] claude stderr: {stderr.decode('utf-8', errors='replace')[:500]}")
        return stdout.decode("utf-8", errors="replace")
    except asyncio.TimeoutError:
        proc.kill()
        logger.warning(f"[chat={chat_id}] claude timed out")
        return "Response timed out after 10 minutes. Process killed."
    finally:
        running_processes.pop(chat_id, None)


# ---------------------------------------------------------------------------
# Response chunking
# ---------------------------------------------------------------------------


def chunk_response(text: str, max_len: int = 3800) -> list[str]:
    """Split at natural boundaries: paragraphs > sentences > hard cut."""
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break

        # Paragraph break
        cut = text.rfind("\n\n", 0, max_len)
        if cut > max_len // 2:
            chunks.append(text[:cut])
            text = text[cut + 2:]
            continue

        # Sentence break
        cut = text.rfind(". ", 0, max_len)
        if cut > max_len // 2:
            chunks.append(text[:cut + 1])
            text = text[cut + 2:]
            continue

        # Hard cut
        chunks.append(text[:max_len])
        text = text[max_len:]

    return chunks


# ---------------------------------------------------------------------------
# Typing loop
# ---------------------------------------------------------------------------


async def send_typing_loop(update: Update) -> None:
    try:
        while True:
            if update.effective_chat:
                await update.effective_chat.send_action("typing")
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update):
        return
    chat_id = update.effective_chat.id
    await supabase_deactivate_sessions(chat_id)
    session_id = str(uuid.uuid4())
    await supabase_create_session(chat_id, session_id)
    short = session_id[:8]
    await update.message.reply_text(f"New session started: {short}")
    logger.info(f"[chat={chat_id}] new session {short}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update):
        return
    chat_id = update.effective_chat.id
    session = await supabase_get_active_session(chat_id)
    if not session:
        await update.message.reply_text("No active session. Send /new to start one.")
        return
    text = (
        f"Session: {session['claude_session_id'][:8]}\n"
        f"Model: {session['current_model']}\n"
        f"Messages: {session['message_count']}\n"
        f"Tokens: {session['total_tokens']}\n"
        f"Last message: {session.get('last_message_at') or 'never'}\n"
        f"Created: {session['created_at']}"
    )
    await update.message.reply_text(text)


async def cmd_compact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update):
        return
    chat_id = update.effective_chat.id
    session = await supabase_get_active_session(chat_id)
    if not session:
        await update.message.reply_text("No active session to compact.")
        return

    await update.message.reply_text("Compacting session...")

    summary = await run_claude(
        session["claude_session_id"],
        session["current_model"],
        (
            "Summarise our conversation so far into a compact context that preserves all key "
            "decisions, state, and open threads. This summary will become the start of a new session."
        ),
        chat_id,
    )

    await supabase_deactivate_sessions(chat_id)
    new_session_id = str(uuid.uuid4())
    await supabase_create_session(chat_id, new_session_id, session["current_model"])

    # Seed new session with summary
    await run_claude(
        new_session_id,
        session["current_model"],
        f"Context from previous session:\n\n{summary}",
        chat_id,
    )

    old_short = session["claude_session_id"][:8]
    new_short = new_session_id[:8]
    await update.message.reply_text(f"Compacted {old_short} into {new_short}")
    logger.info(f"[chat={chat_id}] compacted {old_short} -> {new_short}")


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /model <opus|sonnet|haiku>")
        return

    model_map = {
        "opus": "claude-opus-4-6",
        "sonnet": "claude-sonnet-4-6",
        "haiku": "claude-haiku-4-5",
    }
    choice = context.args[0].lower()
    if choice not in model_map:
        await update.message.reply_text(f"Unknown model. Choose: {', '.join(model_map.keys())}")
        return

    model_id = model_map[choice]
    chat_id = update.effective_chat.id
    session = await supabase_get_active_session(chat_id)
    if session:
        await supabase_update_session(session["id"], current_model=model_id)
    await update.message.reply_text(f"Model switched to {choice} ({model_id})")


async def cmd_kill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update):
        return
    chat_id = update.effective_chat.id
    proc = running_processes.get(chat_id)
    if proc and proc.returncode is None:
        proc.kill()
        running_processes.pop(chat_id, None)
        await update.message.reply_text("Killed running process.")
        logger.info(f"[chat={chat_id}] process killed by /kill command")
    else:
        await update.message.reply_text("No process running.")


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update):
        return
    chat_id = update.effective_chat.id
    session = await supabase_get_active_session(chat_id)
    if not session:
        await update.message.reply_text("No active session.")
        return
    await update.message.reply_text(
        f"Session {session['claude_session_id'][:8]}: {session['message_count']} messages"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update):
        return
    text = (
        "/new — Start new session\n"
        "/reset — Same as /new\n"
        "/status — Current session info\n"
        "/compact — Compress context into new session\n"
        "/model <opus|sonnet|haiku> — Switch model\n"
        "/kill — Stop running process\n"
        "/history — Recent session history\n"
        "/help — This message"
    )
    await update.message.reply_text(text)


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update):
        return
    chat_id = update.effective_chat.id

    # Guard: already processing
    proc = running_processes.get(chat_id)
    if proc and proc.returncode is None:
        await update.message.reply_text(
            "Still processing previous message. Use /kill to abort or wait."
        )
        return

    # Get or create session
    session = await supabase_get_active_session(chat_id)
    if not session:
        session_id = str(uuid.uuid4())
        session = await supabase_create_session(chat_id, session_id)
        logger.info(f"[chat={chat_id}] auto-created session {session_id[:8]}")

    typing_task = asyncio.create_task(send_typing_loop(update))
    try:
        response = await run_claude(
            session["claude_session_id"],
            session["current_model"],
            update.message.text or "",
            chat_id,
        )

        if not response or not response.strip():
            await update.message.reply_text("(empty response from Claude)")
            return

        if len(response) > 15000:
            # Upload as file
            fname = f"/tmp/response-{session['claude_session_id'][:8]}.md"
            with open(fname, "w") as fh:
                fh.write(response)
            summary = response[:500] + "\n\n(Full response attached as file)"
            await update.message.reply_text(summary)
            with open(fname, "rb") as fh:
                await update.message.reply_document(document=fh, filename="response.md")
        else:
            for chunk in chunk_response(response):
                await update.message.reply_text(chunk)

        # Update session stats
        await supabase_update_session(
            session["id"],
            message_count=session["message_count"] + 1,
            last_message_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        logger.exception(f"[chat={chat_id}] error handling message: {exc}")
        await update.message.reply_text(f"Error: {exc}")
    finally:
        typing_task.cancel()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "No bot token found. Set TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN in env."
        )

    logger.info(f"Starting Telegram chat bot (allowed_chat_ids={ALLOWED_CHAT_IDS})")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("reset", cmd_new))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("compact", cmd_compact))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("kill", cmd_kill))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
