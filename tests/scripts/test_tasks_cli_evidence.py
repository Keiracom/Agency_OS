"""KEI-89 Gate 2 — tests for bd complete --evidence in scripts/tasks_cli.py.

Covers:
  (1) positive_valid_evidence     — completes task, task_verifications row
                                    inserted with correct test_output,
                                    tasks.status set to 'done'.
  (2) negative_missing_evidence   — no --evidence flag → exits 1 with
                                    explanatory error.
  (3) negative_schema_fail        — missing required field → exits 1 with
                                    "evidence schema invalid" message.
  (4) negative_hash_collision     — re-using identical evidence on a
                                    different task → exits 1 with
                                    "matches prior verification" message.
  (5) positive_no_side_effects    — valid evidence path inserts ONE
                                    verification row (no extra DB writes).

Uses FakeCursor / FakeConn from _db_mocks (shared infra); does NOT touch
the live Supabase DB.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "tasks_cli.py"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db_mocks import FakeCursor, make_patch_connect  # type: ignore[import-not-found]  # noqa: E402

# ─── module fixture ───────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("tasks_cli_ev", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["tasks_cli_ev"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def patch_connect(mod, monkeypatch):
    return make_patch_connect(monkeypatch)


# ─── shared evidence fixture ──────────────────────────────────────────────────

_VALID_EVIDENCE = {
    "acceptance_items": ["All four pytest tests pass with no failures"],
    "commands": [
        {
            "cmd": "pytest tests/scripts/test_tasks_cli_evidence.py -v",
            "output": "4 passed in 0.42s — PASSED acceptance gate confirmed",
        }
    ],
    "verifier_session_uuid": "abc123-session-uuid-def456",
    "timestamp": "2026-05-17T10:00:00+10:00",
}


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


# ─── FakeConn that supports rollback tracking ─────────────────────────────────


class TrackingFakeConn:
    """FakeConn variant that tracks rollbacks and supports multi-fetchone calls."""

    def __init__(self, cur: FakeCursor) -> None:
        self._cur = cur
        self.commits = 0
        self.rollbacks = 0

    def cursor(self) -> FakeCursor:
        return self._cur

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def __enter__(self) -> TrackingFakeConn:
        return self

    def __exit__(self, *a: Any) -> None:
        return None


class MultiStepCursor(FakeCursor):
    """Cursor that cycles through a pre-configured sequence of fetchone/fetchall
    responses, one per execute() call. Enables testing multi-step transactions.
    """

    def __init__(self, step_responses: list[tuple | list | None]) -> None:
        super().__init__()
        self._steps = list(step_responses)
        self._step_idx = 0

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.executed.append((sql, params))
        self._step_idx += 1

    def fetchone(self) -> tuple | None:
        idx = self._step_idx - 1
        if idx < len(self._steps):
            val = self._steps[idx]
            return val if isinstance(val, tuple) else None
        return None

    def fetchall(self) -> list[tuple]:
        idx = self._step_idx - 1
        if idx < len(self._steps):
            val = self._steps[idx]
            return val if isinstance(val, list) else []
        return []


# ─── (1) positive valid evidence ─────────────────────────────────────────────


def test_positive_valid_evidence_completes_task(mod, monkeypatch, tmp_path, capsys):
    """Valid evidence: task_verifications INSERT + tasks UPDATE both fire,
    commit is called, exit code 0.
    """
    ev_file = tmp_path / "evidence.json"
    ev_file.write_text(json.dumps(_VALID_EVIDENCE))

    # Step sequence (post KEI-90 Gate 3 addition):
    #  execute[0] = Gate 3 SELECT deployment, claimed_by → fetchone returns (False, 'aiden')
    #  execute[1] = hash-uniqueness SELECT  → fetchall returns []  (no collision)
    #  execute[2] = INSERT task_verifications → fetchone not called
    #  execute[3] = UPDATE tasks RETURNING → fetchone returns the done row
    cur = MultiStepCursor(
        step_responses=[
            (False, "aiden"),  # Gate 3: deployment=False → no-op return
            [],  # hash check fetchall → no prior rows
            None,  # INSERT (no return used)
            ("KEI-89", "Gate 2 evidence test", "done"),  # UPDATE RETURNING
        ]
    )
    conn = TrackingFakeConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setenv("CALLSIGN", "aiden")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)

    rc = mod.main(["complete", "KEI-89", "--evidence", str(ev_file)])
    assert rc == 0, capsys.readouterr().err

    # Four execute calls fired: Gate 3, hash check, INSERT task_verifications,
    # UPDATE tasks. The KEI-106 linear-sync enqueue is gone — _enqueue_linear_sync
    # is locked to a no-op under the Linear-read-only LAW (Dave 2026-05-20).
    assert len(cur.executed) == 4

    # INSERT contained the canonical JSON as test_output param
    insert_sql, insert_params = cur.executed[2]
    assert "task_verifications" in insert_sql
    assert insert_params[1] == "KEI-89"  # task_id
    assert insert_params[2] == "aiden"  # verified_by
    stored_output = insert_params[4]  # test_output
    round_tripped = json.loads(stored_output)
    assert round_tripped["acceptance_items"] == _VALID_EVIDENCE["acceptance_items"]

    # One commit fired (main complete); no rollback. The KEI-106 linear-sync
    # enqueue's separate connect+commit is gone — _enqueue_linear_sync is a
    # no-op under the Linear-read-only LAW.
    assert conn.commits == 1
    assert conn.rollbacks == 0

    # Linear-read-only LAW guard — PROVES the lock: no completion_sync_queue
    # (linear-sink) INSERT fired. _enqueue_linear_sync is a hard no-op.
    assert not any("completion_sync_queue" in sql for sql, _ in cur.executed), (
        "linear-sink enqueue must be suppressed under the Linear-read-only LAW"
    )

    out = capsys.readouterr().out
    assert "KEI-89" in out


# ─── (2) negative missing evidence ───────────────────────────────────────────


def test_negative_missing_evidence_exits_nonzero(mod, monkeypatch, capsys):
    """No --evidence flag → exits 1 with explanatory error on stderr."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setenv("CALLSIGN", "aiden")

    rc = mod.main(["complete", "KEI-89"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--evidence" in err
    assert "required" in err.lower() or "refusing" in err.lower()


# ─── (3) negative schema fail ────────────────────────────────────────────────


def test_negative_schema_fail_missing_required_field(mod, monkeypatch, tmp_path, capsys):
    """Evidence missing 'commands' field → exits 1, stderr contains
    'evidence schema invalid'.
    """
    bad_evidence = {
        "acceptance_items": ["Some item"],
        # 'commands' intentionally omitted
        "verifier_session_uuid": "uuid-xyz",
        "timestamp": "2026-05-17T10:00:00+10:00",
    }
    ev_file = tmp_path / "bad_evidence.json"
    ev_file.write_text(json.dumps(bad_evidence))

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setenv("CALLSIGN", "aiden")

    rc = mod.main(["complete", "KEI-89", "--evidence", str(ev_file)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "evidence schema invalid" in err


# ─── (4) negative hash collision ─────────────────────────────────────────────


def test_negative_hash_collision_rejects_reuse(mod, monkeypatch, tmp_path, capsys):
    """Re-using identical evidence on a different task → exits 1, stderr
    contains 'matches prior verification'.
    """
    ev_file = tmp_path / "evidence.json"
    ev_file.write_text(json.dumps(_VALID_EVIDENCE))

    canonical_str = _canonical(_VALID_EVIDENCE)

    # The hash-check SELECT returns one prior row from a different task
    # with the same canonical JSON as test_output.
    prior_row = ("KEI-88", canonical_str, "2026-05-16T08:00:00+10:00")

    cur = MultiStepCursor(
        step_responses=[
            (False, "aiden"),  # Gate 3: deployment=False → no-op return
            [prior_row],  # hash check fetchall → collision found
        ]
    )
    conn = TrackingFakeConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setenv("CALLSIGN", "aiden")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)

    rc = mod.main(["complete", "KEI-89", "--evidence", str(ev_file)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "matches prior verification" in err
    assert "KEI-88" in err

    # Gate 3 SELECT + hash-check SELECT fired; no INSERT or UPDATE
    assert len(cur.executed) == 2


# ─── (5) positive no extra side effects ──────────────────────────────────────


def test_positive_evidence_path_inserts_exactly_one_verification_row(
    mod, monkeypatch, tmp_path, capsys
):
    """Valid evidence: exactly one INSERT into task_verifications fires
    (no duplicate writes, no phantom statements).
    """
    ev_file = tmp_path / "evidence.json"
    ev_file.write_text(json.dumps(_VALID_EVIDENCE))

    cur = MultiStepCursor(
        step_responses=[
            (False, "aiden"),  # Gate 3: deployment=False → no-op return
            [],  # hash check
            None,  # INSERT
            ("KEI-89", "Side-effect test task", "done"),  # UPDATE RETURNING
        ]
    )
    conn = TrackingFakeConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setenv("CALLSIGN", "aiden")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)

    rc = mod.main(["complete", "KEI-89", "--evidence", str(ev_file)])
    assert rc == 0

    insert_calls = [
        sql for sql, _ in cur.executed if "INSERT" in sql.upper() and "task_verifications" in sql
    ]
    assert len(insert_calls) == 1, f"expected 1 INSERT, got {len(insert_calls)}: {insert_calls}"


# ─── (6) Agency_OS-y244 regression — dict-shape acceptance_items ─────────────


def test_positive_dict_acceptance_items_coerced_to_text(mod, monkeypatch, tmp_path, capsys):
    """Regression: when acceptance_items[0] is a dict ({criterion, satisfied,
    evidence}), behavioral_test must be coerced to text before SQL params bind.

    Prior to Agency_OS-y244 fix the raw dict was passed to psycopg, which
    raised `cannot adapt type 'dict' using placeholder '%s'` at the INSERT.
    Post-fix: criterion field becomes the behavioral_test string; INSERT
    binds a str cleanly.
    """
    dict_evidence = {
        "acceptance_items": [
            {
                "criterion": "PR #1045 merged after dual-concur",
                "satisfied": True,
                "evidence": "gh api .../merge returned merged=true sha=9af6197a",
            }
        ],
        "commands": [
            {
                "cmd": "gh pr view 1045 --json state",
                "output": '{"state":"MERGED"} — verified PR landed cleanly on origin/main',
            }
        ],
        "verifier_session_uuid": "session-uuid-y244-regression-test",
        "timestamp": "2026-05-18T21:20:00+00:00",
    }
    ev_file = tmp_path / "dict_evidence.json"
    ev_file.write_text(json.dumps(dict_evidence))

    cur = MultiStepCursor(
        step_responses=[
            (False, "nova"),  # Gate 3: deployment=False → no-op return
            [],
            None,
            ("KEI-y244", "Dict regression task", "done"),
        ]
    )
    conn = TrackingFakeConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setenv("CALLSIGN", "nova")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)

    rc = mod.main(["complete", "KEI-y244", "--evidence", str(ev_file)])
    assert rc == 0, capsys.readouterr().err

    _, insert_params = cur.executed[2]
    behavioral_test_param = insert_params[3]
    assert isinstance(behavioral_test_param, str), (
        f"behavioral_test must be str (text column); got {type(behavioral_test_param).__name__}"
    )
    assert behavioral_test_param == "PR #1045 merged after dual-concur"


def test_positive_dict_acceptance_items_without_criterion_falls_back_to_json(
    mod, monkeypatch, tmp_path, capsys
):
    """Dict acceptance_item missing 'criterion' key → JSON-serialise the
    whole dict so no data is lost.
    """
    dict_no_criterion = {
        "acceptance_items": [{"description": "no criterion key here", "satisfied": True}],
        "commands": [
            {
                "cmd": "synthetic test command",
                "output": "synthetic output text long enough to pass min-length validator",
            }
        ],
        "verifier_session_uuid": "session-no-criterion-fallback-uuid",
        "timestamp": "2026-05-18T21:25:00+00:00",
    }
    ev_file = tmp_path / "no_criterion_evidence.json"
    ev_file.write_text(json.dumps(dict_no_criterion))

    cur = MultiStepCursor(
        step_responses=[
            (False, "nova"),  # Gate 3: deployment=False → no-op return
            [],
            None,
            ("KEI-y244b", "Fallback task", "done"),
        ]
    )
    conn = TrackingFakeConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setenv("CALLSIGN", "nova")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)

    rc = mod.main(["complete", "KEI-y244b", "--evidence", str(ev_file)])
    assert rc == 0, capsys.readouterr().err

    _, insert_params = cur.executed[2]
    behavioral_test_param = insert_params[3]
    assert isinstance(behavioral_test_param, str)
    parsed = json.loads(behavioral_test_param)
    assert parsed == {"description": "no criterion key here", "satisfied": True}
