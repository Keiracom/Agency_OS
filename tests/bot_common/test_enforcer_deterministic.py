"""Comprehensive tests for src/bot_common/enforcer_deterministic.py.

Existing coverage was scattered across FP-tuning regression test files
(test_track4_*, test_track5_*, test_enforcer_r3_pytest_pattern) which
locked specific regex changes but didn't comprehensively exercise all
branches of all 5 check_r* functions. This file fills the gap with
branch-coverage-oriented tests.

Functions tested:
  check_r2 — STEP-0-BEFORE-EXECUTION (deterministic, recent_messages-aware)
  check_r3 — COMPLETION-REQUIRES-VERIFICATION (hybrid; STRICT/SOFT/no-trigger paths)
  check_r4 — NO-UNREVIEWED-MAIN-PUSH (deterministic violation + exempt)
  check_r6 — SAVE-CLAIM-REQUIRES-PROOF (hybrid)
  check_r8 — DISPATCH-COORDINATION (deterministic, recent_messages-aware)
"""

from __future__ import annotations

from src.bot_common.enforcer_deterministic import (
    check_r2,
    check_r3,
    check_r4,
    check_r6,
    check_r8,
)

# ─────────────────────────────────────────────────────────────────────────────
# check_r4 — NO-UNREVIEWED-MAIN-PUSH
# ─────────────────────────────────────────────────────────────────────────────


def test_r4_fires_on_git_push_origin_main() -> None:
    result = check_r4("Just ran git push origin main — fix is live.")
    assert result is not None
    assert result["rule_number"] == 4


def test_r4_fires_on_force_pushed_to_main() -> None:
    result = check_r4("force.pushed to main with the recovery commit")
    assert result is not None
    assert result["rule_number"] == 4


def test_r4_fires_on_bypassed_pr_review() -> None:
    result = check_r4("bypassed PR review for the urgent hotfix.")
    assert result is not None


def test_r4_fires_on_pushed_straight_to_main() -> None:
    result = check_r4("pushed straight to main — emergency override.")
    assert result is not None


def test_r4_exempt_pr_n_merged() -> None:
    """`PR #715 merged` is a legitimate PR-merge mention, not a direct push."""
    assert check_r4("PR #715 merged at 23:21 UTC.") is None


def test_r4_exempt_gh_pr_merge() -> None:
    assert check_r4("ran gh pr merge 715 --squash") is None


def test_r4_exempt_merge_pr() -> None:
    assert check_r4("did merge pr 715 cleanly") is None


def test_r4_exempt_pushed_to_feature_branch() -> None:
    """Pushing to a feature branch is fine."""
    assert check_r4("pushed to origin aiden/feature-x") is None


def test_r4_no_match_on_plain_status() -> None:
    assert check_r4("Working on the feature.") is None


# ─────────────────────────────────────────────────────────────────────────────
# check_r6 — SAVE-CLAIM-REQUIRES-PROOF (hybrid)
# ─────────────────────────────────────────────────────────────────────────────


def test_r6_no_save_claim_returns_none_no_skip() -> None:
    """No save trigger → (None, False) so caller falls through to LLM."""
    result, skip = check_r6("Working on the feature.")
    assert result is None
    assert skip is False


def test_r6_save_claim_with_commit_hash_passes() -> None:
    """Save claim + commit-hash evidence → (None, True) PASS."""
    text = "state saved — see commit 6a3661b1 for the MANUAL update."
    result, skip = check_r6(text)
    assert result is None
    assert skip is True


def test_r6_save_claim_with_sql_evidence_passes() -> None:
    """Save claim + SQL output evidence → PASS."""
    text = "ceo_memory updated — 1 rows affected by INSERT."
    result, skip = check_r6(text)
    assert result is None
    assert skip is True


def test_r6_save_claim_with_drive_byte_evidence_passes() -> None:
    """Save claim + byte count (Drive mirror) → PASS."""
    text = "manual updated — drive mirror success, 5234 bytes written."
    result, skip = check_r6(text)
    assert result is None
    assert skip is True


def test_r6_save_claim_no_evidence_violates() -> None:
    """Save claim + NO store-specific evidence → (violation, True)."""
    text = "Daily log written, state saved, manual updated. Done."
    result, skip = check_r6(text)
    assert result is not None
    assert result["rule_number"] == 6
    assert skip is True


# ─────────────────────────────────────────────────────────────────────────────
# check_r3 — COMPLETION-REQUIRES-VERIFICATION (hybrid)
# ─────────────────────────────────────────────────────────────────────────────


def test_r3_no_trigger_falls_through_to_llm() -> None:
    result, skip = check_r3("Working on the feature.")
    assert result is None
    assert skip is False


def test_r3_strict_complete_with_commit_hash_passes() -> None:
    """STRICT 'complete' + commit-hash evidence → PASS, skip LLM."""
    text = "Task complete — commit 6a3661b1 on origin/main."
    result, skip = check_r3(text)
    assert result is None
    assert skip is True


def test_r3_strict_complete_without_evidence_violates() -> None:
    """STRICT 'complete' + no evidence → (violation, True)."""
    text = "Task complete. Standing by."
    result, skip = check_r3(text)
    assert result is not None
    assert result["rule_number"] == 3
    assert skip is True


def test_r3_soft_done_with_evidence_passes() -> None:
    """SOFT 'done' + evidence → PASS, skip LLM."""
    text = "Done with the build, all 33 tests passed in 0.5s."
    result, skip = check_r3(text)
    assert result is None
    assert skip is True


def test_r3_soft_done_without_evidence_falls_to_llm() -> None:
    """SOFT 'done' + no evidence → (None, False) — caller falls to LLM."""
    text = "Done."
    result, skip = check_r3(text)
    assert result is None
    assert skip is False


def test_r3_exception_synthetic_test_passes() -> None:
    """`synthetic test` exemption → (None, True)."""
    text = "Build complete — synthetic test scenario, no real deploy."
    result, skip = check_r3(text)
    assert result is None
    assert skip is True


def test_r3_exception_governance_gatekeeper_passes() -> None:
    text = "[GOVERNANCE] Gatekeeper announcement — build complete."
    result, skip = check_r3(text)
    assert result is None
    assert skip is True


def test_r3_adjective_complete_not_strict() -> None:
    """Track 7: 'coverage chain complete' is adjective, not completion claim."""
    result, skip = check_r3("coverage chain complete — bot_common fully unit-tested")
    assert result is None
    assert skip is False


def test_r3_adjective_is_complete_not_strict() -> None:
    """Track 7: 'X is complete' adjective form falls through to LLM."""
    result, skip = check_r3("bot_common coverage chain is complete")
    assert result is None
    assert skip is False


def test_r3_deployment_complete_without_evidence_violates() -> None:
    """Track 7: compound 'deployment complete' still triggers STRICT."""
    result, skip = check_r3("Deployment complete. All services green.")
    assert result is not None
    assert result["rule_number"] == 3
    assert skip is True


def test_r3_migration_complete_with_evidence_passes() -> None:
    """Track 7: compound 'migration complete' + commit hash → PASS."""
    result, skip = check_r3("Migration complete — commit abc1234 applied.")
    assert result is None
    assert skip is True


# ─────────────────────────────────────────────────────────────────────────────
# check_r2 — STEP-0-BEFORE-EXECUTION
# ─────────────────────────────────────────────────────────────────────────────


def test_r2_no_execution_language_passes() -> None:
    assert check_r2("Standing by.", recent_messages=[]) is None


def test_r2_execution_with_step_0_in_text_passes() -> None:
    """Step 0 in current message → exempt."""
    text = "Step 0 RESTATE — Objective: shipping the feature. Now committing."
    assert check_r2(text, recent_messages=[]) is None


def test_r2_execution_with_step_0_in_recent_passes() -> None:
    """Step 0 in recent_messages window → exempt."""
    recent = ["Step 0 RESTATE — Objective: build the feature."]
    text = "Now committing the changes."
    assert check_r2(text, recent_messages=recent) is None


def test_r2_execution_without_step_0_violates() -> None:
    """Execution language + no Step 0 anywhere → violation."""
    text = "Now committing the changes."
    result = check_r2(text, recent_messages=["unrelated chatter", "more chatter"])
    assert result is not None
    assert result["rule_number"] == 2


def test_r2_exempt_planning_language() -> None:
    """`will commit` / `going to push` — planning, not execution."""
    assert check_r2("Will commit after CI passes.", recent_messages=[]) is None
    assert check_r2("Going to push the fix shortly.", recent_messages=[]) is None


def test_r2_exempt_negation() -> None:
    assert check_r2("Haven't committed yet — awaiting concur.", recent_messages=[]) is None


def test_r2_exempt_propose_tag() -> None:
    """[PROPOSE:...] tag exempts the trigger."""
    text = "[propose:aiden] committing the feature now."
    assert check_r2(text, recent_messages=[]) is None


def test_r2_recent_messages_none_conservative_pass() -> None:
    """recent_messages=None → conservative pass (caller doesn't have context)."""
    text = "Committing now."
    assert check_r2(text, recent_messages=None) is None


def test_r2_exempt_fully_deployed_status() -> None:
    """Track 8: 'FULLY DEPLOYED' is status reporting, not new execution."""
    assert check_r2("Track 7 FULLY DEPLOYED. Listener restarted at 01:24 UTC.", recent_messages=[]) is None


def test_r2_exempt_pr_tally() -> None:
    """Track 8: '19 PRs merged' is a tally, not new merge execution."""
    assert check_r2("Session total: 19 PRs merged (#722-741).", recent_messages=[]) is None
    assert check_r2("19 PRs merged this session.", recent_messages=[]) is None


def test_r2_exempt_deployed_at_timestamp() -> None:
    """Track 8: 'deployed at <digit>' is past-tense status."""
    assert check_r2("Deployed at 01:12:05 UTC. R9 LAYER 2 active.", recent_messages=[]) is None


def test_r2_exempt_shipped_in_pr() -> None:
    """Track 8: 'shipped in PR' is past-tense reference."""
    assert check_r2("Shipped in PR #740 to main.", recent_messages=[]) is None


def test_r2_exempt_merge_pull_request() -> None:
    """Track 8: GitHub merge commit message format."""
    assert check_r2("Merge pull request #741 from Keiracom/max/r9-standby-exempt", recent_messages=[]) is None


# ─────────────────────────────────────────────────────────────────────────────
# check_r8 — DISPATCH-COORDINATION
# ─────────────────────────────────────────────────────────────────────────────


def test_r8_no_dispatch_passes() -> None:
    assert check_r8("Working on the feature.", recent_messages=[]) is None


def test_r8_dispatched_with_proposal_and_concur_passes() -> None:
    """Dispatch action + proposal + concur in recent_messages → PASS."""
    recent = [
        "[DISPATCH-PROPOSAL:AIDEN] sending Orion the rebase task",
        "[CONCUR:elliot] approved",
    ]
    text = "Atlas dispatched per Dave directive #8."
    assert check_r8(text, recent_messages=recent) is None


def test_r8_dispatched_without_proposal_violates() -> None:
    """Dispatch action + no proposal in recent → violation.

    Uses bare 'dispatched' without Track 5 exempt phrases (no `Dave directive`,
    no own-clone elliot→atlas / aiden→orion pattern).
    """
    recent = ["[CONCUR:elliot] approved"]  # has concur but no proposal
    text = "Orchestrator dispatched the cleanup task."
    result = check_r8(text, recent_messages=recent)
    assert result is not None
    assert result["rule_number"] == 8


def test_r8_dispatched_without_concur_violates() -> None:
    """Dispatch action + proposal but no concur → violation."""
    recent = ["[DISPATCH-PROPOSAL:AIDEN] sending the rebase task"]
    text = "Orchestrator dispatched the cleanup task."
    result = check_r8(text, recent_messages=recent)
    assert result is not None
    assert result["rule_number"] == 8


def test_r8_conditional_language_exempt() -> None:
    """`I can dispatch` is an offer, not an action — Track 5 exempt."""
    assert check_r8("I can dispatch Orion if you confirm.", recent_messages=[]) is None


def test_r8_recent_messages_none_conservative_pass() -> None:
    """recent_messages=None → conservative pass."""
    text = "Atlas dispatched per Dave directive."
    assert check_r8(text, recent_messages=None) is None
