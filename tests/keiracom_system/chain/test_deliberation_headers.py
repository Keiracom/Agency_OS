"""Unit tests for the deliberation-headers contract/parser (orion).

gate_roadmap persona_bank_reasoning_headers. Deterministic — no LLM.
"""

from __future__ import annotations

import pytest

from src.keiracom_system.chain.deliberation_headers import (
    REQUIRED_HEADERS,
    DeliberationFormatError,
    is_valid,
    parse,
    validate,
)

WELL_FORMED = """\
[REVIEW:concur:orion]
DELIBERATION:
DECISION: concur — both KEI acceptance criteria verified at PR #1401.
CHALLENGE: none — dead-letter write and backoff both asserted in the test file.
TRADEOFFS: strict criterion reading vs intent — read each criterion literally against the test.
REJECTED: rejecting on missing integration test — the unit assertions already cover both criteria.
ATTRIBUTION: orion (spec/compliance lens) — PR #1401, tests/pipeline/test_enrichment_retry.py.
"""


def test_parse_extracts_all_five():
    parsed = parse(WELL_FORMED)
    assert set(parsed) == set(REQUIRED_HEADERS)
    assert parsed["DECISION"].startswith("concur")
    assert "test file" in parsed["CHALLENGE"]


def test_validate_returns_headers_on_complete_block():
    h = validate(WELL_FORMED)
    assert h.decision.startswith("concur")
    assert h.attribution.startswith("orion")
    assert h.as_dict()["TRADEOFFS"]


def test_is_valid_true_on_complete():
    assert is_valid(WELL_FORMED) is True


@pytest.mark.parametrize("drop", REQUIRED_HEADERS)
def test_validate_raises_on_each_missing_header(drop):
    block = "\n".join(line for line in WELL_FORMED.splitlines() if not line.startswith(f"{drop}:"))
    assert is_valid(block) is False
    with pytest.raises(DeliberationFormatError, match=drop):
        validate(block)


def test_validate_raises_on_empty_header():
    block = WELL_FORMED.replace(
        "REJECTED: rejecting on missing integration test — the unit assertions already cover both criteria.",
        "REJECTED:",
    )
    with pytest.raises(DeliberationFormatError, match="REJECTED"):
        validate(block)


def test_multiline_value_captured_until_next_header():
    block = """\
DECISION: reject
the artifact is not reachable
CHALLENGE: PR not found at the cited URL
TRADEOFFS: none
REJECTED: proceeding on good faith
ATTRIBUTION: orion — cited PR #9999
"""
    h = validate(block)
    assert "not reachable" in h.decision  # continuation line folded into DECISION
    assert h.challenge == "PR not found at the cited URL"


def test_last_occurrence_wins():
    block = """\
DECISION: first
DECISION: concur — final
CHALLENGE: x
TRADEOFFS: x
REJECTED: x
ATTRIBUTION: orion — ref
"""
    assert validate(block).decision == "concur — final"


def test_empty_text_is_invalid():
    assert is_valid("") is False
