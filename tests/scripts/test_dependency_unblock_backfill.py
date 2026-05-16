"""KEI-78 — behavioural tests for the dependency auto-unblock backfill.

The trigger itself is exercised live via the migration smoke (verbatim probe
posted in the PR description). These tests target the Python backfill wrapper:
the SQL emission shape, idempotency, dry-run, and the candidate-dep enumeration.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestrator import dependency_unblock_backfill as dub  # noqa: E402


class _FakeCursor:
    def __init__(self, recipes):
        self._recipes = recipes
        self._idx = 0
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        out = self._recipes[self._idx]
        self._idx += 1
        return out

    def fetchone(self):
        out = self._recipes[self._idx]
        self._idx += 1
        return out

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _FakeConn:
    def __init__(self, recipes):
        self._cursor = _FakeCursor(recipes)
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_backfill_dry_run_does_not_invoke_function(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    fake = _FakeConn(
        [
            [("KEI-58",), ("KEI-49",)],  # candidate deps
            (3,),  # blocked count
        ]
    )
    monkeypatch.setattr(dub, "psycopg", type("p", (), {"connect": lambda *a, **k: fake}))
    stats = dub.backfill(dry_run=True)
    assert stats["blocked_scanned"] == 3
    assert stats["candidate_done_deps"] == 2
    assert stats["unblocked"] == 0
    assert not fake.committed


def test_backfill_invokes_fn_once_per_distinct_dep(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    fake = _FakeConn(
        [
            [("KEI-58",), ("KEI-49",)],
            (2,),
            (1,),  # fn returns 1 unblocked for KEI-58
            (0,),  # fn returns 0 unblocked for KEI-49
        ]
    )
    monkeypatch.setattr(dub, "psycopg", type("p", (), {"connect": lambda *a, **k: fake}))
    stats = dub.backfill(dry_run=False)
    assert stats["unblocked"] == 1
    assert fake.committed


def test_backfill_no_blocked_tasks_is_noop(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    fake = _FakeConn(
        [
            [],  # no candidate deps
            (0,),  # blocked count = 0
        ]
    )
    monkeypatch.setattr(dub, "psycopg", type("p", (), {"connect": lambda *a, **k: fake}))
    stats = dub.backfill(dry_run=False)
    assert stats == {"blocked_scanned": 0, "unblocked": 0, "candidate_done_deps": 0}


def test_dsn_strips_asyncpg(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@host/db")
    assert "+asyncpg" not in dub._dsn()


def test_dsn_raises_when_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    import pytest

    with pytest.raises(RuntimeError):
        dub._dsn()
