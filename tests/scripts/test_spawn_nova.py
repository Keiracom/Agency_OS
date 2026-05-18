"""Tests for scripts/spawn_nova.py (KEI-185).

Verifies the spawn plan + the KEI-184 fallback behaviour. SessionManager is
mocked because KEI-184 (Orion PR #1004) has not landed yet; once it does, the
real import path resolves and `--force` works end-to-end without code change.
"""

from __future__ import annotations

import logging
import sys
import types
from unittest.mock import MagicMock

import pytest

import scripts.spawn_nova as spawn_nova


def test_plan_returns_expected_invariants():
    p = spawn_nova.plan()
    assert p.callsign == "nova"
    assert p.worktree == "/home/elliotbot/clawd/Agency_OS-nova"
    assert p.tmux_session == "nova:0"
    assert p.service == "nova-agent"


def test_spawn_dry_run_returns_zero_without_invoking_session_manager(monkeypatch, caplog):
    """Dry-run path must not import src.fleet.session_manager — the import is
    intentionally deferred so the CLI works pre-KEI-184-merge.
    """
    monkeypatch.setitem(sys.modules, "src.fleet.session_manager", None)
    with caplog.at_level(logging.INFO):
        rc = spawn_nova.spawn(dry_run=True)
    assert rc == 0
    assert any("dry-run mode" in r.message for r in caplog.records)


def test_spawn_real_call_invokes_session_manager(monkeypatch):
    """When SessionManager is importable, spawn() must instantiate it and
    call .spawn() with the plan invariants.
    """
    fake_module = types.ModuleType("src.fleet.session_manager")
    spawned: dict = {}

    class _FakeSM:
        def spawn(self, **kwargs):
            spawned.update(kwargs)

    fake_module.SessionManager = _FakeSM  # type: ignore[attr-defined]
    # Insert at all three layers needed for `from src.fleet.session_manager import SessionManager`.
    src_pkg = types.ModuleType("src")
    fleet_pkg = types.ModuleType("src.fleet")
    monkeypatch.setitem(sys.modules, "src", src_pkg)
    monkeypatch.setitem(sys.modules, "src.fleet", fleet_pkg)
    monkeypatch.setitem(sys.modules, "src.fleet.session_manager", fake_module)
    rc = spawn_nova.spawn(dry_run=False)
    assert rc == 0
    assert spawned["callsign"] == "nova"
    assert spawned["worktree"] == "/home/elliotbot/clawd/Agency_OS-nova"
    assert spawned["tmux_session"] == "nova:0"
    assert spawned["service"] == "nova-agent"


def test_spawn_returns_2_when_session_manager_not_importable(monkeypatch, caplog):
    """KEI-184 not yet merged → ImportError → exit 2 + helpful error message,
    not a stacktrace.
    """
    real_import = (
        __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__
    )

    def _fake_import(name, *args, **kwargs):
        if name == "src.fleet.session_manager":
            raise ImportError("module not found (test stub)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _fake_import)
    with caplog.at_level(logging.ERROR):
        rc = spawn_nova.spawn(dry_run=False)
    assert rc == 2
    assert any("KEI-184" in r.message for r in caplog.records)


def test_cli_main_refuses_without_dry_run_or_force():
    """The CLI default must not silently invoke SessionManager — operator
    must explicitly opt in via --dry-run or --force.
    """
    rc = spawn_nova.main([])
    assert rc == 2


def test_cli_main_dry_run_path(caplog):
    with caplog.at_level(logging.INFO):
        rc = spawn_nova.main(["--dry-run"])
    assert rc == 0
    assert any("dry-run mode" in r.message for r in caplog.records)


@pytest.mark.parametrize("flag", ["--dry-run", "--force"])
def test_cli_main_recognises_required_flags(flag, monkeypatch):
    """Both --dry-run and --force must short-circuit the refusal guard.
    --force still requires SessionManager — we stub it with a MagicMock so the
    test doesn't depend on KEI-184 landing.
    """
    src_pkg = types.ModuleType("src")
    fleet_pkg = types.ModuleType("src.fleet")
    sm_module = types.ModuleType("src.fleet.session_manager")
    sm_module.SessionManager = MagicMock()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src", src_pkg)
    monkeypatch.setitem(sys.modules, "src.fleet", fleet_pkg)
    monkeypatch.setitem(sys.modules, "src.fleet.session_manager", sm_module)
    rc = spawn_nova.main([flag])
    assert rc == 0
