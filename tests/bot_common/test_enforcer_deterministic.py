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
    assert (
        check_r2("Track 7 FULLY DEPLOYED. Listener restarted at 01:24 UTC.", recent_messages=[])
        is None
    )


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
    assert (
        check_r2("Merge pull request #741 from Keiracom/max/r9-standby-exempt", recent_messages=[])
        is None
    )


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


# ---------------------------------------------------------------------------
# R10 — LINEAR-KEI-GATE (Wave 2 Outcome 3)
# ---------------------------------------------------------------------------


def test_r10_no_completion_phrase_returns_none():
    from src.bot_common.enforcer_deterministic import check_r10

    assert check_r10("just chatting about KEI-17 design") is None


def test_r10_pr_merged_without_kei_tag_fires():
    from src.bot_common.enforcer_deterministic import check_r10

    out = check_r10("PR #774 merged at sha abc1234")
    assert out is not None
    assert out["rule_number"] == 10
    assert "without KEI-<N> tag" in out["detail"]


def test_r10_pr_merged_with_kei_tag_no_check_fn_passes():
    from src.bot_common.enforcer_deterministic import check_r10

    # KEI tag present; no Linear-check fn injected → conservative pass.
    out = check_r10("PR #774 merged (KEI-17) at sha abc1234")
    assert out is None


def test_r10_ready_marker_with_kei_tag_and_recent_linear_update_passes():
    from src.bot_common.enforcer_deterministic import check_r10

    # Inject a Linear-check fn that says "yes, KEI-17 was updated".
    fresh = lambda kei, window: True  # noqa: E731
    out = check_r10("[READY:aiden] KEI-17 polling loop shipped", linear_kei_recently_updated=fresh)
    assert out is None


def test_r10_ready_marker_with_stale_kei_fires():
    from src.bot_common.enforcer_deterministic import check_r10

    stale = lambda kei, window: False  # noqa: E731
    out = check_r10(
        "[READY:aiden] KEI-17 polling loop shipped",
        linear_kei_recently_updated=stale,
    )
    assert out is not None
    assert out["rule_number"] == 10
    assert "KEI-17" in out["detail"]
    assert "no Linear status update" in out["detail"]


def test_r10_multiple_keis_mixed_fresh_and_stale_fires_only_on_stale():
    from src.bot_common.enforcer_deterministic import check_r10

    # KEI-17 fresh, KEI-18 stale.
    def probe(kei, window):
        return kei == "KEI-17"

    out = check_r10(
        "Wave 2 KEI-17 + KEI-18 outcomes complete — PR #774 merged",
        linear_kei_recently_updated=probe,
    )
    assert out is not None
    assert "KEI-18" in out["detail"]
    assert "KEI-17" not in out["detail"]  # the fresh one is omitted


def test_r10_exempt_future_intent_passes():
    from src.bot_common.enforcer_deterministic import check_r10

    # Future intent should NOT fire even with completion-shaped phrase.
    assert check_r10("planning to merge PR #774 once CI greens") is None
    assert check_r10("will deploy after smoke verifies") is None


def test_r10_exempt_negation_passes():
    from src.bot_common.enforcer_deterministic import check_r10

    assert check_r10("we haven't merged PR #774 yet — Max is reviewing") is None


def test_r10_exempt_retro_recap_passes():
    from src.bot_common.enforcer_deterministic import check_r10

    # Recap-style mention of past completion should not fire.
    assert check_r10("retro of yesterday: PR #774 merged on time") is None


def test_r10_completion_probe_failure_does_not_fire():
    from src.bot_common.enforcer_deterministic import check_r10

    # If the Linear-check fn raises, that single KEI is skipped (conservative).
    def probe(kei, window):
        raise RuntimeError("Linear API down")

    out = check_r10(
        "[READY:aiden] KEI-17 polling loop shipped",
        linear_kei_recently_updated=probe,
    )
    assert out is None  # no stale_keis collected → conservative pass


def test_r10_four_store_save_complete_phrase_fires_when_no_kei():
    from src.bot_common.enforcer_deterministic import check_r10

    out = check_r10("four-store save complete for Wave 1 cleanup")
    assert out is not None
    assert "without KEI-<N> tag" in out["detail"]


def test_r10_directive_done_phrase_fires_when_no_kei():
    from src.bot_common.enforcer_deterministic import check_r10

    out = check_r10("Wave 2 Outcome 3 complete — enforcer rule shipped")
    assert out is not None
    assert "without KEI-<N> tag" in out["detail"]


# ---------------------------------------------------------------------------
# R11 — CEO-FORMAT-GATE (Wave 2 Dave directive)
# ---------------------------------------------------------------------------

CEO_CH = "C0B2PM3TV0B"
EXEC_CH = "C0B3QB0K1GQ"


def test_r11_non_ceo_channel_always_passes():
    from src.bot_common.enforcer_deterministic import check_r11

    # Even a clearly bad-format message passes if channel isn't #ceo.
    bad = "Random prose dump merged PR #774 with commit abc1234 in scripts/foo.py"
    assert check_r11(bad, channel=EXEC_CH) is None
    assert check_r11(bad, channel=None) is None


def test_r11_ceo_well_formatted_passes():
    from src.bot_common.enforcer_deterministic import check_r11

    good = """**Outcome**
- Phase 0 verified end-to-end on local stack
- Smoke test passed both assertions

**Next**
- Phase 1 ingest unblocked"""
    assert check_r11(good, channel=CEO_CH) is None


def test_r11_ceo_missing_bold_header_fires():
    from src.bot_common.enforcer_deterministic import check_r11

    no_header = """- bullet one is fine on its own
- bullet two also
- but no header"""
    out = check_r11(no_header, channel=CEO_CH)
    assert out is not None
    assert out["rule_number"] == 11
    assert "no bold category header" in out["detail"]


def test_r11_ceo_prose_paragraph_fires():
    from src.bot_common.enforcer_deterministic import check_r11

    prose = (
        "**Header**\n"
        "This is one long sentence about something. "
        "And this is a second sentence in the same line that makes it prose. "
        "Plus a third for safety to ensure the heuristic trips on 2+ sentences in 150+ chars."
    )
    out = check_r11(prose, channel=CEO_CH)
    assert out is not None
    assert "prose paragraph" in out["detail"]


def test_r11_ceo_pr_number_banned():
    from src.bot_common.enforcer_deterministic import check_r11

    with_pr = """**Header**
- something happened
- merged PR #774 today"""
    out = check_r11(with_pr, channel=CEO_CH)
    assert out is not None
    assert "PR #774" in out["detail"] or "banned technical tokens" in out["detail"]


def test_r11_ceo_commit_sha_banned():
    from src.bot_common.enforcer_deterministic import check_r11

    with_sha = """**Header**
- something happened
- at sha abc1234def56"""
    out = check_r11(with_sha, channel=CEO_CH)
    assert out is not None
    assert "banned technical tokens" in out["detail"]


def test_r11_ceo_file_path_banned():
    from src.bot_common.enforcer_deterministic import check_r11

    with_path = """**Header**
- changed src/cognee/client.py and scripts/foo.sh
- result was good"""
    out = check_r11(with_path, channel=CEO_CH)
    assert out is not None
    assert "banned technical tokens" in out["detail"]


def test_r11_ceo_env_var_name_banned():
    from src.bot_common.enforcer_deterministic import check_r11

    with_env = """**Header**
- set GEMINI_API_KEY
- and DB_PROVIDER too"""
    out = check_r11(with_env, channel=CEO_CH)
    assert out is not None
    assert "banned technical tokens" in out["detail"]


def test_r11_ceo_code_fence_banned():
    from src.bot_common.enforcer_deterministic import check_r11

    with_fence = """**Header**
- something
```
code block here
```"""
    out = check_r11(with_fence, channel=CEO_CH)
    assert out is not None
    assert "banned technical tokens" in out["detail"]


def test_r11_concur_request_replacement_exempt():
    """System-generated CONCUR-REQUEST messages from concur_gate pass through —
    they're not agent-authored prose, they're a wrapper artifact."""
    from src.bot_common.enforcer_deterministic import check_r11

    concur = "[AIDEN] [CONCUR-REQUEST:AIDEN] requesting concurrence from peer on: ..."
    # Even though it doesn't have a bold header, exempt path returns None.
    assert check_r11(concur, channel=CEO_CH) is None


def test_r11_multiple_violations_stacked_in_detail():
    from src.bot_common.enforcer_deterministic import check_r11

    bad = "merged PR #774 in scripts/foo.py"  # no header, PR, path
    out = check_r11(bad, channel=CEO_CH)
    assert out is not None
    detail = out["detail"]
    assert "no bold category header" in detail
    assert "banned technical tokens" in detail


def test_r11_single_long_bullet_not_prose():
    """A SINGLE bulleted long line shouldn't trip prose-paragraph heuristic
    (the rule targets un-bulleted multi-sentence runs)."""
    from src.bot_common.enforcer_deterministic import check_r11

    long_bullet = (
        "**Header**\n"
        "- this is a very long bullet that has a couple of sentences in it. "
        "It's still a bullet though so the prose heuristic should not fire on it."
    )
    out = check_r11(long_bullet, channel=CEO_CH)
    # Either passes entirely or only flags non-prose issues.
    if out is not None:
        assert "prose paragraph" not in out["detail"]


# ---------------------------------------------------------------------------
# R13 — DECISION-MIRROR-TO-CEO
# ---------------------------------------------------------------------------

EXECUTION_CH = "C0B3QB0K1GQ"
CEO_CH_R13 = "C0B2PM3TV0B"


def test_r13_propose_with_inline_mirror_token_passes():
    """Case 1: PROPOSE in #execution WITH inline mirror token → pass (no fire)."""
    from src.bot_common.enforcer_deterministic import check_r13

    msg = (
        "[PROPOSE:elliot] Take ownership of the rate-limit detection P1. "
        "Mirrored to #ceo for Dave visibility."
    )
    assert check_r13(msg, channel=EXECUTION_CH) is None


def test_r13_propose_without_mirror_token_fires():
    """Case 2: PROPOSE in #execution WITHOUT mirror token → fail (fires to #ceo)."""
    from src.bot_common.enforcer_deterministic import check_r13

    msg = (
        "[PROPOSE:elliot] Need Dave decision on whether to proceed with the "
        "destructive migration before the post-restart bundle ships."
    )
    out = check_r13(msg, channel=EXECUTION_CH)
    assert out is not None
    assert out["rule_number"] == 13
    assert out["rule_name"] == "DECISION-MIRROR-TO-CEO"
    assert "not escalated" in out["detail"]
    assert out["fire_message"] == "Blocker in #execution not escalated — [paste message]"


def test_r13_propose_in_ceo_is_noop():
    """Case 3: PROPOSE in #ceo itself → no-op (rule only enforces #execution leak)."""
    from src.bot_common.enforcer_deterministic import check_r13

    msg = "[PROPOSE:elliot] Dave decision on the post-restart bundle ordering."
    assert check_r13(msg, channel=CEO_CH_R13) is None


def test_r13_non_propose_message_in_execution_is_noop():
    """Case 4: non-PROPOSE message in #execution → no-op (rule only triggers on
    decision-needed signals)."""
    from src.bot_common.enforcer_deterministic import check_r13

    msg = "Shipped PR #821 — CI green, awaiting peer FINAL on the diff."
    assert check_r13(msg, channel=EXECUTION_CH) is None


def test_r13_each_decision_trigger_phrase_fires_without_mirror():
    """Spot-check every documented decision-needed trigger phrase fires when
    no mirror token is present in #execution. Pins the regex shape against
    accidental edits."""
    from src.bot_common.enforcer_deterministic import check_r13

    phrases = [
        "[PROPOSE:elliot] some decision",
        "This is a Dave decision",
        "CEO call required here",
        "Standing for Dave reply",
        "Blocker requires Dave verbatim",
        "Blocker requires CEO ratification",
    ]
    for p in phrases:
        out = check_r13(p, channel=EXECUTION_CH)
        assert out is not None, f"phrase did not fire R13: {p!r}"
        assert out["rule_number"] == 13


def test_r13_each_mirror_token_suppresses_fire():
    """Spot-check every documented mirror-token form suppresses fire on a
    decision-needed #execution post."""
    from src.bot_common.enforcer_deterministic import check_r13

    base = "[PROPOSE:elliot] something needs Dave decision."
    tokens = [
        "Mirrored to #ceo",
        "Posting to #ceo now",
        "[CEO-MIRROR: ts 1778628999]",
        "#ceo mirror in flight",
        "per R13",
    ]
    for t in tokens:
        msg = f"{base} {t}"
        out = check_r13(msg, channel=EXECUTION_CH)
        assert out is None, f"token did not suppress R13: {t!r}"


def test_r13_no_channel_defaults_to_pass():
    """When channel is unknown / None, R13 must not fire — same convention as R11."""
    from src.bot_common.enforcer_deterministic import check_r13

    msg = "[PROPOSE:elliot] Dave decision needed."
    assert check_r13(msg, channel=None) is None
