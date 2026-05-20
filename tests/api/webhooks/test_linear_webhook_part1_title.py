"""Part 1 (b) — tests for the Linear webhook title-refresh wire.

Covers:
  - _normalise_event update branch now carries the issue title
  - _dispatch_to_tasks status op refreshes public.tasks.title
  - the refresh SQL uses a COALESCE/NULLIF guard so a placeholder title
    never clobbers a real one
  - the done-branch status update also refreshes title
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from src.api.webhooks import linear as linear_webhook  # noqa: E402


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[Any, ...]]] = []

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((sql, params or ()))


class _FakeConn:
    def __init__(self) -> None:
        self._cur = _FakeCursor()
        self.committed = False

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self._cur

    def commit(self) -> None:
        self.committed = True


@pytest.fixture
def fake_psycopg(monkeypatch):
    conn = _FakeConn()
    fake = MagicMock()
    fake.connect = MagicMock(return_value=conn)
    monkeypatch.setitem(sys.modules, "psycopg", fake)
    return conn


@pytest.fixture(autouse=True)
def _dsn_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/d")


def _update_payload(identifier: str, state_type: str, title: str | None) -> dict:
    data: dict = {
        "identifier": identifier,
        "state": {"type": state_type, "name": state_type},
        "url": "https://linear.app/x",
    }
    if title is not None:
        data["title"] = title
    return {"action": "update", "type": "Issue", "data": data}


# ─── _normalise_event carries title ────────────────────────────────────────


def test_normalise_update_carries_title():
    out = linear_webhook._normalise_event(_update_payload("KEI-100", "started", "Real issue title"))
    assert out["op"] == "status"
    assert out["title"] == "Real issue title"


def test_normalise_update_title_none_when_absent():
    out = linear_webhook._normalise_event(_update_payload("KEI-100", "started", None))
    assert out["op"] == "status"
    assert out["title"] is None


# ─── _dispatch_to_tasks refreshes title (non-done branch) ───────────────────


def test_dispatch_status_active_refreshes_title(fake_psycopg):
    event = {
        "op": "status",
        "identifier": "KEI-200",
        "task_status": "active",
        "title": "Refreshed title",
        "url": "u",
    }
    linear_webhook._dispatch_to_tasks(event)
    sql, params = fake_psycopg._cur.executed[0]
    assert "title = COALESCE(NULLIF(NULLIF(%s, ''), '(no title)'), title)" in sql
    # param order: (new_status, title, url, identifier)
    assert params == ("active", "Refreshed title", "u", "KEI-200")


def test_dispatch_status_done_refreshes_title(fake_psycopg):
    event = {
        "op": "status",
        "identifier": "KEI-201",
        "task_status": "done",
        "title": "Done-state title",
        "url": "u",
    }
    linear_webhook._dispatch_to_tasks(event)
    sql, params = fake_psycopg._cur.executed[0]
    assert "title = COALESCE(NULLIF(NULLIF(%s, ''), '(no title)'), title)" in sql
    # param order: (title, url, identifier)
    assert params == ("Done-state title", "u", "KEI-201")


def test_dispatch_status_placeholder_title_passed_for_nullif_guard(fake_psycopg):
    """A '(no title)' event title is still passed as a param — the SQL's
    nested NULLIF collapses it so COALESCE keeps the existing row title.
    The guard lives in SQL, so the test asserts the param + the clause."""
    event = {
        "op": "status",
        "identifier": "KEI-202",
        "task_status": "active",
        "title": "(no title)",
        "url": "u",
    }
    linear_webhook._dispatch_to_tasks(event)
    sql, params = fake_psycopg._cur.executed[0]
    assert "NULLIF(NULLIF(%s, ''), '(no title)')" in sql
    assert params[1] == "(no title)"


def test_dispatch_status_missing_title_key_passes_none(fake_psycopg):
    """No title key in the event → None param; COALESCE keeps existing title."""
    event = {"op": "status", "identifier": "KEI-203", "task_status": "active", "url": "u"}
    linear_webhook._dispatch_to_tasks(event)
    _, params = fake_psycopg._cur.executed[0]
    assert params[1] is None


def test_dispatch_create_still_sets_title(fake_psycopg):
    """Regression-lock: the create path's title INSERT is unchanged."""
    event = {
        "op": "create",
        "identifier": "KEI-204",
        "title": "Created title",
        "priority": 2,
        "url": "u",
    }
    linear_webhook._dispatch_to_tasks(event)
    sql, params = fake_psycopg._cur.executed[0]
    assert "INSERT INTO public.tasks" in sql
    assert "Created title" in params
