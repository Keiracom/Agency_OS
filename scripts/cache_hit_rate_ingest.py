#!/usr/bin/env python3
"""cache_hit_rate_ingest.py — Cutover Blocker 9 (Agency_OS-if0r).

Scans Claude session JSONL files at:
  /home/elliotbot/.claude/projects/-home-elliotbot-clawd-Agency-OS{-<callsign>}/*.jsonl

For each assistant message with `message.usage`, sums:
  - cache_read_input_tokens   (cache hits — the GOOD path)
  - cache_creation_input_tokens (cache writes — first-fill cost)
  - input_tokens              (uncached re-read — the EXPENSIVE path)
  - output_tokens

Groups by (rollup_date, callsign), counts distinct session_uuids per group as
spawn_count, and upserts into public.keiracom_cache_hit_rates_daily.

The Supabase view public.keiracom_cache_hit_rates_v1 computes hit_rate_percent
= cache_read / (cache_read + input_tokens) * 100 at query time + the
below_threshold_80 flag for the alert script.

Per Cat 21 lever 15 RATIFIED-CEO LAUNCH-BLOCKER + Elliot dispatch 2026-05-27.

CLI:
  python3 scripts/cache_hit_rate_ingest.py                # last 7 days
  python3 scripts/cache_hit_rate_ingest.py --days 30      # last 30 days
  python3 scripts/cache_hit_rate_ingest.py --dry-run      # no DB writes
  python3 scripts/cache_hit_rate_ingest.py --json-only    # write to JSONL log + skip DB
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("cache_hit_rate_ingest")

CALLSIGNS: tuple[str, ...] = ("elliot", "aiden", "max", "atlas", "orion", "scout", "nova")

PROJECTS_ROOT = Path.home() / ".claude" / "projects"

# elliot's worktree has no suffix; the clones have -<callsign>.
ELLIOT_DIR_NAME = "-home-elliotbot-clawd-Agency-OS"
CLONE_DIR_TEMPLATE = "-home-elliotbot-clawd-Agency-OS-{callsign}"

DEFAULT_JSONL_LOG = Path("/home/elliotbot/clawd/logs/cache-hit-rate-daily.jsonl")


def projects_dir_for(callsign: str) -> Path:
    """Return the Claude projects dir for a given callsign."""
    if callsign == "elliot":
        return PROJECTS_ROOT / ELLIOT_DIR_NAME
    return PROJECTS_ROOT / CLONE_DIR_TEMPLATE.format(callsign=callsign)


def _extract_usage(line: str) -> tuple[date, dict[str, int]] | None:
    """Parse one JSONL line. Return (rollup_date, usage_dict) or None.

    Skips lines that don't carry assistant-message usage. Returns None on any
    parse error so the caller can continue iterating.
    """
    try:
        d = json.loads(line)
    except json.JSONDecodeError:
        return None
    msg = d.get("message")
    if not isinstance(msg, dict):
        return None
    usage = msg.get("usage")
    if not isinstance(usage, dict):
        return None
    # Timestamp can live at the top level or inside the message.
    ts_raw = d.get("timestamp") or msg.get("timestamp")
    if not ts_raw:
        return None
    try:
        # Claude session JSONL uses RFC3339 with Z suffix or +00:00.
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    rollup = ts.astimezone(UTC).date()
    return rollup, {
        "cache_read_input_tokens": int(usage.get("cache_read_input_tokens", 0) or 0),
        "cache_creation_input_tokens": int(usage.get("cache_creation_input_tokens", 0) or 0),
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
    }


def aggregate_callsign(callsign: str, since: date) -> dict[date, dict[str, int]]:
    """Walk one callsign's projects dir + aggregate by date.

    Returns {date: {cache_read, cache_creation, input, output, spawn_count,
    message_count}}. Files outside the since window are skipped at the
    mtime gate to keep cold scanning fast.
    """
    base = projects_dir_for(callsign)
    if not base.exists():
        logger.info("no projects dir for %s at %s — skipping", callsign, base)
        return {}
    # {date: {totals + set of session_uuids for distinct-spawn count}}
    per_date: dict[date, dict[str, Any]] = defaultdict(
        lambda: {
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "message_count": 0,
            "_session_uuids": set(),
        }
    )
    since_ts = datetime.combine(since, datetime.min.time(), tzinfo=UTC).timestamp()
    for jsonl_path in base.glob("*.jsonl"):
        try:
            if jsonl_path.stat().st_mtime < since_ts:
                continue
        except OSError:
            continue
        session_uuid = jsonl_path.stem
        try:
            with jsonl_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    extracted = _extract_usage(line)
                    if extracted is None:
                        continue
                    rollup, usage = extracted
                    if rollup < since:
                        continue
                    bucket = per_date[rollup]
                    bucket["cache_read_input_tokens"] += usage["cache_read_input_tokens"]
                    bucket["cache_creation_input_tokens"] += usage["cache_creation_input_tokens"]
                    bucket["input_tokens"] += usage["input_tokens"]
                    bucket["output_tokens"] += usage["output_tokens"]
                    bucket["message_count"] += 1
                    bucket["_session_uuids"].add(session_uuid)
        except OSError:
            logger.warning("could not read %s — skipping", jsonl_path)
            continue
    # Materialise spawn_count + drop the set.
    out: dict[date, dict[str, int]] = {}
    for d, bucket in per_date.items():
        sessions: set[str] = bucket.pop("_session_uuids")
        bucket["spawn_count"] = len(sessions)
        out[d] = bucket
    return out


def aggregate_all(callsigns: Iterable[str], since: date) -> dict[tuple[date, str], dict[str, int]]:
    """Aggregate across all callsigns. Key = (date, callsign)."""
    out: dict[tuple[date, str], dict[str, int]] = {}
    for cs in callsigns:
        per_date = aggregate_callsign(cs, since)
        for d, agg in per_date.items():
            out[(d, cs)] = agg
    return out


def _dsn() -> str | None:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def upsert_aggregates(aggregates: dict[tuple[date, str], dict[str, int]]) -> int:
    """Upsert into public.keiracom_cache_hit_rates_daily.

    Returns row count written. Raises on connection/SQL error so the systemd
    timer surfaces failures rather than silently dropping data.
    """
    if not aggregates:
        return 0
    dsn = _dsn()
    if not dsn:
        raise RuntimeError("DATABASE_URL / SUPABASE_DB_URL not set — cannot ingest")
    # Lazy import so dry-run + json-only modes don't need psycopg installed.
    import psycopg

    rows = [
        (
            d.isoformat(),
            cs,
            agg["spawn_count"],
            agg["cache_read_input_tokens"],
            agg["cache_creation_input_tokens"],
            agg["input_tokens"],
            agg["output_tokens"],
            agg["message_count"],
        )
        for (d, cs), agg in aggregates.items()
    ]
    sql = """
        INSERT INTO public.keiracom_cache_hit_rates_daily
            (rollup_date, callsign, spawn_count,
             cache_read_tokens, cache_creation_tokens,
             input_tokens, output_tokens, assistant_message_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (rollup_date, callsign) DO UPDATE SET
            spawn_count             = EXCLUDED.spawn_count,
            cache_read_tokens       = EXCLUDED.cache_read_tokens,
            cache_creation_tokens   = EXCLUDED.cache_creation_tokens,
            input_tokens            = EXCLUDED.input_tokens,
            output_tokens           = EXCLUDED.output_tokens,
            assistant_message_count = EXCLUDED.assistant_message_count;
    """
    with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute("SET LOCAL agency_os.callsign = 'dave'")
        cur.executemany(sql, rows)
        conn.commit()
    return len(rows)


def write_jsonl_log(aggregates: dict[tuple[date, str], dict[str, int]], path: Path) -> None:
    """Mirror aggregates to a JSONL log for the CEO rollup integration."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for (d, cs), agg in sorted(aggregates.items()):
            cache_read = agg["cache_read_input_tokens"]
            inp = agg["input_tokens"]
            hit_rate = (cache_read / (cache_read + inp) * 100) if (cache_read + inp) > 0 else None
            fh.write(
                json.dumps(
                    {
                        "rollup_date": d.isoformat(),
                        "callsign": cs,
                        "spawn_count": agg["spawn_count"],
                        "hit_rate_percent": round(hit_rate, 2) if hit_rate is not None else None,
                        "cache_read_tokens": cache_read,
                        "cache_creation_tokens": agg["cache_creation_input_tokens"],
                        "input_tokens": inp,
                        "output_tokens": agg["output_tokens"],
                        "assistant_message_count": agg["message_count"],
                        "ingested_at": datetime.now(UTC).isoformat(),
                    }
                )
                + "\n"
            )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--days", type=int, default=7, help="how many days back (default 7)")
    p.add_argument("--dry-run", action="store_true", help="aggregate only; no DB or log writes")
    p.add_argument("--json-only", action="store_true", help="skip DB; write to JSONL log only")
    p.add_argument("--jsonl-log", type=Path, default=DEFAULT_JSONL_LOG)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    since = datetime.now(UTC).date() - timedelta(days=args.days)
    logger.info("aggregating cache token usage since %s for %d callsigns", since, len(CALLSIGNS))
    aggregates = aggregate_all(CALLSIGNS, since)
    logger.info("aggregated %d (date,callsign) buckets", len(aggregates))

    if args.dry_run:
        for (d, cs), agg in sorted(aggregates.items()):
            cache_read = agg["cache_read_input_tokens"]
            inp = agg["input_tokens"]
            hit_rate = (cache_read / (cache_read + inp) * 100) if (cache_read + inp) > 0 else None
            hr = f"{hit_rate:.2f}%" if hit_rate is not None else "n/a"
            logger.info(
                "  %s %-7s spawns=%d msgs=%d cache_read=%d input=%d hit_rate=%s",
                d,
                cs,
                agg["spawn_count"],
                agg["message_count"],
                cache_read,
                inp,
                hr,
            )
        return 0

    if not args.json_only:
        try:
            n = upsert_aggregates(aggregates)
            logger.info("upserted %d rows into keiracom_cache_hit_rates_daily", n)
        except Exception as exc:  # noqa: BLE001
            logger.exception("upsert failed: %s", exc)
            return 1

    write_jsonl_log(aggregates, args.jsonl_log)
    logger.info("wrote JSONL log to %s", args.jsonl_log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
