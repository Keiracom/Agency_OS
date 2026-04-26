"""
M10 — Tests for scripts/bu_readiness_check.py.

Pure mocks — no Supabase. Confirms the four metric calculators produce
the right pass/fail verdict against the documented thresholds.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "bu_readiness_check.py"
_spec = importlib.util.spec_from_file_location("bu_readiness_check", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
# Register BEFORE exec_module so dataclass field type resolution can find
# the module via sys.modules during class body evaluation.
sys.modules["bu_readiness_check"] = mod
_spec.loader.exec_module(mod)


def _conn(scalar_returns: list, fetchrow_returns: list):
    """asyncpg conn stub — scalar/fetchrow each pop the next scripted value."""
    sc = iter(scalar_returns)
    fr = iter(fetchrow_returns)
    c = MagicMock()
    c.fetchval = AsyncMock(side_effect=lambda *_a, **_k: next(sc))
    c.fetchrow = AsyncMock(side_effect=lambda *_a, **_k: next(fr))
    return c


# ─── coverage ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_coverage_passes_at_threshold():
    # 40% of 50,000 = 20,000 — exactly at threshold should PASS (>=)
    conn = _conn(scalar_returns=[20_000], fetchrow_returns=[])
    m = await mod.measure_coverage(conn)
    assert m.name == "coverage"
    assert m.value == 40.0
    assert m.pass_ is True


@pytest.mark.asyncio
async def test_coverage_fails_below_threshold():
    conn = _conn(scalar_returns=[15_000], fetchrow_returns=[])
    m = await mod.measure_coverage(conn)
    assert m.value == 30.0
    assert m.pass_ is False


# ─── verified ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verified_pct_calculation():
    # 55 of 100 = 55% — at threshold, PASS
    conn = _conn(scalar_returns=[],
                 fetchrow_returns=[{"with_email": 100, "verified": 55}])
    m = await mod.measure_verified(conn)
    assert m.value == 55.0
    assert m.pass_ is True


@pytest.mark.asyncio
async def test_verified_zero_email_is_zero_pct_not_div_zero():
    conn = _conn(scalar_returns=[],
                 fetchrow_returns=[{"with_email": 0, "verified": 0}])
    m = await mod.measure_verified(conn)
    assert m.value == 0.0
    assert m.pass_ is False


# ─── outcomes ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_outcomes_passes_at_500():
    conn = _conn(scalar_returns=[500], fetchrow_returns=[])
    m = await mod.measure_outcomes(conn)
    assert m.value == 500.0
    assert m.pass_ is True


@pytest.mark.asyncio
async def test_outcomes_handles_missing_table():
    """If cis_outreach_outcomes doesn't exist (dev), report 0 and FAIL
    rather than crash."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(side_effect=RuntimeError("relation missing"))
    m = await mod.measure_outcomes(conn)
    assert m.value == 0
    assert m.pass_ is False


# ─── trajectory ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trajectory_pct():
    # 30 new / 100 pre = 30% — at threshold, PASS
    conn = _conn(scalar_returns=[],
                 fetchrow_returns=[{"new_rows": 30, "pre_rows": 100}])
    m = await mod.measure_trajectory(conn)
    assert m.value == 30.0
    assert m.pass_ is True


@pytest.mark.asyncio
async def test_trajectory_pre_zero_is_zero_pct_not_div_zero():
    conn = _conn(scalar_returns=[],
                 fetchrow_returns=[{"new_rows": 0, "pre_rows": 0}])
    m = await mod.measure_trajectory(conn)
    assert m.value == 0.0
    assert m.pass_ is False


# ─── render + roll-up ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gather_metrics_overall_pass_requires_all_four():
    """gather_metrics aggregates four measure_* calls. Overall pass only
    when every metric passes."""
    fetchval_returns = iter([20_000, 500])  # coverage, outcomes
    fetchrow_returns = iter([
        {"with_email": 100, "verified": 60},   # verified — PASS
        {"new_rows": 30, "pre_rows": 100},     # trajectory — PASS (= threshold)
    ])
    conn = MagicMock()
    conn.fetchval = AsyncMock(side_effect=lambda *a, **k: next(fetchval_returns))
    conn.fetchrow = AsyncMock(side_effect=lambda *a, **k: next(fetchrow_returns))

    report = await mod.gather_metrics(conn)
    assert report.overall_pass is True
    assert len(report.metrics) == 4


def test_render_human_includes_pass_fail_marker():
    metrics = [
        mod.Metric(name="coverage",   value=42, unit="pct",   threshold=40, pass_=True,  detail="d"),
        mod.Metric(name="verified",   value=10, unit="pct",   threshold=55, pass_=False, detail="d"),
        mod.Metric(name="outcomes",   value=100, unit="count", threshold=500, pass_=False, detail="d"),
        mod.Metric(name="trajectory", value=33, unit="pct",   threshold=30, pass_=True,  detail="d"),
    ]
    report = mod.ReadinessReport(metrics=metrics, overall_pass=False)
    out = mod.render_human(report)
    assert "✓ coverage" in out
    assert "✗ verified" in out
    assert "FAIL" in out


def test_metric_to_dict_renames_pass_field():
    m = mod.Metric(name="x", value=1, unit="pct", threshold=1, pass_=True, detail="d")
    d = m.to_dict()
    assert "pass" in d
    assert "pass_" not in d
    assert d["pass"] is True


def test_report_to_dict_serializes_to_json():
    """JSON serialization of the report must succeed (used by --json)."""
    metrics = [mod.Metric(name="x", value=1, unit="pct", threshold=1,
                          pass_=True, detail="d")]
    report = mod.ReadinessReport(metrics=metrics, overall_pass=True)
    s = json.dumps(report.to_dict())
    parsed = json.loads(s)
    assert parsed["overall_pass"] is True
    assert parsed["metrics"][0]["pass"] is True
