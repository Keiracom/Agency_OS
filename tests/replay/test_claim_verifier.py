"""tests for src/replay/claim_verifier.py — Drevon PR-A.5 replay-on-claim.

Mocks `sb_get` so tests run without Supabase network access. Covers:
  - Extraction of PR# / commit-hash refs from message text
  - Evidence found in turn_logs → verified=True
  - No evidence → verified=False
  - No refs → conservatively verified=True
  - Partial coverage → verified=True (conservative)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.replay import claim_verifier


@pytest.fixture
def mock_sb_get():
    """Replace sb_get with a programmable stub. Each test sets returns dict
    mapping (table, pattern_substring) → list of fake rows."""

    rows_by_pattern: dict[str, list[dict]] = {}

    def fake_get(table: str, params: dict) -> list[dict]:
        ilike_val = params.get("tool_args_json", "")
        for needle, rows in rows_by_pattern.items():
            if needle in ilike_val:
                return rows
        return []

    with patch.object(claim_verifier, "sb_get", side_effect=fake_get):
        yield rows_by_pattern


# ─────────────────────────────────────────────────────────────────────────────
# Extraction helpers (private but worth locking)
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_pr_numbers_pr_hash_form() -> None:
    assert claim_verifier._extract_pr_numbers("PR #715 merged at 23:21") == [715]


def test_extract_pr_numbers_pull_request_form() -> None:
    assert claim_verifier._extract_pr_numbers("pull request 716 cleared CI") == [716]


def test_extract_pr_numbers_multiple() -> None:
    text = "PRs #715 and #716 both merged"
    assert claim_verifier._extract_pr_numbers(text) == [715, 716]


def test_extract_commit_hashes() -> None:
    out = claim_verifier._extract_commit_hashes("commit 286b4f0d99 verified")
    assert "286b4f0d99" in out


def test_extract_no_refs() -> None:
    assert claim_verifier._extract_pr_numbers("Nothing to verify here.") == []
    assert claim_verifier._extract_commit_hashes("All good.") == []


# ─────────────────────────────────────────────────────────────────────────────
# verify_completion_claim — happy paths
# ─────────────────────────────────────────────────────────────────────────────


def test_no_refs_returns_verified(mock_sb_get) -> None:
    verified, reason = claim_verifier.verify_completion_claim("Standing by, nothing claimed.")
    assert verified is True
    assert "no PR#/commit refs" in reason


def test_pr_evidence_found_via_verify_pr_sh(mock_sb_get) -> None:
    mock_sb_get["verify_pr.sh"] = [
        {
            "id": "log-1",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_args_json": {"command": "bash scripts/verify_pr.sh 715"},
        }
    ]
    verified, reason = claim_verifier.verify_completion_claim("PR #715 merged at 23:21")
    assert verified is True
    assert "verify_pr.sh" in reason
    assert "715" in reason


def test_pr_evidence_found_via_gh_pr_view(mock_sb_get) -> None:
    mock_sb_get["gh pr view"] = [
        {
            "id": "log-2",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_args_json": {"command": "gh pr view 716 --json state,mergeCommit"},
        }
    ]
    verified, reason = claim_verifier.verify_completion_claim("PR #716 verified")
    assert verified is True
    assert "gh pr view" in reason


def test_commit_evidence_found_via_git_cat_file(mock_sb_get) -> None:
    mock_sb_get["git cat-file"] = [
        {
            "id": "log-3",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_args_json": {"command": "git cat-file -t 286b4f0d"},
        }
    ]
    verified, reason = claim_verifier.verify_completion_claim("commit 286b4f0d verified")
    assert verified is True
    assert "git cat-file" in reason


# ─────────────────────────────────────────────────────────────────────────────
# verify_completion_claim — fabrication path (no evidence)
# ─────────────────────────────────────────────────────────────────────────────


def test_pr_no_evidence_returns_unverified(mock_sb_get) -> None:
    # No rows in mock = no evidence anywhere
    verified, reason = claim_verifier.verify_completion_claim("PR #99999 shipped")
    assert verified is False
    assert "99999" in reason


def test_commit_no_evidence_returns_unverified(mock_sb_get) -> None:
    verified, reason = claim_verifier.verify_completion_claim("commit beefdeadbeef merged")
    assert verified is False
    assert "beefdeadbeef" in reason


def test_partial_coverage_conservatively_verifies(mock_sb_get) -> None:
    """One claim has evidence, another doesn't → return True (conservative)."""
    mock_sb_get["gh pr view"] = [
        {
            "id": "log-4",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_args_json": {"command": "gh pr view 715 --json state"},
        }
    ]
    verified, reason = claim_verifier.verify_completion_claim("PRs #715 and #99999 merged")
    assert verified is True
    assert "partial evidence" in reason


# ─────────────────────────────────────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────────────────────────────────────


def test_short_hash_skipped(mock_sb_get) -> None:
    """Hash < 7 chars is not a commit ref — should not be queried."""
    verified, reason = claim_verifier.verify_completion_claim("Status abc.")
    # No refs (3-char hex below threshold) → verified True
    assert verified is True


def test_slack_channel_id_prefix_skipped(mock_sb_get) -> None:
    """Slack channel ID 'c0b...' looks like hex but isn't a commit."""
    text = "Posted to channel c0b2pm3tv0b — ceo channel."
    verified, reason = claim_verifier.verify_completion_claim(text)
    # The 'c0b...' hash is skipped, and no PR refs → no refs → verified True
    assert verified is True


def test_sb_get_failure_returns_no_evidence(mock_sb_get) -> None:
    """If sb_get raises, claim_verifier swallows and reports no evidence."""

    def raise_fn(*args, **kwargs):
        raise RuntimeError("supabase down")

    with patch.object(claim_verifier, "sb_get", side_effect=raise_fn):
        verified, reason = claim_verifier.verify_completion_claim("PR #715 merged")
    assert verified is False
    assert "715" in reason
