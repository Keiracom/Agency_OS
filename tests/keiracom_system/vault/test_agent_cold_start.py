"""Unit tests for agent_cold_start (Agency_OS-yhm8). All external seams mocked —
no Vault, no DB, no real ``claude``."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.keiracom_system.vault import agent_cold_start as acs


def _fake_conn(*, fetchone=None, rowcount=1):
    """A psycopg-like conn whose `with conn.cursor() as cur` yields a mock cursor."""
    cur = MagicMock()
    cur.fetchone.return_value = fetchone
    cur.rowcount = rowcount
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return conn, cur


# ---- pure compose ----------------------------------------------------------


def test_compose_prompt_includes_task_fields():
    task = {
        "id": "t-1",
        "title": "Wire X",
        "task_type": "build",
        "description": "do the thing",
        "acceptance_criteria": "thing is done",
    }
    p = acs.compose_prompt(task)
    assert "t-1" in p and "Wire X" in p and "do the thing" in p and "thing is done" in p


def test_compose_prompt_tolerates_missing_optionals():
    p = acs.compose_prompt({"id": "t-2", "title": None, "task_type": None})
    assert "t-2" in p and "Description" not in p and "Acceptance" not in p


# ---- DB seams --------------------------------------------------------------


def test_fetch_task_found_maps_columns():
    conn, _ = _fake_conn(fetchone=("t-1", "Title", "Desc", "build", 2, None))
    assert acs.fetch_task("t-1", conn=conn) == {
        "id": "t-1",
        "title": "Title",
        "description": "Desc",
        "task_type": "build",
        "priority": 2,
        "acceptance_criteria": None,
    }


def test_fetch_task_absent_returns_none():
    conn, _ = _fake_conn(fetchone=None)
    assert acs.fetch_task("missing", conn=conn) is None


def test_claim_task_won_and_lost():
    conn, cur = _fake_conn(rowcount=1)
    assert acs.claim_task("t-1", "worker", conn=conn) is True
    assert cur.execute.call_args[0][1] == ("worker", "t-1")  # callsign, id
    conn2, _ = _fake_conn(rowcount=0)
    assert acs.claim_task("t-1", "worker", conn=conn2) is False


def test_run_agent_spawns_headless_claude():
    captured = {}

    def fake_popen(cmd, cwd=None):
        captured["cmd"], captured["cwd"] = cmd, cwd
        proc = MagicMock()
        proc.wait.return_value = 0
        return proc

    rc = acs.run_agent("PROMPT", popen=fake_popen)
    assert rc == 0
    assert captured["cmd"] == [acs.CLAUDE_BIN, "-p", "PROMPT", "--dangerously-skip-permissions"]
    assert captured["cwd"] == acs.AGENT_WORKDIR


def test_finalize_done_without_acceptance_only_updates():
    conn, cur = _fake_conn()
    acs.finalize_task("t-1", 0, None, conn=conn)
    sqls = [c[0][0] for c in cur.execute.call_args_list]
    assert len(sqls) == 1 and "status=%s" in sqls[0]
    assert cur.execute.call_args[0][1] == ("done", "t-1")


def test_finalize_done_with_acceptance_inserts_verification_first():
    conn, cur = _fake_conn()
    acs.finalize_task("t-1", 0, "must pass", conn=conn)
    sqls = [c[0][0] for c in cur.execute.call_args_list]
    assert "task_verifications" in sqls[0]  # verification row inserted first
    assert "UPDATE public.tasks SET status=%s" in sqls[1]
    assert cur.execute.call_args[0][1] == ("done", "t-1")


def test_finalize_failure_maps_to_blocked():
    conn, cur = _fake_conn()
    acs.finalize_task("t-1", 1, "must pass", conn=conn)
    sqls = [c[0][0] for c in cur.execute.call_args_list]
    assert all("task_verifications" not in s for s in sqls)  # no verification on failure
    assert cur.execute.call_args[0][1] == ("blocked", "t-1")


# ---- orchestration ---------------------------------------------------------


def _run(monkeypatch, *, task_id="t-1", fetch_ret=None, claim_ret=True, agent_rc=0):
    if task_id is not None:
        monkeypatch.setenv("AGENT_TASK_ID", task_id)
    else:
        monkeypatch.delenv("AGENT_TASK_ID", raising=False)
    monkeypatch.setattr(acs.sys, "argv", ["agent_cold_start"])  # no argv fallback
    calls = {}
    task = fetch_ret if fetch_ret is not None else {"id": task_id, "acceptance_criteria": "ac"}
    finalize = MagicMock()
    rc = acs.run(
        resolve=lambda: calls.setdefault("resolved", True),
        fetch=lambda _tid: task if fetch_ret is not False else None,
        claim=lambda _tid, _cs: claim_ret,
        agent=lambda _p: agent_rc,
        finalize=finalize,
    )
    return rc, finalize, calls


def test_run_happy_path_returns_zero_and_finalizes(monkeypatch):
    rc, finalize, calls = _run(monkeypatch, agent_rc=0)
    assert rc == 0 and calls.get("resolved") is True
    finalize.assert_called_once_with("t-1", 0, "ac")


def test_run_no_task_id(monkeypatch):
    rc, finalize, _ = _run(monkeypatch, task_id=None)
    assert rc == acs.RC_NO_TASK_ID
    finalize.assert_not_called()


def test_run_task_absent(monkeypatch):
    rc, finalize, _ = _run(monkeypatch, fetch_ret=False)
    assert rc == acs.RC_TASK_ABSENT
    finalize.assert_not_called()


def test_run_claim_lost_exits_clean_without_agent(monkeypatch):
    agent = MagicMock()
    monkeypatch.setenv("AGENT_TASK_ID", "t-1")
    monkeypatch.setattr(acs.sys, "argv", ["agent_cold_start"])
    rc = acs.run(
        resolve=lambda: None,
        fetch=lambda _t: {"id": "t-1", "acceptance_criteria": None},
        claim=lambda _t, _c: False,
        agent=agent,
        finalize=MagicMock(),
    )
    assert rc == 0
    agent.assert_not_called()


def test_run_agent_failure_finalizes_with_nonzero_rc(monkeypatch):
    rc, finalize, _ = _run(monkeypatch, agent_rc=1)
    assert rc == 1
    finalize.assert_called_once_with("t-1", 1, "ac")
