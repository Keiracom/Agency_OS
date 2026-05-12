"""Tests for scripts/linear_to_bd.py — Linear→Beads subprocess wrapper.

Mocks bd subprocess via env-injectable AGENCY_OS_BD_BIN pointing at a shim
script that records its invocations. Verifies:
  - create event invokes `bd create` with correct title + priority + external-ref
  - create idempotent: skip when find_existing_by_url returns a match
  - status closed event invokes `bd close`
  - status active event invokes `bd update --status active`
  - status idempotent: skip when bd issue already matches
  - unknown op exits 0 cleanly
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "linear_to_bd.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("linear_to_bd", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["linear_to_bd"] = m
    spec.loader.exec_module(m)
    return m


def _capture_bd_calls(mod, monkeypatch, list_response: list[dict] | None = None):
    """Replace _run_bd with a closure that records (args, stdin) tuples."""
    calls: list[tuple[list[str], str | None]] = []

    def _fake(args, stdin=None, timeout=15):
        calls.append((args, stdin))
        if args[:2] == ["list", "--json"]:
            return 0, json.dumps(list_response or []), ""
        return 0, "", ""

    monkeypatch.setattr(mod, "_run_bd", _fake)
    return calls


# handle_create ───────────────────────────────────────────────────────────────


def test_handle_create_invokes_bd_create_with_external_ref(mod, monkeypatch):
    calls = _capture_bd_calls(mod, monkeypatch)
    event = {
        "op": "create",
        "identifier": "KEI-77",
        "title": "Wire the receiver",
        "priority": 0,  # bd critical
        "url": "https://linear.app/keiracom/issue/KEI-77/wire",
    }
    rc = mod.handle_create(event)
    assert rc == 0
    create_calls = [c for c in calls if c[0][0] == "create"]
    assert len(create_calls) == 1
    args = create_calls[0][0]
    assert "--title" in args and "Wire the receiver" in args
    assert "--external-ref" in args
    assert "https://linear.app/keiracom/issue/KEI-77/wire" in args
    assert "--priority" in args and "0" in args


def test_handle_create_idempotent_skip_when_url_already_mapped(mod, monkeypatch):
    existing = [
        {"id": "Agency_OS-abc", "external_ref": "https://linear.app/keiracom/issue/KEI-77/wire"},
    ]
    calls = _capture_bd_calls(mod, monkeypatch, list_response=existing)
    event = {
        "op": "create",
        "identifier": "KEI-77",
        "title": "Wire the receiver",
        "priority": 0,
        "url": "https://linear.app/keiracom/issue/KEI-77/wire",
    }
    rc = mod.handle_create(event)
    assert rc == 0
    create_calls = [c for c in calls if c[0][0] == "create"]
    assert len(create_calls) == 0  # idempotent skip


# handle_status ───────────────────────────────────────────────────────────────


def test_handle_status_closed_invokes_bd_close(mod, monkeypatch):
    existing = [
        {
            "id": "Agency_OS-abc",
            "status": "open",
            "external_ref": "https://linear.app/keiracom/issue/KEI-77",
        },
    ]
    calls = _capture_bd_calls(mod, monkeypatch, list_response=existing)
    event = {
        "op": "status",
        "identifier": "KEI-77",
        "bd_status": "closed",
        "url": "https://linear.app/keiracom/issue/KEI-77",
    }
    rc = mod.handle_status(event)
    assert rc == 0
    close_calls = [c for c in calls if c[0][:2] == ["close", "Agency_OS-abc"]]
    assert len(close_calls) == 1


def test_handle_status_active_invokes_bd_update(mod, monkeypatch):
    existing = [
        {
            "id": "Agency_OS-def",
            "status": "open",
            "external_ref": "https://linear.app/keiracom/issue/KEI-88",
        },
    ]
    calls = _capture_bd_calls(mod, monkeypatch, list_response=existing)
    event = {
        "op": "status",
        "identifier": "KEI-88",
        "bd_status": "active",
        "url": "https://linear.app/keiracom/issue/KEI-88",
    }
    rc = mod.handle_status(event)
    assert rc == 0
    update_calls = [c for c in calls if c[0][:2] == ["update", "Agency_OS-def"]]
    assert len(update_calls) == 1
    assert "--status" in update_calls[0][0] and "active" in update_calls[0][0]


def test_handle_status_idempotent_skip_when_already_matching(mod, monkeypatch):
    existing = [
        {
            "id": "Agency_OS-ghi",
            "status": "active",
            "external_ref": "https://linear.app/keiracom/issue/KEI-99",
        },
    ]
    calls = _capture_bd_calls(mod, monkeypatch, list_response=existing)
    event = {
        "op": "status",
        "identifier": "KEI-99",
        "bd_status": "active",
        "url": "https://linear.app/keiracom/issue/KEI-99",
    }
    rc = mod.handle_status(event)
    assert rc == 0
    assert all(c[0][:2] != ["update", "Agency_OS-ghi"] for c in calls)


def test_handle_status_skip_when_no_bd_mapping(mod, monkeypatch):
    """Status update for a Linear issue without a bd counterpart: skip cleanly."""
    calls = _capture_bd_calls(mod, monkeypatch, list_response=[])
    event = {
        "op": "status",
        "identifier": "KEI-100",
        "bd_status": "closed",
        "url": "https://linear.app/x",
    }
    rc = mod.handle_status(event)
    assert rc == 0
    assert all(c[0][0] not in {"close", "update"} for c in calls)


# main ────────────────────────────────────────────────────────────────────────


def test_main_unknown_op_returns_zero(mod, monkeypatch, tmp_path):
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps({"op": "unknown"}))
    rc = mod.main(["--event-file", str(event_file)])
    assert rc == 0


def test_main_empty_stdin_returns_zero(mod, monkeypatch):
    monkeypatch.setattr(sys, "stdin", type("F", (), {"isatty": lambda self: True, "read": lambda self: ""})())
    rc = mod.main([])
    assert rc == 0
