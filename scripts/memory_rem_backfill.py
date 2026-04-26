"""
P10 — REM Backfill (one-shot historical memory consolidation).

Companion to scripts/memory_consolidation.py (OC1 — Dreaming pattern).
The Dreaming sweep is designed for the recent window (default 30d).
This script handles the COLD STORE — every daily_log in
elliot_internal.memories that's already older than --age-threshold-days
(default 7) gets a one-time replay through the same five-factor scoring
+ promotion pipeline.

Why a separate script?
  - Dreaming is the ongoing nightly sweep — small windows, fast.
  - REM Backfill is a one-shot migration over historical data.
  - Same scoring lib (memory_consolidation) so the verdicts agree
    with what the nightly Dreaming would have produced if it had been
    running all along.
  - OC1's WHERE-NOT-EXISTS idempotency guard means rerunning the
    backfill never creates duplicate core_facts.

Usage
-----
    python3 scripts/memory_rem_backfill.py                     # dry-run preview
    python3 scripts/memory_rem_backfill.py --execute           # write
    python3 scripts/memory_rem_backfill.py --age-threshold-days 14
    python3 scripts/memory_rem_backfill.py --min-score 0.7
    python3 scripts/memory_rem_backfill.py --max-rows 5000     # cap per run

Exit codes: 0 OK · 3 DB unavailable.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, SCRIPTS_DIR)

from dotenv import load_dotenv  # noqa: E402

load_dotenv("/home/elliotbot/.config/agency-os/.env")

import asyncpg  # noqa: E402

# Reuse the OC1 lib — same scoring, same idempotent INSERT.
from memory_consolidation import (  # noqa: E402
    Memory,
    promote_to_core_fact,
    score,
)

from src.config.settings import settings  # noqa: E402

DEFAULT_AGE_THRESHOLD_DAYS = 7
DEFAULT_MIN_SCORE          = 0.6
DEFAULT_BATCH_SIZE         = 200
DEFAULT_MAX_ROWS           = 0       # 0 = unbounded


# ── DB I/O ────────────────────────────────────────────────────────────────

async def fetch_old_daily_logs(
    conn, *, age_threshold_days: int, max_rows: int,
) -> list[Memory]:
    """Pull every daily_log strictly OLDER than the age threshold,
    newest-first within the cold window. max_rows == 0 → unbounded."""
    cutoff = datetime.now(UTC) - timedelta(days=age_threshold_days)
    if max_rows > 0:
        rows = await conn.fetch(
            """
            SELECT id, content, content_hash, type, created_at, metadata
            FROM elliot_internal.memories
            WHERE deleted_at IS NULL
              AND type = 'daily_log'
              AND created_at < $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            cutoff, max_rows,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT id, content, content_hash, type, created_at, metadata
            FROM elliot_internal.memories
            WHERE deleted_at IS NULL
              AND type = 'daily_log'
              AND created_at < $1
            ORDER BY created_at DESC
            """,
            cutoff,
        )
    return [
        Memory(
            id=str(r["id"]),
            content=r["content"] or "",
            content_hash=r["content_hash"],
            type=r["type"],
            created_at=r["created_at"],
            metadata=r["metadata"] or {},
        )
        for r in rows
    ]


def _chunked(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


# ── Pipeline ──────────────────────────────────────────────────────────────

async def replay(
    conn,
    *,
    age_threshold_days: int,
    min_score: float,
    batch_size: int,
    max_rows: int,
    dry_run: bool,
) -> dict:
    cold = await fetch_old_daily_logs(
        conn,
        age_threshold_days=age_threshold_days,
        max_rows=max_rows,
    )

    promoted: list[Memory] = []
    above_threshold_total = 0

    for batch in _chunked(cold, batch_size):
        # Score the batch in isolation so frequency / consolidation factors
        # stay bounded and meaningful per-window.
        score(batch)
        for m in batch:
            if m.composite >= min_score:
                above_threshold_total += 1
                # OC1 idempotency: WHERE NOT EXISTS keyed on
                # metadata->>'consolidated_from' = m.id ensures a re-run
                # is a no-op.
                if await promote_to_core_fact(conn, m, dry_run=dry_run):
                    promoted.append(m)

    return {
        "scanned":             len(cold),
        "above_threshold":     above_threshold_total,
        "promoted":            len(promoted),
        "skipped_dup_guard":   above_threshold_total - len(promoted),
        "age_threshold_days":  age_threshold_days,
        "min_score":           min_score,
        "batch_size":          batch_size,
        "max_rows":            max_rows or "unbounded",
        "top_promotions": [
            {
                "id":        m.id,
                "composite": m.composite,
                "created":   m.created_at.date().isoformat(),
                "preview":   (m.content or "")[:120].replace("\n", " "),
            }
            for m in sorted(promoted, key=lambda x: x.composite, reverse=True)[:10]
        ],
    }


# ── Render ────────────────────────────────────────────────────────────────

def render_human(result: dict, *, dry_run: bool) -> str:
    lines = [
        "=" * 72,
        f"REM Backfill — {'DRY-RUN' if dry_run else 'EXECUTE'}",
        "=" * 72,
        f"  age threshold     : > {result['age_threshold_days']} days old",
        f"  min score         : {result['min_score']}",
        f"  batch size        : {result['batch_size']}",
        f"  max rows per run  : {result['max_rows']}",
        "",
        f"  scanned (cold daily_log):           {result['scanned']:,}",
        f"  above promotion threshold:          {result['above_threshold']:,}",
        f"  promoted (new core_fact rows):      {result['promoted']:,}",
        f"  skipped by OC1 idempotency guard:   {result['skipped_dup_guard']:,}",
    ]
    if result["top_promotions"]:
        lines.append("")
        lines.append("  Top promotions:")
        for p in result["top_promotions"]:
            lines.append(
                f"    {p['composite']:>5.3f}  {p['created']}  {p['id'][:8]}  {p['preview']}"
            )
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────

async def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P10 REM Backfill — one-shot memory migration.")
    ap.add_argument("--age-threshold-days", type=int, default=DEFAULT_AGE_THRESHOLD_DAYS,
                    help="Only replay daily_logs strictly OLDER than this (default 7).")
    ap.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE,
                    help="Composite-score threshold for promotion (default 0.6).")
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                    help="Score window size (default 200).")
    ap.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS,
                    help="Cap rows pulled per run (default 0 = unbounded).")
    ap.add_argument("--execute", action="store_true",
                    help="Apply writes. Default is dry-run.")
    args = ap.parse_args(argv)
    dry_run = not args.execute

    if args.age_threshold_days < 0:
        print("--age-threshold-days must be >= 0", file=sys.stderr)
        return 2
    if args.batch_size <= 0:
        print("--batch-size must be > 0", file=sys.stderr)
        return 2

    try:
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn, statement_cache_size=0)
    except Exception as exc:  # noqa: BLE001
        print(f"DB unavailable: {exc}", file=sys.stderr)
        return 3

    try:
        result = await replay(
            conn,
            age_threshold_days=args.age_threshold_days,
            min_score=args.min_score,
            batch_size=args.batch_size,
            max_rows=args.max_rows,
            dry_run=dry_run,
        )
    finally:
        await conn.close()

    print(render_human(result, dry_run=dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
