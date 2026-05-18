"""Unit tests for scripts/fleet_supervisor.py (KEI-174).

All external calls (psycopg, subprocess, urllib) are mocked.
Covers all 6 scenarios + CEO post format check.
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Bootstrap: ensure scripts/ is importable
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import fleet_supervisor as fs  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

NOW_UTC = _dt.datetime(2026, 5, 17, 12, 0, 0, tzinfo=_dt.UTC)
RECENT = NOW_UTC - _dt.timedelta(minutes=5)
STALE = NOW_UTC - _dt.timedelta(minutes=20)


def _fake_conn(
    active_claim: tuple[str, str] | None = None,
    last_tool_call: _dt.datetime | None = RECENT,
    queue_counts: tuple[int, int, int] = (1, 0, 0),
    phase_max: int = 99,
    next_claim: tuple[str, str] | None = ("KEI-100", "Test task"),
):
    """Build a minimal mock psycopg connection for scenario tests."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    # Sequence fetchone returns per test need
    cursor.fetchone.side_effect = [
        # get_phase_max
        (phase_max,) if phase_max else None,
        # get_active_claim
        active_claim,
        # claim_next_task (only called when no active claim)
        next_claim,
        # get_last_tool_call
        (last_tool_call,),
        # extra calls if needed
        None,
        None,
        None,
    ]
    cursor.fetchall.return_value = []
    cursor.rowcount = 0
    return conn, cursor


# ---------------------------------------------------------------------------
# Test helpers for patching
# ---------------------------------------------------------------------------

AGENT_ELLIOT = {"callsign": "elliot", "tmux": "elliottbot:0", "service": "elliot-agent"}


def _patch_externals(
    tmux_alive: bool = True,
    context_full: bool = False,
    prs: list | None = None,
):
    """Return a context manager tuple for common patches."""
    prs = prs or []
    patches = [
        patch.object(fs, "tmux_has_session", return_value=tmux_alive),
        patch.object(fs, "context_is_full", return_value=context_full),
        patch.object(fs, "tmux_send"),
        patch.object(fs, "fetch_linear_description", return_value=("Title", "Desc")),
        patch.object(fs, "restart_service"),
        patch.object(fs, "list_open_prs", return_value=prs),
    ]
    return patches


# ---------------------------------------------------------------------------
# Scenario 1: idle with queue → claim + inject
# ---------------------------------------------------------------------------


def test_scenario_1_idle_with_queue(monkeypatch):
    conn = MagicMock()

    monkeypatch.setattr(fs, "get_phase_max", lambda c: 99)
    monkeypatch.setattr(fs, "get_active_claim", lambda c, cs: None)
    monkeypatch.setattr(fs, "claim_next_task", lambda c, cs, ph: ("KEI-100", "Build feature"))
    monkeypatch.setattr(fs, "fetch_linear_description", lambda kei: ("Build feature", "Do X"))
    monkeypatch.setattr(fs, "tmux_has_session", lambda s: True)
    monkeypatch.setattr(fs, "inject_task", MagicMock())
    monkeypatch.setattr(fs, "find_pr_for_review", lambda prs, cs: None)
    monkeypatch.setattr(fs, "list_open_prs", lambda: [])

    inject_mock = MagicMock()
    monkeypatch.setattr(fs, "inject_task", inject_mock)

    status = fs.process_agent(AGENT_ELLIOT, conn, [], 99)

    assert status.active_task_id == "KEI-100"
    assert "claimed" in status.summary
    inject_mock.assert_called_once()


# ---------------------------------------------------------------------------
# Scenario 2a: idle + queue empty + open PR needs review
# ---------------------------------------------------------------------------


def test_scenario_2_idle_no_queue_pr_review(monkeypatch):
    conn = MagicMock()
    pr = {
        "number": 42,
        "title": "[AIDEN] feat: something",
        "url": "https://github.com/org/repo/pull/42",
        "reviews": [],
        "author": {"login": "aidenbot"},
    }
    monkeypatch.setattr(fs, "get_phase_max", lambda c: 99)
    monkeypatch.setattr(fs, "get_active_claim", lambda c, cs: None)
    monkeypatch.setattr(fs, "claim_next_task", lambda c, cs, ph: None)
    monkeypatch.setattr(fs, "tmux_has_session", lambda s: True)
    monkeypatch.setattr(fs, "insert_review_task", MagicMock())
    inject_mock = MagicMock()
    monkeypatch.setattr(fs, "inject_task", inject_mock)

    status = fs.process_agent(AGENT_ELLIOT, conn, [pr], 99)

    assert status.active_task_id == "REVIEW-PR-42"
    inject_mock.assert_called_once()
    assert "reviewing PR #42" in status.summary


# ---------------------------------------------------------------------------
# Scenario 2b: idle + no queue + no PRs → log only
# ---------------------------------------------------------------------------


def test_scenario_2_idle_no_work(monkeypatch):
    conn = MagicMock()
    monkeypatch.setattr(fs, "get_phase_max", lambda c: 99)
    monkeypatch.setattr(fs, "get_active_claim", lambda c, cs: None)
    monkeypatch.setattr(fs, "claim_next_task", lambda c, cs, ph: None)
    monkeypatch.setattr(fs, "tmux_has_session", lambda s: True)
    inject_mock = MagicMock()
    monkeypatch.setattr(fs, "inject_task", inject_mock)

    status = fs.process_agent(AGENT_ELLIOT, conn, [], 99)

    assert status.active_task_id is None
    inject_mock.assert_not_called()
    assert "idle" in status.summary


# ---------------------------------------------------------------------------
# Scenario 3a: claimed + stale (<100% context) → nudge
# ---------------------------------------------------------------------------


def test_scenario_3_stuck_low_context(monkeypatch):
    conn = MagicMock()
    # Return a timestamp 16 minutes ago (stale beyond the 15-min threshold)
    stale_ts = _dt.datetime.now(_dt.UTC) - _dt.timedelta(minutes=16)

    monkeypatch.setattr(fs, "get_phase_max", lambda c: 99)
    monkeypatch.setattr(fs, "get_active_claim", lambda c, cs: ("KEI-55", "Stale task"))
    monkeypatch.setattr(fs, "get_last_tool_call", lambda c, cs: stale_ts)
    monkeypatch.setattr(fs, "tmux_has_session", lambda s: True)
    monkeypatch.setattr(fs, "context_is_full", lambda s: False)
    inject_mock = MagicMock()
    monkeypatch.setattr(fs, "inject_task", inject_mock)
    monkeypatch.setattr(fs, "restart_service", MagicMock())

    status = fs.process_agent(AGENT_ELLIOT, conn, [], 99)

    inject_mock.assert_called_once()
    nudge_text = inject_mock.call_args[0][1]
    assert "KEI-55" in nudge_text
    assert "nudged" in status.summary


# ---------------------------------------------------------------------------
# Scenario 3b: claimed + stale + 100% context → restart + re-claim
# ---------------------------------------------------------------------------


def test_scenario_3_stuck_high_context(monkeypatch):
    conn = MagicMock()
    # Return a timestamp 16 minutes ago (stale beyond the 15-min threshold)
    stale_ts = _dt.datetime.now(_dt.UTC) - _dt.timedelta(minutes=16)

    restart_mock = MagicMock()
    inject_mock = MagicMock()

    monkeypatch.setattr(fs, "get_phase_max", lambda c: 99)
    monkeypatch.setattr(fs, "get_active_claim", lambda c, cs: ("KEI-55", "Context-full task"))
    monkeypatch.setattr(fs, "get_last_tool_call", lambda c, cs: stale_ts)
    monkeypatch.setattr(fs, "tmux_has_session", lambda s: True)
    monkeypatch.setattr(fs, "context_is_full", lambda s: True)
    monkeypatch.setattr(fs, "restart_service", restart_mock)
    monkeypatch.setattr(fs, "inject_task", inject_mock)
    monkeypatch.setattr(fs, "fetch_linear_description", lambda kei: ("Context-full task", "desc"))

    status = fs.process_agent(AGENT_ELLIOT, conn, [], 99)

    restart_mock.assert_called_once_with("elliot-agent")
    inject_mock.assert_called_once()
    assert "restarted" in status.summary
    assert "context" in status.summary


# ---------------------------------------------------------------------------
# Scenario 4: dead tmux → restart + claim
# ---------------------------------------------------------------------------


def test_scenario_4_dead_tmux(monkeypatch):
    conn = MagicMock()
    restart_mock = MagicMock()
    inject_mock = MagicMock()

    call_count = [0]

    def tmux_alive_after_restart(session):
        call_count[0] += 1
        return call_count[0] > 1  # first call returns False (dead), second True (alive)

    monkeypatch.setattr(fs, "tmux_has_session", tmux_alive_after_restart)
    monkeypatch.setattr(fs, "restart_service", restart_mock)
    monkeypatch.setattr(fs, "claim_next_task", lambda c, cs, ph: ("KEI-99", "Next task"))
    monkeypatch.setattr(fs, "fetch_linear_description", lambda kei: ("Next task", "details"))
    monkeypatch.setattr(fs, "inject_task", inject_mock)

    status = fs.process_agent(AGENT_ELLIOT, conn, [], 99)

    restart_mock.assert_called_once_with("elliot-agent")
    assert "dead" in status.summary or "restarted" in status.summary


# ---------------------------------------------------------------------------
# Scenario 5: agent has authored PR + idle (queue empty after shipping)
# ---------------------------------------------------------------------------


def test_scenario_5_shipped_pr_idle(monkeypatch):
    conn = MagicMock()
    pr = {
        "number": 99,
        "title": "[ELLIOT] feat: shipped thing",
        "url": "https://github.com/org/repo/pull/99",
        "reviews": [],
        "author": {"login": "elliotbot"},
    }
    monkeypatch.setattr(fs, "get_phase_max", lambda c: 99)
    monkeypatch.setattr(fs, "get_active_claim", lambda c, cs: None)
    monkeypatch.setattr(fs, "claim_next_task", lambda c, cs, ph: None)
    monkeypatch.setattr(fs, "tmux_has_session", lambda s: True)
    inject_mock = MagicMock()
    monkeypatch.setattr(fs, "inject_task", inject_mock)

    status = fs.process_agent(AGENT_ELLIOT, conn, [pr], 99)

    # Agent has open authored PR, queue empty — correctly idle
    assert status.active_task_id is None
    inject_mock.assert_not_called()
    assert "idle" in status.summary or "shipped" in status.summary


# ---------------------------------------------------------------------------
# Scenario 6: stale claim release
# ---------------------------------------------------------------------------


def test_scenario_6_stale_claim_release():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.rowcount = 3

    released = fs.release_stale_claims(conn)

    conn.commit.assert_called_once()
    assert released == 3
    executed_sql = cursor.execute.call_args[0][0]
    assert "available" in executed_sql
    assert "2 hours" in executed_sql or "INTERVAL" in executed_sql


# ---------------------------------------------------------------------------
# CEO post format: plain English, no PR #, no code fences
# ---------------------------------------------------------------------------


def test_ceo_post_format(monkeypatch):
    report = fs.FleetReport(
        statuses=[
            fs.AgentStatus(
                "elliot",
                "elliottbot:0",
                "elliot-agent",
                summary="building KEI-50 (last activity 3m ago)",
            ),
            fs.AgentStatus(
                "aiden", "aiden:0", "aiden-agent", summary="was idle, claimed KEI-51, injected task"
            ),
            fs.AgentStatus(
                "max", "max:0", "max-agent", summary="shipped pull request, idle, queue empty"
            ),
            fs.AgentStatus(
                "atlas", "atlas:0", "atlas-agent", summary="building KEI-52 (last activity 2m ago)"
            ),
            fs.AgentStatus(
                "orion", "orion:0", "orion-agent", summary="was idle, claimed KEI-53, injected task"
            ),
            fs.AgentStatus(
                "scout",
                "scout:0",
                "scout-agent",
                summary="queue empty, no reviews — correctly idle",
            ),
        ],
        queue_available=2,
        queue_active=3,
        queue_done=10,
    )

    posted_texts = []

    def fake_subprocess_run(cmd, **kwargs):
        if cmd[0].endswith("tg"):
            posted_texts.append(cmd[-1])
        result = MagicMock()
        result.returncode = 0
        return result

    with patch("fleet_supervisor.subprocess.run", side_effect=fake_subprocess_run):
        fs.post_ceo_status(report)

    assert posted_texts, "post_ceo_status should have called tg"
    text = posted_texts[0]

    # Must have Fleet Status header
    assert "Fleet Status" in text

    # Must contain all 6 agents
    for callsign in ["elliot", "aiden", "max", "atlas", "orion", "scout"]:
        assert callsign in text

    # Must contain queue counts
    assert "2 available" in text
    assert "3 active" in text
    assert "10 done" in text

    # Must NOT contain code fence markers
    assert "```" not in text


# ---------------------------------------------------------------------------
# Review prompt: correct format
# ---------------------------------------------------------------------------


def test_build_review_prompt_format():
    prompt = fs.build_review_prompt(42, "feat: add thing", "https://gh/pr/42", "elliot")
    assert "PR #42" in prompt
    assert "[REVIEW:elliot]" in prompt
    assert "APPROVE or HOLD" in prompt
    assert "gh pr view 42" in prompt


# ---------------------------------------------------------------------------
# Task prompt: description truncated at 2000 chars
# ---------------------------------------------------------------------------


def test_build_task_prompt_truncation():
    long_desc = "x" * 3000
    prompt = fs.build_task_prompt("KEI-1", "Title", long_desc)
    assert "x" * 2000 in prompt
    assert "x" * 2001 not in prompt
    assert "Don't ask — execute" in prompt


# ---------------------------------------------------------------------------
# PR authorship detection
# ---------------------------------------------------------------------------


def test_is_authored_by_callsign():
    pr = {"title": "[ELLIOT] feat: something", "reviews": []}
    assert fs.is_authored_by_callsign(pr, "elliot") is True
    assert fs.is_authored_by_callsign(pr, "aiden") is False


def test_agent_has_reviewed():
    pr = {"reviews": [{"body": "looks good [REVIEW:elliot] APPROVE"}]}
    assert fs.agent_has_reviewed(pr, "elliot") is True
    assert fs.agent_has_reviewed(pr, "aiden") is False


# ---------------------------------------------------------------------------
# KEI-176: find_pr_for_review checks PR comments for [REVIEW:callsign] markers
# ---------------------------------------------------------------------------


def test_find_pr_for_review_skips_already_reviewed(monkeypatch):
    """Agent does NOT get dispatched for a PR where its [REVIEW:callsign] is in comments."""
    pr = {
        "number": 55,
        "title": "[ELLIOT] feat: some work",
        "url": "https://github.com/org/repo/pull/55",
        "reviews": [],
    }

    def fake_fetch_comments(pr_number):
        return [{"body": "[REVIEW:aiden] APPROVE — looks good"}]

    monkeypatch.setattr(fs, "fetch_pr_comments", fake_fetch_comments)

    result = fs.find_pr_for_review([pr], "aiden")

    # aiden has reviewed this PR via comment — must NOT be selected
    assert result is None


def test_find_pr_for_review_picks_unreviewed_pr(monkeypatch):
    """When one PR has an aiden review comment and another doesn't, pick the unreviewed one."""
    pr_reviewed = {
        "number": 10,
        "title": "[ELLIOT] feat: reviewed thing",
        "url": "https://github.com/org/repo/pull/10",
        "reviews": [],
    }
    pr_fresh = {
        "number": 20,
        "title": "[ELLIOT] feat: fresh thing",
        "url": "https://github.com/org/repo/pull/20",
        "reviews": [],
    }

    def fake_fetch_comments(pr_number):
        if pr_number == 10:
            return [{"body": "[REVIEW:aiden] HOLD — needs changes"}]
        return []

    monkeypatch.setattr(fs, "fetch_pr_comments", fake_fetch_comments)

    result = fs.find_pr_for_review([pr_reviewed, pr_fresh], "aiden")

    assert result is not None
    assert result["number"] == 20


def test_find_pr_for_review_callsign_case_insensitive(monkeypatch):
    """[REVIEW:AIDEN] (uppercase) is recognized as aiden already reviewed."""
    pr = {
        "number": 77,
        "title": "[ELLIOT] feat: caps test",
        "url": "https://github.com/org/repo/pull/77",
        "reviews": [],
    }

    def fake_fetch_comments(pr_number):
        return [{"body": "[REVIEW:AIDEN] APPROVE"}]

    monkeypatch.setattr(fs, "fetch_pr_comments", fake_fetch_comments)

    result = fs.find_pr_for_review([pr], "aiden")

    # Despite uppercase AIDEN, the match should fire and the PR should be skipped
    assert result is None


# ---------------------------------------------------------------------------
# KEI-202 — supervisor observation writer (institutional knowledge capture)
# ---------------------------------------------------------------------------


def _capture_observations_conn():
    """Build a fake psycopg connection that records every INSERT'd
    observation payload for assertions."""
    captured: list[dict] = []
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    def fake_execute(sql, params=None):
        if "INSERT INTO public.agent_memories" in (sql or ""):
            content, typed_metadata, tags = params
            captured.append({"content": content, "typed_metadata": typed_metadata, "tags": tags})

    cursor.execute = MagicMock(side_effect=fake_execute)
    conn.commit = MagicMock()
    conn._captured = captured
    return conn


def test_write_observation_inserts_correct_shape():
    """One call → one INSERT with the documented column shape."""
    import json as _json

    conn = _capture_observations_conn()
    fs._write_observation(
        conn,
        cycle_id="cycle-xyz",
        scenario="scenario_1_idle_with_queue",
        agent_callsign="atlas",
        kei_id="KEI-202",
        action="claimed",
        outcome="was idle, claimed KEI-202, injected task",
    )
    assert len(conn._captured) == 1
    row = conn._captured[0]
    content = _json.loads(row["content"])
    md = _json.loads(row["typed_metadata"])
    assert content["scenario"] == "scenario_1_idle_with_queue"
    assert content["agent"] == "atlas"
    assert content["kei_id"] == "KEI-202"
    assert content["action"] == "claimed"
    assert content["outcome"] == "was idle, claimed KEI-202, injected task"
    assert "timestamp" in content
    assert md["cycle_id"] == "cycle-xyz"
    assert md["supervisor_version"] == fs.SUPERVISOR_VERSION
    assert md["agent"] == "atlas"
    assert md["kei_id"] == "KEI-202"
    assert md["action"] == "claimed"
    assert "supervisor" in row["tags"]
    assert "fleet_observation" in row["tags"]
    assert "scenario_1_idle_with_queue" in row["tags"]
    assert "atlas" in row["tags"]


def test_write_observation_swallows_db_errors(caplog):
    """Best-effort: institutional-memory write failure MUST NOT propagate.
    The supervisor cycle survives + logs a warning (per feedback_silence_is_status
    + supervisor-must-survive-downstream-outages)."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute = MagicMock(side_effect=RuntimeError("supabase pooler down"))
    conn.commit = MagicMock()

    with caplog.at_level("WARNING"):
        fs._write_observation(
            conn,
            cycle_id="cycle-xyz",
            scenario="scenario_4_dead_session",
            agent_callsign="atlas",
            kei_id=None,
            action="restarted",
            outcome="session dead, restarted, queue empty",
        )
    assert any("supabase pooler down" in r.message for r in caplog.records)


def test_record_handler_observation_classifies_actions():
    """The bridge function inspects status.summary to pick the right action."""
    import json as _json

    conn = _capture_observations_conn()
    cases = [
        ("was idle, claimed KEI-X, injected task", "claimed"),
        ("was idle, reviewing PR #42", "dispatched_review"),
        ("100%% context, restarted, re-claimed KEI-X", "restarted"),
        ("nudged on KEI-X (16m stale)", "nudged"),
        ("shipped pull request, idle, queue empty", "marked_idle_shipped"),
        ("building KEI-X (last activity 3m ago)", "no_op_building"),
        ("queue empty, no reviews — correctly idle", "marked_idle"),
    ]
    for summary, _ in cases:
        status = fs.AgentStatus(
            callsign="atlas",
            tmux_session="atlas:0",
            service_name="atlas-agent",
            summary=summary,
        )
        fs._record_handler_observation(conn, "cycle-1", "scenario_test", status)
    assert len(conn._captured) == 7
    for i, (_, expected) in enumerate(cases):
        assert _json.loads(conn._captured[i]["content"])["action"] == expected, (
            f"case {i}: {cases[i][0]!r} → expected {expected}"
        )


def test_process_agent_writes_observation_on_idle_with_queue(monkeypatch):
    """E2E Scenario 1 — process_agent writes one observation row per resolution."""
    import json as _json

    conn = _capture_observations_conn()
    monkeypatch.setattr(fs, "get_active_claim", lambda c, cs: None)
    monkeypatch.setattr(fs, "claim_next_task", lambda c, cs, ph: ("KEI-100", "Test task"))
    monkeypatch.setattr(fs, "fetch_linear_description", lambda kei: ("Test", "Do X"))
    monkeypatch.setattr(fs, "tmux_has_session", lambda s: True)
    monkeypatch.setattr(fs, "inject_task", MagicMock())

    status = fs.process_agent(AGENT_ELLIOT, conn, [], 99, cycle_id="cycle-abc")

    assert status.active_task_id == "KEI-100"
    assert len(conn._captured) == 1
    md = _json.loads(conn._captured[0]["typed_metadata"])
    assert md["cycle_id"] == "cycle-abc"
    assert "scenario_1_idle_with_queue" in conn._captured[0]["tags"]
    assert md["action"] == "claimed"


def test_process_agent_writes_observation_on_dead_session(monkeypatch):
    """E2E Scenario 4 — dead-tmux resolution writes its observation."""
    conn = _capture_observations_conn()
    monkeypatch.setattr(fs, "tmux_has_session", lambda s: False)
    monkeypatch.setattr(fs, "restart_service", MagicMock())
    monkeypatch.setattr(fs, "claim_next_task", lambda c, cs, ph: None)
    monkeypatch.setattr(fs, "inject_task", MagicMock())

    status = fs.process_agent(AGENT_ELLIOT, conn, [], 99, cycle_id="cycle-abc")
    assert status.tmux_alive is False
    assert len(conn._captured) == 1
    assert "scenario_4_dead_session" in conn._captured[0]["tags"]


def test_process_agent_writes_observation_per_cycle_id(monkeypatch):
    """3 process_agent calls — first two share cycle_id, third differs.
    Observations downstream correlate per cycle for retrieval/analysis."""
    import json as _json

    conn = _capture_observations_conn()
    monkeypatch.setattr(fs, "get_active_claim", lambda c, cs: None)
    monkeypatch.setattr(fs, "claim_next_task", lambda c, cs, ph: ("KEI-X", "X"))
    monkeypatch.setattr(fs, "fetch_linear_description", lambda kei: ("X", "x"))
    monkeypatch.setattr(fs, "tmux_has_session", lambda s: True)
    monkeypatch.setattr(fs, "inject_task", MagicMock())

    fs.process_agent(AGENT_ELLIOT, conn, [], 99, cycle_id="cycle-shared")
    fs.process_agent(AGENT_ELLIOT, conn, [], 99, cycle_id="cycle-shared")
    fs.process_agent(AGENT_ELLIOT, conn, [], 99, cycle_id="cycle-other")

    cycles = [_json.loads(c["typed_metadata"])["cycle_id"] for c in conn._captured]
    assert cycles == ["cycle-shared", "cycle-shared", "cycle-other"]


def test_supervisor_version_constant_exists():
    """SUPERVISOR_VERSION sentinel is exposed for typed_metadata + KEI-185 bump."""
    assert isinstance(fs.SUPERVISOR_VERSION, int)
    assert fs.SUPERVISOR_VERSION >= 1
