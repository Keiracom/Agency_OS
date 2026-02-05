#!/usr/bin/env python3
"""
Quick helper to log Elliot's message to the shared Boardroom context.
Called via: python log_elliot.py "message text"
"""

import sys
import json
import fcntl
from datetime import datetime
from pathlib import Path

SHARED_LOG_PATH = Path("/home/elliotbot/clawd/data/boardroom_chat.jsonl")
BOARDROOM_CHAT_ID = -5240078568


def main():
    if len(sys.argv) < 2:
        print("Usage: python log_elliot.py 'message text'")
        sys.exit(1)
    
    message = " ".join(sys.argv[1:])
    
    # Ensure log exists
    SHARED_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "agent": "elliot",
        "sender": "Elliot",
        "text": message[:2000],
        "chat_id": BOARDROOM_CHAT_ID
    }
    
    with open(SHARED_LOG_PATH, "a") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(json.dumps(entry) + "\n")
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    print(f"Logged: {message[:50]}...")


if __name__ == "__main__":
    main()
