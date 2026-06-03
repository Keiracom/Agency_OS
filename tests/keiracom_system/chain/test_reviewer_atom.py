"""Tests for src/keiracom_system/chain/reviewer_atom.py — ReviewerAtom schema.

Coverage:
  - parse_reviewer_verdict resolves APPROVE / HOLD / REJECT from explicit
    `verdict` field on the atom (highest priority).
  - parse_reviewer_verdict resolves verdict from the leading token of
    atom.content (persona shape — REJECT:/CONCUR: prefix lines).
  - CONCUR token normalises to APPROVE.
  - Missing verdict + non-recognisable content -> HOLD safe default.
  - Atom not found (fetcher returns None) -> HOLD.
  - Fetcher raising an exception -> HOLD (never escalates).
  - Works against both dict-shaped atoms and dataclass-like objects.
  - Case-insensitive token detection.
  - Both ':' and ' ' separators after the verdict token.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from src.keiracom_system.chain.reviewer_atom import (
    ReviewerAtom,
    parse_reviewer_verdict,
)


def _fetcher(atom: Any):
    """Tiny fixture-builder: returns a fetcher that always yields `atom`."""

    def f(_atom_id: str) -> Any:
        return atom

    return f


# ─── Explicit verdict field ───────────────────────────────────────────────


@pytest.mark.parametrize("verdict_in", ["APPROVE", "HOLD", "REJECT"])
def test_explicit_verdict_field_dict(verdict_in: str) -> None:
    atom = {"verdict": verdict_in, "rationale": f"because {verdict_in.lower()}"}
    result = parse_reviewer_verdict("atom-1", fetcher=_fetcher(atom))
    assert result.verdict == verdict_in
    assert result.rationale == f"because {verdict_in.lower()}"
    assert result.atom_id == "atom-1"
    assert result.raw is atom


def test_explicit_verdict_field_concur_aliases_to_approve() -> None:
    atom = {"verdict": "CONCUR", "rationale": "spec satisfied"}
    result = parse_reviewer_verdict("a", fetcher=_fetcher(atom))
    assert result.verdict == "APPROVE"
    assert result.rationale == "spec satisfied"


def test_explicit_verdict_case_insensitive() -> None:
    atom = {"verdict": "reject", "content": "ignored"}
    result = parse_reviewer_verdict("a", fetcher=_fetcher(atom))
    assert result.verdict == "REJECT"


def test_explicit_verdict_falls_back_to_content_when_value_invalid() -> None:
    # invalid 'verdict' string + valid leading token in content => use content.
    atom = {"verdict": "??", "content": "APPROVE: looks good"}
    result = parse_reviewer_verdict("a", fetcher=_fetcher(atom))
    assert result.verdict == "APPROVE"
    assert result.rationale == "looks good"


# ─── Leading-token extraction from content ────────────────────────────────


@pytest.mark.parametrize(
    "leading,expected_verdict",
    [
        ("REJECT: No artifact produced.", "REJECT"),
        ("CONCUR: spec criteria all satisfied", "APPROVE"),
        ("APPROVE: green-light from atlas", "APPROVE"),
        ("HOLD: pending Dave decision", "HOLD"),
        ("reject: lowercase too", "REJECT"),
        ("APPROVE artifact reachable + spec met", "APPROVE"),  # space sep, not colon
    ],
)
def test_leading_token_from_content(leading: str, expected_verdict: str) -> None:
    atom = {"content": leading + "\nMore context on the next lines."}
    result = parse_reviewer_verdict("a", fetcher=_fetcher(atom))
    assert result.verdict == expected_verdict
    # rationale is the tail of the FIRST line only
    assert "\n" not in result.rationale


def test_leading_token_dataclass_shape() -> None:
    @dataclass
    class FakeAtom:
        content: str
        verdict: str | None = None

    atom = FakeAtom(content="REJECT: missing migration", verdict=None)
    result = parse_reviewer_verdict("a", fetcher=_fetcher(atom))
    assert result.verdict == "REJECT"
    assert result.rationale == "missing migration"


# ─── Safe-default HOLD ────────────────────────────────────────────────────


def test_atom_not_found_defaults_hold() -> None:
    result = parse_reviewer_verdict("missing-id", fetcher=_fetcher(None))
    assert result.verdict == "HOLD"
    assert "fetch failed" in result.rationale or "not found" in result.rationale
    assert result.raw is None


def test_fetcher_raises_defaults_hold() -> None:
    def boom(_atom_id: str) -> Any:
        raise RuntimeError("DB down")

    result = parse_reviewer_verdict("a", fetcher=boom)
    assert result.verdict == "HOLD"


def test_empty_content_defaults_hold() -> None:
    atom = {"content": ""}
    result = parse_reviewer_verdict("a", fetcher=_fetcher(atom))
    assert result.verdict == "HOLD"


def test_content_without_leading_token_defaults_hold() -> None:
    atom = {"content": "The implementation looks broadly fine to me but I cannot say for sure."}
    result = parse_reviewer_verdict("a", fetcher=_fetcher(atom))
    assert result.verdict == "HOLD"


def test_content_with_verdict_token_mid_sentence_defaults_hold() -> None:
    # 'REJECT' appears mid-text — only LEADING token counts.
    atom = {"content": "After consideration we'd REJECT this if it were ours."}
    result = parse_reviewer_verdict("a", fetcher=_fetcher(atom))
    assert result.verdict == "HOLD"


def test_atom_with_no_content_no_verdict_defaults_hold() -> None:
    atom = {"unrelated_field": "foo"}
    result = parse_reviewer_verdict("a", fetcher=_fetcher(atom))
    assert result.verdict == "HOLD"


# ─── Returned object contract ─────────────────────────────────────────────


def test_reviewer_atom_is_frozen() -> None:
    r = parse_reviewer_verdict("a", fetcher=_fetcher({"verdict": "APPROVE"}))
    with pytest.raises(Exception):  # FrozenInstanceError subclass of Exception
        r.verdict = "REJECT"  # type: ignore[misc]


def test_returns_reviewer_atom_dataclass() -> None:
    r = parse_reviewer_verdict("a", fetcher=_fetcher({"verdict": "HOLD"}))
    assert isinstance(r, ReviewerAtom)
