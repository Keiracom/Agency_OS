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
        spawn_recall=lambda _t: "",  # zr7e.5: no real Hindsight call
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
        save_atoms=lambda *a, **k: None,
        spawn_recall=lambda _t: "",  # zr7e.5: no real Hindsight call in unit tests
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
        save_atoms=lambda *a, **k: None,
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
        save_atoms=lambda *a, **k: None,
        notify=lambda *a, **kw: notify_calls.append(a),
    )
    assert notify_calls[0][3] == "blocked"
    assert notify_calls[0][4] == 2


# ---- save_exit_atoms (AtomV1 memory capture, zr7e.4) ------------------------


def test_run_calls_save_atoms_after_finalize_before_notify(monkeypatch):
    """run() invokes save_atoms once, with (task, rc, status), between
    finalize and notify."""
    monkeypatch.setenv("AGENT_TASK_ID", "t-1")
    monkeypatch.setattr(acs.sys, "argv", ["agent_cold_start"])
    order = []
    save_calls = []
    task = {"id": "t-1", "title": "My Task", "acceptance_criteria": None}
    acs.run(
        resolve=lambda: None,
        fetch=lambda _t: task,
        claim=lambda _t, _c: True,
        agent=lambda _p: 0,
        finalize=lambda *a: order.append("finalize"),
        save_atoms=lambda *a: (order.append("save"), save_calls.append(a)),
        notify=lambda *a, **kw: order.append("notify"),
        spawn_recall=lambda _t: "",  # zr7e.5: no real Hindsight call
    )
    assert order == ["finalize", "save", "notify"]
    assert save_calls == [(task, 0, "done")]


def test_save_exit_atoms_builds_conversation_and_calls_classify(monkeypatch):
    """save_exit_atoms feeds task brief + completion stamp to classify_and_save
    with the env/default customer_id."""
    import src.keiracom_system.chat.exit_cycle as ec

    captured = {}

    async def fake_classify(conversation, customer_id, **kw):
        captured["conversation"] = conversation
        captured["customer_id"] = customer_id
        # atom_ids=[] so save_exit_atoms' zr7e.9 publish loop has nothing to send.
        return MagicMock(skipped_reason=None, atom_ids=[])

    monkeypatch.setattr(ec, "classify_and_save", fake_classify)
    monkeypatch.setenv("AGENT_CUSTOMER_ID", "7")
    acs.save_exit_atoms({"id": "t-9", "title": "Wire X", "description": "Do the thing"}, 0, "done")
    assert captured["customer_id"] == 7
    convo = captured["conversation"]
    assert convo[0]["role"] == "user" and "Do the thing" in convo[0]["content"]
    assert convo[1]["role"] == "assistant" and "rc=0" in convo[1]["content"]


def test_save_exit_atoms_fail_open_on_classify_error(monkeypatch):
    """An error anywhere in the capture path must be swallowed — never raises."""
    import src.keiracom_system.chat.exit_cycle as ec

    def boom(*_a, **_k):
        raise RuntimeError("gemini exploded")

    monkeypatch.setattr(ec, "classify_and_save", boom)
    # no exception = pass
    acs.save_exit_atoms({"id": "t-1", "title": "T", "description": "d"}, 1, "blocked")


# ---- zr7e.9 NATS handoff publish on save_exit_atoms -------------------------


def test_publish_handoff_publishes_correct_envelope(monkeypatch):
    """_publish_handoff publishes to keiracom.agent.handoff with the full payload
    and reads from_callsign from AGENT_CALLSIGN env."""
    captured: dict = {}

    class _FakeNC:
        async def connect(self, url, connect_timeout=2):  # noqa: ARG002
            captured["url"] = url

        async def publish(self, subject, payload):
            captured["subject"] = subject
            captured["payload"] = payload

        async def flush(self):
            captured["flushed"] = True

        async def close(self):
            captured["closed"] = True

    monkeypatch.setattr("nats.aio.client.Client", lambda: _FakeNC())
    monkeypatch.setenv("AGENT_CALLSIGN", "worker-3")

    ok = acs._publish_handoff(task_id="t-42", atom_id="atom-99")

    assert ok is True
    assert captured["subject"] == acs.HANDOFF_SUBJECT == "keiracom.agent.handoff"
    assert captured["url"] == acs.NATS_URL
    assert captured["flushed"] is True and captured["closed"] is True
    body = json.loads(captured["payload"].decode())
    assert body["task_id"] == "t-42"
    assert body["atom_id"] == "atom-99"
    assert body["from_callsign"] == "worker-3"
    assert body["to_callsign"] == ""  # V1 default — subscribers self-route
    assert isinstance(body["ts"], int)


def test_publish_handoff_fail_open_on_nats_error(monkeypatch):
    """NATS connect failure → False, no exception escapes."""

    class _BoomNC:
        async def connect(self, url, connect_timeout=2):  # noqa: ARG002
            raise OSError("nats unreachable")

        async def publish(self, *a, **kw): ...
        async def flush(self): ...
        async def close(self): ...

    monkeypatch.setattr("nats.aio.client.Client", lambda: _BoomNC())

    assert acs._publish_handoff(task_id="t-x", atom_id="a-x") is False


def test_save_exit_atoms_publishes_one_per_atom_id(monkeypatch):
    """save_exit_atoms iterates result.atom_ids and calls _publish_handoff once
    per atom, with the task_id stringified."""
    import src.keiracom_system.chat.exit_cycle as ec

    async def fake_classify(conversation, customer_id, **kw):  # noqa: ARG001
        return MagicMock(skipped_reason=None, atom_ids=["a-1", "a-2", "a-3"])

    monkeypatch.setattr(ec, "classify_and_save", fake_classify)

    calls: list[dict] = []
    monkeypatch.setattr(acs, "_publish_handoff", lambda **kw: (calls.append(kw), True)[1])

    acs.save_exit_atoms({"id": "t-5", "title": "T", "description": "d"}, 0, "done")

    assert [c["atom_id"] for c in calls] == ["a-1", "a-2", "a-3"]
    assert all(c["task_id"] == "t-5" for c in calls)


def test_save_exit_atoms_no_publish_when_no_atoms(monkeypatch):
    """Empty atom_ids → zero publishes (no atom = no V1 handoff signal)."""
    import src.keiracom_system.chat.exit_cycle as ec

    async def fake_classify(conversation, customer_id, **kw):  # noqa: ARG001
        return MagicMock(skipped_reason="no_decisions", atom_ids=[])

    monkeypatch.setattr(ec, "classify_and_save", fake_classify)

    calls: list[dict] = []
    monkeypatch.setattr(acs, "_publish_handoff", lambda **kw: (calls.append(kw), True)[1])

    acs.save_exit_atoms({"id": "t-6", "title": "T", "description": "d"}, 0, "done")

    assert calls == []


def test_save_exit_atoms_fail_open_when_publish_raises(monkeypatch):
    """Even if _publish_handoff raises (contract says it shouldn't, but defence in
    depth), save_exit_atoms must not propagate — outer try/except swallows it."""
    import src.keiracom_system.chat.exit_cycle as ec

    async def fake_classify(conversation, customer_id, **kw):  # noqa: ARG001
        return MagicMock(skipped_reason=None, atom_ids=["a-1"])

    def boom_publish(**_kw):
        raise RuntimeError("publish exploded")

    monkeypatch.setattr(ec, "classify_and_save", fake_classify)
    monkeypatch.setattr(acs, "_publish_handoff", boom_publish)

    # No exception escapes.
    acs.save_exit_atoms({"id": "t-7", "title": "T", "description": "d"}, 0, "done")


# ---- zr7e.5 L2 Hindsight spawn-context recall --------------------------------


def test_run_prepends_recall_block_when_present(monkeypatch):
    """When spawn_recall returns a non-empty block, run() prepends it to the
    compose_prompt output before passing to the agent — separated by a blank line."""
    monkeypatch.setenv("AGENT_TASK_ID", "t-r1")
    monkeypatch.setattr(acs.sys, "argv", ["agent_cold_start"])
    captured: dict = {}
    task = {"id": "t-r1", "title": "Wire X", "description": "ship it", "acceptance_criteria": None}

    acs.run(
        resolve=lambda: None,
        fetch=lambda _t: task,
        claim=lambda _t, _c: True,
        agent=lambda prompt: captured.setdefault("prompt", prompt) or 0,
        finalize=lambda *a: None,
        save_atoms=lambda *a, **k: None,
        spawn_recall=lambda _t: "[PRIOR CONTEXT]\n- atom A\n- atom B",
    )

    prompt = captured["prompt"]
    # block is first, then a blank line, then the task-centric prompt
    assert prompt.startswith("[PRIOR CONTEXT]\n- atom A\n- atom B\n\n")
    # compose_prompt content still present after the block
    assert "Task ID: t-r1" in prompt and "ship it" in prompt


def test_run_skips_block_when_recall_returns_empty(monkeypatch):
    """Empty recall block → prompt unchanged (no leading blank lines, no header)."""
    monkeypatch.setenv("AGENT_TASK_ID", "t-r2")
    monkeypatch.setattr(acs.sys, "argv", ["agent_cold_start"])
    captured: dict = {}
    task = {"id": "t-r2", "title": "T", "description": "d", "acceptance_criteria": None}

    acs.run(
        resolve=lambda: None,
        fetch=lambda _t: task,
        claim=lambda _t, _c: True,
        agent=lambda prompt: captured.setdefault("prompt", prompt) or 0,
        finalize=lambda *a: None,
        save_atoms=lambda *a, **k: None,
        spawn_recall=lambda _t: "",
    )

    # First line is the worker preamble (compose_prompt start) — no recall header.
    assert captured["prompt"].startswith("You are an ephemeral Keiracom worker agent")


def test_recall_spawn_context_calls_build_with_task_type_and_brief(monkeypatch):
    """_recall_spawn_context passes task_type + (description OR title fallback)
    as task_brief, and returns the build helper's output verbatim."""
    import src.retrieval.spawn_recall as sr

    captured: dict = {}

    def fake_build(*, task_type, task_brief):
        captured["task_type"] = task_type
        captured["task_brief"] = task_brief
        return "BLOCK"

    monkeypatch.setattr(sr, "build_spawn_context_block", fake_build)

    out = acs._recall_spawn_context(
        {"id": "t-1", "task_type": "review", "description": "desc text"}
    )
    assert out == "BLOCK"
    assert captured == {"task_type": "review", "task_brief": "desc text"}

    # description missing → falls back to title
    captured.clear()
    acs._recall_spawn_context({"id": "t-2", "task_type": "build", "title": "title text"})
    assert captured["task_brief"] == "title text"


def test_recall_spawn_context_fail_open_returns_empty_on_error(monkeypatch):
    """Any error during recall → returns "", spawn proceeds without context."""
    import src.retrieval.spawn_recall as sr

    def boom(**_kw):
        raise RuntimeError("hindsight down")

    monkeypatch.setattr(sr, "build_spawn_context_block", boom)

    assert acs._recall_spawn_context({"id": "t-x", "task_type": "build"}) == ""


# ---- nd3b notify suppression for intermediate V1-chain steps -----------------


def _nd3b_run(monkeypatch, *, chain_step: str | None):
    """Drive run() once with notify recorded + CHAIN_STEP set/unset as requested."""
    monkeypatch.setenv("AGENT_TASK_ID", "t-cs")
    monkeypatch.setattr(acs.sys, "argv", ["agent_cold_start"])
    if chain_step is None:
        monkeypatch.delenv("CHAIN_STEP", raising=False)
    else:
        monkeypatch.setenv("CHAIN_STEP", chain_step)
    notify_calls: list = []
    acs.run(
        resolve=lambda: None,
        fetch=lambda _t: {"id": "t-cs", "title": "T", "acceptance_criteria": None},
        claim=lambda _t, _c: True,
        agent=lambda _p: 0,
        finalize=lambda *a: None,
        save_atoms=lambda *a, **k: None,
        notify=lambda *a, **kw: notify_calls.append((a, kw)),
        spawn_recall=lambda _t: "",
    )
    return notify_calls


def test_run_suppresses_notify_for_intermediate_chain_step(monkeypatch):
    """CHAIN_STEP=intermediate hop → notify must NOT fire (no #ceo spam)."""
    for intermediate in ("aiden_plan", "max_challenge", "nova_build", "orion_spec"):
        notify_calls = _nd3b_run(monkeypatch, chain_step=intermediate)
        assert notify_calls == [], f"intermediate step {intermediate!r} should suppress notify"


def test_run_calls_notify_for_final_chain_step(monkeypatch):
    """CHAIN_STEP=atlas_safety → notify fires (final reviewer posts to #ceo)."""
    notify_calls = _nd3b_run(monkeypatch, chain_step="atlas_safety")
    assert len(notify_calls) == 1


def test_run_calls_notify_when_chain_step_unset(monkeypatch):
    """CHAIN_STEP absent → notify fires as today (non-chain tasks unaffected)."""
    notify_calls = _nd3b_run(monkeypatch, chain_step=None)
    assert len(notify_calls) == 1


def test_run_calls_notify_when_chain_step_blank(monkeypatch):
    """CHAIN_STEP set but whitespace-only → treated as unset → notify fires."""
    notify_calls = _nd3b_run(monkeypatch, chain_step="   ")
    assert len(notify_calls) == 1
