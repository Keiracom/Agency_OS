"""Tests for the physical RAM ceiling (Agency_OS-cuit)."""

from __future__ import annotations

from unittest.mock import patch

from src.dispatcher import physical_ceiling as pc

# --- _read_available_mb ---


def test_reads_available_mb_from_proc_meminfo(tmp_path):
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(
        "MemTotal:       16370196 kB\n"
        "MemFree:         2299564 kB\n"
        "MemAvailable:    4096000 kB\n"
        "Buffers:          197352 kB\n"
    )
    with patch.object(pc, "_MEMINFO_PATH", meminfo):
        assert pc._read_available_mb() == 4000  # 4096000 kB // 1024


def test_returns_none_when_meminfo_missing(tmp_path):
    with patch.object(pc, "_MEMINFO_PATH", tmp_path / "no_meminfo"):
        assert pc._read_available_mb() is None


def test_returns_none_on_malformed_meminfo(tmp_path):
    bad = tmp_path / "meminfo"
    bad.write_text("NotAMemInfoFile: garbage\n")
    with patch.object(pc, "_MEMINFO_PATH", bad):
        assert pc._read_available_mb() is None


# --- get_physical_ceiling ---


def test_explicit_env_takes_priority(monkeypatch, tmp_path):
    monkeypatch.setenv(pc._PHYSICAL_CEILING_ENV, "7")
    # Even if /proc/meminfo would give a different answer, explicit wins.
    assert pc.get_physical_ceiling() == 7


def test_explicit_env_clamped_to_at_least_1(monkeypatch):
    monkeypatch.setenv(pc._PHYSICAL_CEILING_ENV, "0")
    assert pc.get_physical_ceiling() == 1


def test_invalid_explicit_env_falls_through_to_ram(monkeypatch, tmp_path):
    monkeypatch.setenv(pc._PHYSICAL_CEILING_ENV, "not-a-number")
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemAvailable:    2048000 kB\n")  # 2000 MB
    monkeypatch.setenv(pc._AGENT_FOOTPRINT_MB_ENV, "256")
    with patch.object(pc, "_MEMINFO_PATH", meminfo):
        assert pc.get_physical_ceiling() == 7  # 2000 // 256


def test_computed_from_available_ram(monkeypatch, tmp_path):
    monkeypatch.delenv(pc._PHYSICAL_CEILING_ENV, raising=False)
    monkeypatch.setenv(pc._AGENT_FOOTPRINT_MB_ENV, "256")
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemAvailable:    1024000 kB\n")  # 1000 MB
    with patch.object(pc, "_MEMINFO_PATH", meminfo):
        assert pc.get_physical_ceiling() == 3  # 1000 // 256


def test_fallback_default_when_meminfo_missing(monkeypatch, tmp_path):
    monkeypatch.delenv(pc._PHYSICAL_CEILING_ENV, raising=False)
    with patch.object(pc, "_MEMINFO_PATH", tmp_path / "absent"):
        assert pc.get_physical_ceiling() == pc.DEFAULT_PHYSICAL_CEILING


def test_custom_footprint_env(monkeypatch, tmp_path):
    monkeypatch.delenv(pc._PHYSICAL_CEILING_ENV, raising=False)
    monkeypatch.setenv(pc._AGENT_FOOTPRINT_MB_ENV, "512")
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemAvailable:    2048000 kB\n")  # 2000 MB
    with patch.object(pc, "_MEMINFO_PATH", meminfo):
        assert pc.get_physical_ceiling() == 3  # 2000 // 512


# --- check_physical_ceiling ---


def test_admits_spawn_below_ceiling(monkeypatch):
    monkeypatch.setenv(pc._PHYSICAL_CEILING_ENV, "4")
    ok, reason = pc.check_physical_ceiling(active_count=3)
    assert ok is True
    assert reason == ""


def test_refuses_spawn_at_ceiling(monkeypatch):
    monkeypatch.setenv(pc._PHYSICAL_CEILING_ENV, "4")
    ok, reason = pc.check_physical_ceiling(active_count=4)
    assert ok is False
    assert "4/4" in reason
    assert "OOM" in reason


def test_refuses_spawn_above_ceiling(monkeypatch):
    monkeypatch.setenv(pc._PHYSICAL_CEILING_ENV, "4")
    ok, reason = pc.check_physical_ceiling(active_count=10)
    assert ok is False


def test_ceiling_of_one_admits_first_then_refuses(monkeypatch):
    monkeypatch.setenv(pc._PHYSICAL_CEILING_ENV, "1")
    ok, _ = pc.check_physical_ceiling(active_count=0)
    assert ok is True
    ok, reason = pc.check_physical_ceiling(active_count=1)
    assert ok is False
    assert "1/1" in reason


def test_reason_includes_env_hint(monkeypatch):
    monkeypatch.setenv(pc._PHYSICAL_CEILING_ENV, "2")
    _, reason = pc.check_physical_ceiling(active_count=2)
    assert pc._PHYSICAL_CEILING_ENV in reason


def test_zero_active_always_admits(monkeypatch):
    monkeypatch.setenv(pc._PHYSICAL_CEILING_ENV, "4")
    ok, _ = pc.check_physical_ceiling(active_count=0)
    assert ok is True
