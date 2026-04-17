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
import sys
import uuid
from datetime import datetime, timezone

# Add repo root to sys.path so `from src.*` imports resolve when this script
# is launched directly by systemd (sys.path[0] is src/telegram_bot/ by default,
# which doesn't expose the `src` package). Tests work because pytest injects
# rootdir; production didn't. Fixes #351 regression caught at service restart.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

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

from src.telegram_bot.tag_handler import handle_tag, handle_tag_confirmation
from src.telegram_bot.recall_handler import handle_recall
from src.telegram_bot.save_handler import cmd_save

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# load_dotenv default override=False — systemd-injected CALLSIGN/WORK_DIR_OVERRIDE
# from EnvironmentFile=.env.aiden survive this load (LAW XVII)
load_dotenv("/home/elliotbot/.config/agency-os/.env")

# LAW XVII: callsign + per-callsign workspace override
CALLSIGN: str = os.getenv("CALLSIGN", "elliot")
WORK_DIR: str = os.getenv("WORK_DIR_OVERRIDE", "/home/elliotbot/clawd/Agency_OS")

BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
# Empty TELEGRAM_CHAT_ID = no allowed chats yet (Aiden first-/start populates it)
_chat_id_raw = os.getenv("TELEGRAM_CHAT_ID", "7267788033")
ALLOWED_CHAT_IDS: list[int] = [int(x.strip()) for x in _chat_id_raw.split(",") if x.strip()]
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
CLAUDE_BIN: str = "/home/elliotbot/.local/bin/claude"
LOG_FILE: str = f"/home/elliotbot/clawd/logs/telegram-chat-bot-{CALLSIGN}.log"

SUPABASE_HEADERS: dict[str, str] = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# LAW XVII: callsign tag for outbound messages
CALLSIGN_TAG: str = f"[{CALLSIGN.upper()}]"

# Sender classification for group chats (LAW XVII)
BOT_USERNAME: str = ""  # populated at startup from getMe
KNOWN_PEER_BOTS: set[str] = {"eeeeelllliiiioooottt_bot", "aaaaidenbot", "scoutbotstephensbot"}  # lowercase
DAVE_USER_ID: int = 7267788033  # hardcoded CEO user_id — only this human gets Sender.DAVE
# Peer cross-post: bot-to-bot visibility bypass (Telegram doesn't deliver bot-to-bot)
_PEER_MAP = {"elliot": "aiden", "aiden": "elliot", "scout": "elliot"}
PEER_INBOX: str | None = f"/tmp/telegram-relay-{_PEER_MAP[CALLSIGN]}/inbox" if CALLSIGN in _PEER_MAP else None
GROUP_CHAT_ID = -1003926592540


class Sender:
    DAVE = "dave"       # human boss — follow instructions
    PEER_BOT = "peer"   # other bot — discuss only, no directives
    SELF = "self"       # own message — ignore
    UNKNOWN = "unknown"  # unknown sender — reject in group, allow in private


# Group chat: bot-to-bot turn counter (resets when Dave speaks)
_bot_turns_without_dave: dict[int, int] = {}  # chat_id -> count
MAX_BOT_TURNS = 2  # max back-and-forth without Dave before going quiet

# Security alert rate limiter: (user_id, chat_id) -> last alert timestamp
_security_alert_cache: dict[tuple[int, int], float] = {}
SECURITY_ALERT_COOLDOWN = 300  # 5 min dedup window

# In-memory process tracking: chat_id -> subprocess handle
running_processes: dict[int, asyncio.subprocess.Process] = {}

# ---------------------------------------------------------------------------
# Relay state
# ---------------------------------------------------------------------------

RELAY_DIR = f"/tmp/telegram-relay-{CALLSIGN}"  # per-callsign isolation (LAW XVII)
INBOX_DIR = f"{RELAY_DIR}/inbox"    # messages FROM Telegram TO tmux session
OUTBOX_DIR = f"{RELAY_DIR}/outbox"  # messages FROM tmux session TO Telegram

os.makedirs(INBOX_DIR, exist_ok=True)
os.makedirs(OUTBOX_DIR, exist_ok=True)

# Relay defaults ON only if tmux target exists (no tmux = use subprocess path)
_TMUX_TARGETS = {"elliot": "elliottbot", "aiden": "aiden", "scout": "scout"}
_tmux_session = _TMUX_TARGETS.get(CALLSIGN, f"{CALLSIGN}bot")
_tmux_exists = os.system(f"tmux has-session -t {_tmux_session} 2>/dev/null") == 0
relay_mode: dict[int, bool] = {cid: True for cid in ALLOWED_CHAT_IDS} if _tmux_exists else {}
# When relay is ON, messages continue the tmux session directly
RELAY_SESSION_ID: str | None = None  # set by /relay on, read from latest JSONL

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


def classify_sender(update: Update) -> str:
    """Four-axis sender classification (security-hardened).

    1. is_bot + username == self     → SELF (ignore)
    2. is_bot + username in peers    → PEER_BOT (discuss, no directives)
    3. not is_bot + user.id == Dave  → DAVE (boss, follow instructions)
    4. else                          → UNKNOWN (reject in group, log)
    """
    user = update.effective_user
    if not user:
        return Sender.UNKNOWN
    # Axis 1: Self detection
    if user.is_bot and user.username and user.username.lower() == BOT_USERNAME.lower():
        return Sender.SELF
    # Axis 2: Peer bot detection
    if user.is_bot and user.username and user.username.lower() in KNOWN_PEER_BOTS:
        return Sender.PEER_BOT
    # Axis 3: Dave — verified by user_id, not just is_bot=False
    if not user.is_bot and user.id == DAVE_USER_ID:
        return Sender.DAVE
    # Axis 4: Unknown — any other human or unrecognized bot
    logger.warning(f"[classify] UNKNOWN sender: user_id={user.id} username={user.username} is_bot={user.is_bot}")
    return Sender.UNKNOWN


async def reply_tagged(message, text: str, **kwargs) -> None:
    """Reply with CALLSIGN_TAG prefix (LAW XVII compliance)."""
    tagged = f"{CALLSIGN_TAG} {text}"
    if len(tagged) <= 4096:
        await message.reply_text(tagged, **kwargs)
    else:
        # Split long messages, tag only the first chunk
        chunks = [tagged[i:i + 4096] for i in range(0, len(tagged), 4096)]
        for chunk in chunks:
            await message.reply_text(chunk, **kwargs)


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


import json as _json
import time as _time  # noqa: F401 (used by relay helpers)


async def run_claude(
    session_id: str | None,
    model: str,
    message: str,
    chat_id: int,
) -> tuple[str, str | None]:
    """Spawn claude -p and return (text_response, real_session_id).

    If session_id is None or doesn't exist yet in Claude's history,
    runs without --resume to create a new session.  Always uses
    --output-format json so we can capture the real session_id.
    """
    cmd = [CLAUDE_BIN, "-p", "--model", model, "--output-format", "json"]
    if session_id:
        cmd.extend(["--resume", session_id])
    cmd.append(message)

    label = session_id[:8] if session_id else "new"
    logger.info(f"[chat={chat_id}] spawning claude session={label} model={model}")

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
        raw = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        if err:
            logger.debug(f"[chat={chat_id}] claude stderr: {err[:500]}")

        # If --resume failed (session not found), retry without it
        if proc.returncode != 0 and session_id and "No conversation found" in err:
            logger.info(f"[chat={chat_id}] session {label} not found, creating new")
            cmd2 = [CLAUDE_BIN, "-p", "--model", model, "--output-format", "json", message]
            proc2 = await asyncio.create_subprocess_exec(
                *cmd2,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=WORK_DIR,
                env={**os.environ},
            )
            running_processes[chat_id] = proc2
            stdout2, _ = await asyncio.wait_for(proc2.communicate(), timeout=600)
            raw = stdout2.decode("utf-8", errors="replace").strip()

        # Parse JSON output — last line should be the result object
        real_session_id = None
        text_result = ""
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = _json.loads(line)
                if obj.get("type") == "result":
                    text_result = obj.get("result", "")
                    real_session_id = obj.get("session_id")
            except _json.JSONDecodeError:
                continue

        if not text_result and raw:
            text_result = raw  # fallback to raw output

        return text_result, real_session_id

    except asyncio.TimeoutError:
        proc.kill()
        logger.warning(f"[chat={chat_id}] claude timed out")
        return "Response timed out after 10 minutes. Process killed.", None
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
    await update.message.reply_text("Session reset. Next message starts a fresh conversation.")
    logger.info(f"[chat={chat_id}] sessions deactivated, next msg creates new")


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

    summary, _ = await run_claude(
        session["claude_session_id"],
        session["current_model"],
        (
            "Summarise our conversation so far into a compact context that preserves all key "
            "decisions, state, and open threads. This summary will become the start of a new session."
        ),
        chat_id,
    )

    await supabase_deactivate_sessions(chat_id)

    # Seed new session — let Claude create the real session_id
    seed_resp, new_real_id = await run_claude(
        None,
        session["current_model"],
        f"Context from previous session:\n\n{summary}",
        chat_id,
    )
    new_session_id = new_real_id or str(uuid.uuid4())
    await supabase_create_session(chat_id, new_session_id, session["current_model"])

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
        "/relay on|off — Toggle relay to tmux session\n"
        "/save [type] <text> — Save typed memory (pattern/decision/skill/reasoning/test_result/general)\n"
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
    sender = classify_sender(update)
    is_group = update.effective_chat.type in ("group", "supergroup")
    user = update.effective_user
    logger.info(f"[msg] chat={chat_id} sender={sender} is_group={is_group} from={user.username if user else '?'} is_bot={user.is_bot if user else '?'} text={(update.message.text or '')[:60]}")

    # Self messages — always ignore
    if sender == Sender.SELF:
        return

    # Unknown sender in group — reject, log, and alert Dave (rate-limited)
    if sender == Sender.UNKNOWN and is_group:
        user = update.effective_user
        uid = user.id if user else 0
        uname = user.username if user else "?"
        logger.warning(f"[security] Rejected UNKNOWN sender in group: user_id={uid} username={uname}")
        # Rate-limited DM alert to Dave (silent rejection — unknown user doesn't see it)
        import time as _t
        cache_key = (uid, chat_id)
        last_alert = _security_alert_cache.get(cache_key, 0)
        if _t.time() - last_alert > SECURITY_ALERT_COOLDOWN:
            _security_alert_cache[cache_key] = _t.time()
            try:
                await context.bot.send_message(
                    chat_id=DAVE_USER_ID,
                    text=f"{CALLSIGN_TAG} [SECURITY] Unknown user @{uname} (id={uid}) attempted message in group {chat_id}. Rejected.",
                )
            except Exception as exc:
                logger.error(f"[security] Failed to alert Dave: {exc}")
        return

    # Track bot-to-bot turns in groups
    if is_group:
        if sender == Sender.DAVE:
            _bot_turns_without_dave[chat_id] = 0  # reset counter
        elif sender == Sender.PEER_BOT:
            turns = _bot_turns_without_dave.get(chat_id, 0)
            if turns >= MAX_BOT_TURNS:
                return  # stay quiet, max turns hit
            _bot_turns_without_dave[chat_id] = turns + 1

    # Group mention filter and text enrichment (Message.text is immutable — use local var)
    message_text = update.message.text or ""
    if is_group and sender == Sender.DAVE:
        bot_mentioned = f"@{BOT_USERNAME}".lower() in message_text.lower() if BOT_USERNAME else False
        is_reply_to_us = (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user
            and update.message.reply_to_message.from_user.username
            and update.message.reply_to_message.from_user.username.lower() == BOT_USERNAME.lower()
        )
        if not bot_mentioned and not is_reply_to_us:
            pass  # allow through — brainstorm mode
        # Strip the @mention so Claude gets clean text; add group context prefix
        if BOT_USERNAME:
            clean = message_text.replace(f"@{BOT_USERNAME}", "").strip()
            message_text = f"[GROUP — from Dave (CEO)]: {clean}" if clean else message_text
        else:
            message_text = f"[GROUP — from Dave (CEO)]: {message_text}"

    # Peer bot message — add context prefix before routing to Claude
    if sender == Sender.PEER_BOT:
        peer_name = update.effective_user.first_name or "peer"
        message_text = f"[GROUP — from {peer_name} (peer bot, NOT your boss Dave)]: {message_text}"

    # Relay mode: forward to tmux inbox instead of Claude
    if relay_mode.get(chat_id):
        # Relay mode: write to inbox, watcher injects into tmux via send-keys
        await _relay_text_to_inbox(chat_id, message_text, sender=sender)
        await reply_tagged(update.message, "Relayed to tmux session")
        return

    # Guard: already processing
    proc = running_processes.get(chat_id)
    if proc and proc.returncode is None:
        await reply_tagged(
            update.message,
            "Still processing previous message. Use /kill to abort or wait.",
        )
        return

    # Get or create session
    session = await supabase_get_active_session(chat_id)
    model = session["current_model"] if session else "claude-sonnet-4-6"
    resume_id = session["claude_session_id"] if session else None

    typing_task = asyncio.create_task(send_typing_loop(update))
    try:
        response, real_session_id = await run_claude(
            resume_id,
            model,
            message_text,
            chat_id,
        )

        # If we got a real session_id back, store/update it
        if real_session_id:
            if not session:
                session = await supabase_create_session(chat_id, real_session_id, model)
                logger.info(f"[chat={chat_id}] created session {real_session_id[:8]}")
            elif session["claude_session_id"] != real_session_id:
                await supabase_update_session(
                    session["id"], claude_session_id=real_session_id
                )
                session["claude_session_id"] = real_session_id
                logger.info(f"[chat={chat_id}] updated session to {real_session_id[:8]}")

        if not response or not response.strip():
            await reply_tagged(update.message, "(empty response from Claude)")
            return

        sid_label = (session or {}).get("claude_session_id", real_session_id or "?")
        if len(response) > 15000:
            fname = f"/tmp/response-{sid_label[:8]}.md"
            with open(fname, "w") as fh:
                fh.write(response)
            summary = f"{CALLSIGN_TAG} {response[:500]}\n\n(Full response attached as file)"
            await update.message.reply_text(summary)
            with open(fname, "rb") as fh:
                await update.message.reply_document(document=fh, filename="response.md")
        else:
            first = True
            for chunk in chunk_response(response):
                if first:
                    await reply_tagged(update.message, chunk)
                    first = False
                else:
                    await update.message.reply_text(chunk)

        # Update session stats
        if session:
            await supabase_update_session(
                session["id"],
                message_count=session["message_count"] + 1,
                last_message_at=datetime.now(timezone.utc).isoformat(),
            )

    except Exception as exc:
        logger.exception(f"[chat={chat_id}] error handling message: {exc}")
        await reply_tagged(update.message, f"Error: {exc}")
    finally:
        typing_task.cancel()


# ---------------------------------------------------------------------------
# Relay helpers
# ---------------------------------------------------------------------------


async def _relay_text_to_inbox(chat_id: int, text: str, sender: str = Sender.DAVE) -> None:
    """Write a text message to the inbox dir for the tmux session to pick up."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    msg_id = f"{ts}_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": msg_id,
        "type": "text",
        "chat_id": chat_id,
        "text": text,
        "sender": sender,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    path = os.path.join(INBOX_DIR, f"{msg_id}.json")
    with open(path, "w") as f:
        _json.dump(payload, f)
    logger.info(f"[relay] text message written to {path}")


async def _outbox_watcher(app: Application) -> None:
    """Watch outbox dir and send messages to Telegram."""
    bot = app.bot
    logger.info("[relay] outbox watcher started")
    while True:
        try:
            for fname in sorted(os.listdir(OUTBOX_DIR)):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(OUTBOX_DIR, fname)
                try:
                    with open(fpath) as f:
                        msg = _json.load(f)

                    chat_id = msg.get("chat_id", ALLOWED_CHAT_IDS[0])

                    if msg.get("type") == "text":
                        text = msg.get("text", "")
                        if len(text) > 4000:
                            tmp = f"/tmp/relay-out-{fname}.md"
                            with open(tmp, "w") as tf:
                                tf.write(text)
                            with open(tmp, "rb") as tf:
                                await bot.send_document(chat_id=chat_id, document=tf, filename="message.md")
                            os.unlink(tmp)
                        else:
                            for chunk in chunk_response(text):
                                await bot.send_message(chat_id=chat_id, text=chunk)

                    elif msg.get("type") == "file":
                        file_path = msg.get("file_path", "")
                        caption = msg.get("caption", "")
                        if os.path.exists(file_path):
                            with open(file_path, "rb") as fh:
                                await bot.send_document(
                                    chat_id=chat_id,
                                    document=fh,
                                    filename=os.path.basename(file_path),
                                    caption=caption[:1024] if caption else None,
                                )

                    os.unlink(fpath)
                    logger.info(f"[relay] outbox sent: {fname}")

                    # Cross-post group messages to peer bot's inbox (Telegram bot-to-bot blind spot)
                    if chat_id == GROUP_CHAT_ID and PEER_INBOX and msg.get("type") == "text":
                        os.makedirs(PEER_INBOX, exist_ok=True)
                        peer_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                        peer_fname = f"{peer_ts}_{uuid.uuid4().hex[:8]}.json"
                        peer_payload = {
                            "id": peer_fname.replace(".json", ""),
                            "type": "text",
                            "chat_id": chat_id,
                            "text": f"[GROUP — from {CALLSIGN.upper()} (peer bot, NOT your boss Dave)]: {msg.get('text', '')}",
                            "sender": "peer",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                        with open(os.path.join(PEER_INBOX, peer_fname), "w") as pf:
                            _json.dump(peer_payload, pf)
                        logger.info(f"[relay] cross-posted to peer inbox: {peer_fname}")

                except Exception as e:
                    logger.error(f"[relay] outbox error processing {fname}: {e}")
                    os.makedirs(f"{RELAY_DIR}/errors", exist_ok=True)
                    os.rename(fpath, os.path.join(f"{RELAY_DIR}/errors", fname))

        except Exception as e:
            logger.error(f"[relay] outbox watcher error: {e}")

        await asyncio.sleep(1)


# ---------------------------------------------------------------------------
# Relay command handler
# ---------------------------------------------------------------------------


def _find_tmux_session_id() -> str | None:
    """Find the most recently active Claude session JSONL in the project."""
    import glob
    pattern = os.path.expanduser(
        "~/.claude/projects/-home-elliotbot-clawd-Agency-OS/*.jsonl"
    )
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    if files:
        return os.path.basename(files[0]).replace(".jsonl", "")
    return None


async def cmd_relay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global RELAY_SESSION_ID
    if not await auth_check(update):
        return
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        status = "ON" if relay_mode.get(chat_id) else "OFF"
        sid = RELAY_SESSION_ID[:8] if RELAY_SESSION_ID else "none"
        await update.message.reply_text(
            f"Relay: {status}\nSession: {sid}\n/relay on — continue tmux session\n/relay off — bot Claude"
        )
        return

    if args[0].lower() == "on":
        RELAY_SESSION_ID = _find_tmux_session_id()
        if not RELAY_SESSION_ID:
            await update.message.reply_text("No tmux session found.")
            return
        relay_mode[chat_id] = True
        await update.message.reply_text(f"Relay ON ({RELAY_SESSION_ID[:8]})")
        logger.info(f"[relay] ON — session {RELAY_SESSION_ID[:8]}")
    elif args[0].lower() == "off":
        relay_mode[chat_id] = False
        await update.message.reply_text("Relay OFF")
        logger.info("[relay] OFF")
    else:
        await update.message.reply_text("Usage: /relay on|off")


# ---------------------------------------------------------------------------
# Photo and document handlers (relay mode only)
# ---------------------------------------------------------------------------


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update):
        return
    chat_id = update.effective_chat.id

    if not relay_mode.get(chat_id):
        await update.message.reply_text("Photos only supported in relay mode. Use /relay on first.")
        return

    photo = update.message.photo[-1]  # largest size
    file = await photo.get_file()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    msg_id = f"{ts}_{uuid.uuid4().hex[:8]}"

    file_path = os.path.join(INBOX_DIR, f"{msg_id}.jpg")
    await file.download_to_drive(file_path)

    payload = {
        "id": msg_id,
        "type": "photo",
        "chat_id": chat_id,
        "file_path": file_path,
        "caption": update.message.caption or "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    meta_path = os.path.join(INBOX_DIR, f"{msg_id}.json")
    with open(meta_path, "w") as f:
        _json.dump(payload, f)

    # Silent — no confirmation message
    logger.info(f"[relay] photo saved to {file_path}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update):
        return
    chat_id = update.effective_chat.id

    if not relay_mode.get(chat_id):
        await update.message.reply_text("Files only supported in relay mode. Use /relay on first.")
        return

    doc = update.message.document
    file = await doc.get_file()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    msg_id = f"{ts}_{uuid.uuid4().hex[:8]}"

    ext = os.path.splitext(doc.file_name or "file")[1] or ""
    file_path = os.path.join(INBOX_DIR, f"{msg_id}{ext}")
    await file.download_to_drive(file_path)

    payload = {
        "id": msg_id,
        "type": "document",
        "chat_id": chat_id,
        "file_path": file_path,
        "file_name": doc.file_name or "unknown",
        "mime_type": doc.mime_type or "",
        "caption": update.message.caption or "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    meta_path = os.path.join(INBOX_DIR, f"{msg_id}.json")
    with open(meta_path, "w") as f:
        _json.dump(payload, f)

    # Silent — no confirmation message
    logger.info(f"[relay] document saved to {file_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "No bot token found. Set TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN in env."
        )

    logger.info(f"Starting Telegram chat bot {CALLSIGN_TAG} callsign={CALLSIGN!r} work_dir={WORK_DIR!r} allowed_chat_ids={ALLOWED_CHAT_IDS}")
    if not BOT_TOKEN:
        logger.error(f"{CALLSIGN_TAG} TELEGRAM_BOT_TOKEN not set — refusing to start")
        sys.exit(1)
    if not ALLOWED_CHAT_IDS:
        logger.warning(f"{CALLSIGN_TAG} TELEGRAM_CHAT_ID empty — bot will accept first /start to capture chat_id (one-shot)")

    async def post_init(application: Application) -> None:
        global BOT_USERNAME
        bot_info = await application.bot.get_me()
        BOT_USERNAME = bot_info.username or ""
        logger.info(f"Bot username resolved: @{BOT_USERNAME}")
        asyncio.create_task(_outbox_watcher(application))

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Command handlers first
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("reset", cmd_new))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("compact", cmd_compact))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("kill", cmd_kill))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("relay", cmd_relay))
    app.add_handler(CommandHandler("save", cmd_save))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("tag", handle_tag))
    app.add_handler(CommandHandler("recall", handle_recall))

    # Tag confirmation observer — must run BEFORE the main text fallback
    async def _tag_confirm_observer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        consumed = await handle_tag_confirmation(update, context)
        if not consumed:
            await handle_message(update, context)

    # Media handlers before text fallback
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    # Text fallback: tag confirmation intercept, then normal message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _tag_confirm_observer))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
