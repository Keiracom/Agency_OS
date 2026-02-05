#!/usr/bin/env python3
"""
Boardroom Sync Service
Monitors the Keiracom Boardroom and logs ALL messages (including bot messages)
to the shared context file for cross-agent visibility.
"""

import asyncio
import json
import os
import fcntl
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from dotenv import load_dotenv

# Load environment
load_dotenv()
load_dotenv(Path.home() / ".config/agency-os/.env")

# Config
BOARDROOM_CHAT_ID = int(os.getenv("BOARDROOM_CHAT_ID", "-5240078568"))
SHARED_LOG_PATH = Path("/home/elliotbot/clawd/data/boardroom_chat.jsonl")

# Bot tokens - we need a bot that can see all messages
# Using Elliot's bot token (has admin in the group)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_ELLIOT", "8381203809:AAGk9lZ5Hl6Rg22uOgS_MlttnIYH50Uh-ow")


def ensure_log_exists():
    """Create the shared log file if it doesn't exist."""
    SHARED_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SHARED_LOG_PATH.exists():
        SHARED_LOG_PATH.touch()


def append_to_log(entry: dict):
    """Append a message to the shared log (thread-safe)."""
    ensure_log_exists()
    with open(SHARED_LOG_PATH, "a") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(json.dumps(entry) + "\n")
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def determine_agent(user) -> str:
    """Determine which agent sent the message based on bot username."""
    if not user:
        return "unknown"
    if user.is_bot:
        username = user.username or ""
        if "elliot" in username.lower() or user.id == 8381203809:
            return "elliot"
        elif "gemini" in username.lower() or user.id == 8136528801:
            return "gemini"
        else:
            return "bot"
    return "user"


async def handle_message(update: Update, context):
    """Handle all messages in the Boardroom."""
    message = update.message
    if not message:
        return
    
    # Only process messages from the Boardroom
    if message.chat_id != BOARDROOM_CHAT_ID:
        return
    
    # Skip non-text messages
    if not message.text:
        return
    
    # Determine sender
    user = message.from_user
    agent = determine_agent(user)
    
    # Get sender name
    if user:
        sender = user.first_name or user.username or "Unknown"
        if user.last_name:
            sender = f"{sender} {user.last_name}"
    else:
        sender = "Unknown"
    
    # Clean text (remove robot emoji prefix from Gemini)
    text = message.text
    if text.startswith("🤖 "):
        text = text[3:]
    
    # Create log entry
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "agent": agent,
        "sender": sender,
        "text": text[:2000],
        "chat_id": message.chat_id,
        "message_id": message.message_id,
        "user_id": user.id if user else None
    }
    
    # Append to shared log
    append_to_log(entry)
    print(f"[SYNC] {agent}/{sender}: {text[:50]}...")


async def main():
    """Start the sync service."""
    print(f"Starting Boardroom Sync Service...")
    print(f"Monitoring chat: {BOARDROOM_CHAT_ID}")
    print(f"Logging to: {SHARED_LOG_PATH}")
    
    # Build application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handle ALL messages (including from other bots)
    app.add_handler(MessageHandler(
        filters.ALL,
        handle_message
    ))
    
    # Start polling
    print("Sync service running...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
