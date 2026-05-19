"""Unit tests for scripts/fleet_supervisor.py (KEI-174).

All external calls (psycopg, subprocess, urllib) are mocked.
Covers all 6 scenarios + CEO post format check.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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


# ─── KEI-199: PR-existence pre-check for claim dispatch ─────────────────────


def test_fetch_open_pr_kei_ids_extracts_from_title_and_body(monkeypatch):
    """KEI-199 — open PR titles + bodies are scanned for KEI-NNN tokens.
    Anchor: 4 drift-syncs (KEI-90/122/187/188) caused by supervisor
    re-claiming work already in-flight via OPEN PRs."""
    fake_output = json.dumps(
        [
            {
                "title": "[AIDEN] feat(kei199): supervisor PR-existence pre-check",
                "body": "Closes KEI-199",
            },
            {"title": "[MAX] fix(kei188): migration apply gate", "body": "Also touches KEI-90"},
            {"title": "[ELLIOT] docs(no-kei)", "body": "no kei mentioned"},
        ]
    )
    fake_result = MagicMock(returncode=0, stdout=fake_output)
    with patch("subprocess.run", return_value=fake_result):
        ids = fs.fetch_open_pr_kei_ids()
    assert ids == {"KEI-199", "KEI-188", "KEI-90"}


def test_fetch_open_pr_kei_ids_fail_open_on_gh_error(monkeypatch):
    """KEI-199 — gh CLI failure must NOT block claims (fail-open)."""
    fake_result = MagicMock(returncode=1, stdout="", stderr="gh: not found")
    with patch("subprocess.run", return_value=fake_result):
        ids = fs.fetch_open_pr_kei_ids()
    assert ids == set()


def test_fetch_open_pr_kei_ids_fail_open_on_subprocess_exception(monkeypatch):
    """KEI-199 — subprocess.SubprocessError or OSError still fail-open."""
    with patch("subprocess.run", side_effect=OSError("no gh in PATH")):
        ids = fs.fetch_open_pr_kei_ids()
    assert ids == set()


def test_fetch_open_pr_kei_ids_handles_malformed_json(monkeypatch):
    """KEI-199 — JSON parse failure fail-opens to empty set."""
    fake_result = MagicMock(returncode=0, stdout="not valid json")
    with patch("subprocess.run", return_value=fake_result):
        ids = fs.fetch_open_pr_kei_ids()
    assert ids == set()


class _FakeCur:
    """Test helper: configurable cursor returning preset rows."""

    def __init__(self, candidates=None, blocker_rows=None):
        self.candidates = list(candidates or [])
        self.blocker_rows = list(blocker_rows or [])
        self._next_fetchall = self.candidates
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        # Heuristic: if the SQL references task_verifications OR public.tasks
        # WHERE id = ANY (blocker lookup), the NEXT fetchall returns blocker_rows.
        # Otherwise it returns the candidate list.
        if "status != 'done'" in sql and "ANY" in sql:
            self._next_fetchall = self.blocker_rows
        else:
            self._next_fetchall = self.candidates

    def fetchall(self):
        rows = self._next_fetchall
        # Subsequent fetchall calls return [] unless re-armed by another execute.
        self._next_fetchall = []
        return rows

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _FakeConn:
    def __init__(self, cur: _FakeCur):
        self._cur = cur

    def cursor(self):
        return self._cur

    def commit(self):
        pass


def test_claim_next_task_excludes_keis_with_open_prs(monkeypatch):
    """KEI-199 — when an open PR mentions KEI-N, claim_next_task SKIPS that
    KEI-N in the SELECT (id != ALL excluded_keis). Anchor scenario: the 4
    drift-syncs would have been prevented by this filter."""
    with patch.object(fs, "fetch_open_pr_kei_ids", return_value={"KEI-188"}):
        cur = _FakeCur(candidates=[("KEI-200", "different task", "")])
        result = fs.claim_next_task(_FakeConn(cur), "aiden", 99)
        assert result == ("KEI-200", "different task")
        select_query = next(q for q, _ in cur.executed if "SELECT id, title" in q)
        assert "!= ALL" in select_query
        select_params = next(p for q, p in cur.executed if "SELECT id, title" in q)
        # phase_max, sorted(open_pr_keis), candidate_limit
        assert select_params[0] == 99
        assert select_params[1] == ["KEI-188"]


def test_claim_next_task_no_open_prs_uses_unfiltered_query(monkeypatch):
    """KEI-199 — when no open PRs exist (or fetch fails), the SELECT runs
    without the exclusion clause (preserves prior behaviour)."""
    with patch.object(fs, "fetch_open_pr_kei_ids", return_value=set()):
        cur = _FakeCur(candidates=[("KEI-300", "available task", "")])
        result = fs.claim_next_task(_FakeConn(cur), "aiden", 99)
        assert result == ("KEI-300", "available task")
        select_query = next(q for q, _ in cur.executed if "SELECT id, title" in q)
        assert "!= ALL" not in select_query


# ─── KEI-204: dep-blocked drift filter ──────────────────────────────────────


def test_extract_blocker_keis_matches_six_canonical_phrasings():
    """KEI-204 — the 6 patterns from this session's drift cases all extract."""
    samples = {
        "FOLLOW-UP after KEI-185": "KEI-185",
        "depends on KEI-100": "KEI-100",
        "gated on KEI-50": "KEI-50",
        "blocked on KEI-99": "KEI-99",
        "sub of KEI-185": "KEI-185",
        "(KEI-192 follow-up)": "KEI-192",
    }
    for text, expected in samples.items():
        blockers = fs.extract_blocker_keis(text)
        assert expected in blockers, f"failed to extract {expected} from {text!r}"


def test_extract_blocker_keis_empty_on_nondep_text():
    """KEI-204 — no false positives when text mentions KEI-N without dep phrasing."""
    assert fs.extract_blocker_keis("KEI-200: build feature") == set()
    assert fs.extract_blocker_keis("") == set()
    assert fs.extract_blocker_keis(None) == set()


def test_claim_next_task_skips_dep_blocked_candidate(monkeypatch):
    """KEI-204 — when top candidate's title says 'FOLLOW-UP after KEI-X' and
    KEI-X is still status != 'done', claim_next_task skips it and tries next."""
    with patch.object(fs, "fetch_open_pr_kei_ids", return_value=set()):
        # Candidate 1: blocked on KEI-185 (not done). Candidate 2: clean.
        cur = _FakeCur(
            candidates=[
                ("KEI-191", "FOLLOW-UP after KEI-185 migration", "details"),
                ("KEI-300", "unblocked task", "no deps"),
            ],
            blocker_rows=[("KEI-185",)],  # KEI-185 still active = unfinished
        )
        result = fs.claim_next_task(_FakeConn(cur), "aiden", 99)
        # Skip the blocked candidate, claim the clean one
        assert result == ("KEI-300", "unblocked task")


def test_claim_next_task_claims_dep_blocked_when_blocker_done(monkeypatch):
    """KEI-204 — when 'FOLLOW-UP after KEI-X' AND KEI-X status == 'done',
    claim_next_task proceeds with that row."""
    with patch.object(fs, "fetch_open_pr_kei_ids", return_value=set()):
        cur = _FakeCur(
            candidates=[("KEI-191", "FOLLOW-UP after KEI-185 migration", "")],
            blocker_rows=[],  # empty → KEI-185 is done OR not found
        )
        result = fs.claim_next_task(_FakeConn(cur), "aiden", 99)
        assert result == ("KEI-191", "FOLLOW-UP after KEI-185 migration")


def test_claim_next_task_returns_none_when_all_candidates_blocked(monkeypatch):
    """KEI-204 — if every top-N candidate is dep-blocked, return None
    instead of claiming a blocked row."""
    with patch.object(fs, "fetch_open_pr_kei_ids", return_value=set()):
        cur = _FakeCur(
            candidates=[
                ("KEI-301", "depends on KEI-100", ""),
                ("KEI-302", "blocked on KEI-200", ""),
            ],
            blocker_rows=[("KEI-100",), ("KEI-200",)],  # both blockers unfinished
        )
        result = fs.claim_next_task(_FakeConn(cur), "aiden", 99)
        assert result is None


# ---------------------------------------------------------------------------
# KEI-185 — Nova in AGENTS list + supervisor v2 enable flag
# ---------------------------------------------------------------------------


def test_kei185_nova_is_seventh_agent_in_fleet():
    """Nova must appear in AGENTS so the supervisor process_agent loop sees it."""
    callsigns = [a["callsign"] for a in fs.AGENTS]
    assert "nova" in callsigns
    nova = next(a for a in fs.AGENTS if a["callsign"] == "nova")
    assert nova["tmux"] == "nova:0"
    assert nova["service"] == "nova-agent"


def test_kei185_supervisor_v2_disabled_by_default(monkeypatch):
    monkeypatch.delenv("FLEET_SUPERVISOR_V2_ENABLED", raising=False)
    assert fs._supervisor_v2_enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "yes", "on", "Yes"])
def test_kei185_supervisor_v2_enabled_recognises_truthy_strings(val, monkeypatch):
    monkeypatch.setenv("FLEET_SUPERVISOR_V2_ENABLED", val)
    assert fs._supervisor_v2_enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "no", "off", "", "   "])
def test_kei185_supervisor_v2_enabled_rejects_falsy_strings(val, monkeypatch):
    monkeypatch.setenv("FLEET_SUPERVISOR_V2_ENABLED", val)
    assert fs._supervisor_v2_enabled() is False


def test_kei185_try_run_supervisor_v2_falls_back_on_importerror(monkeypatch, caplog):
    """When supervisor_v2 module is absent (KEI-183 PR #990 not merged),
    _try_run_supervisor_v2 must log a warning and return False so main()
    falls through to v1 instead of crashing.
    """
    import logging as _logging

    real_import = (
        __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__
    )

    def _fake_import(name, *args, **kwargs):
        if name == "src.fleet" or "supervisor_v2" in name:
            raise ImportError("v2 stub absent")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _fake_import)
    with caplog.at_level(_logging.WARNING):
        result = fs._try_run_supervisor_v2()
    assert result is False
    assert any("PR #990" in r.message for r in caplog.records)


def test_kei185_try_run_supervisor_v2_invokes_v2_when_present(monkeypatch):
    """When v2 imports cleanly, _try_run_supervisor_v2 must call v2.run()
    exactly once and return True so v1 is skipped.
    """
    import types as _types

    v2_module = _types.ModuleType("src.fleet.supervisor_v2")
    calls: list[str] = []

    def _v2_run():
        calls.append("ran")

    v2_module.run = _v2_run  # type: ignore[attr-defined]
    src_pkg = _types.ModuleType("src")
    fleet_pkg = _types.ModuleType("src.fleet")
    fleet_pkg.supervisor_v2 = v2_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src", src_pkg)
    monkeypatch.setitem(sys.modules, "src.fleet", fleet_pkg)
    monkeypatch.setitem(sys.modules, "src.fleet.supervisor_v2", v2_module)
    result = fs._try_run_supervisor_v2()
    assert result is True
    assert calls == ["ran"]
# ─── KEI-190: symmetric HOLD parsing ─────────────────────────────────────────


def test_comment_marker_matches_bare_hold():
    """KEI-190: [REVIEW:HOLD:orion] (the form every reviewer actually uses)
    must match — prior regex required -final and silently re-dispatched."""
    assert fs.comment_has_review_marker("[REVIEW:HOLD:orion]", "orion") is True


def test_comment_marker_matches_lowercase_hold():
    assert fs.comment_has_review_marker("[REVIEW:hold:scout] some body", "scout") is True


def test_comment_marker_matches_hold_final():
    assert fs.comment_has_review_marker("[REVIEW:HOLD-FINAL:max]", "max") is True


def test_comment_marker_matches_approve():
    """Regression — approve path must still match after the regex change."""
    assert fs.comment_has_review_marker("[REVIEW:approve:aiden] LGTM", "aiden") is True


def test_comment_marker_matches_bare_review():
    """Backwards compat — bare [REVIEW:callsign] still matches."""
    assert fs.comment_has_review_marker("[REVIEW:atlas] note", "atlas") is True


def test_comment_marker_no_match_for_other_callsign():
    assert fs.comment_has_review_marker("[REVIEW:HOLD:scout]", "orion") is False


def test_agent_has_reviewed_skips_pr_with_hold_comment(monkeypatch):
    """KEI-190 acceptance: PR with [REVIEW:HOLD:scout] is recognized as
    already-reviewed by scout, supervisor does NOT re-dispatch."""
    pr = {
        "number": 981,
        "title": "[ORION] feat(kei152): paddle handlers",
        "reviews": [],
    }
    monkeypatch.setattr(
        fs,
        "fetch_pr_comments",
        lambda _pr_number: [{"body": "[REVIEW:HOLD:scout] dup density 19.3%"}],
    )
    assert fs.agent_has_reviewed(pr, "scout") is True


# ─── KEI-189: Sonar QG dual-endpoint check ───────────────────────────────────


def test_fetch_sonar_status_returns_both_dimensions(monkeypatch):
    """KEI-189: fetch_sonar_status reads issues + QG endpoints."""

    class _Resp:
        def __init__(self, body):
            self._body = body

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return self._body

    def fake_urlopen(req, timeout=10):
        url = req if isinstance(req, str) else getattr(req, "full_url", "")
        if "issues/search" in url:
            return _Resp(b'{"total": 3, "issues": []}')
        if "qualitygates/project_status" in url:
            return _Resp(
                b'{"projectStatus": {"status": "ERROR", "conditions": ['
                b'{"metricKey": "new_duplicated_lines_density", "status": "ERROR",'
                b'"actualValue": "19.3", "errorThreshold": "3"}]}}'
            )
        return _Resp(b"{}")

    monkeypatch.setattr(fs.urllib.request, "urlopen", fake_urlopen)
    out = fs.fetch_sonar_status(981)
    assert out["issues_total"] == 3
    assert out["qg_status"] == "ERROR"
    assert any("new_duplicated_lines_density" in c for c in out["qg_failing"])


def test_fetch_sonar_status_fail_open(monkeypatch):
    """Sonar fetch failure → empty dict, never raises."""

    def bad_urlopen(*_a, **_k):
        raise RuntimeError("network down")

    monkeypatch.setattr(fs.urllib.request, "urlopen", bad_urlopen)
    out = fs.fetch_sonar_status(999)
    # Empty dict — fail-open, no fields set, no exception
    assert out == {}


def test_format_sonar_brief_renders_both_endpoints():
    sonar = {
        "issues_total": 2,
        "qg_status": "ERROR",
        "qg_failing": ["new_duplicated_lines_density=19.3 (>3)"],
    }
    text = fs._format_sonar_brief(sonar)
    assert "/api/issues/search" in text
    assert "total NEW unresolved: 2" in text
    assert "/api/qualitygates/project_status" in text
    assert "status: ERROR" in text
    assert "new_duplicated_lines_density" in text
    assert "BOTH endpoints" in text


def test_format_sonar_brief_empty_when_no_data():
    assert fs._format_sonar_brief({}) == ""


def test_build_review_prompt_includes_sonar_block(monkeypatch):
    """KEI-189 acceptance: review brief includes BOTH Sonar dimensions."""
    monkeypatch.setattr(
        fs,
        "fetch_sonar_status",
        lambda _n: {
            "issues_total": 0,
            "qg_status": "ERROR",
            "qg_failing": ["new_duplicated_lines_density=19.3 (>3)"],
        },
    )
    prompt = fs.build_review_prompt(
        pr_number=981,
        pr_title="[ORION] feat(kei152): paddle",
        pr_url="https://github.com/x/y/pull/981",
        callsign="aiden",
    )
    assert "Sonar" in prompt
    assert "issues_total" in prompt or "total NEW" in prompt
    assert "qg_status" in prompt or "status: ERROR" in prompt
    assert "BOTH endpoints" in prompt
