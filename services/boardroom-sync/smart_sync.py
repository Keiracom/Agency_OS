#!/usr/bin/env python3
"""
Smart Boardroom Sync
Watches Elliot's transcript and extracts only Boardroom-related messages.
Tracks chat context from user messages to attribute responses correctly.
"""

import json
import re
import time
import fcntl
from datetime import datetime
from pathlib import Path

# Config
SESSIONS_DIR = Path.home() / ".clawdbot/agents/main/sessions"
SHARED_LOG_PATH = Path("/home/elliotbot/clawd/data/boardroom_chat.jsonl")
STATE_FILE = Path("/home/elliotbot/clawd/data/.boardroom_sync_state.json")
BOARDROOM_CHAT_ID = -5240078568

# State
current_chat_context = None
processed_entries = set()


def load_state():
    """Load sync state from disk."""
    global processed_entries
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
                processed_entries = set(state.get("processed", []))
        except:
            processed_entries = set()


def save_state():
    """Save sync state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        # Only keep last 1000 entries to prevent unbounded growth
        recent = list(processed_entries)[-1000:]
        json.dump({"processed": recent}, f)


def append_to_log(entry: dict):
    """Append a message to the shared log (thread-safe)."""
    SHARED_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SHARED_LOG_PATH, "a") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(json.dumps(entry) + "\n")
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def extract_chat_id(text: str) -> int:
    """Extract chat ID from user message metadata."""
    # Pattern: [Telegram Dave id:... +Xm 2026-01-01 00:00 UTC]
    # The Boardroom messages have this format
    
    # Check for explicit Boardroom chat ID
    if str(BOARDROOM_CHAT_ID) in text:
        return BOARDROOM_CHAT_ID
    
    # Check for Boardroom mention
    if "boardroom" in text.lower():
        return BOARDROOM_CHAT_ID
    
    # Check for Telegram group indicators (message_id at end suggests group chat)
    if "[message_id:" in text.lower():
        return BOARDROOM_CHAT_ID
    
    # Check for @KeiracomGemini mentions (Boardroom context)
    if "@keiracomgemini" in text.lower():
        return BOARDROOM_CHAT_ID
    
    return None


def is_boardroom_context(entry: dict) -> bool:
    """Check if this entry is in Boardroom context."""
    global current_chat_context
    
    msg = entry.get("message", {})
    role = msg.get("role")
    content = msg.get("content", "")
    
    if isinstance(content, list):
        content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
    
    # User messages update context
    if role == "user":
        chat_id = extract_chat_id(content)
        if chat_id:
            current_chat_context = chat_id
            return chat_id == BOARDROOM_CHAT_ID
        # If no chat ID found, keep previous context
        return current_chat_context == BOARDROOM_CHAT_ID
    
    # Assistant messages use current context
    if role == "assistant":
        return current_chat_context == BOARDROOM_CHAT_ID
    
    return False


def extract_text(content) -> str:
    """Extract plain text from message content."""
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
        return " ".join(parts)
    
    return ""


def get_entry_id(entry: dict, line_num: int) -> str:
    """Generate unique ID for an entry."""
    ts = entry.get("timestamp", "")
    msg = entry.get("message", {})
    role = msg.get("role", "")
    return f"{ts}:{role}:{line_num}"


def process_transcript(transcript_path: Path):
    """Process a transcript file and extract Boardroom messages."""
    global current_chat_context
    
    if not transcript_path.exists():
        return
    
    with open(transcript_path) as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        
        if entry.get("type") != "message":
            continue
        
        # Check if already processed
        entry_id = get_entry_id(entry, i)
        if entry_id in processed_entries:
            continue
        
        # Check Boardroom context
        if not is_boardroom_context(entry):
            processed_entries.add(entry_id)
            continue
        
        msg = entry.get("message", {})
        role = msg.get("role")
        content = msg.get("content", "")
        text = extract_text(content)
        
        # Skip empty, tool calls, or very short
        if not text or len(text) < 5:
            processed_entries.add(entry_id)
            continue
        
        # Skip noise
        if text.strip() in ["NO_REPLY", "HEARTBEAT_OK"]:
            processed_entries.add(entry_id)
            continue
        
        if "<function_calls>" in text or "function_calls" in text:
            processed_entries.add(entry_id)
            continue
        
        if "<" in text or "antml:" in text:
            processed_entries.add(entry_id)
            continue
        
        # Only log assistant messages (user messages come from Gemini bridge)
        if role == "assistant":
            log_entry = {
                "ts": entry.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                "agent": "elliot",
                "sender": "Elliot",
                "text": text[:2000],
                "chat_id": BOARDROOM_CHAT_ID,
                "source": "transcript_sync"
            }
            append_to_log(log_entry)
            print(f"[SYNC] Elliot: {text[:60]}...")
        
        processed_entries.add(entry_id)


def get_active_transcripts() -> list:
    """Get recently modified transcript files."""
    if not SESSIONS_DIR.exists():
        return []
    
    transcripts = list(SESSIONS_DIR.glob("*.jsonl"))
    # Sort by modification time, most recent first
    transcripts.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    # Return top 3 most recent
    return transcripts[:3]


def main():
    """Main sync loop."""
    print("Starting Smart Boardroom Sync...")
    print(f"Watching: {SESSIONS_DIR}")
    print(f"Logging to: {SHARED_LOG_PATH}")
    
    load_state()
    
    try:
        while True:
            for transcript in get_active_transcripts():
                process_transcript(transcript)
            save_state()
            time.sleep(2)  # Check every 2 seconds
    except KeyboardInterrupt:
        print("\nShutting down...")
        save_state()


if __name__ == "__main__":
    main()
