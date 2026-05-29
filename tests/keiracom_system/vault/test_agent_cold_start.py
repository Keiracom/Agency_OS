"""Unit tests for agent_cold_start (Agency_OS-yhm8). All external seams mocked —
no Vault, no DB, no real ``claude``."""

from __future__ import annotations

import json
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
    conn, cur = _fake_conn(fetchone=("t-1", "Title", "Desc", 2, None))
    assert acs.fetch_task("t-1", conn=conn) == {
        "id": "t-1",
        "title": "Title",
        "description": "Desc",
        "priority": 2,
        "acceptance_criteria": None,
    }
    # regression guard: public.tasks has NO task_type column — must not be selected
    assert "task_type" not in cur.execute.call_args[0][0]


def test_run_sets_task_type_from_env(monkeypatch):
    # task_type is not a tasks column; it must come from the AGENT_TASK_TYPE env var.
    monkeypatch.setenv("AGENT_TASK_ID", "t-1")
    monkeypatch.setenv("AGENT_TASK_TYPE", "review")
    monkeypatch.setattr(acs.sys, "argv", ["agent_cold_start"])
    seen = {}
    acs.run(
        resolve=lambda: None,
        fetch=lambda _t: {"id": "t-1", "acceptance_criteria": None},
        claim=lambda _t, _c: True,
        agent=lambda prompt: seen.update(prompt=prompt) or 0,
        finalize=lambda *a: None,
    )
    assert "review" in seen["prompt"]  # AGENT_TASK_TYPE flowed into the prompt


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


def test_finalize_done_without_acceptance_inserts_generic_verification():
    # require_verification_before_done fires on EVERY done transition regardless of
    # acceptance_criteria — a verification row must always be inserted (Aiden catch).
    conn, cur = _fake_conn()
    acs.finalize_task("t-1", 0, None, conn=conn)
    sqls = [c[0][0] for c in cur.execute.call_args_list]
    assert "task_verifications" in sqls[0]  # evidence inserted even with no acceptance_criteria
    assert "UPDATE public.tasks SET status=%s" in sqls[1]
    assert "no acceptance criteria" in cur.execute.call_args_list[0][0][1][3]  # generic test_output
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


# ---- notify_complete -------------------------------------------------------


def test_notify_complete_calls_dispatcher_endpoint(monkeypatch):
    """notify_complete POSTs to /dispatcher/task_complete and swallows errors."""
    import urllib.request as urlreq

    captured = {}

    class _FakeResp:
        def read(self):
            return b'{"notified":true}'

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data)
        return _FakeResp()

    monkeypatch.setattr(urlreq, "urlopen", fake_urlopen)
    acs.notify_complete("t-1", "atlas", "Build X", "done", 0, dispatcher_url="http://testhost:4001")
    assert captured["url"] == "http://testhost:4001/dispatcher/task_complete"
    assert captured["body"] == {
        "task_id": "t-1",
        "callsign": "atlas",
        "title": "Build X",
        "status": "done",
        "rc": 0,
    }


def test_notify_complete_fail_open_on_network_error(monkeypatch):
    """A network error must be swallowed — never raises."""
    import urllib.request as urlreq

    monkeypatch.setattr(
        urlreq, "urlopen", lambda *a, **kw: (_ for _ in ()).throw(OSError("refused"))
    )
    acs.notify_complete("t-2", "scout", "", "blocked", 1, dispatcher_url="http://127.0.0.1:4001")
    # no exception = pass


def test_run_calls_notify_after_finalize(monkeypatch):
    """run() calls notify with the correct status derived from agent rc."""
    monkeypatch.setenv("AGENT_TASK_ID", "t-1")
    monkeypatch.setenv("AGENT_CALLSIGN", "orion")
    monkeypatch.setattr(acs.sys, "argv", ["agent_cold_start"])
    notify_calls = []
    acs.run(
        resolve=lambda: None,
        fetch=lambda _t: {"id": "t-1", "title": "My Task", "acceptance_criteria": None},
        claim=lambda _t, _c: True,
        agent=lambda _p: 0,
        finalize=lambda *a: None,
        notify=lambda *a, **kw: notify_calls.append((a, kw)),
    )
    assert len(notify_calls) == 1
    args, _ = notify_calls[0]
    assert args[0] == "t-1"  # task_id
    assert args[1] == "orion"  # callsign from env
    assert args[2] == "My Task"  # title
    assert args[3] == "done"  # status (rc=0)
    assert args[4] == 0  # rc


def test_run_notify_blocked_on_agent_failure(monkeypatch):
    """rc != 0 → notify receives status='blocked'."""
    monkeypatch.setenv("AGENT_TASK_ID", "t-1")
    monkeypatch.delenv("AGENT_CALLSIGN", raising=False)
    monkeypatch.setattr(acs.sys, "argv", ["agent_cold_start"])
    notify_calls = []
    acs.run(
        resolve=lambda: None,
        fetch=lambda _t: {"id": "t-1", "title": "", "acceptance_criteria": None},
        claim=lambda _t, _c: True,
        agent=lambda _p: 2,
        finalize=lambda *a: None,
        notify=lambda *a, **kw: notify_calls.append(a),
    )
    assert notify_calls[0][3] == "blocked"
    assert notify_calls[0][4] == 2
