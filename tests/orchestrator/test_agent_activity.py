"""Tests for scripts/orchestrator/agent_activity.py — compute_activity_state.

Covers the four-state output table:
  active                 (DB activity_state='active' — inbox not consulted)
  idle_with_work_queued  (DB idle + filesystem inbox has pending file)
  idle                   (DB idle + filesystem inbox empty)
  no_data                (DB failure or callsign absent from view)

Plus DI-hook tests for inbox file detection and the default DB-failure path.
"""

from __future__ import annotations

from pathlib import Path

from scripts.orchestrator.agent_activity import (
    INBOX_PATH_TEMPLATE,
    _default_inbox_has_pending,
    compute_activity_state,
)


def _const(value):
    """Build a 1-arg callable returning `value` regardless of input."""

    def f(_callsign: str):
        return value

    return f


# ─── compute_activity_state combinatorics ────────────────────────────────


def test_active_short_circuits_inbox_check() -> None:
    # If db_state='active', inbox MUST NOT be consulted (we don't even know
    # if pending work is "queued behind me" or "for the active agent" — and
    # the active state is the strongest signal).
    inbox_called = {"count": 0}

    def inbox(_cs: str) -> bool:
        inbox_called["count"] += 1
        return True

    result = compute_activity_state(
        "scout", db_state_fn=_const("active"), inbox_has_pending_fn=inbox
    )
    assert result == "active"
    assert inbox_called["count"] == 0


def test_no_data_propagates() -> None:
    result = compute_activity_state(
        "scout", db_state_fn=_const("no_data"), inbox_has_pending_fn=_const(True)
    )
    # no_data must NOT be upgraded to idle_with_work_queued — we don't know
    # the agent's actual state, only that the inbox has a file.
    assert result == "no_data"


def test_idle_plus_pending_inbox_becomes_idle_with_work_queued() -> None:
    result = compute_activity_state(
        "scout", db_state_fn=_const("idle"), inbox_has_pending_fn=_const(True)
    )
    assert result == "idle_with_work_queued"


def test_idle_with_empty_inbox_stays_idle() -> None:
    result = compute_activity_state(
        "scout", db_state_fn=_const("idle"), inbox_has_pending_fn=_const(False)
    )
    assert result == "idle"


# ─── _default_inbox_has_pending — filesystem behaviour ───────────────────


def test_inbox_pending_true_when_file_present(tmp_path: Path, monkeypatch) -> None:
    inbox_dir = tmp_path / "inbox"
    inbox_dir.mkdir()
    (inbox_dir / "msg-1.json").write_text("{}")

    # Redirect INBOX_PATH_TEMPLATE so the default function checks our tmp_path.
    monkeypatch.setattr(
        "scripts.orchestrator.agent_activity.INBOX_PATH_TEMPLATE",
        str(inbox_dir).replace("inbox", "{callsign}"),
    )

    assert _default_inbox_has_pending("inbox") is True


def test_inbox_pending_false_when_dir_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.orchestrator.agent_activity.INBOX_PATH_TEMPLATE",
        str(tmp_path / "definitely-not-there-{callsign}"),
    )
    assert _default_inbox_has_pending("anything") is False


def test_inbox_pending_false_when_dir_empty(tmp_path: Path, monkeypatch) -> None:
    inbox_dir = tmp_path / "empty"
    inbox_dir.mkdir()
    monkeypatch.setattr(
        "scripts.orchestrator.agent_activity.INBOX_PATH_TEMPLATE",
        str(inbox_dir).replace("empty", "{callsign}"),
    )
    assert _default_inbox_has_pending("empty") is False


def test_inbox_pending_ignores_subdirs(tmp_path: Path, monkeypatch) -> None:
    # A subdirectory under inbox/ is NOT a pending message — only regular files
    # count. processed/ + dlq/ subdirectories are common siblings of pending
    # messages in the relay scheme.
    inbox_dir = tmp_path / "subdir-only"
    inbox_dir.mkdir()
    (inbox_dir / "processed").mkdir()
    monkeypatch.setattr(
        "scripts.orchestrator.agent_activity.INBOX_PATH_TEMPLATE",
        str(inbox_dir).replace("subdir-only", "{callsign}"),
    )
    assert _default_inbox_has_pending("subdir-only") is False


# ─── Module-level constant sanity ────────────────────────────────────────


def test_inbox_path_template_uses_callsign_placeholder() -> None:
    assert "{callsign}" in INBOX_PATH_TEMPLATE
    assert "telegram-relay" in INBOX_PATH_TEMPLATE
