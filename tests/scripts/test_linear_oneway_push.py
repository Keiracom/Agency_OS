"""tests for scripts/orchestrator/linear_oneway_push.py — Agency_OS-1x3x Part 4.

Linear API + psycopg both mocked — no live Linear write. Verifies:
  - is_terminal_transition: close / reopen push; non-terminal churn skipped
  - _linear_state_id: status → LINEAR_STATE_ID_* env resolution
  - fetch_pending: coarse SQL + precise Python gate
  - push_to_linear: success / GraphQL-error / rejected / network-error
  - mark_synced: watermark UPDATE touches ONLY linear_synced_status
  - run_once: dry-run never writes; apply pushes + advances watermark;
    failure path collects + alerts + fails loud
  - one-way invariant: the module issues no Linear READ query
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "linear_oneway_push.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("linear_oneway_push", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["linear_oneway_push"] = m
    spec.loader.exec_module(m)
    return m


class _Cursor:
    def __init__(self, fetchall_rows=None):
        self._all = fetchall_rows or []
        self.executed: list[tuple[str, tuple | None]] = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._all

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


# ─── is_terminal_transition ────────────────────────────────────────────────


def test_close_transition_is_pending(mod):
    """active → done (watermark active) — a close. Push it."""
    assert mod.is_terminal_transition("done", "active") is True


def test_first_close_with_null_watermark_is_pending(mod):
    """done, never pushed (watermark NULL) — a close. Push it."""
    assert mod.is_terminal_transition("done", None) is True


def test_reopen_transition_is_pending(mod):
    """done → active (watermark done) — a reopen. Push it."""
    assert mod.is_terminal_transition("active", "done") is True


def test_terminal_to_terminal_change_is_pending(mod):
    """done → dismissed — still a terminal transition (reached cancelled)."""
    assert mod.is_terminal_transition("dismissed", "done") is True


def test_non_terminal_churn_is_not_pending(mod):
    """available ↔ active is plain workflow churn — never pushed."""
    assert mod.is_terminal_transition("active", "available") is False


def test_non_terminal_first_sync_is_not_pending(mod):
    """active, never pushed (watermark NULL) — not a terminal transition."""
    assert mod.is_terminal_transition("active", None) is False


def test_already_synced_is_not_pending(mod):
    """status == watermark — idempotent skip, no double-write."""
    assert mod.is_terminal_transition("done", "done") is False


# ─── _linear_state_id ──────────────────────────────────────────────────────


def test_linear_state_id_resolves_done(mod, monkeypatch):
    monkeypatch.setenv("LINEAR_STATE_ID_DONE", "uuid-done")
    assert mod._linear_state_id("done") == "uuid-done"


def test_linear_state_id_dismissed_maps_to_canceled(mod, monkeypatch):
    monkeypatch.setenv("LINEAR_STATE_ID_CANCELED", "uuid-cancel")
    assert mod._linear_state_id("dismissed") == "uuid-cancel"


def test_linear_state_id_unknown_status_returns_empty(mod):
    assert mod._linear_state_id("nonsense_status") == ""


# ─── fetch_pending ─────────────────────────────────────────────────────────


def test_fetch_pending_filters_via_python_gate(mod):
    """SQL is coarse (status <> watermark); the Python gate drops the
    non-terminal-churn candidate the SQL still returns."""
    cur = _Cursor(
        fetchall_rows=[
            ("KEI-1", "done", None),  # close → pending
            ("KEI-2", "active", "available"),  # churn → dropped
            ("KEI-3", "available", "done"),  # reopen → pending
        ]
    )
    pending = mod.fetch_pending(_Conn(cur))
    assert [p["id"] for p in pending] == ["KEI-1", "KEI-3"]


def test_fetch_pending_sql_is_coarse_candidate_filter(mod):
    cur = _Cursor()
    mod.fetch_pending(_Conn(cur))
    sql, _ = cur.executed[0]
    assert "status IS DISTINCT FROM linear_synced_status" in sql
    assert "id LIKE 'KEI-%'" in sql


# ─── push_to_linear ────────────────────────────────────────────────────────


def _fake_urlopen(response_obj):
    import json as _json

    class _Resp:
        def __init__(self, body):
            self._b = body

        def read(self):
            return self._b

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    def _open(req, timeout=None):
        return _Resp(_json.dumps(response_obj).encode())

    return _open


def test_push_to_linear_success(mod, monkeypatch):
    monkeypatch.setattr(
        mod.urllib.request,
        "urlopen",
        _fake_urlopen({"data": {"issueUpdate": {"success": True}}}),
    )
    mod.push_to_linear("key", "KEI-9", "state-uuid")  # no raise


def test_push_to_linear_rejected_raises(mod, monkeypatch):
    monkeypatch.setattr(
        mod.urllib.request,
        "urlopen",
        _fake_urlopen({"data": {"issueUpdate": {"success": False}}}),
    )
    with pytest.raises(RuntimeError, match="rejected"):
        mod.push_to_linear("key", "KEI-9", "state-uuid")


def test_push_to_linear_graphql_errors_raise(mod, monkeypatch):
    monkeypatch.setattr(
        mod.urllib.request,
        "urlopen",
        _fake_urlopen({"errors": [{"message": "bad id"}]}),
    )
    with pytest.raises(RuntimeError, match="GraphQL errors"):
        mod.push_to_linear("key", "KEI-9", "state-uuid")


def test_push_to_linear_network_error_raises(mod, monkeypatch):
    def _boom(req, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr(mod.urllib.request, "urlopen", _boom)
    with pytest.raises(RuntimeError, match="network error"):
        mod.push_to_linear("key", "KEI-9", "state-uuid")


# ─── mark_synced ───────────────────────────────────────────────────────────


def test_mark_synced_updates_only_watermark_column(mod):
    """The watermark UPDATE must touch ONLY linear_synced_status — so the
    KEI-228 emit trigger guard skips it (no echo)."""
    cur = _Cursor()
    conn = _Conn(cur)
    mod.mark_synced(conn, "KEI-5", "done")
    sql, params = cur.executed[0]
    assert "SET linear_synced_status = %s" in sql
    assert "status =" not in sql.replace("linear_synced_status =", "")
    assert "title" not in sql and "priority" not in sql
    assert params == ("done", "KEI-5")
    assert conn.commits == 1


# ─── run_once ──────────────────────────────────────────────────────────────


def test_run_once_dry_run_never_writes(mod, monkeypatch):
    cur = _Cursor(fetchall_rows=[("KEI-1", "done", None)])
    pushed = []
    monkeypatch.setattr(mod, "push_to_linear", lambda *a: pushed.append(a))
    stats = mod.run_once(_Conn(cur), "key", apply=False)
    assert stats == {"pending": 1, "pushed": 0, "failed": 0}
    assert pushed == []  # dry-run touched Linear zero times


def test_run_once_apply_pushes_and_marks(mod, monkeypatch):
    cur = _Cursor(fetchall_rows=[("KEI-1", "done", None)])
    conn = _Conn(cur)
    monkeypatch.setenv("LINEAR_STATE_ID_DONE", "uuid-done")
    pushed = []
    monkeypatch.setattr(mod, "push_to_linear", lambda *a: pushed.append(a))
    stats = mod.run_once(conn, "key", apply=True)
    assert stats["pushed"] == 1 and stats["failed"] == 0
    assert pushed == [("key", "KEI-1", "uuid-done")]
    # watermark advanced
    update_sql = cur.executed[-1][0]
    assert "linear_synced_status" in update_sql


def test_run_once_failure_collects_and_alerts(mod, monkeypatch):
    cur = _Cursor(fetchall_rows=[("KEI-1", "done", None)])
    monkeypatch.setenv("LINEAR_STATE_ID_DONE", "uuid-done")

    def _boom(*a):
        raise RuntimeError("linear network error: down")

    monkeypatch.setattr(mod, "push_to_linear", _boom)
    alerts = []
    monkeypatch.setattr(mod, "_emit_failure_alert", lambda f: alerts.append(f))
    stats = mod.run_once(_Conn(cur), "key", apply=True)
    assert stats["failed"] == 1 and stats["pushed"] == 0
    assert alerts and alerts[0][0][0] == "KEI-1"  # fail-loud alert fired


def test_run_once_missing_state_id_is_a_failure(mod, monkeypatch):
    """No LINEAR_STATE_ID for the status → fail loud, do not push blind."""
    cur = _Cursor(fetchall_rows=[("KEI-1", "done", None)])
    monkeypatch.delenv("LINEAR_STATE_ID_DONE", raising=False)
    alerts = []
    monkeypatch.setattr(mod, "_emit_failure_alert", lambda f: alerts.append(f))
    monkeypatch.setattr(mod, "push_to_linear", lambda *a: pytest.fail("must not push"))
    stats = mod.run_once(_Conn(cur), "key", apply=True)
    assert stats["failed"] == 1
    assert alerts


# ─── one-way invariant ─────────────────────────────────────────────────────


def test_module_issues_no_linear_read_query(mod):
    """One-way guard: the only Linear GraphQL the module emits is the
    issueUpdate mutation — no `query {` read of Linear issue data."""
    source = SCRIPT.read_text()
    assert "issueUpdate" in source
    # no Linear GraphQL *query* (read) — the push reads Supabase, not Linear
    assert "issues(" not in source
    assert "query(" not in source
