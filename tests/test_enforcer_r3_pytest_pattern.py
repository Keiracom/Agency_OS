"""Regression tests for R3 evidence regex — pytest output pattern (PR #708 follow-up).

Per Elliot non-blocking note on PR #707: `_R3_EVIDENCE_RE` missed pytest
output ("4 passed in 0.69s" form) because the prior `\\d+/\\d+\\s+(?:pass|fail)`
pattern only covered the ratio form ("4/4 pass"). This module asserts the
new `\\d+\\s+(?:passed|failed|error|errors)\\b` token catches the pytest form.
"""

from __future__ import annotations

from src.bot_common.enforcer_deterministic import check_r3


def test_pytest_passed_form_satisfies_strict_claim() -> None:
    """Completion claim + verbatim 'N passed in Xs' pytest output → PASS."""
    text = "Build complete. tests/test_x.py — 4 passed in 0.69s"
    result, skip_llm = check_r3(text)
    assert result is None
    assert skip_llm is True


def test_pytest_failed_form_satisfies_strict_claim() -> None:
    """Completion claim + 'N failed' pytest output → PASS."""
    text = "Task complete. tests/test_y.py — 2 failed in 1.20s"
    result, skip_llm = check_r3(text)
    assert result is None
    assert skip_llm is True


def test_pytest_errors_form_satisfies_strict_claim() -> None:
    """Completion claim + '3 errors' form → PASS."""
    text = "All stores written. 5 passed, 3 errors in 2.10s"
    result, skip_llm = check_r3(text)
    assert result is None
    assert skip_llm is True


def test_strict_claim_without_any_evidence_still_violates() -> None:
    """Sanity: regression test the regex addition didn't broaden too much.

    A bare completion claim with no evidence should STILL fire R3.
    """
    text = "Task complete. Ship it."
    result, skip_llm = check_r3(text)
    assert result is not None
    assert result["rule_number"] == 3
    assert skip_llm is True
