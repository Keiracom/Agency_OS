"""Tests for scripts/dispatcher/_envelope_route.py.

Covers the 4-way router (task_dispatch / decision_response /
paused_pending_decision / unknown→quarantine).

bd: Agency_OS-8416
"""

from __future__ import annotations

from pathlib import Path

from scripts.dispatcher._envelope_route import (
    ROUTABLE_TYPES,
    RouteAction,
    quarantine_envelope,
    route_envelope,
)


def test_routable_types_is_the_3_consumed_types():
    """The router consumes 3 of the 4 envelope types from PR #1181 schema —
    `task_dispatch` is implicit (default spawn path), the other 3 are explicit.
    """
    assert (
        frozenset({"task_dispatch", "decision_response", "paused_pending_decision"})
        == ROUTABLE_TYPES
    )


def test_task_dispatch_returns_spawn_action_no_resume_context(tmp_path: Path):
    action, resume = route_envelope(
        {"type": "task_dispatch", "id": "t1", "brief": "x"},
        claimed_path=tmp_path / "t1.json",
        quarantine_dir=tmp_path / "q",
    )
    assert action == RouteAction.SPAWN
    assert resume is None


def test_decision_response_returns_resume_action_with_envelope_as_context(tmp_path: Path):
    envelope = {
        "type": "decision_response",
        "id": "r1",
        "decision": "push_fixup",
        "original_task_ref": "review-pr-X",
    }
    action, resume = route_envelope(
        envelope,
        claimed_path=tmp_path / "r1.json",
        quarantine_dir=tmp_path / "q",
    )
    assert action == RouteAction.RESUME
    assert resume is envelope  # passed through verbatim for the composer


def test_paused_pending_decision_returns_log_paused_action(tmp_path: Path):
    action, resume = route_envelope(
        {"type": "paused_pending_decision", "id": "p1", "task_ref": "t1"},
        claimed_path=tmp_path / "p1.json",
        quarantine_dir=tmp_path / "q",
    )
    assert action == RouteAction.LOG_PAUSED
    assert resume is None


def test_unknown_type_quarantines_and_returns_quarantine_action(tmp_path: Path):
    src = tmp_path / "weird.json"
    src.write_text('{"type":"not_a_real_type"}')
    quarantine = tmp_path / "q"
    action, resume = route_envelope(
        {"type": "not_a_real_type", "id": "w1"},
        claimed_path=src,
        quarantine_dir=quarantine,
    )
    assert action == RouteAction.QUARANTINE
    assert resume is None
    # The file should have moved + a .reason sidecar should exist.
    assert not src.exists()
    moved = quarantine / "weird.json"
    assert moved.exists()
    reason = quarantine / "weird.json.reason"
    assert reason.exists()
    assert "not_a_real_type" in reason.read_text()


def test_missing_type_field_quarantines(tmp_path: Path):
    src = tmp_path / "no_type.json"
    src.write_text("{}")
    quarantine = tmp_path / "q"
    action, _ = route_envelope({}, claimed_path=src, quarantine_dir=quarantine)
    assert action == RouteAction.QUARANTINE
    assert (quarantine / "no_type.json").exists()


def test_quarantine_envelope_uses_injectable_mover(tmp_path: Path):
    """The mover callable is injectable so tests don't depend on shutil.move."""
    src = tmp_path / "x.json"
    src.write_text("{}")
    quarantine = tmp_path / "q"
    calls: list[tuple[str, str]] = []

    def fake_mover(s: str, d: str) -> None:
        calls.append((s, d))
        Path(d).write_text(Path(s).read_text())  # mimic the move

    dest = quarantine_envelope(src, quarantine, reason="testing", mover=fake_mover)
    assert calls == [(str(src), str(dest))]
    assert dest.exists()
