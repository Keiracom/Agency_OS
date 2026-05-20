"""tests for scripts/backfill_task_titles_from_linear.py — Part 1 title backfill.

Linear GraphQL + psycopg both mocked. Verifies:
  - fetch_linear_titles paginates and builds {identifier: title}
  - plan_backfill partitions bad-title rows into matched / unmatched
  - unmatched: identifier absent from Linear, OR Linear title is a placeholder
  - apply_backfill issues an idempotent UPDATE per matched row
  - the UPDATE's WHERE clause re-asserts the bad-title predicate
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "backfill_task_titles_from_linear.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("backfill_task_titles", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["backfill_task_titles"] = m
    spec.loader.exec_module(m)
    return m


class _Cursor:
    """psycopg cursor stand-in with rowcount (the shared FakeCursor lacks it)."""

    def __init__(self, fetchall_rows=None, fetchone_row=None):
        self._all = fetchall_rows or []
        self._one = fetchone_row
        self.executed: list[tuple[str, tuple | None]] = []
        self.rowcount = 1

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._all

    def fetchone(self):
        return self._one

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return None


class _Conn:
    def __init__(self, cur):
        self._cur = cur
        self.commits = 0

    def cursor(self):
        return self._cur

    def commit(self):
        self.commits += 1


# ─── fetch_linear_titles ──────────────────────────────────────────────────


def _fake_urlopen_factory(pages):
    """Return a urlopen stand-in that yields each page response in order."""
    calls = {"n": 0}

    class _Resp:
        def __init__(self, body):
            self._body = body

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    def _urlopen(req, timeout=None):
        body = json.dumps(pages[calls["n"]]).encode()
        calls["n"] += 1
        return _Resp(body)

    return _urlopen


def test_fetch_linear_titles_paginates(mod, monkeypatch):
    """Two-page Linear response → both pages merged into one dict."""
    monkeypatch.setenv("LINEAR_API_KEY", "lin_test")
    page1 = {
        "data": {
            "issues": {
                "nodes": [{"identifier": "KEI-1", "title": "first"}],
                "pageInfo": {"hasNextPage": True, "endCursor": "c1"},
            }
        }
    }
    page2 = {
        "data": {
            "issues": {
                "nodes": [{"identifier": "KEI-2", "title": "second"}],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
    }
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_urlopen_factory([page1, page2]))
    titles = mod.fetch_linear_titles()
    assert titles == {"KEI-1": "first", "KEI-2": "second"}


def test_fetch_linear_titles_raises_on_graphql_errors(mod, monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "lin_test")
    err_page = {"errors": [{"message": "team not found"}]}
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_urlopen_factory([err_page]))
    with pytest.raises(RuntimeError, match="Linear GraphQL errors"):
        mod.fetch_linear_titles()


def test_fetch_linear_titles_missing_key_raises(mod, monkeypatch):
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="LINEAR_API_KEY"):
        mod.fetch_linear_titles()


# ─── plan_backfill ─────────────────────────────────────────────────────────


def test_plan_backfill_matches_good_titles(mod):
    cur = _Cursor(fetchall_rows=[("KEI-1",), ("KEI-2",)])
    linear = {"KEI-1": "real title one", "KEI-2": "real title two"}
    plan = mod.plan_backfill(_Conn(cur), linear)
    assert sorted(plan["matched"]) == [
        ("KEI-1", "real title one"),
        ("KEI-2", "real title two"),
    ]
    assert plan["unmatched"] == []


def test_plan_backfill_unmatched_when_identifier_absent(mod):
    """A bad-title row whose identifier has no Linear issue → unmatched."""
    cur = _Cursor(fetchall_rows=[("KEI-1",), ("KEI-999",)])
    linear = {"KEI-1": "real title"}
    plan = mod.plan_backfill(_Conn(cur), linear)
    assert plan["matched"] == [("KEI-1", "real title")]
    assert plan["unmatched"] == ["KEI-999"]


def test_plan_backfill_unmatched_when_linear_title_is_placeholder(mod):
    """Linear issue exists but its title is itself a placeholder → unmatched
    (the backfill cannot repair the row, so it is surfaced for triage)."""
    cur = _Cursor(fetchall_rows=[("KEI-1",), ("KEI-2",), ("KEI-3",)])
    linear = {"KEI-1": "real", "KEI-2": "(no title)", "KEI-3": ""}
    plan = mod.plan_backfill(_Conn(cur), linear)
    assert plan["matched"] == [("KEI-1", "real")]
    assert sorted(plan["unmatched"]) == ["KEI-2", "KEI-3"]


# ─── apply_backfill ────────────────────────────────────────────────────────


def test_apply_backfill_issues_update_per_matched_row(mod):
    cur = _Cursor()
    written = mod.apply_backfill(_Conn(cur), [("KEI-1", "t1"), ("KEI-2", "t2")])
    assert written == 2
    assert len(cur.executed) == 2
    sql, params = cur.executed[0]
    assert "UPDATE public.tasks" in sql
    assert params == ("t1", "KEI-1")


def test_apply_backfill_where_clause_is_idempotent(mod):
    """The UPDATE WHERE must re-assert the bad-title predicate so a row that
    gained a title between plan and apply is left untouched."""
    cur = _Cursor()
    mod.apply_backfill(_Conn(cur), [("KEI-1", "t1")])
    sql, _ = cur.executed[0]
    assert "title IS NULL" in sql
    assert "title = ''" in sql
    assert "title = '(no title)'" in sql


def test_apply_backfill_commits(mod):
    cur = _Cursor()
    conn = _Conn(cur)
    mod.apply_backfill(conn, [("KEI-1", "t1")])
    assert conn.commits == 1


def test_count_remaining_reads_bad_title_predicate(mod):
    cur = _Cursor(fetchone_row=(0,))
    assert mod.count_remaining(_Conn(cur)) == 0
    sql, _ = cur.executed[0]
    assert "count(*)" in sql
    assert "title = '(no title)'" in sql
