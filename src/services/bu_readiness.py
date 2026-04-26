"""
M10 — BU readiness threshold calculations (shared lib).

Single source of truth for the four sellable thresholds documented in
the Manual:
  - Coverage   ≥ 40% of settings.TARGET_BU_SIZE
  - Verified   ≥ 55% of dm_email rows have dm_email_verified=true
  - Outcomes   ≥ 500 rows in cis_outreach_outcomes
  - Trajectory ≥ 30% standard month-over-month growth rate
                 (rows created last 30d / rows created 30-60d ago)

Consumers:
  - scripts/bu_readiness_check.py  (cron + CLI)
  - src/api/routes/bu_readiness.py (REST endpoint feeding the widget)

Both call gather_metrics(conn) so the cron, the dashboard, and the
REST response can never disagree on numbers.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass

from src.config.settings import settings

logger = logging.getLogger(__name__)

# ── Thresholds (canonical Manual values) ───────────────────────────────────
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


# ── Per-metric measurements ────────────────────────────────────────────────

async def measure_coverage(conn) -> Metric:
    target = max(1, int(getattr(settings, "TARGET_BU_SIZE", 50_000)))
    n = await conn.fetchval("SELECT COUNT(*) FROM business_universe")
    pct = (n / target) * 100
    return Metric(
        name="coverage",
        value=round(pct, 2),
        unit="pct",
        threshold=COVERAGE_THRESHOLD_PCT,
        pass_=pct >= COVERAGE_THRESHOLD_PCT,
        detail=f"{n:,} of {target:,} BU rows",
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
    except Exception as exc:  # noqa: BLE001
        # M10-3 — surface the failure instead of silently zeroing.
        logger.error(
            "measure_outcomes: cis_outreach_outcomes query failed (%s) — reporting 0",
            exc,
        )
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
    """Standard month-over-month BU growth rate.

    M10-4 — corrected from "last 30d / pre-30d" to the canonical MoM
    definition: rows created in the last 30 days versus rows created in
    the 30-60-day window. Both windows are equal length so the ratio is
    comparable across time and not biased by historical accumulation.
    """
    days = TRAJECTORY_LOOKBACK_DAYS
    row = await conn.fetchrow(
        f"""
        SELECT
          COUNT(*) FILTER (
            WHERE created_at >= NOW() - INTERVAL '{days} days'
          ) AS new_rows,
          COUNT(*) FILTER (
            WHERE created_at >= NOW() - INTERVAL '{2 * days} days'
              AND created_at <  NOW() - INTERVAL '{days} days'
          ) AS prev_rows
        FROM business_universe
        """,
    )
    new_rows  = int(row["new_rows"] or 0)
    prev_rows = int(row["prev_rows"] or 0)
    pct = (new_rows / prev_rows * 100) if prev_rows > 0 else 0.0
    return Metric(
        name="trajectory",
        value=round(pct, 2),
        unit="pct",
        threshold=TRAJECTORY_THRESHOLD_PCT,
        pass_=pct >= TRAJECTORY_THRESHOLD_PCT,
        detail=(
            f"{new_rows:,} created last {days}d / "
            f"{prev_rows:,} created {days}-{2 * days}d ago"
        ),
    )


# ── Roll-up ────────────────────────────────────────────────────────────────

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


# ── Convenience: human render (used by the CLI) ────────────────────────────

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


def render_json(report: ReadinessReport) -> str:
    return json.dumps(report.to_dict(), indent=2)
