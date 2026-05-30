"""Agency_OS-wdcw — durable receiver-side dedup for /dispatcher/chain_complete.

Lives in src/dispatcher/main.py (NOT src/keiracom_system/) so direct psycopg
is allowed per boundary_matrix_v1 — keiracom_system is MAL-scoped, the
dispatcher is the supabase-layer caller. Replaces the in-process state-file
flag that PR #1364 added and was wiped on dispatcher restart.

  _chain_complete_already_posted(chain_id):
    - DSN unset → False (fail-open: no DB, no dedup gate, post proceeds)
    - INSERT RETURNING populated → False (we won the insert; first post)
    - INSERT RETURNING empty (conflict) → True (already posted; skip Slack)
    - Any DB error → False (fail-open; posting once-too-often beats never posting)
    - +asyncpg DSN suffix is stripped before connect (KEI-218 pattern)

  dispatcher_chain_complete (the route):
    - Ledger says "already posted" → no Slack relay, returns deduped reason
    - Ledger says "first time" → Slack relay fires; subprocess.run reached
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from unittest.mock import MagicMock

from src.dispatcher import main as dm

# ---------------------------------------------------------------------------
# Fake psycopg helpers
# ---------------------------------------------------------------------------


def _fake_psycopg(monkeypatch, *, fetchone_return, captured: dict | None = None):
    """Patch psycopg.connect → a fake conn whose cur.fetchone returns the supplied
    row. `captured` (if provided) gets {dsn, query, params}."""
    cap = captured if captured is not None else {}

    @contextmanager
    def _fake_cursor():
        cur = MagicMock()

        def _execute(query, params=None):
            cap["query"] = query
            cap["params"] = params

        cur.execute.side_effect = _execute
        cur.fetchone.return_value = fetchone_return
        yield cur

    @contextmanager
    def _fake_connect(dsn, **_kw):
        cap["dsn"] = dsn
        conn = MagicMock()
        conn.cursor.side_effect = _fake_cursor
        conn.commit = MagicMock()
        yield conn

    fake_module = MagicMock()
    fake_module.connect.side_effect = _fake_connect
    monkeypatch.setitem(__import__("sys").modules, "psycopg", fake_module)


# ---------------------------------------------------------------------------
# _chain_complete_already_posted — DSN guard + insert semantics + fail-open
# ---------------------------------------------------------------------------


def test_already_posted_returns_false_when_dsn_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert dm._chain_complete_already_posted("c-1") is False


def test_already_posted_first_call_returning_row_is_false(monkeypatch):
    """RETURNING populated → we inserted (first post) → caller proceeds."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    _fake_psycopg(monkeypatch, fetchone_return=("c-2",))
    assert dm._chain_complete_already_posted("c-2") is False


def test_already_posted_conflict_returning_empty_is_true(monkeypatch):
    """RETURNING None (ON CONFLICT DO NOTHING fired) → already posted → skip."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    _fake_psycopg(monkeypatch, fetchone_return=None)
    assert dm._chain_complete_already_posted("c-3") is True


def test_already_posted_strips_asyncpg_suffix(monkeypatch):
    """DSN with +asyncpg gets stripped before psycopg connect (KEI-218 pattern)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    captured: dict = {}
    _fake_psycopg(monkeypatch, fetchone_return=("c-4",), captured=captured)
    dm._chain_complete_already_posted("c-4")
    assert "+asyncpg" not in captured["dsn"]
    assert captured["dsn"] == "postgresql://u:p@h/db"


def test_already_posted_uses_insert_on_conflict_returning(monkeypatch):
    """SQL shape pinned: INSERT ... ON CONFLICT DO NOTHING RETURNING chain_id."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    captured: dict = {}
    _fake_psycopg(monkeypatch, fetchone_return=("c-5",), captured=captured)
    dm._chain_complete_already_posted("c-5")
    assert "INSERT INTO public.keiracom_chain_complete_posted" in captured["query"]
    assert "ON CONFLICT (chain_id) DO NOTHING" in captured["query"]
    assert "RETURNING chain_id" in captured["query"]
    assert captured["params"] == ("c-5",)


def test_already_posted_fail_open_on_db_error(monkeypatch):
    """Any psycopg error → returns False (fail-open: caller posts anyway)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    fake_module = MagicMock()
    fake_module.connect.side_effect = OSError("db unreachable")
    monkeypatch.setitem(__import__("sys").modules, "psycopg", fake_module)
    assert dm._chain_complete_already_posted("c-6") is False


# ---------------------------------------------------------------------------
# dispatcher_chain_complete route — dedup gate wires before Slack relay
# ---------------------------------------------------------------------------


def test_dispatcher_chain_complete_skips_slack_when_ledger_says_already_posted(monkeypatch):
    """Ledger hit → no subprocess.run; response carries deduped reason."""
    monkeypatch.setattr(dm, "_chain_complete_already_posted", lambda _cid: True)

    def explode(*a, **kw):
        raise AssertionError("subprocess.run must NOT be called when dedup hits")

    monkeypatch.setattr("subprocess.run", explode)

    req = dm.ChainCompleteRequest(task_id="t-7", chain_id="c-7", brief="x", steps=[])
    resp = asyncio.run(dm.dispatcher_chain_complete(req))
    assert resp == {"notified": False, "reason": "deduped_already_posted"}


def test_dispatcher_chain_complete_fires_slack_when_ledger_says_first_time(monkeypatch):
    """Ledger says first time (False) → subprocess.run IS called with the relay cmd."""
    monkeypatch.setattr(dm, "_chain_complete_already_posted", lambda _cid: False)
    # avoid the cost-lookup hitting Supabase in tests
    monkeypatch.setattr(dm, "_lookup_chain_cost_aud", lambda _tid: None)

    captured: dict = {}

    def fake_run(cmd, *, capture_output, text, timeout, env):  # noqa: ARG001
        captured["cmd"] = cmd
        captured["channel"] = cmd[cmd.index("-c") + 1] if "-c" in cmd else None
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        return result

    monkeypatch.setattr("subprocess.run", fake_run)

    req = dm.ChainCompleteRequest(
        task_id="t-8", chain_id="c-8", brief="scaffold auth", steps=["aiden_plan"]
    )
    resp = asyncio.run(dm.dispatcher_chain_complete(req))
    assert resp == {"notified": True}
    # ceo channel + the chain summary in the message
    assert captured["channel"] == "ceo"
    msg = captured["cmd"][-1]
    assert "Chain complete" in msg and "c-8" in msg and "scaffold auth" in msg
