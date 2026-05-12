"""tests for src/bot_common/verify_gate.py — S1 outbound completion-claim verifier.

verify_gate.py shipped in PR #703 (177 LOC) without unit test coverage.
This file fills that gap. Tests cover:
  - Completion-trigger pattern detection (positive + negative + exempt phrases)
  - PR-ref extraction (PR #N / pull request N forms)
  - Commit-hash extraction (7-40 hex chars, with boundary)
  - verify_pr / verify_commit subprocess wrappers (mocked)
  - gate_check end-to-end (claim with/without PR/hash; verified vs fabricated)
  - R_VERIFY_SKIP env bypass

Mocks subprocess.run so tests run without gh/git binaries.
"""

from __future__ import annotations

import os
import subprocess
from unittest.mock import patch

import pytest

from src.bot_common import verify_gate

# ─────────────────────────────────────────────────────────────────────────────
# Completion-trigger pattern detection
# ─────────────────────────────────────────────────────────────────────────────


def test_trigger_matches_shipped() -> None:
    assert verify_gate.has_completion_trigger("PR shipped to main.")


def test_trigger_matches_merged() -> None:
    assert verify_gate.has_completion_trigger("PR merged to origin.")


def test_trigger_matches_state_merged_json() -> None:
    assert verify_gate.has_completion_trigger('state = "MERGED"')


def test_trigger_matches_merge_pr_phrase() -> None:
    assert verify_gate.has_completion_trigger("Did merge pr 123 today.")


def test_trigger_exempt_planning_language() -> None:
    """'planning to ship' should NOT trigger."""
    assert not verify_gate.has_completion_trigger("Planning to ship after CI.")


def test_trigger_exempt_negation() -> None:
    """'not shipped yet' should NOT trigger."""
    assert not verify_gate.has_completion_trigger("Not shipped yet — awaiting concur.")


def test_trigger_exempt_could_not_resolve() -> None:
    """Quoting an error message about 'could not resolve' should NOT trigger."""
    assert not verify_gate.has_completion_trigger(
        "gh: Could not resolve PR #99999. Failed verification."
    )


def test_trigger_exempt_meta_discussion() -> None:
    """'fabricated' / 'hallucinated' meta-discussion exempt."""
    assert not verify_gate.has_completion_trigger(
        "The agent fabricated a PR shipped claim earlier."
    )
    assert not verify_gate.has_completion_trigger(
        "Hallucinated commit hash detected in completion claim."
    )


def test_trigger_no_match_on_plain_text() -> None:
    assert not verify_gate.has_completion_trigger("Working on the feature.")


# ─────────────────────────────────────────────────────────────────────────────
# PR ref extraction
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_pr_refs_hash_form() -> None:
    assert verify_gate.extract_pr_refs("PR #715 merged") == [715]


def test_extract_pr_refs_pull_request_form() -> None:
    assert verify_gate.extract_pr_refs("pull request 716 closed") == [716]


def test_extract_pr_refs_multiple() -> None:
    out = verify_gate.extract_pr_refs("PR #715 and pull request 716 both merged")
    assert 715 in out and 716 in out


def test_extract_pr_refs_none() -> None:
    assert verify_gate.extract_pr_refs("No PR mentioned here.") == []


# ─────────────────────────────────────────────────────────────────────────────
# Commit hash extraction
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_commit_hashes_short() -> None:
    out = verify_gate.extract_commit_hashes("commit 6a3661b1 verified")
    assert "6a3661b1" in out


def test_extract_commit_hashes_long() -> None:
    out = verify_gate.extract_commit_hashes("commit 6a3661b100f2690e9e6b0ff7a4c9edb5c78c1d07")
    assert "6a3661b100f2690e9e6b0ff7a4c9edb5c78c1d07" in out


def test_extract_commit_hashes_only_matches_lowercase_hex() -> None:
    """`_HASH_RE` only matches lowercase hex per current verify_gate.py:53.

    Uppercase hex like 'ABC1234' is NOT matched. Real git commit hashes from
    `gh` / `git log` are always lowercase, so this is operationally correct.
    """
    assert verify_gate.extract_commit_hashes("Commit ABC1234 verified") == []
    # Lowercase form IS matched
    assert "abc1234" in verify_gate.extract_commit_hashes("commit abc1234 verified")


def test_extract_commit_hashes_none() -> None:
    assert verify_gate.extract_commit_hashes("Plain text no hex.") == []


# ─────────────────────────────────────────────────────────────────────────────
# verify_pr (subprocess wrapper for `gh pr view`)
# ─────────────────────────────────────────────────────────────────────────────


def test_verify_pr_exists_state_merged() -> None:
    fake = subprocess.CompletedProcess(
        args=["gh", "pr", "view", "715", "--json", "state"],
        returncode=0,
        stdout='{"state":"MERGED"}',
        stderr="",
    )
    with patch.object(subprocess, "run", return_value=fake):
        exists, state = verify_gate.verify_pr(715)
    assert exists is True
    assert state == "MERGED"


def test_verify_pr_does_not_exist() -> None:
    fake = subprocess.CompletedProcess(
        args=["gh", "pr", "view", "99999", "--json", "state"],
        returncode=1,
        stdout="",
        stderr="GraphQL: Could not resolve to a PullRequest.",
    )
    with patch.object(subprocess, "run", return_value=fake):
        exists, state = verify_gate.verify_pr(99999)
    assert exists is False
    assert state == ""


def test_verify_pr_gh_failure_conservative_pass() -> None:
    """gh failure for reasons other than 'could not resolve' → conservative pass."""
    fake = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="HTTP 500: upstream down"
    )
    with patch.object(subprocess, "run", return_value=fake):
        exists, state = verify_gate.verify_pr(715)
    assert exists is True  # Conservative — don't block on transient gh outage


def test_verify_pr_subprocess_timeout_conservative_pass() -> None:
    with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("gh", 10)):
        exists, state = verify_gate.verify_pr(715)
    assert exists is True


# ─────────────────────────────────────────────────────────────────────────────
# verify_commit (subprocess wrapper for `git cat-file -t`)
# ─────────────────────────────────────────────────────────────────────────────


def test_verify_commit_exists() -> None:
    fake = subprocess.CompletedProcess(
        args=["git", "cat-file", "-t", "6a3661b1"],
        returncode=0,
        stdout="commit\n",
        stderr="",
    )
    with patch.object(subprocess, "run", return_value=fake):
        assert verify_gate.verify_commit("6a3661b1") is True


def test_verify_commit_does_not_exist() -> None:
    fake = subprocess.CompletedProcess(
        args=["git", "cat-file", "-t", "deadbeef"],
        returncode=1,
        stdout="",
        stderr="fatal: Not a valid object name deadbeef",
    )
    with patch.object(subprocess, "run", return_value=fake):
        assert verify_gate.verify_commit("deadbeef") is False


def test_verify_commit_returns_non_commit_object() -> None:
    """git cat-file -t may return 'tree' / 'blob' for non-commit hashes — must return False."""
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="tree\n", stderr="")
    with patch.object(subprocess, "run", return_value=fake):
        assert verify_gate.verify_commit("abc1234") is False


def test_verify_commit_git_failure_conservative_pass() -> None:
    with patch.object(subprocess, "run", side_effect=FileNotFoundError("no git")):
        assert verify_gate.verify_commit("abc1234") is True


# ─────────────────────────────────────────────────────────────────────────────
# gate_check end-to-end
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_env_skip():
    prior = os.environ.pop("R_VERIFY_SKIP", None)
    yield
    if prior is not None:
        os.environ["R_VERIFY_SKIP"] = prior


def test_gate_check_no_trigger_passes() -> None:
    """Message without completion-trigger phrase → always (True, None)."""
    ok, reason = verify_gate.gate_check("Working on the feature. Standing by.")
    assert ok is True
    assert reason is None


def test_gate_check_trigger_no_refs_passes() -> None:
    """Trigger phrase but no PR# / commit refs → (True, None) — nothing to verify."""
    ok, reason = verify_gate.gate_check("Just shipped the doc edits.")
    assert ok is True
    assert reason is None


def test_gate_check_skip_env_passes() -> None:
    """R_VERIFY_SKIP=1 bypasses all checks."""
    os.environ["R_VERIFY_SKIP"] = "1"
    ok, reason = verify_gate.gate_check("PR #99999 shipped to main. commit deadbeefbeef merged.")
    assert ok is True
    assert reason is None


def test_gate_check_fabricated_pr_blocks() -> None:
    """Completion claim with fabricated PR # → (False, blocker)."""
    fake_gh = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="could not resolve"
    )
    with patch.object(subprocess, "run", return_value=fake_gh):
        ok, reason = verify_gate.gate_check("PR #99999 shipped to main.")
    assert ok is False
    assert "99999" in reason
    assert "does not exist" in reason


def test_gate_check_fabricated_commit_blocks() -> None:
    """Completion claim with fabricated commit hash → (False, blocker)."""

    def fake_run(cmd, **kwargs):
        if "git" in cmd[0]:
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stdout="", stderr="fatal: Not a valid object"
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch.object(subprocess, "run", side_effect=fake_run):
        ok, reason = verify_gate.gate_check(
            "Shipped commit beefdeadbeef beefdeadbeef beefdead. State=MERGED."
        )
    assert ok is False
    assert "beefdead" in reason


def test_gate_check_legitimate_pr_passes() -> None:
    """Completion claim with REAL PR # → (True, None)."""
    fake_gh = subprocess.CompletedProcess(
        args=[], returncode=0, stdout='{"state":"MERGED"}', stderr=""
    )
    with patch.object(subprocess, "run", return_value=fake_gh):
        ok, reason = verify_gate.gate_check("PR #715 shipped to main.")
    assert ok is True
    assert reason is None


def test_gate_check_skips_digit_only_hash() -> None:
    """Pure digit string (e.g. '12345678') should be skipped as a hash candidate."""
    fake_gh = subprocess.CompletedProcess(
        args=[], returncode=0, stdout='{"state":"MERGED"}', stderr=""
    )
    with patch.object(subprocess, "run", return_value=fake_gh):
        ok, reason = verify_gate.gate_check("PR #715 shipped. 12345678 is just a number.")
    assert ok is True


def test_gate_check_skips_slack_channel_id_lookalike() -> None:
    """Hash starting with 'c0b' looks like a Slack channel ID, not a commit."""
    fake_gh = subprocess.CompletedProcess(
        args=[], returncode=0, stdout='{"state":"MERGED"}', stderr=""
    )
    with patch.object(subprocess, "run", return_value=fake_gh):
        ok, reason = verify_gate.gate_check("PR #715 shipped to channel c0b2pm3tv0b.")
    assert ok is True
