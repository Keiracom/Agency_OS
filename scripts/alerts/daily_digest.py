#!/usr/bin/env python3
"""Last-24h digest (cost, calls, BU updates, leads created) to TG group."""

from __future__ import annotations

import asyncio
import os
import sys

import asyncpg


async def main() -> int:
    dsn = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not dsn:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 1
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        cost = await conn.fetchrow(
            """SELECT COALESCE(SUM(cost_aud), 0) AS c, COUNT(*) AS n FROM sdk_usage_log
               WHERE created_at > NOW() - INTERVAL '24 hours'""",
        )
        top = await conn.fetchrow(
            """SELECT agent_type, COUNT(*) AS n FROM sdk_usage_log
               WHERE created_at > NOW() - INTERVAL '24 hours'
               GROUP BY agent_type ORDER BY n DESC LIMIT 1""",
        )
        bu_n = await conn.fetchval(
            "SELECT COUNT(*) FROM business_universe WHERE updated_at > NOW() - INTERVAL '24 hours'",
        )
        lead_n = await conn.fetchval(
            "SELECT COUNT(*) FROM leads WHERE created_at > NOW() - INTERVAL '24 hours'",
        )
    finally:
        await conn.close()
    top_s = f"{top['agent_type']}×{top['n']}" if top else "none"
    msg = (
        f"[ELLIOT] 📊 24h digest: ${float(cost['c']):.2f} AUD "
        f"({cost['n']} SDK calls, top {top_s}) | BU updates {bu_n} | leads {lead_n}"
    )
    proc = await asyncio.create_subprocess_exec("tg", "-g", msg)
    await proc.wait()
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
