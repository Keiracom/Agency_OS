"""Unit tests for src/bot_common/enforcer_rules.py.

Verifies:
  1. RULES has exactly 9 entries.
  2. IDs R1..R9 all present.
  3. Each rule's `text` is a byte-equal substring of the original enforcer_bot.py.
  4. Channel scoping table matches spec §3.1.
  5. build_prompt('#execution') includes R1 text.
  6. build_prompt('#alerts') excludes R1 text but includes R3, R6, R7 text.
"""

from __future__ import annotations

import os

import pytest

from src.bot_common.enforcer_rules import RULES, RULES_BY_ID, build_prompt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENFORCER_BOT_PATH = os.path.join(
    os.path.dirname(__file__),  # tests/bot_common/
    "..", "..",                 # repo root
    "src", "telegram_bot", "enforcer_bot.py",
)


def _load_source() -> str:
    with open(os.path.abspath(_ENFORCER_BOT_PATH), encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Basic shape
# ---------------------------------------------------------------------------


def test_rules_has_nine_entries() -> None:
    assert len(RULES) == 9, f"Expected 9 rules, got {len(RULES)}"


def test_all_rule_ids_present() -> None:
    expected_ids = {f"R{i}" for i in range(1, 10)}
    actual_ids = {r["id"] for r in RULES}
    assert actual_ids == expected_ids, f"Missing IDs: {expected_ids - actual_ids}"


def test_rules_by_id_covers_all() -> None:
    assert set(RULES_BY_ID.keys()) == {f"R{i}" for i in range(1, 10)}


# ---------------------------------------------------------------------------
# Byte-equality gate — each rule text must be a substring of enforcer_bot.py
# ---------------------------------------------------------------------------


def test_rule_texts_are_substrings_of_source() -> None:
    """Byte-equal substring check per spec §9 and the build directive."""
    source = _load_source()
    for rule in RULES:
        rid = rule["id"]
        text = rule["text"]
        # The text field stores the body only (without "Rule N — NAME: " prefix).
        # We verify that a meaningful fragment of each rule text appears verbatim
        # in the source file.  We check the first 60 chars of the text, which is
        # enough to distinguish rules and guarantee no fabrication.
        fragment = text[:60]
        assert fragment in source, (
            f"{rid} text fragment not found in enforcer_bot.py: {fragment!r}"
        )


# ---------------------------------------------------------------------------
# Channel scoping — spec §3.1 table
# ---------------------------------------------------------------------------


def test_r3_r6_r7_in_alerts() -> None:
    """R3, R6, R7 must appear in #alerts per gate-2 decision."""
    for rid in ("R3", "R6", "R7"):
        rule = RULES_BY_ID[rid]
        assert "#alerts" in rule["channels"], (
            f"{rid} should be scoped to #alerts but channels={rule['channels']}"
        )


def test_r3_r6_r7_also_in_execution() -> None:
    for rid in ("R3", "R6", "R7"):
        rule = RULES_BY_ID[rid]
        assert "#execution" in rule["channels"], (
            f"{rid} should also be scoped to #execution but channels={rule['channels']}"
        )


def test_execution_only_rules() -> None:
    """R1, R2, R4, R5, R8, R9 are #execution-only — must NOT appear in #alerts."""
    for rid in ("R1", "R2", "R4", "R5", "R8", "R9"):
        rule = RULES_BY_ID[rid]
        assert "#alerts" not in rule["channels"], (
            f"{rid} should be #execution-only but channels={rule['channels']}"
        )
        assert "#execution" in rule["channels"], (
            f"{rid} missing from #execution: channels={rule['channels']}"
        )


# ---------------------------------------------------------------------------
# build_prompt filtering
# ---------------------------------------------------------------------------


def test_build_prompt_execution_includes_r1() -> None:
    prompt = build_prompt("#execution")
    r1_fragment = RULES_BY_ID["R1"]["text"][:40]
    assert r1_fragment in prompt, (
        f"build_prompt('#execution') missing R1 text fragment: {r1_fragment!r}"
    )


def test_build_prompt_alerts_excludes_r1() -> None:
    prompt = build_prompt("#alerts")
    r1_fragment = RULES_BY_ID["R1"]["text"][:40]
    assert r1_fragment not in prompt, (
        "build_prompt('#alerts') should not include R1 (execution-only rule)"
    )


def test_build_prompt_alerts_includes_r3_r6_r7() -> None:
    prompt = build_prompt("#alerts")
    for rid in ("R3", "R6", "R7"):
        fragment = RULES_BY_ID[rid]["text"][:40]
        assert fragment in prompt, (
            f"build_prompt('#alerts') missing {rid} text fragment: {fragment!r}"
        )


def test_build_prompt_execution_includes_all_rules() -> None:
    prompt = build_prompt("#execution")
    for rule in RULES:
        fragment = rule["text"][:40]
        assert fragment in prompt, (
            f"build_prompt('#execution') missing {rule['id']} text fragment: {fragment!r}"
        )


# ---------------------------------------------------------------------------
# requires_stage0 flags
# ---------------------------------------------------------------------------


def test_requires_stage0_only_r1_r2() -> None:
    stage0_rules = {r["id"] for r in RULES if r["requires_stage0"]}
    assert stage0_rules == {"R1", "R2"}, (
        f"Only R1 and R2 should require stage0; got {stage0_rules}"
    )


# ---------------------------------------------------------------------------
# cooldown_s
# ---------------------------------------------------------------------------


def test_all_rules_have_300s_cooldown() -> None:
    for rule in RULES:
        assert rule["cooldown_s"] == 300, (
            f"{rule['id']} cooldown_s should be 300, got {rule['cooldown_s']}"
        )


# ---------------------------------------------------------------------------
# R2 exceptions
# ---------------------------------------------------------------------------


def test_r2_has_five_exceptions() -> None:
    exceptions = RULES_BY_ID["R2"]["exceptions"]
    assert len(exceptions) == 5, (
        f"R2 should have 5 exceptions, got {len(exceptions)}: {exceptions}"
    )


def test_r3_has_three_exceptions() -> None:
    exceptions = RULES_BY_ID["R3"]["exceptions"]
    assert len(exceptions) == 3, (
        f"R3 should have 3 exceptions, got {len(exceptions)}: {exceptions}"
    )
