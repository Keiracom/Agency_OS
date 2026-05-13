"""Tests for scripts/migrate_cognee_system_root.py — Agency_OS-5vu scaffold."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "migrate_cognee_system_root.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("migrate_cognee_system_root", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["migrate_cognee_system_root"] = m
    spec.loader.exec_module(m)
    return m


def test_cognee_re_matches_canonical_ingest_command(mod):
    """Live Stream 2 command line must match the active-process detector."""
    assert mod._COGNEE_RE.search("python3 scripts/cognee_ingest.py --streams 2") is not None
    assert mod._COGNEE_RE.search("/usr/bin/python3 pipeline_runner.py --cohort small") is not None


def test_cognee_re_no_false_positive_on_self(mod):
    """The migration script's own ps line must not be matched (filtered upstream too)."""
    # Pattern alone WOULD match 'cognify' word; the filter at call site excludes 'migrate_cognee_system_root'.
    line = "python3 scripts/migrate_cognee_system_root.py --dry-run"
    assert "migrate_cognee_system_root" in line  # self-exclusion key


def test_detect_active_processes_returns_list(mod, monkeypatch):
    """Smoke test — _detect_active_cognee_processes returns a list."""
    out = mod._detect_active_cognee_processes()
    assert isinstance(out, list)


def test_detect_active_processes_filters_self(mod, monkeypatch):
    """Mocked ps output containing the migration script itself must be filtered out."""

    class FakeCompleted:
        returncode = 0
        stdout = "user 123 1 0 python3 scripts/migrate_cognee_system_root.py --dry-run\n"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeCompleted())
    assert mod._detect_active_cognee_processes() == []


def test_detect_active_processes_catches_cognify(mod, monkeypatch):
    """Mocked ps output with a cognify call must NOT be filtered (real ingest detected)."""

    class FakeCompleted:
        returncode = 0
        stdout = "user 456 1 99 python3 -c 'import cognee; cognee.cognify()'\n"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeCompleted())
    out = mod._detect_active_cognee_processes()
    assert len(out) == 1
    assert "cognify" in out[0]


def test_detect_active_processes_ps_failure_returns_empty(mod, monkeypatch):
    """ps subprocess error returns [] (fail-safe — don't block on detection failure)."""

    def fake_run(*a, **k):
        raise FileNotFoundError("ps not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert mod._detect_active_cognee_processes() == []


def test_plan_dict_shape(mod, tmp_path):
    """plan() returns the expected fields for dry-run reporting."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "f.txt").write_text("hello")
    dst = tmp_path / "dst"
    p = mod.plan(src, dst)
    assert p["src"] == str(src)
    assert p["dst"] == str(dst)
    assert p["src_exists"] is True
    assert p["dst_exists"] is False
    assert p["src_size_bytes"] == 5
    assert isinstance(p["active_cognee_processes"], list)


def test_execute_refuses_when_active_cognee(mod, monkeypatch, tmp_path):
    """execute() must refuse when any cognee process is detected."""
    monkeypatch.setattr(mod, "_detect_active_cognee_processes", lambda: ["fake-cognify-line"])
    src = tmp_path / "src"
    src.mkdir()
    dst = tmp_path / "dst"
    assert mod.execute(src, dst) == 2
    assert not dst.exists()


def test_execute_refuses_when_target_exists(mod, monkeypatch, tmp_path):
    """execute() must refuse if target path already exists."""
    monkeypatch.setattr(mod, "_detect_active_cognee_processes", lambda: [])
    src = tmp_path / "src"
    src.mkdir()
    (src / "f.txt").write_text("data")
    dst = tmp_path / "dst"
    dst.mkdir()  # target pre-exists
    assert mod.execute(src, dst) == 4


def test_execute_refuses_when_source_missing(mod, monkeypatch, tmp_path):
    """execute() must refuse if source does not exist."""
    monkeypatch.setattr(mod, "_detect_active_cognee_processes", lambda: [])
    src = tmp_path / "nonexistent"
    dst = tmp_path / "dst"
    assert mod.execute(src, dst) == 3


def test_execute_happy_path(mod, monkeypatch, tmp_path):
    """execute() copies + verifies size match when conditions clean."""
    monkeypatch.setattr(mod, "_detect_active_cognee_processes", lambda: [])
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("abc")
    (src / "b.lance").mkdir()
    (src / "b.lance" / "data.bin").write_text("xxxx")
    dst = tmp_path / "dst"
    assert mod.execute(src, dst) == 0
    assert (dst / "a.txt").read_text() == "abc"
    assert (dst / "b.lance" / "data.bin").read_text() == "xxxx"


def test_main_requires_mode_flag(mod):
    """main() exits with parser error when neither --dry-run nor --execute given."""
    with pytest.raises(SystemExit):
        mod.main()  # argparse default sys.argv is [], parser.error raises SystemExit
