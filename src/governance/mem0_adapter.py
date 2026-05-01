"""
FILE: src/governance/mem0_adapter.py
PURPOSE: Mem0 integration adapter — wraps official mem0 SDK with cap tracking,
         JSONL usage logging, and monthly rollup. Phase 1 Track C2.
"""

import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MEM0_USAGE_LOG = "/home/elliotbot/clawd/logs/mem0-usage.jsonl"
FREE_TIER_ADD_CAP = 10_000
FREE_TIER_SEARCH_CAP = 1_000
WARN_ADD_THRESHOLD = 8_000   # 80% of add cap
WARN_SEARCH_THRESHOLD = 800  # 80% of search cap


def _append_usage(op: str, callsign: str, count: int = 1) -> None:
    """Append one usage event to JSONL log. Best-effort, never raises."""
    try:
        os.makedirs(os.path.dirname(MEM0_USAGE_LOG), exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "op": op,
            "callsign": callsign,
            "count": count,
        }
        with open(MEM0_USAGE_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning(f"[mem0-adapter] usage log write failed: {exc}")


def get_monthly_usage(period: str | None = None) -> dict:
    """Read JSONL and return cumulative counts for the given YYYY-MM period.

    Defaults to current month. Returns {adds, searches, period}.
    """
    if period is None:
        period = datetime.now(timezone.utc).strftime("%Y-%m")
    adds = searches = 0
    try:
        with open(MEM0_USAGE_LOG, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("ts", "").startswith(period):
                        if entry.get("op") == "add":
                            adds += entry.get("count", 1)
                        elif entry.get("op") == "search":
                            searches += entry.get("count", 1)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    except Exception as exc:
        logger.warning(f"[mem0-adapter] get_monthly_usage failed: {exc}")
    return {"adds": adds, "searches": searches, "period": period}


def _check_caps(op: str) -> None:
    """Log cap warnings if approaching free-tier limits. Never raises."""
    usage = get_monthly_usage()
    if op == "add" and usage["adds"] >= WARN_ADD_THRESHOLD:
        logger.warning(
            f"[mem0-adapter] CAP WARNING: {usage['adds']}/{FREE_TIER_ADD_CAP} adds used "
            f"this month ({usage['period']}) — approaching free-tier limit"
        )
    elif op == "search" and usage["searches"] >= WARN_SEARCH_THRESHOLD:
        logger.warning(
            f"[mem0-adapter] CAP WARNING: {usage['searches']}/{FREE_TIER_SEARCH_CAP} searches used "
            f"this month ({usage['period']}) — approaching free-tier limit"
        )


class Mem0Adapter:
    """Wraps the official mem0 Python SDK with usage tracking and cap warnings."""

    def __init__(self) -> None:
        api_key = os.environ.get("MEM0_API_KEY")
        if not api_key:
            raise OSError(
                "MEM0_API_KEY env var is not set. "
                "Set it to your Mem0 API key before using Mem0Adapter."
            )
        try:
            from mem0 import MemoryClient
            self._client = MemoryClient(api_key=api_key)
        except ImportError as exc:
            raise ImportError(
                "mem0ai package not installed. Run: pip install 'mem0ai>=0.1.0'"
            ) from exc

    def add(
        self,
        content: str,
        metadata: dict | None = None,
        callsign: str = "unknown",
        source_type: str = "daily_log",
    ) -> dict:
        """Write a memory to Mem0. Returns API response dict.

        D4 fix: explicit error logging on Mem0 API failure (was fire-and-forget).
        Failures re-raise after logging; usage event only on success.
        """
        _check_caps("add")
        messages = [{"role": "user", "content": content}]
        try:
            result = self._client.add(
                messages,
                user_id=callsign,
                metadata={**(metadata or {}), "source_type": source_type},
            )
        except Exception as exc:
            logger.error(
                "[mem0-adapter] add() failed callsign=%s source_type=%s: %s",
                callsign, source_type, exc,
            )
            raise
        _append_usage("add", callsign)
        return result

    def search(
        self,
        query: str,
        limit: int = 5,
        callsign: str = "unknown",
    ) -> list[dict]:
        """Search Mem0 for memories relevant to query. Returns list of result dicts.

        D4 fix: explicit error logging on Mem0 API failure.
        """
        _check_caps("search")
        try:
            results = self._client.search(query, user_id=callsign, limit=limit)
        except Exception as exc:
            logger.error(
                "[mem0-adapter] search() failed callsign=%s query=%r: %s",
                callsign, query[:80], exc,
            )
            raise
        _append_usage("search", callsign)
        return results if isinstance(results, list) else []

    def delete(self, memory_id: str) -> dict:
        """Delete a memory by ID. Returns API response.

        D4 fix: explicit error logging on Mem0 API failure.
        """
        try:
            return self._client.delete(memory_id)
        except Exception as exc:
            logger.error(
                "[mem0-adapter] delete() failed memory_id=%s: %s", memory_id, exc,
            )
            raise

    def update(self, memory_id: str, content: str) -> dict:
        """Update memory content by ID. Returns API response.

        D4 fix: explicit error logging on Mem0 API failure.
        """
        try:
            return self._client.update(memory_id, content)
        except Exception as exc:
            logger.error(
                "[mem0-adapter] update() failed memory_id=%s: %s", memory_id, exc,
            )
            raise
