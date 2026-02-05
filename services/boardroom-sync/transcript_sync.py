#!/usr/bin/env python3
"""
Transcript Sync Service
Watches Elliot's Clawdbot session transcripts and extracts Boardroom messages
to the shared context file for Gemini visibility.

Runs as a background daemon, tailing the active transcript.
"""

import json
import os
import time
import fcntl
import re
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Config
SESSIONS_DIR = Path.home() / ".clawdbot/agents/main/sessions"
SHARED_LOG_PATH = Path("/home/elliotbot/clawd/data/boardroom_chat.jsonl")
BOARDROOM_CHAT_ID = -5240078568

# Track what we've already synced
last_processed_line = {}


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


def extract_assistant_messages(transcript_path: Path):
    """Extract assistant messages from a transcript that mention the Boardroom."""
    global last_processed_line
    
    if not transcript_path.exists():
        return
    
    path_str = str(transcript_path)
    start_line = last_processed_line.get(path_str, 0)
    
    with open(transcript_path, 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines[start_line:], start=start_line):
        line = line.strip()
        if not line:
            continue
            
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        
        # Look for assistant messages
        if entry.get("type") != "message":
            continue
        
        msg = entry.get("message", {})
        if msg.get("role") != "assistant":
            continue
        
        # Extract text content
        content = msg.get("content", [])
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
            text = " ".join(text_parts)
        else:
            continue
        
        if not text or len(text) < 10:
            continue
        
        # Skip tool calls and system messages
        if text.startswith("<") or "function_calls" in text.lower():
            continue
        
        # Log the assistant message
        log_entry = {
            "ts": entry.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            "agent": "elliot",
            "sender": "Elliot",
            "text": text[:2000],
            "chat_id": BOARDROOM_CHAT_ID,
            "source": "transcript"
        }
        
        append_to_log(log_entry)
        print(f"[SYNC] Elliot: {text[:60]}...")
    
    last_processed_line[path_str] = len(lines)


def get_most_recent_transcript() -> Path:
    """Find the most recently modified transcript file."""
    if not SESSIONS_DIR.exists():
        return None
    
    transcripts = list(SESSIONS_DIR.glob("*.jsonl"))
    if not transcripts:
        return None
    
    return max(transcripts, key=lambda p: p.stat().st_mtime)


class TranscriptHandler(FileSystemEventHandler):
    """Handle transcript file changes."""
    
    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith('.jsonl'):
            return
        
        extract_assistant_messages(Path(event.src_path))


def main():
    """Start the transcript sync service."""
    print("Starting Transcript Sync Service...")
    print(f"Watching: {SESSIONS_DIR}")
    print(f"Logging to: {SHARED_LOG_PATH}")
    
    # Initial sync of the most recent transcript
    recent = get_most_recent_transcript()
    if recent:
        print(f"Initial sync from: {recent.name}")
        extract_assistant_messages(recent)
    
    # Watch for changes
    observer = Observer()
    observer.schedule(TranscriptHandler(), str(SESSIONS_DIR), recursive=False)
    observer.start()
    
    print("Sync service running...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        observer.stop()
    
    observer.join()


if __name__ == "__main__":
    main()
