"""
FILE: src/memory/ratelimit.py
PURPOSE: Daily (UTC) write counter for agent_memories.
         File-backed at /tmp/agent-memory-writes-YYYYMMDD.count.
         Env MEMORY_WRITE_CAP (default 5000).
         check_and_increment() raises RateLimitExceeded if at cap.
"""

import os
from datetime import datetime, timezone

from .types import RateLimitExceeded

_COUNT_DIR = "/tmp"
_COUNT_PREFIX = "agent-memory-writes-"
DEFAULT_CAP = 5000


def _count_file() -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return os.path.join(_COUNT_DIR, f"{_COUNT_PREFIX}{date_str}.count")


def _read_count(path: str) -> int:
    try:
        with open(path) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def _write_count(path: str, count: int) -> None:
    with open(path, "w") as f:
        f.write(str(count))


def check_and_increment() -> int:
    """Read current count; raise RateLimitExceeded if at cap; else increment and return new count."""
    cap = int(os.environ.get("MEMORY_WRITE_CAP", DEFAULT_CAP))
    path = _count_file()
    current = _read_count(path)
    if current >= cap:
        raise RateLimitExceeded(
            f"Daily memory write cap ({cap}) reached. Resets at UTC midnight."
        )
    new_count = current + 1
    _write_count(path, new_count)
    return new_count


def current_count() -> int:
    """Return today's write count without incrementing."""
    return _read_count(_count_file())
