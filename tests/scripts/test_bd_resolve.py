"""KEI-79 — behavioural tests for bd resolve (flip awaiting → resolved + restore task active).

Test matrix:
  - happy path: awaiting decision + valid pick → resolved, task active, exit 0
  - negative: no awaiting decision → exit 2, "no awaiting decision" in stderr
  - negative: pick not in options → exit 2, "not in options" in stderr
  - fail-soft: task not in 'escalated' state → ceo_decisions resolved, task WHERE guard no-ops
  - slack failure: post_to_ceo raises → still exit 0 (fail-open)
  - transaction atomicity: if apply_resolve raises mid-way, tasks UPDATE rolls back
  - helper unit tests: _sanitize, _callsign, _build_ceo_text, _dsn
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts import bd_resolve  # noqa: E402
from tests.scripts._db_mocks import FakeConn, FakeCursor, make_patch_connect  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def patch_connect(monkeypatch: Any) -> Any:
    return make_patch_connect(monkeypatch)


# ---------------------------------------------------------------------------
# Unit tests — pure helpers (no psycopg)
# ---------------------------------------------------------------------------


def test_sanitize_strips_newlines() -> None:
    assert bd_resolve._sanitize("foo\nbar\rbaz") == "foo bar baz"


def test_sanitize_empty_string() -> None:
    assert bd_resolve._sanitize("") == ""


def test_callsign_explicit_override() -> None:
    assert bd_resolve._callsign("max") == "max"


def test_callsign_env_fallback(monkeypatch: Any) -> None:
    monkeypatch.delenv("CALLSIGN", raising=False)
    monkeypatch.delenv("TASKS_CALLSIGN", raising=False)
    assert bd_resolve._callsign() == "dave"
    monkeypatch.setenv("TASKS_CALLSIGN", "scout")
    assert bd_resolve._callsign() == "scout"
    monkeypatch.setenv("CALLSIGN", "elliot")
    assert bd_resolve._callsign() == "elliot"


def test_build_ceo_text_no_outcome() -> None:
    text = bd_resolve._build_ceo_text("dave", "KEI-79", "A", None)
    assert "[RESOLVED:dave]" in text
    assert "KEI-79" in text
    assert "Decision: A" in text
    assert "Outcome" not in text


def test_build_ceo_text_with_outcome() -> None:
    text = bd_resolve._build_ceo_text("dave", "KEI-79", "B", "use option B")
    assert "Outcome: use option B" in text


def test_dsn_strips_asyncpg(monkeypatch: Any) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://host/db")
    assert "+asyncpg" not in bd_resolve._dsn()


def test_dsn_raises_when_unset(monkeypatch: Any) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(RuntimeError):
        bd_resolve._dsn()


# ---------------------------------------------------------------------------
# Unit tests — fetch_awaiting_decision
# ---------------------------------------------------------------------------


def test_fetch_awaiting_decision_returns_id_and_options() -> None:
    cur = FakeCursor(fetchone_row=("uuid-abc", ["Retry", "Abort"]))
    decision_id, options = bd_resolve.fetch_awaiting_decision(cur, "KEI-79")
    assert decision_id == "uuid-abc"
    assert options == ["Retry", "Abort"]


def test_fetch_awaiting_decision_no_row_exits_2() -> None:
    cur = FakeCursor(fetchone_row=None)
    with pytest.raises(SystemExit) as exc_info:
        bd_resolve.fetch_awaiting_decision(cur, "KEI-79")
    assert exc_info.value.code == 2


def test_fetch_awaiting_decision_none_options_returns_empty_list() -> None:
    cur = FakeCursor(fetchone_row=("uuid-xyz", None))
    _, options = bd_resolve.fetch_awaiting_decision(cur, "KEI-79")
    assert options == []


# ---------------------------------------------------------------------------
# Unit tests — validate_pick
# ---------------------------------------------------------------------------


def test_validate_pick_in_options_passes() -> None:
    bd_resolve.validate_pick("Retry", ["Retry", "Abort"], "KEI-79")  # no exception


def test_validate_pick_not_in_options_exits_2(capsys: Any) -> None:
    with pytest.raises(SystemExit) as exc_info:
        bd_resolve.validate_pick("Unknown", ["Retry", "Abort"], "KEI-79")
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "not in options" in captured.err


def test_validate_pick_empty_options_passes() -> None:
    # When no options declared, any pick is valid (free-form decision).
    bd_resolve.validate_pick("anything", [], "KEI-79")


# ---------------------------------------------------------------------------
# Unit tests — apply_resolve SQL shapes
# ---------------------------------------------------------------------------


def test_apply_resolve_writes_correct_sql() -> None:
    cur = FakeCursor()
    bd_resolve.apply_resolve(cur, "dec-1", "KEI-79", "Retry", "go again", "dave")

    assert len(cur.executed) == 2
    # First UPDATE: ceo_decisions
    sql0, params0 = cur.executed[0]
    assert "ceo_decisions" in sql0
    assert "status='resolved'" in sql0
    assert params0 == ("Retry", "go again", "dave", "dec-1")
    # Second UPDATE: tasks
    sql1, params1 = cur.executed[1]
    assert "public.tasks" in sql1
    assert "status='active'" in sql1
    assert "status='escalated'" in sql1  # WHERE guard
    assert params1 == ("KEI-79",)


def test_apply_resolve_null_outcome() -> None:
    cur = FakeCursor()
    bd_resolve.apply_resolve(cur, "dec-1", "KEI-79", "A", None, "dave")
    _, params0 = cur.executed[0]
    assert params0[1] is None  # decision_outcome


# ---------------------------------------------------------------------------
# Integration — resolve() function via monkeypatched psycopg
# ---------------------------------------------------------------------------


def _make_args(
    task: str = "KEI-79",
    pick: str = "Retry",
    outcome: str | None = None,
    callsign: str | None = None,
) -> types.SimpleNamespace:
    return types.SimpleNamespace(task=task, pick=pick, outcome=outcome, callsign=callsign)


def test_happy_path_exits_0(monkeypatch: Any, capsys: Any) -> None:
    """awaiting decision + valid pick → resolved, exit 0, JSON stdout."""
    cur = FakeCursor(fetchone_row=("dec-uuid", ["Retry", "Abort"]))
    conn = FakeConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)
    monkeypatch.setattr(bd_resolve, "_post_resolution", lambda *a, **k: None)

    result = bd_resolve.resolve(_make_args(pick="Retry"))
    assert result == 0
    assert conn.commits == 1

    out = capsys.readouterr().out
    data = __import__("json").loads(out)
    assert data["task_id"] == "KEI-79"
    assert data["pick"] == "Retry"


def test_no_awaiting_decision_exits_2(monkeypatch: Any) -> None:
    """When no awaiting row exists, exit 2."""
    cur = FakeCursor(fetchone_row=None)
    conn = FakeConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)

    with pytest.raises(SystemExit) as exc_info:
        bd_resolve.resolve(_make_args())
    assert exc_info.value.code == 2


def test_no_awaiting_decision_stderr_message(monkeypatch: Any, capsys: Any) -> None:
    cur = FakeCursor(fetchone_row=None)
    conn = FakeConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)

    with pytest.raises(SystemExit):
        bd_resolve.resolve(_make_args())
    assert "no awaiting decision" in capsys.readouterr().err


def test_pick_not_in_options_exits_2(monkeypatch: Any, capsys: Any) -> None:
    """Pick value not in declared options → exit 2, 'not in options' in stderr."""
    cur = FakeCursor(fetchone_row=("dec-uuid", ["Retry", "Abort"]))
    conn = FakeConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)

    with pytest.raises(SystemExit) as exc_info:
        bd_resolve.resolve(_make_args(pick="UnknownOption"))
    assert exc_info.value.code == 2
    assert "not in options" in capsys.readouterr().err


def test_task_not_escalated_fails_soft(monkeypatch: Any) -> None:
    """Policy: if task is NOT in 'escalated' state the WHERE guard on tasks
    UPDATE silently no-ops — ceo_decisions still resolved (commit still
    happens). Simulated by the cursor being correctly formed; the WHERE guard
    is enforced by the DB not by Python, so we just assert commit still fires.
    """
    cur = FakeCursor(fetchone_row=("dec-uuid", ["A", "B"]))
    conn = FakeConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)
    monkeypatch.setattr(bd_resolve, "_post_resolution", lambda *a, **k: None)

    result = bd_resolve.resolve(_make_args(pick="A"))
    assert result == 0
    assert conn.commits == 1
    # Both SQL statements were still sent (guard is in SQL WHERE, not Python)
    assert any("public.tasks" in sql for sql, _ in cur.executed)


def test_slack_failure_still_exits_0(monkeypatch: Any) -> None:
    """If post_to_ceo raises, resolve must still exit 0 (fail-open)."""
    cur = FakeCursor(fetchone_row=("dec-uuid", ["A"]))
    conn = FakeConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)

    def boom(*a: Any, **k: Any) -> None:
        raise RuntimeError("slack 503")

    monkeypatch.setattr(bd_resolve, "_post_resolution", boom)

    result = bd_resolve.resolve(_make_args(pick="A"))
    assert result == 0


def test_slack_failure_warn_to_stderr(monkeypatch: Any, capsys: Any) -> None:
    """Slack failure prints 'warn: ceo post failed:' to stderr, exit 0."""
    cur = FakeCursor(fetchone_row=("dec-uuid", ["A"]))
    conn = FakeConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)

    # Patch _post_resolution to raise — resolve() must swallow and warn
    monkeypatch.setattr(
        bd_resolve,
        "_post_resolution",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("rate limit")),
    )
    result = bd_resolve.resolve(_make_args(pick="A"))
    assert result == 0
    assert "warn: ceo post failed" in capsys.readouterr().err


def test_transaction_atomicity_on_exception(monkeypatch: Any) -> None:
    """If apply_resolve raises mid-transaction, rollback fires and exit is 1.

    We simulate this by making the cursor's second execute() raise; a real
    psycopg conn would rollback on __exit__. FakeConn doesn't auto-rollback
    but we track commits — zero commits means the write never landed.
    """

    class ExplodingCursor(FakeCursor):
        def __init__(self) -> None:
            super().__init__(fetchone_row=("dec-uuid", ["A", "B"]))
            self._execute_count = 0

        def execute(self, sql: str, params: Any = None) -> None:
            self._execute_count += 1
            if self._execute_count == 2:
                # Simulate DB error on second UPDATE (tasks)
                raise RuntimeError("DB constraint violation")
            super().execute(sql, params)

    cur = ExplodingCursor()

    class RollbackConn(FakeConn):
        def __init__(self, c: Any) -> None:
            super().__init__(c)
            self.rolled_back = False

        def __exit__(self, *a: Any) -> None:
            self.rolled_back = True

    conn = RollbackConn(cur)

    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: conn)

    result = bd_resolve.resolve(_make_args(pick="A"))
    assert result == 1
    assert conn.commits == 0  # commit never called because exception raised first
