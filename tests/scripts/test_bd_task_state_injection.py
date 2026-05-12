"""Tests for scripts/bd_task_state_injection.py — KEI-31 component 3."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "bd_task_state_injection.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("bd_task_state_injection", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["bd_task_state_injection"] = m
    spec.loader.exec_module(m)
    return m


def test_render_injection_no_active(mod):
    out = mod.render_injection("aiden", None, [])
    assert "Beads task state" in out
    assert "Active issue: none assigned to aiden" in out
    assert "Ready queue: empty" in out


def test_render_injection_with_active_and_ready(mod):
    active = {
        "id": "Agency_OS-xyz",
        "title": "Build the thing",
        "status": "active",
        "dependencies": [{"depends_on_id": "Agency_OS-abc"}],
        "description": "Why this exists\n1. Step one\n2. Step two",
    }
    ready = [
        {"id": "Agency_OS-r1", "priority": 1, "title": "First ready"},
        {"id": "Agency_OS-r2", "priority": 2, "title": "Second ready"},
    ]
    out = mod.render_injection("aiden", active, ready)
    assert "**Agency_OS-xyz**" in out
    assert "Build the thing" in out
    assert "Blocked by: Agency_OS-abc" in out
    assert "1. Step one" in out
    assert "Agency_OS-r1" in out
    assert "Agency_OS-r2" in out


def test_render_injection_active_no_blockers(mod):
    active = {"id": "Agency_OS-q", "title": "Solo task", "status": "active", "description": ""}
    out = mod.render_injection("aiden", active, [])
    assert "Blocked by: none" in out


def test_get_ready_issues_parses_json(mod, monkeypatch):
    def _fake(args, timeout=10):
        return 0, '[{"id":"Agency_OS-a","priority":0,"title":"A"}]'
    monkeypatch.setattr(mod, "_run_bd", _fake)
    out = mod.get_ready_issues()
    assert out == [{"id": "Agency_OS-a", "priority": 0, "title": "A"}]


def test_get_ready_issues_handles_nonzero(mod, monkeypatch):
    monkeypatch.setattr(mod, "_run_bd", lambda *a, **k: (1, ""))
    assert mod.get_ready_issues() == []


def test_get_active_for_callsign_picks_in_progress(mod, monkeypatch):
    def _fake(args, timeout=10):
        return 0, json.dumps([
            {"id": "x", "status": "open"},
            {"id": "y", "status": "in_progress"},
            {"id": "z", "status": "closed"},
        ])
    import json
    monkeypatch.setattr(mod, "_run_bd", _fake)
    out = mod.get_active_for_callsign("aiden")
    assert out["id"] == "y"


def test_main_returns_zero_on_no_bd(mod, monkeypatch):
    monkeypatch.setattr(mod, "_run_bd", lambda *a, **k: (-1, ""))
    monkeypatch.setenv("CALLSIGN", "aiden")
    rc = mod.main()
    assert rc == 0
