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

# Shared psycopg fakes — single source of truth, avoids Sonar
# new_duplicated_lines_density on per-test cursor/conn stand-ins.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db_mocks import FakeConn as _Conn  # noqa: E402
from _db_mocks import FakeCursor as _Cursor  # noqa: E402


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("linear_oneway_push", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["linear_oneway_push"] = m
    spec.loader.exec_module(m)
    return m


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


# ─── fetch_create_pending ──────────────────────────────────────────────────


def test_fetch_create_pending_returns_opted_in_rows(mod):
    cur = _Cursor(fetchall_rows=[("task-7", "Real KEI title", "a desc", 2)])
    out = mod.fetch_create_pending(_Conn(cur))
    assert out == [
        {"id": "task-7", "title": "Real KEI title", "description": "a desc", "priority": 2}
    ]


def test_fetch_create_pending_sql_requires_opt_in_flag(mod):
    """The candidate SQL MUST gate on linear_create_pending — public.tasks
    holds REVIEW-PR-*/smoke rows with no linear_url that must never mirror."""
    cur = _Cursor()
    mod.fetch_create_pending(_Conn(cur))
    sql, _ = cur.executed[0]
    assert "linear_create_pending IS TRUE" in sql
    assert "linear_url IS NULL" in sql


def test_fetch_create_pending_skips_junk_titles(mod):
    cur = _Cursor(
        fetchall_rows=[
            ("task-1", "Good title", None, None),
            ("task-2", "(no title)", None, None),
            ("task-3", "", None, None),
        ]
    )
    out = mod.fetch_create_pending(_Conn(cur))
    assert [r["id"] for r in out] == ["task-1"]


# ─── create_in_linear ──────────────────────────────────────────────────────


def test_create_in_linear_success_returns_url(mod, monkeypatch):
    monkeypatch.setattr(
        mod.urllib.request,
        "urlopen",
        _fake_urlopen(
            {"data": {"issueCreate": {"success": True, "issue": {"url": "https://lin/KEI-9"}}}}
        ),
    )
    url = mod.create_in_linear("key", "team", "Title", "desc", 2)
    assert url == "https://lin/KEI-9"


def test_create_in_linear_rejected_raises(mod, monkeypatch):
    monkeypatch.setattr(
        mod.urllib.request,
        "urlopen",
        _fake_urlopen({"data": {"issueCreate": {"success": False, "issue": None}}}),
    )
    with pytest.raises(RuntimeError, match="rejected"):
        mod.create_in_linear("key", "team", "Title", None, None)


def test_create_in_linear_graphql_errors_raise(mod, monkeypatch):
    monkeypatch.setattr(
        mod.urllib.request,
        "urlopen",
        _fake_urlopen({"errors": [{"message": "team not found"}]}),
    )
    with pytest.raises(RuntimeError, match="GraphQL errors"):
        mod.create_in_linear("key", "team", "Title", None, None)


def test_create_in_linear_network_error_raises(mod, monkeypatch):
    def _boom(req, timeout=None):
        raise OSError("refused")

    monkeypatch.setattr(mod.urllib.request, "urlopen", _boom)
    with pytest.raises(RuntimeError, match="network error"):
        mod.create_in_linear("key", "team", "Title", None, None)


# ─── create-intent bookkeeping ─────────────────────────────────────────────


def test_consume_create_intent_clears_flag(mod):
    cur = _Cursor()
    mod.consume_create_intent(_Conn(cur), "task-5")
    sql, params = cur.executed[0]
    assert "linear_create_pending = FALSE" in sql
    assert params == ("task-5",)


def test_record_created_url_writes_linear_url(mod):
    cur = _Cursor()
    mod.record_created_url(_Conn(cur), "task-5", "https://lin/KEI-9")
    sql, params = cur.executed[0]
    assert "SET linear_url = %s" in sql
    assert params == ("https://lin/KEI-9", "task-5")


def test_rearm_create_intent_resets_flag(mod):
    cur = _Cursor()
    mod.rearm_create_intent(_Conn(cur), "task-5")
    sql, _ = cur.executed[0]
    assert "linear_create_pending = TRUE" in sql


# ─── run_once: status path ─────────────────────────────────────────────────


def _no_creates(mod, monkeypatch):
    """Stub fetch_create_pending → [] so status-path tests stay isolated."""
    monkeypatch.setattr(mod, "fetch_create_pending", lambda _c: [])


def test_run_once_dry_run_never_writes(mod, monkeypatch):
    """Dry-run must NOT resolve LINEAR_STATE_ID — that env var is absent in
    CI; resolving it in dry-run falsely marked a terminal task `failed`
    (regression lock for run 26152062782). Env var cleared so the test
    mirrors CI, not a state-id-set local proxy."""
    monkeypatch.delenv("LINEAR_STATE_ID_DONE", raising=False)
    monkeypatch.setattr(mod, "fetch_pending", lambda _c: [{"id": "KEI-1", "status": "done"}])
    monkeypatch.setattr(mod, "fetch_create_pending", lambda _c: [])
    pushed = []
    monkeypatch.setattr(mod, "push_to_linear", lambda *a: pushed.append(a))
    stats = mod.run_once(_Conn(_Cursor()), "key", apply=False)
    assert stats["pending"] == 1 and stats["pushed"] == 0 and stats["failed"] == 0
    assert pushed == []  # dry-run touched Linear zero times


def test_run_once_apply_pushes_and_marks(mod, monkeypatch):
    cur = _Cursor()
    monkeypatch.setenv("LINEAR_STATE_ID_DONE", "uuid-done")
    monkeypatch.setattr(mod, "fetch_pending", lambda _c: [{"id": "KEI-1", "status": "done"}])
    _no_creates(mod, monkeypatch)
    pushed = []
    monkeypatch.setattr(mod, "push_to_linear", lambda *a: pushed.append(a))
    stats = mod.run_once(_Conn(cur), "key", apply=True)
    assert stats["pushed"] == 1 and stats["failed"] == 0
    assert pushed == [("key", "KEI-1", "uuid-done")]
    assert "linear_synced_status" in cur.executed[-1][0]  # watermark advanced


def test_run_once_failure_collects_and_alerts(mod, monkeypatch):
    monkeypatch.setenv("LINEAR_STATE_ID_DONE", "uuid-done")
    monkeypatch.setattr(mod, "fetch_pending", lambda _c: [{"id": "KEI-1", "status": "done"}])
    _no_creates(mod, monkeypatch)

    def _boom(*a):
        raise RuntimeError("linear network error: down")

    monkeypatch.setattr(mod, "push_to_linear", _boom)
    alerts = []
    monkeypatch.setattr(mod, "_emit_failure_alert", lambda f: alerts.append(f))
    stats = mod.run_once(_Conn(_Cursor()), "key", apply=True)
    assert stats["failed"] == 1 and stats["pushed"] == 0
    assert alerts and alerts[0][0][0] == "KEI-1"  # fail-loud alert fired


def test_run_once_missing_state_id_is_a_failure(mod, monkeypatch):
    """No LINEAR_STATE_ID for the status → fail loud, do not push blind."""
    monkeypatch.delenv("LINEAR_STATE_ID_DONE", raising=False)
    monkeypatch.setattr(mod, "fetch_pending", lambda _c: [{"id": "KEI-1", "status": "done"}])
    _no_creates(mod, monkeypatch)
    alerts = []
    monkeypatch.setattr(mod, "_emit_failure_alert", lambda f: alerts.append(f))
    monkeypatch.setattr(mod, "push_to_linear", lambda *a: pytest.fail("must not push"))
    stats = mod.run_once(_Conn(_Cursor()), "key", apply=True)
    assert stats["failed"] == 1
    assert alerts


# ─── run_once: GAP-A create path ───────────────────────────────────────────


def _one_create(mod, monkeypatch):
    monkeypatch.setattr(mod, "fetch_pending", lambda _c: [])
    monkeypatch.setattr(
        mod,
        "fetch_create_pending",
        lambda _c: [{"id": "task-7", "title": "New KEI", "description": "d", "priority": 2}],
    )


def test_run_once_create_dry_run_no_consume_no_create(mod, monkeypatch):
    """Dry-run for creates: counts the candidate but never consumes the
    intent and never calls issueCreate."""
    _one_create(mod, monkeypatch)
    calls = []
    monkeypatch.setattr(mod, "consume_create_intent", lambda *a: calls.append("consume"))
    monkeypatch.setattr(mod, "create_in_linear", lambda *a: calls.append("create"))
    stats = mod.run_once(_Conn(_Cursor()), "key", apply=False)
    assert stats["create_pending"] == 1 and stats["created"] == 0
    assert calls == []  # no consume, no create in dry-run


def test_run_once_create_consumes_intent_before_create(mod, monkeypatch):
    """Crash-safety: the intent is consumed BEFORE issueCreate, so a crash
    yields a recoverable missed-create, never a duplicate Linear issue."""
    _one_create(mod, monkeypatch)
    order = []
    monkeypatch.setattr(mod, "consume_create_intent", lambda *a: order.append("consume"))
    monkeypatch.setattr(mod, "create_in_linear", lambda *a: (order.append("create"), "url")[1])
    monkeypatch.setattr(mod, "record_created_url", lambda *a: order.append("record"))
    stats = mod.run_once(_Conn(_Cursor()), "key", apply=True)
    assert stats["created"] == 1
    assert order == ["consume", "create", "record"]


def test_run_once_create_failure_rearms_and_alerts(mod, monkeypatch):
    """A clean issueCreate failure re-arms the intent (retry next tick) and
    fires a fail-loud alert."""
    _one_create(mod, monkeypatch)
    monkeypatch.setattr(mod, "consume_create_intent", lambda *a: None)
    rearmed = []
    monkeypatch.setattr(mod, "rearm_create_intent", lambda c, t: rearmed.append(t))

    def _boom(*a):
        raise RuntimeError("linear network error: down")

    monkeypatch.setattr(mod, "create_in_linear", _boom)
    alerts = []
    monkeypatch.setattr(mod, "_emit_failure_alert", lambda f: alerts.append(f))
    stats = mod.run_once(_Conn(_Cursor()), "key", apply=True)
    assert stats["create_failed"] == 1 and stats["created"] == 0
    assert rearmed == ["task-7"]  # re-armed for retry
    assert alerts and alerts[0][0][0] == "task-7"


# ─── one-way invariant ─────────────────────────────────────────────────────


def test_module_issues_no_linear_read_query(mod):
    """One-way guard: the module's only Linear GraphQL ops are the
    issueUpdate + issueCreate mutations — no read query of Linear data."""
    source = SCRIPT.read_text()
    assert "issueUpdate" in source and "issueCreate" in source
    # no Linear GraphQL *query* (read) — the push reads Supabase, not Linear
    assert "issues(" not in source
    assert "query(" not in source
