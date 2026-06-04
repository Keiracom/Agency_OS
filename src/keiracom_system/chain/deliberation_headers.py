"""deliberation_headers.py — structured deliberation-output contract + parser.

gate_roadmap component `persona_bank_reasoning_headers`. The v1-chain reviewer
personas (personas/v1_chain/{nova,orion,atlas}.md) must emit a structured
deliberation block so the Reasoning Listener (reasoning_capture) can persist the
WHY at every hop without LLM-side parsing guesswork. This module is the
deterministic contract: the five required headers + a parser/validator that the
listener (and the proof) use to extract them.

The block a persona emits:

    DELIBERATION:
    DECISION: <the verdict / chosen path, one line>
    CHALLENGE: <the flaw or risk raised>
    TRADEOFFS: <what was weighed against what>
    REJECTED: <the alternative(s) dismissed and why>
    ATTRIBUTION: <persona callsign + the evidence reference relied on>

Parsing is deterministic — no LLM. A block missing or emptying any required
header is REJECTED (that is the negative bar the proof exercises).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Order is the canonical emission order; all five are required.
REQUIRED_HEADERS: tuple[str, ...] = (
    "DECISION",
    "CHALLENGE",
    "TRADEOFFS",
    "REJECTED",
    "ATTRIBUTION",
)

# A header line: start-of-line, the exact header token, a colon. The value is
# everything after the colon up to (but not including) the next header line.
_HEADER_RE = re.compile(
    r"^(?P<header>" + "|".join(REQUIRED_HEADERS) + r")[ \t]*:[ \t]*(?P<value>.*)$",
    re.MULTILINE,
)


class DeliberationFormatError(ValueError):
    """Raised when a deliberation block is missing or empties a required header."""


@dataclass(frozen=True)
class DeliberationHeaders:
    decision: str
    challenge: str
    tradeoffs: str
    rejected: str
    attribution: str

    def as_dict(self) -> dict[str, str]:
        return {
            "DECISION": self.decision,
            "CHALLENGE": self.challenge,
            "TRADEOFFS": self.tradeoffs,
            "REJECTED": self.rejected,
            "ATTRIBUTION": self.attribution,
        }


def parse(text: str) -> dict[str, str]:
    """Extract recognized headers → values from a deliberation block.

    Multi-line values are supported: a header's value runs from its colon to the
    next recognized header (or end of text). Only the LAST occurrence of a header
    wins (a persona that restates a header overrides the earlier one). Values are
    stripped. Headers absent from `text` are simply absent from the result —
    `validate()` is what enforces completeness.
    """
    matches = list(_HEADER_RE.finditer(text))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end("value")
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        # The first line's value is m.group('value'); append any continuation up
        # to the next header.
        value = (m.group("value") + text[start:end]).strip()
        out[m.group("header")] = value
    return out


def validate(text: str) -> DeliberationHeaders:
    """Parse + assert every required header is present and non-empty.

    Returns a `DeliberationHeaders`. Raises `DeliberationFormatError` naming the
    first offending header (missing or empty) — the deterministic reject path.
    """
    parsed = parse(text)
    missing = [h for h in REQUIRED_HEADERS if h not in parsed]
    if missing:
        raise DeliberationFormatError(
            f"deliberation block missing required header(s): {', '.join(missing)}"
        )
    empty = [h for h in REQUIRED_HEADERS if not parsed[h].strip()]
    if empty:
        raise DeliberationFormatError(
            f"deliberation block has empty required header(s): {', '.join(empty)}"
        )
    return DeliberationHeaders(
        decision=parsed["DECISION"],
        challenge=parsed["CHALLENGE"],
        tradeoffs=parsed["TRADEOFFS"],
        rejected=parsed["REJECTED"],
        attribution=parsed["ATTRIBUTION"],
    )


def is_valid(text: str) -> bool:
    """True iff `text` contains a complete deliberation block. No raise."""
    try:
        validate(text)
    except DeliberationFormatError:
        return False
    return True


__all__ = [
    "REQUIRED_HEADERS",
    "DeliberationFormatError",
    "DeliberationHeaders",
    "is_valid",
    "parse",
    "validate",
]
