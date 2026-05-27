#!/usr/bin/env python3
"""cache_hit_rate_alert.py — Cutover Blocker 9 (Agency_OS-if0r).

Reads public.keiracom_cache_hit_rates_v1 + writes a structured alert line to
/home/elliotbot/clawd/logs/cache-hit-rate-alerts.jsonl for any (date, callsign)
where hit_rate_percent < 80% over the last N days (default 1).

The 80% threshold is the gate floor. The 95% target tracks the bounded-spawn
baseline anchored at Atlas 0.79 AUD per Cat 21 lever 15 RATIFIED-CEO. Anything
below 80% means the cache is doing less work than expected — most likely
cause is identity/system-prompt churn between spawns that invalidates the
cache block.

Exit codes:
  0 — no alerts fired (hit rate at or above threshold across all reported rows)
  1 — alerts fired (one or more (date, callsign) rows below threshold)
  2 — query/connection failure (operational; check supabase env + DSN)

CLI:
  python3 scripts/cache_hit_rate_alert.py                 # last 1 day
  python3 scripts/cache_hit_rate_alert.py --days 7        # last 7 days
  python3 scripts/cache_hit_rate_alert.py --threshold 90  # tighter floor
  python3 scripts/cache_hit_rate_alert.py --dry-run       # query only; no log write
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger("cache_hit_rate_alert")

DEFAULT_ALERTS_LOG = Path("/home/elliotbot/clawd/logs/cache-hit-rate-alerts.jsonl")
DEFAULT_THRESHOLD_PERCENT = 80.0


def _dsn() -> str | None:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def query_breaches(since: date, threshold_percent: float) -> list[dict]:
    """Query the view for rows below threshold since the given date.

    Returns list of dict rows; empty list means no breaches.
    """
    dsn = _dsn()
    if not dsn:
        raise RuntimeError("DATABASE_URL / SUPABASE_DB_URL not set — cannot query")
    import psycopg

    sql = """
        SELECT rollup_date, callsign, spawn_count, hit_rate_percent,
               cache_read_tokens, cache_creation_tokens, input_tokens,
               output_tokens, assistant_message_count
        FROM public.keiracom_cache_hit_rates_v1
        WHERE rollup_date >= %s
          AND hit_rate_percent IS NOT NULL
          AND hit_rate_percent < %s
        ORDER BY rollup_date DESC, callsign;
    """
    rows: list[dict] = []
    with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute(sql, (since.isoformat(), threshold_percent))
        for row in cur.fetchall():
            rows.append(
                {
                    "rollup_date": row[0].isoformat()
                    if hasattr(row[0], "isoformat")
                    else str(row[0]),
                    "callsign": row[1],
                    "spawn_count": row[2],
                    "hit_rate_percent": float(row[3]) if row[3] is not None else None,
                    "cache_read_tokens": int(row[4]),
                    "cache_creation_tokens": int(row[5]),
                    "input_tokens": int(row[6]),
                    "output_tokens": int(row[7]),
                    "assistant_message_count": int(row[8]),
                }
            )
    return rows


def write_alerts(breaches: list[dict], threshold_percent: float, path: Path) -> None:
    """Append one alert line per breach to the JSONL log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fired_at = datetime.now(UTC).isoformat()
    with path.open("a", encoding="utf-8") as fh:
        for row in breaches:
            fh.write(
                json.dumps(
                    {
                        "fired_at": fired_at,
                        "severity": "warning",
                        "kei": "Agency_OS-if0r",
                        "title": (
                            f"cache hit-rate below {threshold_percent:.0f}% for "
                            f"{row['callsign']} on {row['rollup_date']}"
                        ),
                        "rollup_date": row["rollup_date"],
                        "callsign": row["callsign"],
                        "hit_rate_percent": row["hit_rate_percent"],
                        "threshold_percent": threshold_percent,
                        "spawn_count": row["spawn_count"],
                        "cache_read_tokens": row["cache_read_tokens"],
                        "cache_creation_tokens": row["cache_creation_tokens"],
                        "input_tokens": row["input_tokens"],
                        "output_tokens": row["output_tokens"],
                        "assistant_message_count": row["assistant_message_count"],
                    }
                )
                + "\n"
            )


def format_breach_summary(breaches: list[dict], threshold_percent: float) -> str:
    """Human-readable single-line summary for stdout / CEO post."""
    if not breaches:
        return f"No callsigns below {threshold_percent:.0f}% threshold."
    lines = [f"{len(breaches)} (date, callsign) breaches of {threshold_percent:.0f}% threshold:"]
    for row in breaches:
        lines.append(
            f"  {row['rollup_date']} {row['callsign']:7s} "
            f"hit_rate={row['hit_rate_percent']:.2f}%  "
            f"spawns={row['spawn_count']}  "
            f"cache_read={row['cache_read_tokens']:>9d}  "
            f"input={row['input_tokens']:>9d}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--days", type=int, default=1, help="how many days back (default 1)")
    p.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD_PERCENT,
        help=f"alert threshold percent (default {DEFAULT_THRESHOLD_PERCENT})",
    )
    p.add_argument("--dry-run", action="store_true", help="query only; no log write")
    p.add_argument("--alerts-log", type=Path, default=DEFAULT_ALERTS_LOG)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    since = datetime.now(UTC).date() - timedelta(days=max(args.days - 1, 0))
    try:
        breaches = query_breaches(since, args.threshold)
    except Exception as exc:  # noqa: BLE001
        logger.exception("query failed: %s", exc)
        return 2

    summary = format_breach_summary(breaches, args.threshold)
    print(summary)
    if not breaches:
        return 0

    if not args.dry_run:
        write_alerts(breaches, args.threshold, args.alerts_log)
        logger.info("wrote %d alert(s) to %s", len(breaches), args.alerts_log)
    return 1


if __name__ == "__main__":
    sys.exit(main())
