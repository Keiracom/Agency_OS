"""
M10 — Tests for the BU readiness threshold lib.

Now imports the shared lib at src/services/bu_readiness.py (M10-1).
Pure mocks — no Supabase. Confirms the four metric calculators produce
the right pass/fail verdict against the documented thresholds.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services import bu_readiness as mod


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


@pytest.mark.asyncio
async def test_coverage_uses_settings_target_bu_size(monkeypatch):
    """M10-2 — Coverage denominator must come from settings.TARGET_BU_SIZE."""
    from src.config.settings import settings as _s
    monkeypatch.setattr(_s, "TARGET_BU_SIZE", 10_000)
    # 4,000 of 10,000 = 40% — passes
    conn = _conn(scalar_returns=[4_000], fetchrow_returns=[])
    m = await mod.measure_coverage(conn)
    assert m.value == 40.0
    assert m.pass_ is True
    assert "10,000 BU rows" in m.detail


# ─── verified ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verified_pct_calculation():
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
async def test_outcomes_logs_when_table_missing(caplog):
    """M10-3 — DB error must be logged via logger.error, not silently
    swallowed. measure_outcomes still returns 0/FAIL so the report is
    well-formed."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(side_effect=RuntimeError("relation missing"))
    with caplog.at_level("ERROR", logger="src.services.bu_readiness"):
        m = await mod.measure_outcomes(conn)
    assert m.value == 0
    assert m.pass_ is False
    assert any("measure_outcomes" in r.message for r in caplog.records)


# ─── trajectory ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trajectory_uses_standard_mom_window():
    """M10-4 — numerator = last 30d, denominator = 30-60d-ago window
    (standard MoM), NOT total pre-window."""
    conn = _conn(scalar_returns=[],
                 fetchrow_returns=[{"new_rows": 30, "prev_rows": 100}])
    m = await mod.measure_trajectory(conn)
    assert m.value == 30.0
    assert m.pass_ is True
    # The detail string should reference both windows clearly
    assert "30d" in m.detail
    assert "30-60d ago" in m.detail


@pytest.mark.asyncio
async def test_trajectory_pre_zero_is_zero_pct_not_div_zero():
    conn = _conn(scalar_returns=[],
                 fetchrow_returns=[{"new_rows": 0, "prev_rows": 0}])
    m = await mod.measure_trajectory(conn)
    assert m.value == 0.0
    assert m.pass_ is False


# ─── render + roll-up ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gather_metrics_overall_pass_requires_all_four():
    fetchval_returns = iter([20_000, 500])
    fetchrow_returns = iter([
        {"with_email": 100, "verified": 60},
        {"new_rows": 30, "prev_rows": 100},
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
    metrics = [mod.Metric(name="x", value=1, unit="pct", threshold=1,
                          pass_=True, detail="d")]
    report = mod.ReadinessReport(metrics=metrics, overall_pass=True)
    s = json.dumps(report.to_dict())
    parsed = json.loads(s)
    assert parsed["overall_pass"] is True
    assert parsed["metrics"][0]["pass"] is True
