"""Tests for fleet_supervisor.release_already_reviewed_claims.

Sibling to test_fleet_supervisor_auto_claim_race.py. That one tests the
dispatch-TIME race pre-check; this one tests the post-review claim sweeper
that fires every supervisor cycle.

bd: Agency_OS-tp15 (follow-up to Agency_OS-f0qn / PR #1199).
"""

from __future__ import annotations

import subprocess
from typing import Any
from unittest.mock import MagicMock

from scripts import fleet_supervisor

# ─── _callsign_review_marker_in_comments ───────────────────────────────────────


def test_marker_helper_returns_true_when_marker_present():
    comments = [
        {"body": "thumbs up"},
        {"body": "[NOVA] **[REVIEW:approve:nova]** — looks good."},
    ]
    assert fleet_supervisor._callsign_review_marker_in_comments(comments, "nova") is True


def test_marker_helper_returns_true_for_hold_marker():
    comments = [{"body": "[REVIEW:HOLD:nova] one NIT"}]
    assert fleet_supervisor._callsign_review_marker_in_comments(comments, "nova") is True


def test_marker_helper_returns_false_when_callsign_absent():
    comments = [{"body": "[REVIEW:approve:atlas]"}, {"body": "other text"}]
    assert fleet_supervisor._callsign_review_marker_in_comments(comments, "nova") is False


def test_marker_helper_returns_false_on_empty_comments():
    assert fleet_supervisor._callsign_review_marker_in_comments([], "nova") is False


def test_marker_helper_handles_missing_body_field():
    comments = [{}, {"body": None}]
    assert fleet_supervisor._callsign_review_marker_in_comments(comments, "nova") is False


# ─── release_already_reviewed_claims ───────────────────────────────────────────


def _fake_conn_with_review_claims(rows: list[tuple[str, str]]) -> Any:
    """Return a MagicMock psycopg connection scripting the SELECT result."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = rows
    cursor.rowcount = 1  # each UPDATE pretends to affect 1 row
    return conn, cursor


def test_release_skips_when_no_active_review_claims(monkeypatch):
    conn, cursor = _fake_conn_with_review_claims(rows=[])
    fetch_calls: list[int] = []
    monkeypatch.setattr(
        fleet_supervisor,
        "fetch_pr_comments",
        lambda n: fetch_calls.append(n) or [],
    )
    released = fleet_supervisor.release_already_reviewed_claims(conn)
    assert released == 0
    assert fetch_calls == []  # never reached fetch path
    conn.commit.assert_not_called()


def test_release_clears_claim_when_marker_present(monkeypatch):
    conn, cursor = _fake_conn_with_review_claims(
        rows=[("REVIEW-PR-1179", "nova")],
    )
    monkeypatch.setattr(
        fleet_supervisor,
        "fetch_pr_comments",
        lambda n: [{"body": "[REVIEW:approve:nova] — done."}],
    )
    released = fleet_supervisor.release_already_reviewed_claims(conn)
    assert released == 1
    # UPDATE was issued
    update_calls = [c for c in cursor.execute.call_args_list if "UPDATE public.tasks" in c.args[0]]
    assert len(update_calls) == 1
    assert update_calls[0].args[1] == ("REVIEW-PR-1179",)
    conn.commit.assert_called_once()


def test_release_skips_claim_when_no_marker(monkeypatch):
    conn, cursor = _fake_conn_with_review_claims(
        rows=[("REVIEW-PR-1200", "nova")],
    )
    monkeypatch.setattr(
        fleet_supervisor,
        "fetch_pr_comments",
        lambda n: [{"body": "[REVIEW:approve:atlas]"}],  # different callsign
    )
    released = fleet_supervisor.release_already_reviewed_claims(conn)
    assert released == 0
    update_calls = [c for c in cursor.execute.call_args_list if "UPDATE public.tasks" in c.args[0]]
    assert update_calls == []
    conn.commit.assert_not_called()


def test_release_handles_multiple_claims_independently(monkeypatch):
    conn, cursor = _fake_conn_with_review_claims(
        rows=[
            ("REVIEW-PR-1100", "nova"),  # marker present → release
            ("REVIEW-PR-1101", "nova"),  # no marker → skip
            ("REVIEW-PR-1102", "atlas"),  # marker present → release
        ],
    )

    def _comments(pr_number: int) -> list[dict]:
        return {
            1100: [{"body": "[REVIEW:approve:nova]"}],
            1101: [{"body": "no review marker here"}],
            1102: [{"body": "[REVIEW:HOLD:atlas]"}],
        }[pr_number]

    monkeypatch.setattr(fleet_supervisor, "fetch_pr_comments", _comments)
    released = fleet_supervisor.release_already_reviewed_claims(conn)
    assert released == 2
    update_calls = [c for c in cursor.execute.call_args_list if "UPDATE public.tasks" in c.args[0]]
    update_targets = sorted(c.args[1][0] for c in update_calls)
    assert update_targets == ["REVIEW-PR-1100", "REVIEW-PR-1102"]


def test_release_skips_malformed_task_id(monkeypatch):
    """Defensive: a non-conforming REVIEW-PR-... id should be skipped, not raise."""
    conn, cursor = _fake_conn_with_review_claims(
        rows=[("REVIEW-PR-not-a-number", "nova")],
    )
    monkeypatch.setattr(fleet_supervisor, "fetch_pr_comments", lambda n: [])
    released = fleet_supervisor.release_already_reviewed_claims(conn)
    assert released == 0


def test_release_fails_open_on_gh_timeout(monkeypatch):
    """gh subprocess timeout → log + skip + continue with next claim."""
    conn, cursor = _fake_conn_with_review_claims(
        rows=[
            ("REVIEW-PR-9001", "nova"),  # will timeout
            ("REVIEW-PR-9002", "nova"),  # second one succeeds
        ],
    )

    def _comments(pr_number: int) -> list[dict]:
        if pr_number == 9001:
            raise subprocess.TimeoutExpired(cmd="gh", timeout=15)
        return [{"body": "[REVIEW:approve:nova]"}]

    monkeypatch.setattr(fleet_supervisor, "fetch_pr_comments", _comments)
    released = fleet_supervisor.release_already_reviewed_claims(conn)
    # 9001 skipped on timeout; 9002 released cleanly
    assert released == 1


def test_release_does_not_call_commit_when_zero_released(monkeypatch):
    """commit() costs network/disk — only fire when we actually changed rows."""
    conn, cursor = _fake_conn_with_review_claims(
        rows=[("REVIEW-PR-1234", "nova")],
    )
    monkeypatch.setattr(
        fleet_supervisor,
        "fetch_pr_comments",
        lambda n: [{"body": "no marker"}],
    )
    fleet_supervisor.release_already_reviewed_claims(conn)
    conn.commit.assert_not_called()
