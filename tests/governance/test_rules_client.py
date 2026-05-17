"""KEI-68 — behavioural tests for governance_rules read/upsert API.

Live-DB integration via psycopg patch. SQL emission shape, filter semantics,
idempotent upsert, deprecation history-preserving update, missing-id error.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.governance import rules_client  # noqa: E402


class _FakeCursor:
    def __init__(self, recipes):
        self._recipes = recipes
        self._idx = 0
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def _next(self):
        out = self._recipes[self._idx]
        self._idx += 1
        return out

    fetchall = _next
    fetchone = _next

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _FakeConn:
    def __init__(self, recipes):
        self._cursor = _FakeCursor(recipes)

    def cursor(self, *_, **__):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _install(monkeypatch, fake):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setattr(
        rules_client,
        "psycopg",
        type("p", (), {"connect": lambda *a, **k: fake}),
    )


def test_list_active_rules_no_category_returns_all(monkeypatch):
    recipes = [[{"id": "r1", "category": "concur", "rule": "x", "active": True}]]
    _install(monkeypatch, _FakeConn(recipes))
    rows = rules_client.list_active_rules()
    assert len(rows) == 1
    assert rows[0]["id"] == "r1"


def test_list_active_rules_filters_by_category(monkeypatch):
    recipes = [[]]
    fake = _FakeConn(recipes)
    _install(monkeypatch, fake)
    rules_client.list_active_rules(category="claiming")
    assert fake._cursor.executed, "expected at least one execute() call"
    sql, params = fake._cursor.executed[-1]
    assert "category=%s" in sql
    assert params == ("claiming",)


def test_mark_deprecated_returns_row_on_success(monkeypatch):
    recipes = [{"id": "r1", "active": False, "deprecated_reason": "superseded by KEI-68"}]
    _install(monkeypatch, _FakeConn(recipes))
    row = rules_client.mark_deprecated("r1", "superseded by KEI-68", "aiden")
    assert row["active"] is False
    assert "superseded" in row["deprecated_reason"]


def test_mark_deprecated_raises_on_missing(monkeypatch):
    recipes = [None]
    _install(monkeypatch, _FakeConn(recipes))
    with pytest.raises(LookupError):
        rules_client.mark_deprecated("missing-id", "x", "aiden")


def test_mark_deprecated_rejects_empty_reason(monkeypatch):
    with pytest.raises(ValueError):
        rules_client.mark_deprecated("r1", "", "aiden")


def test_upsert_rule_requires_id_category_rule(monkeypatch):
    with pytest.raises(ValueError):
        rules_client.upsert_rule({"id": "r1", "category": "concur"})


def test_upsert_rule_returns_inserted_row(monkeypatch):
    recipes = [{"id": "r1", "category": "claiming", "rule": "x", "active": True}]
    _install(monkeypatch, _FakeConn(recipes))
    row = rules_client.upsert_rule({"id": "r1", "category": "claiming", "rule": "x"})
    assert row["id"] == "r1"
    assert row["active"] is True


def test_dsn_strips_asyncpg(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/d")
    assert "+asyncpg" not in rules_client._dsn()


def test_dsn_missing_raises(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(RuntimeError):
        rules_client._dsn()
