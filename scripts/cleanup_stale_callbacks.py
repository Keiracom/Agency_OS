#!/usr/bin/env python3
"""cleanup_stale_callbacks.py — delete failed callbacks older than N days.

Addresses the C2 Prefect audit WARN finding (38 stale callbacks, oldest 18
days) by running a bounded DELETE. Safe-mode default: dry-run prints the
count that WOULD be deleted. Pass --execute to perform the delete.

Usage:
    python scripts/cleanup_stale_callbacks.py            # dry-run
    python scripts/cleanup_stale_callbacks.py --execute  # actual delete
    python scripts/cleanup_stale_callbacks.py --days 14  # custom age threshold

Exit 0 on success (always prints count). Exit 2 on SQL error.

Scope guards:
- Only deletes rows where status = 'failed' (successful or pending rows left alone).
- Minimum age threshold: 7 days default, --days N to adjust. Refuses 0 or negative.
- Dry-run by default. Must pass --execute explicitly to mutate the table.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path


def _load_env(env_path: str) -> None:
    if not os.path.exists(env_path):
        return
    for line in Path(env_path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


async def run(days: int, execute: bool) -> int:
    import asyncpg
    db_url = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not db_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        count_sql = (
            "SELECT COUNT(*) FROM public.evo_flow_callbacks "
            "WHERE status = 'failed' "
            f"AND created_at < NOW() - INTERVAL '{days} days'"
        )
        stale_count = await conn.fetchval(count_sql)
        print(f"stale_failed_callbacks_older_than_{days}d={stale_count}")

        if not execute:
            print("(dry-run — pass --execute to actually delete)")
            return 0

        del_sql = (
            "DELETE FROM public.evo_flow_callbacks "
            "WHERE status = 'failed' "
            f"AND created_at < NOW() - INTERVAL '{days} days'"
        )
        result = await conn.execute(del_sql)
        # asyncpg returns "DELETE N" string
        deleted = int(result.split()[-1]) if result.startswith("DELETE") else -1
        print(f"deleted={deleted}")
        return 0
    finally:
        await conn.close()


def main() -> int:
    _load_env("/home/elliotbot/.config/agency-os/.env")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.days <= 0:
        print("ERROR: --days must be positive", file=sys.stderr)
        return 2

    return asyncio.run(run(args.days, args.execute))


if __name__ == "__main__":
    sys.exit(main())
