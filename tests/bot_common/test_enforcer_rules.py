"""tests for src/bot_common/enforcer_rules.py — LLM prompt + constants module.

Locks the public constants (CHECK_MODEL, MAX_WINDOW, HIGH_SEVERITY_RULES,
TRIGGER_PATTERNS) and verifies should_check() pre-filter behavior. Also
sanity-checks RULES_PROMPT content for the LLM-only rules (R3 SOFT + R9).

Constants drift-detection: post Phase-5 round table (Track 4 / 5 / 6),
MAX_WINDOW = 50 and HIGH_SEVERITY_RULES = {3, 6}. Any future change should
update this test deliberately.
"""

from __future__ import annotations

from src.bot_common import enforcer_rules

# ─────────────────────────────────────────────────────────────────────────────
# Constants drift-detection
# ─────────────────────────────────────────────────────────────────────────────


def test_check_model_is_gpt4o_mini() -> None:
    """Locked to gpt-4o-mini for cost/latency. Change consciously."""
    assert enforcer_rules.CHECK_MODEL == "gpt-4o-mini"


def test_max_window_is_50() -> None:
    """Track 4 bumped 20→50. Drift would silently shrink R2 lookback."""
    assert enforcer_rules.MAX_WINDOW == 50


def test_flag_cooldown_is_300_seconds() -> None:
    """5 min cooldown between same-rule fires. Prevents flood."""
    assert enforcer_rules.FLAG_COOLDOWN_SECONDS == 300


def test_high_severity_rules_contains_r3_and_r6() -> None:
    """R3 + R6 route to both #alerts AND #execution per PR #672."""
    assert frozenset({3, 6}) == enforcer_rules.HIGH_SEVERITY_RULES


def test_trigger_patterns_is_tuple_and_lowercase() -> None:
    """TRIGGER_PATTERNS is an immutable tuple of lowercase strings."""
    assert isinstance(enforcer_rules.TRIGGER_PATTERNS, tuple)
    assert all(isinstance(p, str) for p in enforcer_rules.TRIGGER_PATTERNS)
    assert all(p == p.lower() for p in enforcer_rules.TRIGGER_PATTERNS), (
        "TRIGGER_PATTERNS must be lowercase for case-insensitive matching in should_check"
    )


def test_trigger_patterns_includes_core_completion_words() -> None:
    """Core completion-claim triggers MUST be present."""
    required = {"commit", "pushed", "pr #", "merged", "deployed", "complete", "done"}
    actual = set(enforcer_rules.TRIGGER_PATTERNS)
    missing = required - actual
    assert not missing, f"TRIGGER_PATTERNS missing required: {missing}"


def test_trigger_patterns_includes_save_claims() -> None:
    """Save-claim triggers MUST be present (R6 evidence chain)."""
    required = {"ceo_memory updated", "manual updated", "drive mirror", "daily_log written"}
    actual = set(enforcer_rules.TRIGGER_PATTERNS)
    missing = required - actual
    assert not missing, f"TRIGGER_PATTERNS missing save-claim triggers: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# should_check pre-filter
# ─────────────────────────────────────────────────────────────────────────────


def test_should_check_matches_commit() -> None:
    assert enforcer_rules.should_check("Just committed the fix.")


def test_should_check_matches_pr_hash() -> None:
    assert enforcer_rules.should_check("Looking at PR #715")


def test_should_check_case_insensitive() -> None:
    assert enforcer_rules.should_check("MERGED to MAIN")


def test_should_check_no_match_on_plain_text() -> None:
    assert not enforcer_rules.should_check("Hello team, standing by.")


def test_should_check_matches_save_claim() -> None:
    assert enforcer_rules.should_check("ceo_memory updated with new state")


# ─────────────────────────────────────────────────────────────────────────────
# RULES_PROMPT content sanity
# ─────────────────────────────────────────────────────────────────────────────


def test_rules_prompt_mentions_rule_3_soft() -> None:
    """LLM prompt MUST cover R3 SOFT fallback (the only LLM path for R3)."""
    assert "Rule 3" in enforcer_rules.RULES_PROMPT
    assert "SOFT" in enforcer_rules.RULES_PROMPT or "soft" in enforcer_rules.RULES_PROMPT


def test_rules_prompt_mentions_rule_9() -> None:
    """LLM prompt MUST cover R9 DIRECTIVE-INITIATIVE (LLM-only rule)."""
    assert "Rule 9" in enforcer_rules.RULES_PROMPT
    assert "DIRECTIVE-INITIATIVE" in enforcer_rules.RULES_PROMPT


def test_rules_prompt_specifies_json_response_format() -> None:
    """LLM must return JSON; prompt must instruct that explicitly."""
    p = enforcer_rules.RULES_PROMPT
    assert "JSON" in p
    assert '"violation"' in p
    assert '"rule_number"' in p


def test_rules_prompt_specifies_no_dave_check() -> None:
    """Dave's messages are exempt from enforcement."""
    assert "Dave" in enforcer_rules.RULES_PROMPT
    # Either explicit exempt OR exclusion mention
    assert "Do NOT flag Dave" in enforcer_rules.RULES_PROMPT or (
        "Dave's messages" in enforcer_rules.RULES_PROMPT
        and "exempt" in enforcer_rules.RULES_PROMPT.lower()
    )
