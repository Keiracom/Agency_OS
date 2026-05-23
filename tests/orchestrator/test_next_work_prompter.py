"""Tests for scripts/orchestrator/next_work_prompter.py — Agency_OS-sg29.

Classifier discipline (Aiden's note on the bd issue):
  - AUTHOR-blocked: CI red on the PR with at least one failing context NOT
    red on origin/main HEAD, OR a HOLD comment newer than the author's
    latest commit. Author must act → 1 nudge.
  - REVIEWER-blocked: CI green AND author's latest commit newer than every
    HOLD AND not yet dual-approved. Waiting on reviewer → 0 nudges to author.
  - INFRA-blocked: every failing PR check is also failing on main HEAD →
    repo-wide infra, not author-caused → 0 nudges to author.
  - MIXED: PR red on context X + main green on X (even if PR red on Y +
    main red on Y) → author owns X → 1 nudge.

Negative-path discipline (feedback_negative_path_test_before_approve):
  every fixture asserts the EXACT nudge count expected, not just "no error".
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "orchestrator"))

import next_work_prompter as nwp  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_caches(monkeypatch):
    nwp._reset_main_head_cache()
    yield
    nwp._reset_main_head_cache()


def _pr(
    number: int,
    title: str = "[ORION] feat(x): thing",
    failing_checks: list[str] | None = None,
    commits_ts: list[str] | None = None,
    hold_comments: list[tuple[str, str]] | None = None,
    approvals: list[str] | None = None,
) -> dict:
    """Build a synthetic PR record matching gh pr list --json shape."""
    rollup = []
    for name in failing_checks or []:
        rollup.append({"name": name, "conclusion": "FAILURE"})
    commits = [{"commit": {"committer": {"date": ts}}} for ts in (commits_ts or [])]
    comments = []
    for body, at in hold_comments or []:
        comments.append({"body": body, "createdAt": at})
    for cs in approvals or []:
        comments.append({"body": f"[CONCUR:{cs}]", "createdAt": "2099-01-01T00:00:00Z"})
    return {
        "number": number,
        "title": title,
        "statusCheckRollup": rollup,
        "commits": commits,
        "comments": comments,
    }


def _stub_main_failures(monkeypatch, failures: set[str]) -> None:
    monkeypatch.setattr(nwp, "_main_head_failures", lambda: failures)


def test_author_blocked_pr_red_main_green_one_nudge(monkeypatch):
    """PR backend test red + main backend test green → author owns it → AUTHOR."""
    pr = _pr(
        2001,
        failing_checks=["Backend Tests (Pytest)"],
        commits_ts=["2026-05-23T10:00:00Z"],
    )
    _stub_main_failures(monkeypatch, set())  # main is green on everything

    assert nwp.classify_pr_block(pr) == "author"

    monkeypatch.setattr(nwp, "_open_prs", lambda: [pr])
    assert nwp._own_prs_needing_fix("orion") == [2001]


def test_reviewer_blocked_green_ci_author_responded_zero_nudges(monkeypatch):
    """CI green, no HOLD newer than author's latest commit → REVIEWER."""
    pr = _pr(
        2002,
        failing_checks=[],
        commits_ts=["2026-05-23T15:00:00Z"],  # author commit AFTER any HOLD
        hold_comments=[("[REVIEW:HOLD:aiden] please fix X", "2026-05-23T12:00:00Z")],
    )
    _stub_main_failures(monkeypatch, set())

    assert nwp.classify_pr_block(pr) == "reviewer"

    monkeypatch.setattr(nwp, "_open_prs", lambda: [pr])
    assert nwp._own_prs_needing_fix("orion") == []


def test_infra_blocked_pr_red_main_also_red_zero_nudges(monkeypatch):
    """PR Vercel red + main Vercel red on same context → INFRA → no nudge.

    This is exactly the PR #1112 scenario that fired the false-nudge loop.
    """
    pr = _pr(
        1112,
        title="[ORION] feat(fleet-supervisor): fast error-aware agent stall detector",
        failing_checks=["Vercel – frontend"],
        commits_ts=["2026-05-20T22:49:00Z"],
    )
    _stub_main_failures(monkeypatch, {"Vercel – frontend"})

    assert nwp.classify_pr_block(pr) == "infra"

    monkeypatch.setattr(nwp, "_open_prs", lambda: [pr])
    assert nwp._own_prs_needing_fix("orion") == []


def test_mixed_pr_red_on_author_context_main_red_on_other_one_nudge(monkeypatch):
    """PR red on Backend Tests + Vercel; main red ONLY on Vercel.

    Author owns Backend Tests failure (NOT mirrored on main). Even though
    Vercel red mirrors main, the presence of a non-mirrored failure makes
    the whole PR AUTHOR-blocked → 1 nudge.
    """
    pr = _pr(
        2003,
        failing_checks=["Backend Tests (Pytest)", "Vercel – frontend"],
        commits_ts=["2026-05-23T10:00:00Z"],
    )
    _stub_main_failures(monkeypatch, {"Vercel – frontend"})

    assert nwp.classify_pr_block(pr) == "author"

    monkeypatch.setattr(nwp, "_open_prs", lambda: [pr])
    assert nwp._own_prs_needing_fix("orion") == [2003]


def test_author_blocked_hold_newer_than_latest_commit(monkeypatch):
    """CI green BUT a HOLD comment is newer than author's latest commit →
    author has not yet responded to the HOLD → AUTHOR."""
    pr = _pr(
        2004,
        failing_checks=[],
        commits_ts=["2026-05-23T10:00:00Z"],
        hold_comments=[("[REVIEW:HOLD:aiden] please fix Z", "2026-05-23T14:00:00Z")],
    )
    _stub_main_failures(monkeypatch, set())

    assert nwp.classify_pr_block(pr) == "author"


def test_dual_approved_returns_none(monkeypatch):
    """Two non-author CONCURs + green CI → merge-ready, classifier returns None."""
    pr = _pr(
        2005,
        title="[ORION] feat(x): thing",
        failing_checks=[],
        commits_ts=["2026-05-23T10:00:00Z"],
        approvals=["aiden", "max"],
    )
    _stub_main_failures(monkeypatch, set())

    assert nwp.classify_pr_block(pr) is None

    monkeypatch.setattr(nwp, "_open_prs", lambda: [pr])
    assert nwp._own_prs_needing_fix("orion") == []


def test_author_exclusion_other_callsigns_pr_ignored(monkeypatch):
    """A PR authored by SCOUT is not in orion's fix list, even if AUTHOR-blocked."""
    scout_pr = _pr(
        2006,
        title="[SCOUT] feat(y): other",
        failing_checks=["Backend Tests (Pytest)"],
        commits_ts=["2026-05-23T10:00:00Z"],
    )
    _stub_main_failures(monkeypatch, set())

    monkeypatch.setattr(nwp, "_open_prs", lambda: [scout_pr])
    assert nwp._own_prs_needing_fix("orion") == []
    assert nwp._own_prs_needing_fix("scout") == [2006]


def test_prompt_worker_silent_on_infra_blocked_pr(monkeypatch):
    """End-to-end: orion has only an INFRA-blocked PR + nothing in bd ready
    → prompt_worker returns None (silent — no nudge to inject)."""
    pr = _pr(
        1112,
        title="[ORION] feat(fleet-supervisor): fast error-aware agent stall detector",
        failing_checks=["Vercel – frontend"],
        commits_ts=["2026-05-20T22:49:00Z"],
    )
    _stub_main_failures(monkeypatch, {"Vercel – frontend"})
    monkeypatch.setattr(nwp, "_open_prs", lambda: [pr])
    monkeypatch.setattr(nwp, "_bd_in_progress", lambda cs: None)
    monkeypatch.setattr(nwp, "_bd_next_ready_for", lambda cs: None)

    assert nwp.prompt_worker("orion") is None


def test_prompt_worker_nudges_on_author_blocked_pr(monkeypatch):
    """End-to-end: AUTHOR-blocked PR → prompt_worker returns a [NEXT-WORK] string."""
    pr = _pr(
        2007,
        failing_checks=["Backend Tests (Pytest)"],
        commits_ts=["2026-05-23T10:00:00Z"],
    )
    _stub_main_failures(monkeypatch, set())
    monkeypatch.setattr(nwp, "_open_prs", lambda: [pr])

    prompt = nwp.prompt_worker("orion")
    assert prompt is not None
    assert "[NEXT-WORK:orion]" in prompt
    assert "2007" in prompt
