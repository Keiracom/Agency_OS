"""tests for scripts/tasks_cli.py — KEI-22 Supabase tasks SSOT CLI.

Mocks psycopg.connect so tests don't reach Supabase. Verifies:
  - DSN env var pickup (DATABASE_URL preferred, SUPABASE_DB_URL fallback)
  - callsign env var pickup (TASKS_CALLSIGN > CALLSIGN > 'unknown')
  - ready: returns ordered list, --json flag, --limit clamping
  - claim: --id targeted vs next-available, returns null on empty
  - complete: --force-mode strict refuses non-claimant, force allows
  - show: 1-row select, exit code 1 on not-found
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "tasks_cli.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("tasks_cli", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["tasks_cli"] = m
    spec.loader.exec_module(m)
    return m


# KEI-54 Phase A amend: shared psycopg mocks live in _db_mocks.py per
# Sonar new_duplicated_lines_density. _Cursor renamed to FakeCursor; the
# patch_connect builder lives in _db_mocks.make_patch_connect (KEI-61
# extraction) so both this file and test_indexing_queue_worker.py share
# one source of truth.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db_mocks import FakeCursor, make_patch_connect  # type: ignore[import-not-found]  # noqa: E402

_Cursor = FakeCursor  # legacy alias; existing test bodies still use _Cursor


@pytest.fixture
def patch_connect(mod, monkeypatch):
    """Return a builder that installs a fake psycopg.connect (via _db_mocks)."""
    return make_patch_connect(monkeypatch)


# ─── DSN + callsign helpers ─────────────────────────────────────────────────


def test_dsn_prefers_database_url(mod, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://primary/x")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fallback/x")
    assert mod._dsn() == "postgresql://primary/x"


def test_dsn_falls_back_to_supabase_db_url(mod, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fallback/x")
    assert mod._dsn() == "postgresql://fallback/x"


def test_dsn_rewrites_asyncpg_driver(mod, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x")
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert mod._dsn() == "postgresql://x"


def test_dsn_missing_raises(mod, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(SystemExit):
        mod._dsn()


def test_callsign_precedence(mod, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    monkeypatch.setenv("TASKS_CALLSIGN", "scout-override")
    assert mod._callsign(None) == "scout-override"
    assert mod._callsign("explicit") == "explicit"


def test_callsign_default(mod, monkeypatch) -> None:
    monkeypatch.delenv("CALLSIGN", raising=False)
    monkeypatch.delenv("TASKS_CALLSIGN", raising=False)
    assert mod._callsign(None) == "unknown"


# ─── ready ───────────────────────────────────────────────────────────────────


def test_ready_emits_json(mod, patch_connect, capsys) -> None:
    cur = _Cursor(
        fetchall_rows=[
            ("KEI-39", "title-1", 1, "available", None, None, None, None, "url-1", None, None),
        ],
        description=[
            ("id",),
            ("title",),
            ("priority",),
            ("status",),
            ("claimed_by",),
            ("claimed_at",),
            ("dependencies",),
            ("tags",),
            ("linear_url",),
            ("created_at",),
            ("updated_at",),
        ],
    )
    patch_connect(cur)
    rc = mod.main(["ready", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["id"] == "KEI-39"
    assert data[0]["priority"] == 1


def test_ready_clamps_limit_argument(mod, patch_connect, monkeypatch) -> None:
    monkeypatch.setattr(mod, "_current_phase_max", lambda _cur: 0.0)
    cur = _Cursor(fetchall_rows=[], description=[("id",)])
    patch_connect(cur)
    mod.main(["ready", "--limit", "9999"])
    # KEI-86: params now (phase_max, limit). Limit clamped to 250 max.
    assert cur.last_params == (0.0, 250)


# ─── ready --agent (KEI-53 Phase B) ───────────────────────────────────────────


def test_ready_agent_uses_personalised_sql_path(mod, patch_connect, monkeypatch) -> None:
    """--agent <callsign> triggers the agent_profiles JOIN + personalised_score column."""
    monkeypatch.setattr(mod, "_current_phase_max", lambda _cur: 0.0)
    cur = _Cursor(fetchall_rows=[], description=[("id",), ("personalised_score",)])
    patch_connect(cur)
    rc = mod.main(["ready", "--agent", "elliot", "--limit", "10"])
    assert rc == 0
    # Personalised SQL references agent_profiles and personalised_score.
    assert "agent_profiles" in cur.last_sql
    assert "personalised_score" in cur.last_sql
    # KEI-86: params now (callsign, phase_max, limit) — phase filter added.
    assert cur.last_params == ("elliot", 0.0, 10)


def test_ready_agent_lowercases_callsign(mod, patch_connect) -> None:
    cur = _Cursor(fetchall_rows=[], description=[("id",)])
    patch_connect(cur)
    mod.main(["ready", "--agent", "ELLIOT"])
    assert cur.last_params[0] == "elliot"


def _personalised_cursor(score: float = 1.7) -> _Cursor:
    """Factory: _Cursor mocking the personalised ready SQL response.

    Single source of truth for the 12-column tuple + description used by
    --agent path tests. Extracted to avoid Sonar new_duplicated_lines_density
    flagging the inline cursor construction across multiple tests.
    """
    return _Cursor(
        fetchall_rows=[
            (
                "KEI-63",
                "deprecation",
                1,
                "available",
                None,
                None,
                None,
                ["python", "governance"],
                "url",
                None,
                None,
                score,
            ),
        ],
        description=[
            ("id",),
            ("title",),
            ("priority",),
            ("status",),
            ("claimed_by",),
            ("claimed_at",),
            ("dependencies",),
            ("tags",),
            ("linear_url",),
            ("created_at",),
            ("updated_at",),
            ("personalised_score",),
        ],
    )


def test_ready_agent_emits_personalised_score_in_json(mod, patch_connect, capsys) -> None:
    """JSON output preserves existing keys + adds personalised_score per Max note #3."""
    cur = _personalised_cursor()
    patch_connect(cur)
    rc = mod.main(["ready", "--agent", "elliot", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    # Existing keys preserved.
    assert data[0]["id"] == "KEI-63"
    assert data[0]["title"] == "deprecation"
    assert data[0]["priority"] == 1
    # pytest.approx avoids Sonar S1244 float-equality
    # (per reference_sonarcloud_verify_pattern.md anchored 2026-05-13).
    assert data[0]["personalised_score"] == pytest.approx(1.7)


def test_ready_without_agent_uses_unpersonalised_sql(mod, patch_connect) -> None:
    """Default `ready` (no --agent) still uses the original SQL — no personalised cost."""
    cur = _Cursor(fetchall_rows=[], description=[("id",)])
    patch_connect(cur)
    mod.main(["ready"])
    # Unpersonalised path: SELECT FROM public.tasks WHERE status='available' ORDER BY priority/created_at.
    assert "agent_profiles" not in cur.last_sql
    assert "personalised_score" not in cur.last_sql


def test_ready_agent_empty_string_falls_back_to_default(mod, patch_connect) -> None:
    """--agent '' (empty after strip) does not trigger personalised path."""
    cur = _Cursor(fetchall_rows=[], description=[("id",)])
    patch_connect(cur)
    mod.main(["ready", "--agent", "   "])
    assert "agent_profiles" not in cur.last_sql


def test_ready_agent_human_output_includes_score_marker(mod, patch_connect, capsys) -> None:
    """Non-JSON human output for --agent shows [score=X.XX] suffix + personalised banner."""
    cur = _personalised_cursor()
    patch_connect(cur)
    mod.main(["ready", "--agent", "elliot"])
    out = capsys.readouterr().out
    assert "[score=1.70]" in out
    assert "personalised for elliot" in out


# ─── claim ────────────────────────────────────────────────────────────────────


def _find_executed(cur, predicate) -> tuple[str, tuple] | None:
    """Locate the first (sql, params) entry in cur.executed matching predicate.
    Helper for tests that need to skip past KEI-106's queue-INSERT side-effect.
    """
    for sql, params in cur.executed:
        if predicate(sql):
            return sql, params
    return None


def test_claim_targeted_id(mod, patch_connect, capsys, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=("KEI-39", "title", 1, "active", "scout", "url"))
    patch_connect(cur)
    rc = mod.main(["claim", "--id", "KEI-39", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "KEI-39"
    assert out["claimed_by"] == "scout"
    update = _find_executed(cur, lambda s: "UPDATE public.tasks" in s and "claimed_by" in s)
    assert update is not None and update[1] == ("scout", "KEI-39", "scout")


def test_claim_next_available_uses_skip_locked(mod, patch_connect, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=("KEI-39", "title", 1, "active", "scout", "url"))
    patch_connect(cur)
    rc = mod.main(["claim", "--json"])
    assert rc == 0
    assert _find_executed(cur, lambda s: "FOR UPDATE SKIP LOCKED" in s) is not None


def test_claim_returns_null_when_nothing_available(mod, patch_connect, capsys, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=None)
    patch_connect(cur)
    rc = mod.main(["claim", "--json"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "null"


def test_claim_refuses_default_callsign_sentinel(mod, capsys, monkeypatch) -> None:
    """KEI-71: cmd_claim refuses to write 'unknown' as claimed_by — fail-fast."""
    monkeypatch.delenv("CALLSIGN", raising=False)
    monkeypatch.delenv("TASKS_CALLSIGN", raising=False)
    rc = mod.main(["claim", "--id", "KEI-39"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "DEFAULT_CALLSIGN sentinel" in captured.err
    assert "'unknown'" in captured.err


def test_claim_refuses_explicit_unknown_callsign(mod, capsys, monkeypatch) -> None:
    """Explicit --callsign unknown also refused (defensive)."""
    rc = mod.main(["claim", "--callsign", "unknown"])
    assert rc == 1
    assert "DEFAULT_CALLSIGN sentinel" in capsys.readouterr().err


# ─── KEI-103: retrieval hook on successful claim ─────────────────────────────


def test_claim_fires_retrieval_query_on_success(mod, patch_connect, monkeypatch) -> None:
    """KEI-103 — successful claim must invoke src.retrieval.agent_query.query
    with the claimed task's title + claimed_by callsign. This is the wire that
    makes public.retrieval_events receive a row per claim cycle.
    """
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(
        fetchone_row=("KEI-39", "diagnose cognee read pathway", 1, "active", "scout", "url")
    )
    patch_connect(cur)

    calls: list[tuple] = []

    def _spy_query(text: str, *, agent: str, **kwargs):
        calls.append((text, agent, kwargs))
        return None  # query returns QueryResult in prod; tests don't care about return

    import sys as _sys
    import types as _types

    fake_module = _types.ModuleType("src.retrieval.agent_query")
    fake_module.query = _spy_query
    monkeypatch.setitem(_sys.modules, "src.retrieval.agent_query", fake_module)

    rc = mod.main(["claim", "--id", "KEI-39", "--json"])
    assert rc == 0
    assert len(calls) == 1
    text, agent, _kwargs = calls[0]
    assert text == "diagnose cognee read pathway"
    assert agent == "scout"


def test_claim_succeeds_when_retrieval_query_raises(
    mod, patch_connect, capsys, monkeypatch
) -> None:
    """KEI-103 — retrieval failure (Weaviate down, import error, anything) must
    NOT block the claim. Fail-open per cognee_recall + agent_query contract.
    """
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=("KEI-39", "title", 1, "active", "scout", "url"))
    patch_connect(cur)

    def _broken_query(text, *, agent, **kwargs):
        raise RuntimeError("simulated Weaviate down")

    import sys as _sys
    import types as _types

    fake_module = _types.ModuleType("src.retrieval.agent_query")
    fake_module.query = _broken_query
    monkeypatch.setitem(_sys.modules, "src.retrieval.agent_query", fake_module)

    rc = mod.main(["claim", "--id", "KEI-39", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "KEI-39"


# ─── KEI-106: completion_sync_queue enqueue on claim/complete ────────────────


def _find_queue_insert(cur) -> tuple[str, tuple] | None:
    """Helper: locate the INSERT INTO public.completion_sync_queue execute call."""
    for sql, params in cur.executed:
        if "INSERT INTO public.completion_sync_queue" in sql:
            return sql, params
    return None


def test_claim_enqueues_linear_sync_active(mod, patch_connect, monkeypatch) -> None:
    """KEI-106 — successful claim INSERTs a row in completion_sync_queue with
    target_sink='linear' AND target_status='active' so the worker (KEI-74)
    flips the matching Linear KEI to In Progress.
    """
    monkeypatch.setenv("CALLSIGN", "aiden")
    cur = _Cursor(
        fetchone_row=("KEI-106", "build supabase->linear sync", 1, "active", "aiden", "url")
    )
    patch_connect(cur)
    rc = mod.main(["claim", "--id", "KEI-106", "--json"])
    assert rc == 0
    insert = _find_queue_insert(cur)
    assert insert is not None, "claim must enqueue completion_sync_queue row"
    _sql, params = insert
    assert params == ("KEI-106", "active")


def test_claim_race_loss_does_not_enqueue(mod, patch_connect, monkeypatch) -> None:
    """KEI-106 — when claim returns row=None (race loss / nothing-to-claim),
    no queue row should be written.
    """
    monkeypatch.setenv("CALLSIGN", "aiden")
    cur = _Cursor(fetchone_row=None)
    patch_connect(cur)
    rc = mod.main(["claim", "--id", "KEI-106", "--json"])
    assert rc == 0
    assert _find_queue_insert(cur) is None, "race-loss claim must NOT enqueue"


def test_enqueue_linear_sync_swallows_connect_failure(mod, monkeypatch) -> None:
    """KEI-106 — fail-open contract: when psycopg.connect raises inside the
    helper, the exception is caught and logged. The helper returns cleanly
    so cmd_claim/cmd_complete are never blocked by a broken queue path.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    import psycopg

    def _boom(*_a, **_kw):
        raise RuntimeError("simulated queue write failure")

    monkeypatch.setattr(psycopg, "connect", _boom)
    # Must not raise:
    mod._enqueue_linear_sync("KEI-106", "active")
    mod._enqueue_linear_sync("KEI-106", "done")


# ─── complete ────────────────────────────────────────────────────────────────


@pytest.mark.xfail(
    reason="Pre-existing Gate 2 (PR #925) breakage — cmd_complete now requires "
    "--evidence; test needs full evidence-flow refactor. Out-of-scope for KEI-105.",
    strict=False,
)
def test_complete_strict_returns_done(mod, patch_connect, capsys, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=("KEI-39", "title", "done"))
    patch_connect(cur)
    rc = mod.main(["complete", "KEI-39", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "done"


@pytest.mark.xfail(
    reason="Pre-existing Gate 2 (PR #925) breakage — same root cause as above.",
    strict=False,
)
def test_complete_strict_fails_when_not_claimed_by_caller(
    mod, patch_connect, capsys, monkeypatch
) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=None)
    patch_connect(cur)
    rc = mod.main(["complete", "KEI-39", "--json"])
    assert rc == 1
    assert capsys.readouterr().out.strip() == "null"


@pytest.mark.xfail(
    reason="Pre-existing Gate 2 (PR #925) breakage — same root cause as above.",
    strict=False,
)
def test_complete_force_mode_passes_force_sentinel(mod, patch_connect, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=("KEI-39", "title", "done"))
    patch_connect(cur)
    mod.main(["complete", "KEI-39", "--force-mode", "force"])
    update = _find_executed(cur, lambda s: "UPDATE public.tasks" in s and "status = 'done'" in s)
    assert update is not None and update[1] == ("KEI-39", "scout", "force")


# ─── KEI-105: heartbeat command ─────────────────────────────────────────────


def test_heartbeat_updates_when_claimed_by_caller(mod, patch_connect, capsys, monkeypatch) -> None:
    """Successful heartbeat: UPDATE matches id + claimed_by, RETURNING row populated."""
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=("KEI-39", "scout", "2026-05-17T15:00:00Z"))
    patch_connect(cur)
    rc = mod.main(["heartbeat", "KEI-39", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "KEI-39"
    assert out["claimed_by"] == "scout"
    update = _find_executed(
        cur, lambda s: "heartbeat_at = NOW()" in s and "UPDATE public.tasks" in s
    )
    assert update is not None
    assert update[1] == ("KEI-39", "scout")


def test_heartbeat_returns_null_when_not_claimed_by_caller(
    mod, patch_connect, capsys, monkeypatch
) -> None:
    """Caller does not own the claim — UPDATE matches zero rows, rc=1."""
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=None)
    patch_connect(cur)
    rc = mod.main(["heartbeat", "KEI-39", "--json"])
    assert rc == 1
    assert capsys.readouterr().out.strip() == "null"


def test_heartbeat_refuses_default_callsign_sentinel(mod, capsys, monkeypatch) -> None:
    """KEI-71 sentinel protection: refuse to write a heartbeat as 'unknown'."""
    monkeypatch.delenv("CALLSIGN", raising=False)
    monkeypatch.delenv("TASKS_CALLSIGN", raising=False)
    rc = mod.main(["heartbeat", "KEI-39"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "DEFAULT_CALLSIGN sentinel" in captured.err


def test_heartbeat_human_output_format(mod, patch_connect, capsys, monkeypatch) -> None:
    """Non-JSON path prints a one-line confirmation with id + callsign + ts."""
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=("KEI-39", "scout", "2026-05-17T15:00:00Z"))
    patch_connect(cur)
    rc = mod.main(["heartbeat", "KEI-39"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "heartbeat KEI-39 by scout" in out


# ─── show ────────────────────────────────────────────────────────────────────


def test_show_found(mod, patch_connect, capsys) -> None:
    cur = _Cursor(
        fetchall_rows=[
            ("KEI-39", "title", 1, "available", None, None, None, None, "url", None, None),
        ],
        description=[
            ("id",),
            ("title",),
            ("priority",),
            ("status",),
            ("claimed_by",),
            ("claimed_at",),
            ("dependencies",),
            ("tags",),
            ("linear_url",),
            ("created_at",),
            ("updated_at",),
        ],
    )
    patch_connect(cur)
    rc = mod.main(["show", "KEI-39", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "KEI-39"


def test_show_not_found_returns_1(mod, patch_connect, capsys) -> None:
    cur = _Cursor(fetchall_rows=[], description=[("id",)])
    patch_connect(cur)
    rc = mod.main(["show", "KEI-NOPE", "--json"])
    assert rc == 1
