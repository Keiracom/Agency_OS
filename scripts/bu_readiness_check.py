"""
M10 — BU readiness threshold instrumentation (CLI / cron entry-point).

Thin wrapper around src/services/bu_readiness.py so the script, the
REST endpoint, and the dashboard widget all draw from one library.

Usage:
    python3 scripts/bu_readiness_check.py            # human output
    python3 scripts/bu_readiness_check.py --json     # machine-readable

Exit codes:
    0  — all four thresholds met
    1  — at least one threshold failed
    3  — DB unavailable
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, REPO_ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv("/home/elliotbot/.config/agency-os/.env")

import asyncpg  # noqa: E402

from src.config.settings import settings  # noqa: E402
from src.services.bu_readiness import (  # noqa: E402
    gather_metrics,
    render_human,
    render_json,
)


async def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="BU readiness threshold check.")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of human output.")
    args = ap.parse_args(argv)

    try:
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn, statement_cache_size=0)
    except Exception as exc:  # noqa: BLE001
        print(f"DB unavailable: {exc}", file=sys.stderr)
        return 3

    try:
        report = await gather_metrics(conn)
    finally:
        await conn.close()

    print(render_json(report) if args.json else render_human(report))
    return 0 if report.overall_pass else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
