"""KEI-90 Gate 3 — tests for deployment peer-verify in scripts/tasks_cli.py.

Strategy: exercises the extracted helper `_check_gate3_peer_verify` directly
with a fake cursor that returns canned rows for the two SELECTs the helper
issues (tasks deployment+claimed_by, then either dave-priors-count or
tool_call_log session-match).

Covers:
  - deployment=false → no-op pass-through
  - deployment=true + missing --verifier → explanatory error
  - deployment=true + verifier == builder → independence error
  - deployment=true + missing verifier_session_uuid → schema error
  - deployment=true + verifier_session conflicts with builder's tool_call_log → error
  - deployment=true + clean independent → success
  - Dave-solo-ops + 0 priors → 2-of-3 path error
  - Dave-solo-ops + 1 prior + distinct session → success
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "tasks_cli.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("tasks_cli_g3", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["tasks_cli_g3"] = m
    spec.loader.exec_module(m)
    return m


class _GateCursor:
    """Cursor that returns scripted fetchone() values in order."""

    def __init__(self, replies: list[object]) -> None:
        self._iter: Iterator[object] = iter(replies)
        self.executed: list[tuple] = []

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.executed.append((sql, params))

    def fetchone(self) -> object:
        return next(self._iter, None)


def test_deployment_false_passes_through(mod):
    cur = _GateCursor([(False, "max"), None])
    err, by = mod._check_gate3_peer_verify(cur, "KEI-X", "elliot", None, "")
    assert err is None and by == "elliot"


def test_deployment_true_missing_verifier(mod):
    cur = _GateCursor([(True, "max")])
    err, _ = mod._check_gate3_peer_verify(cur, "KEI-X", "elliot", None, "uuid-1")
    assert err is not None and "--verifier" in err


def test_deployment_true_verifier_equals_builder(mod):
    cur = _GateCursor([(True, "max")])
    err, by = mod._check_gate3_peer_verify(cur, "KEI-X", "elliot", "max", "uuid-1")
    assert err is not None and "differ from builder" in err
    assert by == "max"


def test_deployment_true_missing_verifier_session(mod):
    cur = _GateCursor([(True, "max")])
    err, _ = mod._check_gate3_peer_verify(cur, "KEI-X", "elliot", "elliot", "")
    assert err is not None and "verifier_session_uuid" in err


def test_deployment_true_session_conflict(mod):
    # First fetchone: tasks row. Second fetchone: tool_call_log MATCH.
    cur = _GateCursor([(True, "max"), (1,)])
    err, _ = mod._check_gate3_peer_verify(cur, "KEI-X", "elliot", "elliot", "uuid-collide")
    assert err is not None and "session-independence" in err


def test_deployment_true_clean_pass(mod):
    # tasks row + tool_call_log returns None (no match).
    cur = _GateCursor([(True, "max"), None])
    err, by = mod._check_gate3_peer_verify(cur, "KEI-X", "elliot", "elliot", "uuid-clean")
    assert err is None and by == "elliot"


def test_dave_solo_ops_missing_secondary(mod):
    # tasks row builder=dave + no --secondary-verifier passed.
    cur = _GateCursor([(True, "dave")])
    err, _ = mod._check_gate3_peer_verify(cur, "KEI-X", "elliot", "elliot", "uuid-1", None)
    assert err is not None and "secondary-verifier" in err


def test_dave_solo_ops_same_verifier_callsigns(mod):
    cur = _GateCursor([(True, "dave")])
    err, _ = mod._check_gate3_peer_verify(cur, "KEI-X", "elliot", "elliot", "uuid-1", "elliot")
    assert err is not None and "distinct callsigns" in err


def test_dave_solo_ops_secondary_is_dave(mod):
    cur = _GateCursor([(True, "dave")])
    err, _ = mod._check_gate3_peer_verify(cur, "KEI-X", "elliot", "elliot", "uuid-1", "dave")
    assert err is not None and "may be 'dave'" in err


def test_dave_solo_ops_clean_two_distinct_sessions(mod):
    # tasks row builder=dave; secondary 'max' has tool_call_log session='uuid-b';
    # final builder-vs-verifier tool_call_log check returns None.
    cur = _GateCursor([(True, "dave"), ("uuid-b",), None])
    err, by = mod._check_gate3_peer_verify(cur, "KEI-X", "elliot", "elliot", "uuid-a", "max")
    assert err is None and by == "elliot"


def test_dave_solo_ops_session_collision_with_secondary(mod):
    # secondary 'max' has same session as the verifier's evidence uuid.
    cur = _GateCursor([(True, "dave"), ("uuid-collide",)])
    err, _ = mod._check_gate3_peer_verify(cur, "KEI-X", "elliot", "elliot", "uuid-collide", "max")
    assert err is not None and "must be distinct" in err
