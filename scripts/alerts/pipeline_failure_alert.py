#!/usr/bin/env python3
"""Alert on permanent_* filter_reason spikes in business_universe (last 1h)."""

from __future__ import annotations

import asyncio
import os
import sys

import asyncpg

THRESHOLD = int(os.environ.get("PIPELINE_FAIL_THRESHOLD", "5"))
WINDOW_HOURS = int(os.environ.get("PIPELINE_FAIL_WINDOW_HOURS", "1"))


async def main() -> int:
    dsn = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not dsn:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 1
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        rows = await conn.fetch(
            """SELECT filter_reason, COUNT(*) AS n FROM business_universe
               WHERE updated_at > NOW() - ($1 * INTERVAL '1 hour')
                 AND filter_reason LIKE 'permanent_%'
               GROUP BY filter_reason ORDER BY n DESC""",
            WINDOW_HOURS,
        )
    finally:
        await conn.close()
    spikes = [(r["filter_reason"], r["n"]) for r in rows if r["n"] >= THRESHOLD]
    if not spikes:
        print(f"OK: no permanent_* spikes >= {THRESHOLD} in last {WINDOW_HOURS}h")
        return 0
    parts = ", ".join(f"{r}={n}" for r, n in spikes)
    msg = f"[ELLIOT] ⚠️ pipeline failures (last {WINDOW_HOURS}h): {parts}"
    proc = await asyncio.create_subprocess_exec("tg", "-g", msg)
    await proc.wait()
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
