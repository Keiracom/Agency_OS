#!/usr/bin/env python3
"""
Gemini Watcher - Monitors shared context for Gemini messages
and notifies Elliot via Telegram when Gemini posts something new.
"""

import json
import time
import os
import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta

# Config
SHARED_CONTEXT = Path("/home/elliotbot/clawd/data/boardroom_chat.jsonl")
STATE_FILE = Path("/home/elliotbot/clawd/data/.gemini_watcher_state")
POLL_INTERVAL = 5  # seconds
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BOARDROOM_CHAT_ID = -5240078568

def get_last_seen_ts() -> str:
    """Get the timestamp of the last message we processed."""
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip()
    return ""

def save_last_seen_ts(ts: str):
    """Save the timestamp of the last message we processed."""
    STATE_FILE.write_text(ts)

def get_new_gemini_messages(since_ts: str) -> list:
    """Get Gemini messages newer than since_ts."""
    if not SHARED_CONTEXT.exists():
        return []
    
    new_messages = []
    with open(SHARED_CONTEXT, "r") as f:
        for line in f:
            try:
                msg = json.loads(line.strip())
                if msg.get("agent") == "gemini" and msg.get("ts", "") > since_ts:
                    new_messages.append(msg)
            except json.JSONDecodeError:
                continue
    
    return new_messages

def notify_elliot(messages: list):
    """Send notification to the Boardroom that Gemini posted."""
    if not TELEGRAM_BOT_TOKEN:
        print("No TELEGRAM_BOT_TOKEN set, skipping notification")
        return
    
    # For each new Gemini message, we could notify - but let's just log for now
    # We don't want duplicate messages in the chat
    for msg in messages:
        ts = msg.get("ts", "")
        text = msg.get("text", "")[:200]
        print(f"[GEMINI {ts}] {text}")

def main():
    """Main loop - watch for Gemini messages."""
    print(f"Gemini Watcher started. Monitoring: {SHARED_CONTEXT}")
    print(f"Poll interval: {POLL_INTERVAL}s")
    
    while True:
        try:
            last_ts = get_last_seen_ts()
            new_msgs = get_new_gemini_messages(last_ts)
            
            if new_msgs:
                print(f"Found {len(new_msgs)} new Gemini message(s)")
                notify_elliot(new_msgs)
                # Update state to latest message
                latest_ts = max(m.get("ts", "") for m in new_msgs)
                save_last_seen_ts(latest_ts)
            
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print("\nWatcher stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    # One-shot mode for checking what's there
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        msgs = get_new_gemini_messages("")
        print(f"Total Gemini messages in context: {len(msgs)}")
        for m in msgs[-5:]:  # Last 5
            print(f"  [{m.get('ts')}] {m.get('text', '')[:100]}")
        sys.exit(0)
    
    main()
