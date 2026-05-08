#!/usr/bin/env python3
"""Alert when 24h propensity pass-rate drops ≥ ANOMALY_DROP_PCT (default 30%) vs 7-day baseline."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import asyncpg

PASS = int(os.environ.get("PASS_THRESHOLD", "70"))
DROP = float(os.environ.get("ANOMALY_DROP_PCT", "30")) / 100.0
MIN_N = int(os.environ.get("ANOMALY_MIN_N", "20"))
_SQL_RATE = """SELECT COUNT(*) FILTER (WHERE propensity_score >= $1)::float AS p, COUNT(*) AS n
    FROM leads WHERE propensity_score IS NOT NULL AND {window}"""
_W_24H = "created_at > NOW() - INTERVAL '24 hours'"
_W_BASE = "created_at BETWEEN NOW() - INTERVAL '7 days' AND NOW() - INTERVAL '24 hours'"


async def _rate(conn, window_sql: str) -> tuple[float, int]:
    row = await conn.fetchrow(_SQL_RATE.format(window=window_sql), PASS)
    n = int(row["n"] or 0)
    return ((float(row["p"]) / n) if n else 0.0, n)


async def main() -> int:
    dsn = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not dsn:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 1
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        cur, n_cur = await _rate(conn, _W_24H)
        base, n_base = await _rate(conn, _W_BASE)
    finally:
        await conn.close()
    if n_cur < MIN_N or n_base < MIN_N:
        return print(f"SKIP: samples 24h={n_cur} 7d={n_base} (need {MIN_N})") or 0
    if base == 0 or (base - cur) / base < DROP:
        return print(f"OK: 24h pass={cur:.1%} vs 7d={base:.1%}") or 0
    msg = f"[ELLIOT] 📉 lead quality anomaly: 24h pass-rate {cur:.1%} vs 7d {base:.1%} (drop ≥ {DROP * 100:.0f}%, threshold≥{PASS})"
    subprocess.run(["tg", "-g", msg], check=False)
    return print(msg) or 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
