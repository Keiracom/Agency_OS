"""Composition metering interpretation tests — Week 3 readiness."""

from datetime import UTC, datetime, timedelta
from typing import Any

from src.keiracom_system.atomization.metering_report import (
    ANTHROPIC_HEALTHY_THRESHOLD,
    ANTHROPIC_TRACK_THRESHOLD,
    ATOMIZER_DENSE_MIN_TOKENS_PER_ATOM,
    ATOMIZER_NOISY_MAX_TOKENS_PER_ATOM,
    CACHE_BLOCKING_THRESHOLD,
    CACHE_HEALTHY_THRESHOLD,
    VERIFIER_BLOCKING_THRESHOLD,
    VERIFIER_WARNING_THRESHOLD,
    MeteringSummary,
    classify_anthropic_cache_rate,
    classify_atomizer_grain,
    classify_composition_curve,
    classify_valkey_hit_rate,
    classify_verifier_rate,
    fetch_summary,
    generate_report,
    render_report,
)

# ---- Threshold constants lock --------------------------------------------


def test_atomizer_grain_thresholds():
    assert ATOMIZER_NOISY_MAX_TOKENS_PER_ATOM == 100.0
    assert ATOMIZER_DENSE_MIN_TOKENS_PER_ATOM == 2000.0


def test_verifier_thresholds():
    assert VERIFIER_BLOCKING_THRESHOLD == 0.10
    assert VERIFIER_WARNING_THRESHOLD == 0.30


def test_cache_thresholds_match_pr1173_baseline():
    """Cross-PR consistency: cache thresholds same as cache_baseline_48h.py."""
    assert CACHE_BLOCKING_THRESHOLD == 0.10
    assert CACHE_HEALTHY_THRESHOLD == 0.40
    assert ANTHROPIC_HEALTHY_THRESHOLD == 0.50
    assert ANTHROPIC_TRACK_THRESHOLD == 0.20


# ---- classify_atomizer_grain ---------------------------------------------


def test_classify_atomizer_grain_zero_atoms_insufficient_data():
    assert "INSUFFICIENT_DATA" in classify_atomizer_grain(1000, 0)


def test_classify_atomizer_grain_noisy_below_100_tokens_per_atom():
    # 1000 tokens / 50 atoms = 20 tokens/atom → NOISY
    out = classify_atomizer_grain(1000, 50)
    assert "ATOMIZER_NOISY" in out
    assert "too sparse" in out


def test_classify_atomizer_grain_dense_above_2000_tokens_per_atom():
    # 50000 tokens / 10 atoms = 5000 tokens/atom → DENSE
    out = classify_atomizer_grain(50000, 10)
    assert "ATOMIZER_DENSE" in out
    assert "too coarse" in out


def test_classify_atomizer_grain_healthy_band():
    # 1000 tokens / 5 atoms = 200 tokens/atom → in [100, 2000] band
    out = classify_atomizer_grain(1000, 5)
    assert out.startswith("HEALTHY")


# ---- classify_verifier_rate ----------------------------------------------


def test_classify_verifier_rate_zero_atoms_insufficient_data():
    assert "INSUFFICIENT_DATA" in classify_verifier_rate(0, 0, 0)


def test_classify_verifier_rate_blocking_when_above_10pct():
    # 15 blocking / 100 atoms = 15% > 10% threshold
    out = classify_verifier_rate(blocking=15, warning=0, total_atoms=100)
    assert "BLOCKING-V1" in out


def test_classify_verifier_rate_track_when_warning_above_30pct():
    # 5 blocking (5%, below blocking threshold) + 35 warning (35%, above warning) / 100
    out = classify_verifier_rate(blocking=5, warning=35, total_atoms=100)
    assert "TRACK-AND-IMPROVE" in out


def test_classify_verifier_rate_healthy_band():
    # Low rates in both buckets
    out = classify_verifier_rate(blocking=2, warning=10, total_atoms=100)
    assert out.startswith("HEALTHY")


# ---- classify_valkey_hit_rate (parity with PR #1173) ---------------------


def test_classify_valkey_hit_rate_zero_lookups_insufficient_data():
    assert "INSUFFICIENT_DATA" in classify_valkey_hit_rate(0, 0)


def test_classify_valkey_hit_rate_blocking_below_10pct():
    out = classify_valkey_hit_rate(hits=5, misses=95)
    assert "BLOCKING-V1" in out


def test_classify_valkey_hit_rate_track_band():
    out = classify_valkey_hit_rate(hits=20, misses=80)  # 20% hit rate
    assert "TRACK-AND-IMPROVE" in out


def test_classify_valkey_hit_rate_healthy_at_40_pct():
    out = classify_valkey_hit_rate(hits=40, misses=60)  # exactly 40%
    assert out.startswith("HEALTHY")


# ---- classify_anthropic_cache_rate ---------------------------------------


def test_classify_anthropic_cache_rate_zero_insufficient_data():
    assert "INSUFFICIENT_DATA" in classify_anthropic_cache_rate(0, 0, 0)


def test_classify_anthropic_cache_rate_below_20pct_track():
    # read 100 / total 1000 = 10%
    out = classify_anthropic_cache_rate(create=900, read=100, standard=0)
    assert "TRACK-AND-IMPROVE" in out


def test_classify_anthropic_cache_rate_marginal_band():
    # read 300 / total 1000 = 30% (between 20% and 50%)
    out = classify_anthropic_cache_rate(create=300, read=300, standard=400)
    assert "MARGINAL" in out


def test_classify_anthropic_cache_rate_healthy_at_50pct():
    out = classify_anthropic_cache_rate(create=200, read=500, standard=300)  # 50%
    assert out.startswith("HEALTHY")


# ---- classify_composition_curve ------------------------------------------


def test_classify_composition_curve_zero_insufficient_data():
    assert "INSUFFICIENT_DATA" in classify_composition_curve(0.0)


def test_classify_composition_curve_under_using():
    out = classify_composition_curve(1.0)
    assert "UNDER_USING" in out
    assert "retrieval may not be firing" in out


def test_classify_composition_curve_context_pressure():
    out = classify_composition_curve(12.0)
    assert "CONTEXT_PRESSURE" in out
    assert "context budget" in out


def test_classify_composition_curve_healthy_provisional():
    out = classify_composition_curve(5.0)
    assert "HEALTHY-PROVISIONAL" in out
    assert "calibrate" in out


# ---- fetch_summary ------------------------------------------------------


def test_fetch_summary_aggregates_all_metric_families():
    """fetch_summary calls the fetcher for each metric name + parses keys."""
    fetcher_calls: list[tuple[str, dict[str, str]]] = []

    def fake_fetcher(metric, tags, _start, _end):
        fetcher_calls.append((metric, tags))
        # Provide minimal canned responses per metric.
        canned: dict[str, dict[str, float]] = {
            "keiracom.atomization.atomizer.tokens": {"in": 500, "out": 300},
            "keiracom.atomization.atoms_produced": {"count": 10},
            "keiracom.atomization.atomizer.latency_ms": {"avg": 250.0},
            "keiracom.atomization.verifier.flags": {"info": 1, "warning": 2, "blocking": 0},
            "keiracom.cache.valkey.lookup": {"hit": 60, "miss": 40},
            "keiracom.cache.anthropic.input_tokens": {"create": 100, "read": 600, "standard": 300},
            "keiracom.atomization.compositions_per_task": {"avg": 4.5},
        }
        return canned.get(metric, {})

    end = datetime.now(UTC)
    start = end - timedelta(hours=24)
    summary = fetch_summary(
        tenant_id="t1",
        window_start=start,
        window_end=end,
        metrics_fetcher=fake_fetcher,
    )
    # Verify all 7 metric families were queried.
    queried = {m for m, _ in fetcher_calls}
    assert "keiracom.atomization.atomizer.tokens" in queried
    assert "keiracom.atomization.atoms_produced" in queried
    assert "keiracom.atomization.atomizer.latency_ms" in queried
    assert "keiracom.atomization.verifier.flags" in queried
    assert "keiracom.cache.valkey.lookup" in queried
    assert "keiracom.cache.anthropic.input_tokens" in queried
    assert "keiracom.atomization.compositions_per_task" in queried
    # Verify parsing.
    assert summary.atomizer_tokens_in == 500
    assert summary.atoms_produced == 10
    assert summary.valkey_hits == 60
    assert summary.anthropic_read_tokens == 600
    assert summary.compositions_per_task_avg == 4.5


def test_fetch_summary_handles_missing_keys_as_zero():
    """If a metric returns empty dict, the summary fields default to 0."""

    def empty_fetcher(*_a, **_kw):
        return {}

    end = datetime.now(UTC)
    summary = fetch_summary(
        tenant_id="t1",
        window_start=end - timedelta(hours=1),
        window_end=end,
        metrics_fetcher=empty_fetcher,
    )
    assert summary.atoms_produced == 0
    assert summary.valkey_hits == 0
    assert summary.compositions_per_task_avg == 0.0


# ---- render_report -------------------------------------------------------


def _make_summary(**overrides) -> MeteringSummary:
    base: dict[str, Any] = {
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "window_start": datetime(2026, 5, 26, 11, 0, tzinfo=UTC),
        "window_end": datetime(2026, 5, 27, 11, 0, tzinfo=UTC),
    }
    base.update(overrides)
    return MeteringSummary(**base)


def test_render_report_contains_all_sections():
    summary = _make_summary(
        atomizer_tokens_in=1000,
        atomizer_tokens_out=500,
        atoms_produced=10,
        atomizer_latency_ms_avg=200.0,
        verifier_flags_info=1,
        verifier_flags_warning=2,
        verifier_flags_blocking=0,
        valkey_hits=60,
        valkey_misses=40,
        anthropic_create_tokens=100,
        anthropic_read_tokens=600,
        anthropic_standard_tokens=300,
        compositions_per_task_avg=4.5,
    )
    text = render_report(summary)
    assert "Atomization Pilot — Metering Report" in text
    assert "## Atomizer" in text
    assert "## Verifier" in text
    assert "## Valkey semantic cache" in text
    assert "## Anthropic prompt cache" in text
    assert "## Composition curve" in text
    assert "## Action" in text
    assert "## Honest framing" in text


def test_render_report_shows_honest_n_equals_one_framing():
    summary = _make_summary()
    text = render_report(summary)
    assert "N=1 tenant" in text
    assert "PROVISIONAL" in text
    assert "first month of traffic" in text


def test_render_report_blocking_propagates_to_action_section():
    summary = _make_summary(
        atoms_produced=10,
        verifier_flags_blocking=5,  # 50% > 10% threshold → BLOCKING-V1
    )
    text = render_report(summary)
    assert "BLOCKING-V1" in text
    assert "pause customer onboarding" in text


def test_render_report_shows_zero_data_state():
    """Fresh tenant — N=0 atoms, N=0 cache lookups — report still renders cleanly."""
    summary = _make_summary()  # all defaults = zeros
    text = render_report(summary)
    assert "INSUFFICIENT_DATA" in text
    # Should not crash on division-by-zero anywhere.


def test_render_report_includes_window_duration():
    summary = _make_summary()
    text = render_report(summary)
    # 24-hour window per defaults (markdown bold prefix on label)
    assert "24.0 hours" in text


# ---- generate_report end-to-end ------------------------------------------


def test_generate_report_e2e():
    """End-to-end: fetcher → summary → markdown."""

    def fake_fetcher(metric, _tags, _start, _end):
        canned = {
            "keiracom.atomization.atomizer.tokens": {"in": 5000, "out": 2000},
            "keiracom.atomization.atoms_produced": {"count": 25},
            "keiracom.atomization.atomizer.latency_ms": {"avg": 300.0},
            "keiracom.atomization.verifier.flags": {"info": 2, "warning": 3, "blocking": 0},
            "keiracom.cache.valkey.lookup": {"hit": 80, "miss": 20},
            "keiracom.cache.anthropic.input_tokens": {
                "create": 500,
                "read": 1500,
                "standard": 1000,
            },
            "keiracom.atomization.compositions_per_task": {"avg": 3.5},
        }
        return canned.get(metric, {})

    now = datetime(2026, 5, 27, 11, 0, tzinfo=UTC)
    report = generate_report(
        tenant_id="dave",
        window_hours=24,
        metrics_fetcher=fake_fetcher,
        now=now,
    )
    # Markdown bold prefix on label: **Tenant:** dave
    assert "dave" in report
    assert "HEALTHY" in report  # at least one verdict should be healthy with these inputs


def test_generate_report_default_window_24h():
    """Default window_hours=24 — fetcher receives 24-hour-prior start."""
    captured_starts: list[datetime] = []

    def fake_fetcher(_metric, _tags, start, end):
        captured_starts.append(start)
        return {}

    now = datetime(2026, 5, 27, 11, 0, tzinfo=UTC)
    generate_report(tenant_id="dave", metrics_fetcher=fake_fetcher, now=now)
    # All fetcher calls used the same start (24h before now)
    assert all(s == now - timedelta(hours=24) for s in captured_starts)
