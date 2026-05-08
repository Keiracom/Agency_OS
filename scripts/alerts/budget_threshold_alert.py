#!/usr/bin/env python3
"""Fires when today's sdk_usage_log cost crosses 80% (warn) / 100% (exceeded) of BUDGET_DAILY_AUD."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import asyncpg

BUDGET = float(os.environ.get("BUDGET_DAILY_AUD", "50"))


async def main() -> int:
    dsn = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not dsn:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 1
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        spent = await conn.fetchval(
            """SELECT COALESCE(SUM(cost_aud), 0) FROM sdk_usage_log
               WHERE created_at::date = CURRENT_DATE""",
        )
    finally:
        await conn.close()
    spent = float(spent or 0)
    pct = (spent / BUDGET * 100) if BUDGET > 0 else 0.0
    if spent >= BUDGET:
        emoji, label = "🚨", "EXCEEDED"
    elif pct >= 80:
        emoji, label = "⚠️", "warning"
    else:
        print(f"OK: ${spent:.2f}/${BUDGET:.2f} AUD ({pct:.0f}%)")
        return 0
    msg = (
        f"[ELLIOT] {emoji} budget {label}: ${spent:.2f}/${BUDGET:.2f} AUD ({pct:.0f}% of daily cap)"
    )
    subprocess.run(["tg", "-g", msg], check=False)
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
