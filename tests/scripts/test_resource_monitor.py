"""Unit tests for scripts/orchestrator/resource_monitor.py (KEI-56)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

import pytest

from scripts.orchestrator import resource_monitor as rm

# /proc/meminfo parsing ─────────────────────────────────────────────────────


def test_read_meminfo_parses_kb(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_text = (
        "MemTotal:       16000000 kB\n"
        "MemFree:         4000000 kB\n"
        "MemAvailable:    8000000 kB\n"
        "Cached:          2000000 kB\n"
    )

    class FakePath:
        def __init__(self, *_a: object, **_kw: object) -> None: ...

        def read_text(self) -> str:
            return fake_text

    monkeypatch.setattr(rm, "Path", FakePath)
    info = rm._read_meminfo()
    # 16,000,000 kB / 1024 ≈ 15625 MiB
    assert info["MemTotal"] == 15625
    assert info["MemAvailable"] == 7812


# loadavg ───────────────────────────────────────────────────────────────────


def test_read_loadavg_three_floats(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePath:
        def __init__(self, *_a: object, **_kw: object) -> None: ...

        def read_text(self) -> str:
            return "0.50 1.25 2.00 1/100 12345\n"

    monkeypatch.setattr(rm, "Path", FakePath)
    out = rm._read_loadavg()
    assert out == [0.50, 1.25, 2.00]


def test_read_loadavg_failure_returns_zeros(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePath:
        def __init__(self, *_a: object, **_kw: object) -> None: ...

        def read_text(self) -> str:
            raise OSError("nope")

    monkeypatch.setattr(rm, "Path", FakePath)
    out = rm._read_loadavg()
    assert out == [0.0, 0.0, 0.0]


# cgroup memory read ────────────────────────────────────────────────────────


def test_read_cgroup_memory_with_cap(tmp_path: Path) -> None:
    unit = tmp_path / "myunit.scope"
    unit.mkdir()
    (unit / "memory.current").write_text(str(100 * 1024 * 1024))  # 100 MiB
    (unit / "memory.max").write_text(str(2 * 1024 * 1024 * 1024))  # 2 GiB
    cur, mx = rm._read_cgroup_memory(unit)
    assert cur == 100
    assert mx == 2048


def test_read_cgroup_memory_no_cap(tmp_path: Path) -> None:
    unit = tmp_path / "uncapped.scope"
    unit.mkdir()
    (unit / "memory.current").write_text(str(50 * 1024 * 1024))
    (unit / "memory.max").write_text("max\n")
    cur, mx = rm._read_cgroup_memory(unit)
    assert cur == 50
    assert mx is None


# breach detection ──────────────────────────────────────────────────────────


def test_detect_breaches_flags_at_warn_pct() -> None:
    cgroups = {
        "weaviate.scope": {"memory_mb": 2300, "memory_max_mb": 2560, "pct_of_cap": 89.8},
        "cognee.scope": {"memory_mb": 2800, "memory_max_mb": 3072, "pct_of_cap": 91.1},
        "small.scope": {"memory_mb": 100, "memory_max_mb": 500, "pct_of_cap": 20.0},
        "uncapped.scope": {"memory_mb": 9999, "memory_max_mb": None, "pct_of_cap": None},
    }
    breaches = rm._detect_breaches(cgroups)
    # Only cognee.scope (91.1%) breached WARN_PCT=90.
    assert len(breaches) == 1
    assert breaches[0]["unit"] == "cognee.scope"
    assert breaches[0]["pct"] == pytest.approx(91.1)


def test_detect_breaches_empty_returns_empty() -> None:
    assert rm._detect_breaches({}) == []


# collect_snapshot integration ──────────────────────────────────────────────


def test_collect_snapshot_assembles_all_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rm, "_read_meminfo", lambda: {"MemTotal": 16000, "MemAvailable": 4000})
    monkeypatch.setattr(rm, "_read_loadavg", lambda: [0.5, 1.0, 1.5])
    monkeypatch.setattr(rm, "_disk_used_pct", lambda _p: 42)
    monkeypatch.setattr(
        rm,
        "_scan_cgroups",
        lambda: {"x.scope": {"memory_mb": 100, "memory_max_mb": 200, "pct_of_cap": 50.0}},
    )
    snap = rm.collect_snapshot(now=datetime(2026, 5, 14, 8, 0, tzinfo=UTC))
    assert snap["total_mb"] == 16000
    assert snap["used_mb"] == 12000  # total - available
    assert snap["free_mb"] == 4000
    assert snap["load_avg"] == [0.5, 1.0, 1.5]
    assert snap["disk_used_pct"] == 42
    assert "x.scope" in snap["cgroups"]
    assert snap["thresholds_breached"] == []
    assert snap["captured_at"].startswith("2026-05-14T08:00")


def test_collect_snapshot_includes_breach() -> None:
    with (
        mock.patch.object(rm, "_read_meminfo", return_value={"MemTotal": 16000, "MemAvailable": 1}),
        mock.patch.object(rm, "_read_loadavg", return_value=[0, 0, 0]),
        mock.patch.object(rm, "_disk_used_pct", return_value=0),
        mock.patch.object(
            rm,
            "_scan_cgroups",
            return_value={
                "hot.scope": {"memory_mb": 950, "memory_max_mb": 1000, "pct_of_cap": 95.0}
            },
        ),
    ):
        snap = rm.collect_snapshot()
    assert len(snap["thresholds_breached"]) == 1
    assert snap["thresholds_breached"][0]["unit"] == "hot.scope"


# breach-dedup state ────────────────────────────────────────────────────────


def test_post_ceo_breach_dedups_within_state() -> None:
    rm._warned_breaches.clear()
    with mock.patch.object(rm.subprocess, "run") as run_mock:
        rm._post_ceo_breach("hot.scope", 95.0, 950)
        rm._post_ceo_breach("hot.scope", 96.0, 960)  # same unit, second call
    # Slack_relay should only be invoked once (second is deduped).
    assert run_mock.call_count == 1
    rm._warned_breaches.clear()


def test_run_cycle_clears_dedup_for_resolved_breaches(monkeypatch: pytest.MonkeyPatch) -> None:
    rm._warned_breaches.clear()
    rm._warned_breaches.add("old.scope")  # imagine prior cycle warned
    monkeypatch.setattr(
        rm,
        "collect_snapshot",
        lambda: {
            "total_mb": 0,
            "used_mb": 0,
            "free_mb": 0,
            "load_avg": [],
            "disk_used_pct": 0,
            "cgroups": {},
            "thresholds_breached": [],
            "captured_at": "x",
        },
    )
    monkeypatch.setattr(rm, "_supabase_write_snapshot", lambda _s: None)
    monkeypatch.setattr(rm, "_post_ceo_breach", lambda *a, **kw: None)
    rm.run_cycle()
    # Resolved → old.scope removed.
    assert "old.scope" not in rm._warned_breaches
