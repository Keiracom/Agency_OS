"""KEI-234 — tests for scripts/restore_linear_state.py.

Covers the pure-Python history-parsing logic (no live Linear API):
  - find_pre_damage_state: filters by actor + window
  - earliest in-window event is the restore target
  - out-of-window events ignored
  - other-actor events ignored (legitimate changes preserved)
  - malformed timestamps tolerated
  - no candidates → None
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "restore_linear_state.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("restore_linear_state", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["restore_linear_state"] = m
    spec.loader.exec_module(m)
    return m


_ACTOR = "actor-buggy-uuid"
_OTHER = "actor-human-uuid"
_W_START = datetime(2026, 5, 19, 11, 4, 0, tzinfo=UTC)
_W_END = datetime(2026, 5, 19, 12, 24, 0, tzinfo=UTC)


def _event(ts: str, actor: str, from_type: str, to_type: str = "unstarted") -> dict:
    return {
        "createdAt": ts,
        "actor": {"id": actor},
        "fromState": {"id": f"id-{from_type}", "type": from_type, "name": from_type.title()},
        "toState": {"id": f"id-{to_type}", "type": to_type, "name": to_type.title()},
    }


def test_finds_in_window_event_by_actor(mod) -> None:
    history = [_event("2026-05-19T11:30:00Z", _ACTOR, "completed")]
    pre = mod.find_pre_damage_state(history, _ACTOR, _W_START, _W_END)
    assert pre is not None
    assert pre["type"] == "completed"
    assert pre["id"] == "id-completed"


def test_returns_none_for_out_of_window_event(mod) -> None:
    history = [_event("2026-05-19T10:00:00Z", _ACTOR, "completed")]
    assert mod.find_pre_damage_state(history, _ACTOR, _W_START, _W_END) is None


def test_returns_none_for_other_actor(mod) -> None:
    history = [_event("2026-05-19T11:30:00Z", _OTHER, "completed")]
    assert mod.find_pre_damage_state(history, _ACTOR, _W_START, _W_END) is None


def test_returns_none_when_history_empty(mod) -> None:
    assert mod.find_pre_damage_state([], _ACTOR, _W_START, _W_END) is None


def test_earliest_in_window_event_wins(mod) -> None:
    """If the bug touched an issue multiple times, restore to the EARLIEST
    pre-damage state (later events would have wrong fromState)."""
    history = [
        _event("2026-05-19T11:45:00Z", _ACTOR, "started"),  # later flip
        _event("2026-05-19T11:30:00Z", _ACTOR, "completed"),  # earlier flip
    ]
    pre = mod.find_pre_damage_state(history, _ACTOR, _W_START, _W_END)
    assert pre["type"] == "completed"


def test_ignores_legitimate_human_changes_inside_window(mod) -> None:
    """Even if a human changed an issue during the window, that's not the bug."""
    history = [
        _event("2026-05-19T11:30:00Z", _OTHER, "started"),
        _event("2026-05-19T11:31:00Z", _ACTOR, "started"),
    ]
    pre = mod.find_pre_damage_state(history, _ACTOR, _W_START, _W_END)
    # Should pick the ACTOR's event, not the human's.
    assert pre["type"] == "started"


def test_tolerates_malformed_timestamp(mod) -> None:
    history = [
        _event("not-a-timestamp", _ACTOR, "completed"),
        _event("2026-05-19T11:30:00Z", _ACTOR, "started"),
    ]
    pre = mod.find_pre_damage_state(history, _ACTOR, _W_START, _W_END)
    assert pre is not None
    assert pre["type"] == "started"


def test_skips_event_with_no_from_state(mod) -> None:
    """Issue.create events have no fromState — must not crash."""
    history = [
        {"createdAt": "2026-05-19T11:30:00Z", "actor": {"id": _ACTOR}, "fromState": None},
        _event("2026-05-19T11:31:00Z", _ACTOR, "completed"),
    ]
    pre = mod.find_pre_damage_state(history, _ACTOR, _W_START, _W_END)
    assert pre is not None
    assert pre["type"] == "completed"


def test_skips_event_with_missing_actor(mod) -> None:
    history = [
        {
            "createdAt": "2026-05-19T11:30:00Z",
            "actor": None,
            "fromState": {"id": "x", "type": "completed", "name": "Completed"},
        },
        _event("2026-05-19T11:31:00Z", _ACTOR, "started"),
    ]
    pre = mod.find_pre_damage_state(history, _ACTOR, _W_START, _W_END)
    assert pre["type"] == "started"


def test_window_inclusive_at_boundaries(mod) -> None:
    """Events exactly at window start/end count as in-window."""
    history_start = [_event("2026-05-19T11:04:00Z", _ACTOR, "completed")]
    history_end = [_event("2026-05-19T12:24:00Z", _ACTOR, "completed")]
    assert mod.find_pre_damage_state(history_start, _ACTOR, _W_START, _W_END) is not None
    assert mod.find_pre_damage_state(history_end, _ACTOR, _W_START, _W_END) is not None
