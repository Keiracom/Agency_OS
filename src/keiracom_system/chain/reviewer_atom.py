"""ReviewerAtom — structured verdict schema for V1 chain reviewer output.

Coordination point with Atlas's verdict_enforcement wiring in advance_step.
Reviewers (orion, atlas) currently emit free-text atoms whose first line starts
with one of REJECT / CONCUR / HOLD / APPROVE. advance_step needs a reliable
way to extract that verdict from any reviewer atom by atom_id.

This module provides:
  - ReviewerAtom dataclass (frozen): verdict + rationale + atom_id (+ raw atom).
  - Verdict literal: APPROVE | HOLD | REJECT (the three Atlas's enforcement
    layer needs to discriminate on).
  - parse_reviewer_verdict(atom_id, *, fetcher=None) -> ReviewerAtom.
    Returns verdict='HOLD' (safe default) when the atom can't be fetched, the
    atom is empty, or no recognisable verdict token is found in its content.

Vocabulary alignment with personas (personas/v1_chain/{orion,atlas}.md):
  - Personas today emit REJECT and CONCUR.
  - This schema normalises CONCUR -> APPROVE so advance_step has a single
    enum to switch on. HOLD is added per dispatch (covers the unknown /
    fetch-failure / safe-default case).

Safe-default principle: a missing or malformed verdict NEVER advances the
chain. parse_reviewer_verdict returns HOLD, which Atlas's enforcement reads
as "do not progress; surface for human review or retry".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Literal
from uuid import UUID

log = logging.getLogger(__name__)

Verdict = Literal["APPROVE", "HOLD", "REJECT"]

_VALID_VERDICTS: tuple[str, ...] = ("APPROVE", "HOLD", "REJECT")
# CONCUR is the persona-emitted token; normalise to APPROVE for advance_step.
_VERDICT_ALIASES: dict[str, Verdict] = {"CONCUR": "APPROVE"}
# Maximum characters of leading content to scan for the verdict token —
# bounds the parse cost and prevents pathological inputs from blocking.
_LEADING_SCAN_CHARS = 64

# Fetcher signature: (atom_id_str) -> atom (AtomV1, dict-like, or None).
# Kept loose so tests can pass a plain dict and production wires AtomStore.
FetcherFn = Callable[[str], Any]


@dataclass(frozen=True)
class ReviewerAtom:
    """Parsed verdict envelope for an atom emitted by a reviewer agent.

    `verdict` is the only field advance_step needs to switch on; `rationale`
    is the human-readable reason (the atom's content body, minus the leading
    verdict token); `atom_id` echoes the input for trace correlation; `raw`
    preserves the underlying atom payload (None when fetch failed).
    """

    verdict: Verdict
    rationale: str = ""
    atom_id: str = ""
    raw: Any = field(default=None)


def _normalize_verdict(token: str) -> Verdict | None:
    """Return canonical Verdict for token, or None if not recognised."""
    t = token.strip().upper()
    if t in _VALID_VERDICTS:
        return t  # type: ignore[return-value]
    if t in _VERDICT_ALIASES:
        return _VERDICT_ALIASES[t]
    return None


def _extract_from_text(content: str) -> tuple[Verdict | None, str]:
    """Find the leading verdict token in `content` (case-insensitive).

    A leading token is one of APPROVE/HOLD/REJECT/CONCUR at position 0 of the
    stripped first line, followed by ':' or whitespace. Returns (verdict,
    rationale) where rationale is the tail after the token+separator. Returns
    (None, content) when no leading token matches.
    """
    if not content:
        return None, ""
    head = content.lstrip()[:_LEADING_SCAN_CHARS]
    first_line = head.split("\n", 1)[0]
    upper = first_line.upper()
    for token in (*_VALID_VERDICTS, *_VERDICT_ALIASES.keys()):
        if upper.startswith(token + ":") or upper.startswith(token + " ") or upper == token:
            verdict = _normalize_verdict(token)
            # Strip token + one separator char to recover the rationale.
            sep_len = len(token) + (1 if len(first_line) > len(token) else 0)
            rationale = first_line[sep_len:].strip()
            return verdict, rationale
    return None, content.strip()


def _atom_field(atom: Any, name: str) -> Any:
    """Read field `name` from an atom that may be a dataclass, dict, or None."""
    if atom is None:
        return None
    if isinstance(atom, dict):
        return atom.get(name)
    return getattr(atom, name, None)


def _default_fetcher(atom_id: str) -> Any:
    """Default fetcher — loads AtomStore lazily so the import surface stays
    light for tests/CI that don't have a DB. Returns None on ANY failure
    (invalid UUID, missing config, DB unreachable, atom not present)."""
    try:
        from uuid import UUID as _UUID  # noqa: PLC0415

        from src.keiracom_system.atomization.atom_store import AtomStore  # noqa: PLC0415

        return AtomStore().get_atom(_UUID(atom_id))
    except Exception as exc:  # noqa: BLE001 — fetch must never raise
        log.debug("reviewer_atom: default fetch failed for %s: %s", atom_id, exc)
        return None


def parse_reviewer_verdict(
    atom_id: str,
    *,
    fetcher: FetcherFn | None = None,
) -> ReviewerAtom:
    """Fetch the atom for `atom_id` and extract its verdict.

    Resolution order:
      1. atom['verdict'] / atom.verdict (canonical structured field if a future
         reviewer atom carries it explicitly).
      2. Leading token of atom['content'] / atom.content (current persona shape).
      3. HOLD safe default (fetch failed, no recognisable token).

    `fetcher` is dependency injection — pass a callable for tests; production
    uses AtomStore.get_atom. Never raises; downstream advance_step is
    guaranteed a ReviewerAtom.
    """
    fetch = fetcher or _default_fetcher
    try:
        atom = fetch(atom_id)
    except Exception as exc:  # noqa: BLE001 — fetcher contract: never escalate
        log.warning("reviewer_atom: fetcher raised for %s: %s", atom_id, exc)
        atom = None

    if atom is None:
        return ReviewerAtom(
            verdict="HOLD",
            rationale="atom not found or fetch failed",
            atom_id=atom_id,
            raw=None,
        )

    # 1. Explicit verdict field wins.
    explicit = _atom_field(atom, "verdict")
    if isinstance(explicit, str):
        verdict = _normalize_verdict(explicit)
        if verdict is not None:
            rationale = _atom_field(atom, "rationale") or _atom_field(atom, "content") or ""
            return ReviewerAtom(
                verdict=verdict,
                rationale=str(rationale).strip(),
                atom_id=atom_id,
                raw=atom,
            )

    # 2. Leading token of content.
    content = _atom_field(atom, "content")
    if isinstance(content, str):
        verdict, rationale = _extract_from_text(content)
        if verdict is not None:
            return ReviewerAtom(
                verdict=verdict,
                rationale=rationale,
                atom_id=atom_id,
                raw=atom,
            )

    # 3. Safe default.
    return ReviewerAtom(
        verdict="HOLD",
        rationale="no verdict field or leading token found",
        atom_id=atom_id,
        raw=atom,
    )
