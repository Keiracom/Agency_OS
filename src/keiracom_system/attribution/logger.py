"""logger.py — JSONL writer + reader for per-spawn attribution.

Cutover Blocker 6 / Cat 21 lever 27 (Dave directive 2026-05-27 via Elliot).
Every spawn traceable to its triggering source — Slack message, PR, cron,
or inbox dispatch.

Storage choice: append-only JSONL at /home/elliotbot/clawd/logs/spawn-
attribution.jsonl, same shape as the existing openai-cost.jsonl + anthropic-
cost.jsonl patterns. Cheap, parsable, no Postgres round-trip per dispatch.
Operator can promote to Postgres later if query patterns demand (see
sibling migration 20260527_keiracom_spawn_attribution.sql for the
Postgres mirror schema).

Per-event JSONL row schema:
  {
    "ts": "2026-05-27T01:23:45.678+00:00",
    "source_type": "slack" | "pr" | "cron" | "inbox" | "unknown",
    "source_id":   "<slack-ts>" | "PR-1202" | "agency-cost-rollup.timer" | "/tmp/telegram-relay-atlas/inbox/...json",
    "callsign":    "atlas",
    "model":       "claude-opus-4-7",
    "input_tokens": ..., "output_tokens": ..., "cache_read_tokens": ..., "cache_write_tokens": ...,
    "cost_usd": 0.50705
  }

ANCHORING:
- Atlas bounded-spawn baseline 2026-05-27 = $0.79 AUD/spawn (session
  78408655-...). Cost field uses Anthropic-authoritative `total_cost_usd`
  when available; otherwise back-computes from tokens + published rates.
- Cutover Readiness Gate COST-TELEMETRY: "per-task-type attribution"
  criterion (restated 2026-05-27 outbox atlas-cutover-gate-verbatim-restate).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

DEFAULT_ATTRIBUTION_LOG = Path("/home/elliotbot/clawd/logs/spawn-attribution.jsonl")

# Canonical source_type values. New types must be added intentionally —
# unknown sources at dispatch-time MUST be tagged "unknown" (not silently
# default to one of the existing types).
SOURCE_TYPES: frozenset[str] = frozenset({"slack", "pr", "cron", "inbox", "unknown"})


@dataclass(frozen=True)
class SpawnAttributionEntry:
    ts: str  # ISO-8601 UTC
    source_type: str  # one of SOURCE_TYPES
    source_id: str
    callsign: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0


class SpawnAttributionError(ValueError):
    """Raised when an attribution entry has invalid source_type."""


def log_spawn_attribution(
    *,
    source_type: str,
    source_id: str,
    callsign: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    cost_usd: float = 0.0,
    log_path: Path | None = None,
    now: datetime | None = None,
) -> SpawnAttributionEntry:
    """Append one attribution event to the JSONL log. Returns the written entry.

    `source_type` MUST be in SOURCE_TYPES (caller responsibility to tag
    dispatches at the right granularity — silently routing to "unknown" is
    a bug, not a behaviour-preserving fallback).
    """
    if source_type not in SOURCE_TYPES:
        raise SpawnAttributionError(
            f"source_type {source_type!r} not in SOURCE_TYPES {sorted(SOURCE_TYPES)}"
        )
    path = log_path or DEFAULT_ATTRIBUTION_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = (now or datetime.now(UTC)).isoformat()
    entry = SpawnAttributionEntry(
        ts=ts,
        source_type=source_type,
        source_id=source_id,
        callsign=callsign,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
        cost_usd=cost_usd,
    )
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(entry)) + "\n")
    return entry


def load_attribution_last_24h(
    *,
    hours: int = 24,
    log_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Read attribution events from the last `hours` window. Returns list of dicts."""
    path = log_path or DEFAULT_ATTRIBUTION_LOG
    if not path.exists():
        return []
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry["ts"])
                if ts < cutoff:
                    continue
                out.append(entry)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    return out


def aggregate_by_source_type(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Group attribution events by source_type. Returns {source_type: {cost_usd_sum, spawn_count}}."""
    by_source: dict[str, dict[str, float]] = {}
    for e in entries:
        st = e.get("source_type", "unknown")
        bucket = by_source.setdefault(st, {"cost_usd_sum": 0.0, "spawn_count": 0})
        bucket["cost_usd_sum"] += float(e.get("cost_usd", 0.0))
        bucket["spawn_count"] += 1
    return {
        k: {"cost_usd_sum": round(v["cost_usd_sum"], 6), "spawn_count": int(v["spawn_count"])}
        for k, v in by_source.items()
    }


def aggregate_by_callsign(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Group attribution events by callsign. Returns {callsign: {cost_usd_sum, spawn_count}}."""
    by_callsign: dict[str, dict[str, float]] = {}
    for e in entries:
        cs = e.get("callsign", "unknown")
        bucket = by_callsign.setdefault(cs, {"cost_usd_sum": 0.0, "spawn_count": 0})
        bucket["cost_usd_sum"] += float(e.get("cost_usd", 0.0))
        bucket["spawn_count"] += 1
    return {
        k: {"cost_usd_sum": round(v["cost_usd_sum"], 6), "spawn_count": int(v["spawn_count"])}
        for k, v in by_callsign.items()
    }
