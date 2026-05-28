"""Unit tests for BoundedSpawnEnforcer (Agency_OS-gcpm / Audit RED-7).

Covers the three classification branches:
  - first spawn for a callsign → DECISION_RECORDED
  - same task_id retried → DECISION_REPEAT_TASK (no kill, no audit)
  - different task_id while prior active → DECISION_VIOLATION (kill + alert + audit)

Plus negative-path coverage:
  - terminate_cb raising → fail-open, killed=False, but new spawn still recorded
  - audit-log path under unwritable parent → exception swallowed, decision still returned
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.dispatcher.bounded_spawn_enforcer import (
    DECISION_RECORDED,
    DECISION_REPEAT_TASK,
    DECISION_VIOLATION,
    BoundedSpawnEnforcer,
)


def _make_enforcer(
    tmp_path: Path,
    *,
    terminate_returns: bool = True,
    terminate_raises: bool = False,
    alerts_emitter: MagicMock | None = None,
) -> tuple[BoundedSpawnEnforcer, MagicMock, MagicMock]:
    terminate_cb = MagicMock()
    if terminate_raises:
        terminate_cb.side_effect = RuntimeError("synthetic terminate failure")
    else:
        terminate_cb.return_value = terminate_returns
    emitter = alerts_emitter or MagicMock()
    enforcer = BoundedSpawnEnforcer(
        terminate_cb=terminate_cb,
        alerts_emitter=emitter,
        audit_log_path=tmp_path / "violations.jsonl",
    )
    return enforcer, terminate_cb, emitter


# ---------- happy path ----------


def test_first_spawn_records_no_violation(tmp_path: Path) -> None:
    enforcer, terminate_cb, emitter = _make_enforcer(tmp_path)
    result = enforcer.record_spawn(key="k1", callsign="orion", task_id="t1", backend="tmux")
    assert result.decision == DECISION_RECORDED
    assert result.killed is False
    assert result.prior is None
    terminate_cb.assert_not_called()
    emitter.assert_not_called()
    assert not (tmp_path / "violations.jsonl").exists()


def test_same_task_id_retried_is_repeat_not_violation(tmp_path: Path) -> None:
    enforcer, terminate_cb, emitter = _make_enforcer(tmp_path)
    enforcer.record_spawn(key="k1", callsign="orion", task_id="t1", backend="tmux")
    # Same task arriving again (e.g. keepalive bounce) → no violation.
    result = enforcer.record_spawn(key="k1-retry", callsign="orion", task_id="t1", backend="tmux")
    assert result.decision == DECISION_REPEAT_TASK
    assert result.killed is False
    assert result.prior is not None
    assert result.prior.task_id == "t1"
    terminate_cb.assert_not_called()
    emitter.assert_not_called()


# ---------- violation path ----------


def test_second_distinct_task_triggers_violation_kill_alert_audit(tmp_path: Path) -> None:
    audit_path = tmp_path / "violations.jsonl"
    enforcer, terminate_cb, emitter = _make_enforcer(tmp_path)
    enforcer.record_spawn(key="k1", callsign="orion", task_id="t1", backend="tmux")
    result = enforcer.record_spawn(key="k2", callsign="orion", task_id="t2", backend="tmux")
    assert result.decision == DECISION_VIOLATION
    assert result.killed is True
    assert result.prior is not None
    assert result.prior.key == "k1"
    assert result.prior.task_id == "t1"
    terminate_cb.assert_called_once_with("k1")
    emitter.assert_called_once()
    alert_payload = emitter.call_args[0][0]
    assert alert_payload["alert"] == "bounded_spawn_violation"
    assert alert_payload["killed"] is True
    assert alert_payload["callsign"] == "orion"
    assert alert_payload["prior_task_id"] == "t1"
    assert alert_payload["new_task_id"] == "t2"

    # Audit JSONL written with a row that matches the violation.
    assert audit_path.exists()
    rows = [json.loads(line) for line in audit_path.read_text().splitlines() if line]
    assert len(rows) == 1
    assert rows[0]["event"] == "bounded_spawn_violation"
    assert rows[0]["prior_task_id"] == "t1"
    assert rows[0]["new_task_id"] == "t2"
    assert rows[0]["killed"] is True

    # The new task is recorded as the canonical active slot.
    snap = enforcer.snapshot()
    assert "orion" in snap
    assert snap["orion"]["task_id"] == "t2"


def test_different_callsigns_do_not_cross_violate(tmp_path: Path) -> None:
    enforcer, terminate_cb, emitter = _make_enforcer(tmp_path)
    enforcer.record_spawn(key="a", callsign="orion", task_id="t1", backend="tmux")
    # Different callsign + different task → separate active slot, no violation.
    result = enforcer.record_spawn(key="b", callsign="atlas", task_id="t2", backend="tmux")
    assert result.decision == DECISION_RECORDED
    assert result.killed is False
    terminate_cb.assert_not_called()
    emitter.assert_not_called()
    snap = enforcer.snapshot()
    assert set(snap.keys()) == {"orion", "atlas"}


# ---------- terminate_cb fail-open ----------


def test_violation_with_terminate_cb_returning_false_records_killed_false(
    tmp_path: Path,
) -> None:
    enforcer, terminate_cb, emitter = _make_enforcer(tmp_path, terminate_returns=False)
    enforcer.record_spawn(key="k1", callsign="orion", task_id="t1", backend="tmux")
    result = enforcer.record_spawn(key="k2", callsign="orion", task_id="t2", backend="tmux")
    assert result.decision == DECISION_VIOLATION
    assert result.killed is False
    terminate_cb.assert_called_once_with("k1")
    # New spawn still recorded as canonical even when prior kill failed.
    assert enforcer.snapshot()["orion"]["task_id"] == "t2"


def test_violation_with_terminate_cb_raising_fails_open(tmp_path: Path) -> None:
    enforcer, terminate_cb, emitter = _make_enforcer(tmp_path, terminate_raises=True)
    enforcer.record_spawn(key="k1", callsign="orion", task_id="t1", backend="tmux")
    # Must not raise — fail-open contract.
    result = enforcer.record_spawn(key="k2", callsign="orion", task_id="t2", backend="tmux")
    assert result.decision == DECISION_VIOLATION
    assert result.killed is False
    emitter.assert_called_once()


# ---------- release / snapshot ----------


def test_release_spawn_removes_active_slot(tmp_path: Path) -> None:
    enforcer, _terminate_cb, _emitter = _make_enforcer(tmp_path)
    enforcer.record_spawn(key="k1", callsign="orion", task_id="t1", backend="tmux")
    released = enforcer.release_spawn("k1")
    assert released is not None
    assert released.callsign == "orion"
    assert enforcer.snapshot() == {}


def test_release_spawn_unknown_key_returns_none(tmp_path: Path) -> None:
    enforcer, _terminate_cb, _emitter = _make_enforcer(tmp_path)
    assert enforcer.release_spawn("nonexistent") is None


def test_release_then_new_task_is_fresh_not_violation(tmp_path: Path) -> None:
    enforcer, terminate_cb, emitter = _make_enforcer(tmp_path)
    enforcer.record_spawn(key="k1", callsign="orion", task_id="t1", backend="tmux")
    enforcer.release_spawn("k1")
    result = enforcer.record_spawn(key="k2", callsign="orion", task_id="t2", backend="tmux")
    assert result.decision == DECISION_RECORDED
    assert result.killed is False
    terminate_cb.assert_not_called()
    emitter.assert_not_called()


# ---------- audit log fail-open ----------


def test_audit_write_failure_does_not_block_violation_handling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Point at a path whose parent cannot be written (use a regular file as the dir).
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("blocking the audit dir from being a dir")
    enforcer = BoundedSpawnEnforcer(
        terminate_cb=MagicMock(return_value=True),
        alerts_emitter=MagicMock(),
        audit_log_path=blocker / "violations.jsonl",
    )
    enforcer.record_spawn(key="k1", callsign="orion", task_id="t1", backend="tmux")
    # Should not raise even though audit write will fail.
    result = enforcer.record_spawn(key="k2", callsign="orion", task_id="t2", backend="tmux")
    assert result.decision == DECISION_VIOLATION
    assert result.killed is True
