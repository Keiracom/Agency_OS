"""cache_baseline_48h.py unit tests — Phase A7 sub-task 5."""

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "cache_baseline_48h.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("cache_baseline_48h", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_classify_valkey_blocking_below_10pct():
    m = _load_module()
    assert "BLOCKING-V1" in m._classify_valkey(0.05)
    assert "BLOCKING-V1" in m._classify_valkey(0.09)


def test_classify_valkey_track_band():
    m = _load_module()
    assert "TRACK-AND-IMPROVE" in m._classify_valkey(0.20)
    assert "TRACK-AND-IMPROVE" in m._classify_valkey(0.39)


def test_classify_valkey_healthy_at_or_above_40pct():
    m = _load_module()
    assert m._classify_valkey(0.40) == "HEALTHY"
    assert m._classify_valkey(0.99) == "HEALTHY"


def test_classify_anthropic_track_below_20pct():
    m = _load_module()
    assert "TRACK-AND-IMPROVE" in m._classify_anthropic(0.10)
    assert "TRACK-AND-IMPROVE" in m._classify_anthropic(0.19)


def test_classify_anthropic_healthy_at_50pct():
    m = _load_module()
    assert m._classify_anthropic(0.50) == "HEALTHY"
    assert m._classify_anthropic(0.99) == "HEALTHY"


def test_safe_divide_zero_denominator():
    m = _load_module()
    assert m._safe_divide(10, 0) == 0.0
    assert m._safe_divide(10, 5) == 2.0


def test_generate_report_includes_hit_rate():
    m = _load_module()

    def fake_fetcher(metric, tags, start, end):
        if metric == "keiracom.cache.valkey.lookup":
            return {"hit": 600, "miss": 400}
        return {"create": 100, "read": 600, "standard": 300}

    end = datetime.now(UTC)
    start = end - timedelta(hours=48)
    report = m.generate_report(
        tenant_id="t1",
        window_start=start,
        window_end=end,
        metrics_fetcher=fake_fetcher,
    )
    assert "60.0%" in report  # valkey hit rate 600 / 1000
    assert "60.0%" in report  # anthropic read 600 / 1000
    assert "HEALTHY" in report
    assert "t1" in report


def test_generate_report_blocking_classification():
    m = _load_module()

    def low_hit_fetcher(metric, tags, start, end):
        if metric == "keiracom.cache.valkey.lookup":
            return {"hit": 5, "miss": 95}
        return {"create": 0, "read": 0, "standard": 100}

    end = datetime.now(UTC)
    start = end - timedelta(hours=48)
    report = m.generate_report(
        tenant_id="t1",
        window_start=start,
        window_end=end,
        metrics_fetcher=low_hit_fetcher,
    )
    assert "BLOCKING-V1" in report


def test_generate_report_zero_traffic_safe():
    """No lookups during window — report shouldn't divide-by-zero."""
    m = _load_module()

    def empty_fetcher(metric, tags, start, end):
        return {}

    end = datetime.now(UTC)
    start = end - timedelta(hours=48)
    report = m.generate_report(
        tenant_id="t1",
        window_start=start,
        window_end=end,
        metrics_fetcher=empty_fetcher,
    )
    assert "0.0%" in report
    assert "BLOCKING-V1" in report  # 0% hit rate triggers blocking


def test_placeholder_fetcher_returns_zeros():
    m = _load_module()
    result = m._placeholder_fetcher()
    assert result == {"hit": 0, "miss": 0, "create": 0, "read": 0, "standard": 0}
