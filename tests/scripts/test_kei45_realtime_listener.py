"""Tests for KEI-45 Phase A.2 Realtime listener."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "kei45_realtime_listener.py"

_spec = importlib.util.spec_from_file_location("kei45_realtime_listener", SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["kei45_realtime_listener"] = _mod
_spec.loader.exec_module(_mod)

CALLSIGN_TO_TMUX = _mod.CALLSIGN_TO_TMUX
on_task_event = _mod.on_task_event
inject_bd_ready_into_pane = _mod.inject_bd_ready_into_pane


def test_callsign_map_covers_all_6_agents():
    """All 6 canonical callsigns mapped to tmux session names."""
    assert set(CALLSIGN_TO_TMUX) == {"elliot", "aiden", "max", "atlas", "orion", "scout"}


def test_callsign_map_matches_canonical_tmux_names():
    """Lockstep with elliot_polling_loop.py:111 CALLSIGN_TO_TMUX."""
    assert CALLSIGN_TO_TMUX["elliot"] == "elliottbot"
    assert CALLSIGN_TO_TMUX["max"] == "maxbot"
    assert CALLSIGN_TO_TMUX["aiden"] == "aiden"
    assert CALLSIGN_TO_TMUX["atlas"] == "atlas"
    assert CALLSIGN_TO_TMUX["orion"] == "orion"
    assert CALLSIGN_TO_TMUX["scout"] == "scout"


# Payload shape mirrors supabase-py 2.x AsyncRealtimeChannel postgres_changes
# delivery (empirically confirmed via DEBUG-log smoke 2026-05-14):
#   {"data": {"type": "INSERT"|"UPDATE", "record": {...}, ...}, "ids": [...]}

def _payload(event_type: str, record: dict) -> dict:
    return {"data": {"type": event_type, "record": record, "schema": "public",
                     "table": "tasks"}, "ids": [9019328]}


def test_on_task_event_fires_wake_for_insert_available():
    """INSERT event with status='available' fans wake to all 6 agents."""
    wakes: list = []

    def fake_inject(callsign):
        wakes.append(callsign)

    with mock.patch.object(_mod, "inject_bd_ready_into_pane", fake_inject):
        on_task_event(_payload("INSERT", {"id": "KEI-99", "status": "available"}))

    assert set(wakes) == set(CALLSIGN_TO_TMUX)


def test_on_task_event_fires_wake_for_update_to_available():
    """UPDATE event with status='available' fans wake (re-availability)."""
    wakes: list = []

    def fake_inject(callsign):
        wakes.append(callsign)

    with mock.patch.object(_mod, "inject_bd_ready_into_pane", fake_inject):
        on_task_event(_payload("UPDATE", {"id": "KEI-99", "status": "available"}))

    assert set(wakes) == set(CALLSIGN_TO_TMUX)


def test_on_task_event_ignores_non_available_status():
    """UPDATE to status='active' (claimed) does NOT fire wake."""
    wakes: list = []

    def fake_inject(callsign):
        wakes.append(callsign)

    with mock.patch.object(_mod, "inject_bd_ready_into_pane", fake_inject):
        on_task_event(_payload("UPDATE", {"id": "KEI-99", "status": "active"}))

    assert wakes == []


def test_on_task_event_ignores_done_status():
    """status='done' does NOT fire wake."""
    wakes: list = []

    def fake_inject(callsign):
        wakes.append(callsign)

    with mock.patch.object(_mod, "inject_bd_ready_into_pane", fake_inject):
        on_task_event(_payload("UPDATE", {"id": "KEI-99", "status": "done"}))

    assert wakes == []


def test_on_task_event_handles_realtime_enum_event_type():
    """supabase-py may pass an enum with .value attribute instead of bare str."""
    wakes: list = []

    class _FakeEnum:
        value = "INSERT"

    def fake_inject(callsign):
        wakes.append(callsign)

    with mock.patch.object(_mod, "inject_bd_ready_into_pane", fake_inject):
        on_task_event({
            "data": {"type": _FakeEnum(), "record": {"id": "KEI-99", "status": "available"}},
            "ids": [1],
        })

    assert set(wakes) == set(CALLSIGN_TO_TMUX)


def test_inject_skips_unknown_callsign(caplog):
    """Unknown callsign → log warning, no tmux call."""
    with caplog.at_level("WARNING"):
        inject_bd_ready_into_pane("bogus_callsign")
    assert "no tmux session mapping" in caplog.text


def test_inject_debounces_rapid_wake_for_same_callsign():
    """Two rapid wakes to same callsign: second is debounced."""
    _mod._last_wake_at.clear()

    with mock.patch.object(_mod.subprocess, "run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)
        inject_bd_ready_into_pane("max")
        first_call_count = mock_run.call_count
        inject_bd_ready_into_pane("max")  # within DEBOUNCE_SECONDS
        second_call_count = mock_run.call_count

    # First call: has-session + send-keys = 2 subprocess calls.
    # Second call: debounced = 0 additional subprocess calls.
    assert first_call_count == 2
    assert second_call_count == 2  # debounced; no new calls


def test_inject_skips_when_tmux_session_missing():
    """tmux has-session returns non-zero → log warning + skip send-keys."""
    _mod._last_wake_at.clear()
    with mock.patch.object(_mod.subprocess, "run") as mock_run:
        # First call (has-session) returns rc=1; should skip send-keys.
        mock_run.return_value = mock.Mock(returncode=1)
        inject_bd_ready_into_pane("orion")
        # Only the has-session call should have been made (no send-keys).
        assert mock_run.call_count == 1
