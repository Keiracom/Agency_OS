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
from typing import Any

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


class _Cursor:
    def __init__(
        self,
        fetchall_rows: list[tuple] | None = None,
        fetchone_row: tuple | None = None,
        description: list[tuple] | None = None,
    ) -> None:
        self._all = fetchall_rows or []
        self._one = fetchone_row
        self.description = [type("col", (), {"name": c[0]})() for c in (description or [])]
        self.last_sql: str = ""
        self.last_params: tuple | None = None

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.last_sql = sql
        self.last_params = params

    def fetchall(self) -> list[tuple]:
        return self._all

    def fetchone(self) -> tuple | None:
        return self._one

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, *a: Any) -> None:
        # Context-manager protocol; the in-memory fake has nothing to clean up.
        return None


class _Conn:
    def __init__(self, cur: _Cursor) -> None:
        self._cur = cur
        self.commits = 0

    def cursor(self) -> _Cursor:
        return self._cur

    def commit(self) -> None:
        self.commits += 1

    def __enter__(self) -> _Conn:
        return self

    def __exit__(self, *a: Any) -> None:
        # Context-manager protocol; the in-memory fake has nothing to clean up.
        return None


@pytest.fixture
def patch_connect(mod, monkeypatch):
    """Return a builder that installs a fake psycopg.connect returning _Conn(cur)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")

    def _patch(cur: _Cursor):
        import psycopg

        monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: _Conn(cur))
        # Re-import after monkeypatch so the module's `import psycopg` picks it up.
        return cur

    return _patch


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


def test_ready_clamps_limit_argument(mod, patch_connect) -> None:
    cur = _Cursor(fetchall_rows=[], description=[("id",)])
    patch_connect(cur)
    mod.main(["ready", "--limit", "9999"])
    # Last param should be the clamped value (250 max).
    assert cur.last_params == (250,)


# ─── ready --agent (KEI-53 Phase B) ───────────────────────────────────────────


def test_ready_agent_uses_personalised_sql_path(mod, patch_connect) -> None:
    """--agent <callsign> triggers the agent_profiles JOIN + personalised_score column."""
    cur = _Cursor(fetchall_rows=[], description=[("id",), ("personalised_score",)])
    patch_connect(cur)
    rc = mod.main(["ready", "--agent", "elliot", "--limit", "10"])
    assert rc == 0
    # Personalised SQL references agent_profiles and personalised_score.
    assert "agent_profiles" in cur.last_sql
    assert "personalised_score" in cur.last_sql
    # Params: (callsign, limit) — lowercased callsign.
    assert cur.last_params == ("elliot", 10)


def test_ready_agent_lowercases_callsign(mod, patch_connect) -> None:
    cur = _Cursor(fetchall_rows=[], description=[("id",)])
    patch_connect(cur)
    mod.main(["ready", "--agent", "ELLIOT"])
    assert cur.last_params[0] == "elliot"


def test_ready_agent_emits_personalised_score_in_json(mod, patch_connect, capsys) -> None:
    """JSON output preserves existing keys + adds personalised_score per Max note #3."""
    cur = _Cursor(
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
                1.7,
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
    patch_connect(cur)
    rc = mod.main(["ready", "--agent", "elliot", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    # Existing keys preserved.
    assert data[0]["id"] == "KEI-63"
    assert data[0]["title"] == "deprecation"
    assert data[0]["priority"] == 1
    # New key added.
    # pytest.approx avoids Sonar S1244 float-equality finding
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
    cur = _Cursor(
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
                1.7,
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
    patch_connect(cur)
    mod.main(["ready", "--agent", "elliot"])
    out = capsys.readouterr().out
    assert "[score=1.70]" in out
    assert "personalised for elliot" in out


# ─── claim ────────────────────────────────────────────────────────────────────


def test_claim_targeted_id(mod, patch_connect, capsys, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=("KEI-39", "title", 1, "active", "scout", "url"))
    patch_connect(cur)
    rc = mod.main(["claim", "--id", "KEI-39", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "KEI-39"
    assert out["claimed_by"] == "scout"
    assert cur.last_params == ("scout", "KEI-39", "scout")


def test_claim_next_available_uses_skip_locked(mod, patch_connect, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=("KEI-39", "title", 1, "active", "scout", "url"))
    patch_connect(cur)
    rc = mod.main(["claim", "--json"])
    assert rc == 0
    assert "FOR UPDATE SKIP LOCKED" in cur.last_sql


def test_claim_returns_null_when_nothing_available(mod, patch_connect, capsys, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=None)
    patch_connect(cur)
    rc = mod.main(["claim", "--json"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "null"


# ─── complete ────────────────────────────────────────────────────────────────


def test_complete_strict_returns_done(mod, patch_connect, capsys, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=("KEI-39", "title", "done"))
    patch_connect(cur)
    rc = mod.main(["complete", "KEI-39", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "done"


def test_complete_strict_fails_when_not_claimed_by_caller(
    mod, patch_connect, capsys, monkeypatch
) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=None)
    patch_connect(cur)
    rc = mod.main(["complete", "KEI-39", "--json"])
    assert rc == 1
    assert capsys.readouterr().out.strip() == "null"


def test_complete_force_mode_passes_force_sentinel(mod, patch_connect, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = _Cursor(fetchone_row=("KEI-39", "title", "done"))
    patch_connect(cur)
    mod.main(["complete", "KEI-39", "--force-mode", "force"])
    assert cur.last_params == ("KEI-39", "scout", "force")


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
