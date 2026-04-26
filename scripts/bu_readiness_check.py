"""
M10 — BU readiness threshold instrumentation.

Measures the four sellable thresholds documented in the Manual:
  - Coverage   ≥ 40% of TARGET_BU_SIZE (default 50,000 BU rows)
  - Verified   ≥ 55% of dm_email rows have dm_email_verified=true
  - Outcomes   ≥ 500 rows in cis_outreach_outcomes
  - Trajectory ≥ 30% month-over-month BU growth rate

Usage:
    python3 scripts/bu_readiness_check.py            # human output
    python3 scripts/bu_readiness_check.py --json     # machine-readable

Exit codes:
    0  — all four thresholds met
    1  — at least one threshold failed
    3  — DB unavailable

Designed to run as a daily cron AND on-demand. Same query path is reused
by src/api/routes/bu_readiness.py so the dashboard widget and the cron
report stay in sync.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict, dataclass

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, REPO_ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv("/home/elliotbot/.config/agency-os/.env")

import asyncpg  # noqa: E402

from src.config.settings import settings  # noqa: E402

# ── Thresholds (canonical Manual values) ───────────────────────────────────
TARGET_BU_SIZE                = 50_000   # 100% coverage target
COVERAGE_THRESHOLD_PCT        = 40.0
VERIFIED_THRESHOLD_PCT        = 55.0
OUTCOMES_THRESHOLD_COUNT      = 500
TRAJECTORY_THRESHOLD_PCT      = 30.0
TRAJECTORY_LOOKBACK_DAYS      = 30


@dataclass
class Metric:
    name: str
    value: float           # the measured value (% or count)
    unit: str              # 'pct' | 'count'
    threshold: float
    pass_: bool            # alias for `pass` (Python keyword)
    detail: str            # human-readable context

    def to_dict(self) -> dict:
        d = asdict(self)
        d["pass"] = d.pop("pass_")
        return d


@dataclass
class ReadinessReport:
    metrics: list[Metric]
    overall_pass: bool

    def to_dict(self) -> dict:
        return {
            "metrics":      [m.to_dict() for m in self.metrics],
            "overall_pass": self.overall_pass,
        }


# ── Query helpers ──────────────────────────────────────────────────────────

async def measure_coverage(conn) -> Metric:
    n = await conn.fetchval("SELECT COUNT(*) FROM business_universe")
    pct = (n / TARGET_BU_SIZE) * 100 if TARGET_BU_SIZE > 0 else 0.0
    return Metric(
        name="coverage",
        value=round(pct, 2),
        unit="pct",
        threshold=COVERAGE_THRESHOLD_PCT,
        pass_=pct >= COVERAGE_THRESHOLD_PCT,
        detail=f"{n:,} of {TARGET_BU_SIZE:,} BU rows",
    )


async def measure_verified(conn) -> Metric:
    row = await conn.fetchrow(
        """
        SELECT
          COUNT(*) FILTER (WHERE dm_email IS NOT NULL)               AS with_email,
          COUNT(*) FILTER (WHERE dm_email_verified = TRUE)           AS verified
        FROM business_universe
        """,
    )
    with_email = int(row["with_email"] or 0)
    verified   = int(row["verified"] or 0)
    pct = (verified / with_email * 100) if with_email > 0 else 0.0
    return Metric(
        name="verified",
        value=round(pct, 2),
        unit="pct",
        threshold=VERIFIED_THRESHOLD_PCT,
        pass_=pct >= VERIFIED_THRESHOLD_PCT,
        detail=f"{verified:,} of {with_email:,} dm_email rows verified",
    )


async def measure_outcomes(conn) -> Metric:
    try:
        n = await conn.fetchval("SELECT COUNT(*) FROM cis_outreach_outcomes")
    except Exception:  # noqa: BLE001
        n = 0
    return Metric(
        name="outcomes",
        value=float(n),
        unit="count",
        threshold=OUTCOMES_THRESHOLD_COUNT,
        pass_=n >= OUTCOMES_THRESHOLD_COUNT,
        detail=f"{n:,} cis_outreach_outcomes rows",
    )


async def measure_trajectory(conn) -> Metric:
    """Month-over-month BU growth rate.
    Numerator   = rows created in the last LOOKBACK_DAYS.
    Denominator = rows that existed BEFORE that lookback window.
    """
    row = await conn.fetchrow(
        f"""
        SELECT
          COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '{TRAJECTORY_LOOKBACK_DAYS} days')
                          AS new_rows,
          COUNT(*) FILTER (WHERE created_at <  NOW() - INTERVAL '{TRAJECTORY_LOOKBACK_DAYS} days')
                          AS pre_rows
        FROM business_universe
        """,
    )
    new_rows = int(row["new_rows"] or 0)
    pre_rows = int(row["pre_rows"] or 0)
    pct = (new_rows / pre_rows * 100) if pre_rows > 0 else 0.0
    return Metric(
        name="trajectory",
        value=round(pct, 2),
        unit="pct",
        threshold=TRAJECTORY_THRESHOLD_PCT,
        pass_=pct >= TRAJECTORY_THRESHOLD_PCT,
        detail=f"{new_rows:,} new in last {TRAJECTORY_LOOKBACK_DAYS}d / {pre_rows:,} pre-window",
    )


async def gather_metrics(conn) -> ReadinessReport:
    metrics = [
        await measure_coverage(conn),
        await measure_verified(conn),
        await measure_outcomes(conn),
        await measure_trajectory(conn),
    ]
    return ReadinessReport(
        metrics=metrics,
        overall_pass=all(m.pass_ for m in metrics),
    )


# ── Output ─────────────────────────────────────────────────────────────────

def render_human(report: ReadinessReport) -> str:
    lines = [
        "=" * 64,
        "BU Readiness Check",
        "=" * 64,
    ]
    for m in report.metrics:
        flag = "✓" if m.pass_ else "✗"
        unit = "%" if m.unit == "pct" else ""
        thr_unit = "%" if m.unit == "pct" else ""
        lines.append(
            f"  {flag} {m.name:<11} {m.value:>10.2f}{unit:<2} "
            f"(threshold ≥ {m.threshold:.0f}{thr_unit})  {m.detail}"
        )
    lines.append("-" * 64)
    lines.append(f"  Overall:    {'PASS' if report.overall_pass else 'FAIL'}")
    return "\n".join(lines)


# ── Entry-point ────────────────────────────────────────────────────────────

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

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(render_human(report))

    return 0 if report.overall_pass else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
