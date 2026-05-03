"""Tests for BU audit gap #4 — signal decay."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.pipeline.stage_4_scoring import score_decay_factor

# ─── score_decay_factor unit tests ───────────────────────────────────────────


def test_decay_factor_none_returns_one():
    """No prior score → no decay applied."""
    assert score_decay_factor(None) == 1.0


def test_decay_factor_fresh_score():
    """Score from today → no decay."""
    now = datetime.now(UTC)
    assert score_decay_factor(now) == 1.0


def test_decay_factor_under_30_days():
    """Score 10 days ago → still fresh."""
    scored_at = datetime.now(UTC) - timedelta(days=10)
    assert score_decay_factor(scored_at) == 1.0


def test_decay_factor_45_days():
    """Score 45 days ago → 0.95 multiplier (30-90 day band)."""
    scored_at = datetime.now(UTC) - timedelta(days=45)
    assert score_decay_factor(scored_at) == 0.95


def test_decay_factor_120_days():
    """Score 120 days ago → 0.85 multiplier (90-180 day band)."""
    scored_at = datetime.now(UTC) - timedelta(days=120)
    assert score_decay_factor(scored_at) == 0.85


def test_decay_factor_200_days():
    """Score 200 days ago → 0.70 multiplier (180+ day band)."""
    scored_at = datetime.now(UTC) - timedelta(days=200)
    assert score_decay_factor(scored_at) == 0.70


def test_decay_factor_exactly_30_days():
    """Boundary: exactly 30 days → enters 0.95 band."""
    scored_at = datetime.now(UTC) - timedelta(days=30)
    assert score_decay_factor(scored_at) == 0.95


def test_decay_factor_exactly_90_days():
    """Boundary: exactly 90 days → enters 0.85 band."""
    scored_at = datetime.now(UTC) - timedelta(days=90)
    assert score_decay_factor(scored_at) == 0.85


def test_decay_factor_exactly_180_days():
    """Boundary: exactly 180 days → enters 0.70 band."""
    scored_at = datetime.now(UTC) - timedelta(days=180)
    assert score_decay_factor(scored_at) == 0.70


# ─── rescore eligibility tests ────────────────────────────────────────────────
# These test the SQL logic intent via direct condition evaluation
# (integration tests against real DB are out of scope here).


def _stage_minus1_eligible(last_rescored_at: datetime | None) -> bool:
    """Mirrors the rescore_engine stage=-1 condition."""
    if last_rescored_at is None:
        return True
    return last_rescored_at < datetime.now(UTC) - timedelta(days=30)


def _stage_passing_eligible(pipeline_stage: int, scored_at: datetime | None) -> bool:
    """Mirrors the rescore_engine stage>=4 condition (aligned to 30d decay band)."""
    if pipeline_stage < 4:
        return False
    if scored_at is None:
        return True  # NULL scored_at = never scored → eligible
    return scored_at < datetime.now(UTC) - timedelta(days=30)


def test_rescore_reject_null_last_rescored_eligible():
    """pipeline_stage=-1 with last_rescored_at NULL → eligible."""
    assert _stage_minus1_eligible(None) is True


def test_rescore_reject_stale_last_rescored_eligible():
    """pipeline_stage=-1 with last_rescored_at 40 days ago → eligible."""
    stale = datetime.now(UTC) - timedelta(days=40)
    assert _stage_minus1_eligible(stale) is True


def test_rescore_reject_recent_last_rescored_not_eligible():
    """pipeline_stage=-1 with last_rescored_at 5 days ago → NOT eligible."""
    recent = datetime.now(UTC) - timedelta(days=5)
    assert _stage_minus1_eligible(recent) is False


def test_rescore_passing_lead_stale_score_eligible():
    """pipeline_stage=5 with scored_at 35 days ago → eligible (aligned to 30d decay band)."""
    scored_at = datetime.now(UTC) - timedelta(days=35)
    assert _stage_passing_eligible(5, scored_at) is True


def test_rescore_passing_lead_null_scored_at_eligible():
    """pipeline_stage=5 with scored_at NULL → eligible (never scored)."""
    assert _stage_passing_eligible(5, None) is True


def test_rescore_passing_lead_recent_score_not_eligible():
    """pipeline_stage=5 with scored_at 10 days ago → NOT eligible (within 30d cooldown)."""
    scored_at = datetime.now(UTC) - timedelta(days=10)
    assert _stage_passing_eligible(5, scored_at) is False


def test_rescore_passing_lead_stage4_eligible():
    """pipeline_stage=4 (boundary) with stale score → eligible."""
    scored_at = datetime.now(UTC) - timedelta(days=100)
    assert _stage_passing_eligible(4, scored_at) is True


def test_rescore_passing_lead_stage3_not_eligible():
    """pipeline_stage=3 (below gate) → NOT eligible regardless of age."""
    scored_at = datetime.now(UTC) - timedelta(days=200)
    assert _stage_passing_eligible(3, scored_at) is False


# ─── decay wiring verification ──────────────────────────────────────────────


def test_rescore_row_applies_decay():
    """Verify _rescore_row calls score_decay_factor (wiring check via source inspection)."""
    import inspect

    from src.pipeline.rescore_engine import RescoreEngine

    source = inspect.getsource(RescoreEngine._rescore_row)
    assert "score_decay_factor" in source, (
        "_rescore_row must call score_decay_factor to apply time-weighted decay"
    )
    assert "decay" in source, "_rescore_row must use decay multiplier"
