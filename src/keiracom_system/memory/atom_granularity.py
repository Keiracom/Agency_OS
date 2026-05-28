"""atom_granularity.py — programmatic validator for the atom-granularity spec.

Spec: `docs/architecture/atom_granularity_spec.md` (Wave 1 CUTOVER GATE,
Agency_OS-3g9t, Dave + Aiden + Viktor ratify 2026-05-27).

Four rules every atom must satisfy or `validate_atom(...)` returns
`ok=False` with the list of violated rule IDs:

  R1 — content size bounds (50–2000 chars by default)
  R2 — single-concept (max sentences + connector + heading heuristics)
  R3 — source-pointer present + non-trivial
  R4 — source-pointer field name is canonical (source_ref or provenance.source)

Two escape valves:
  - `single_concept_override: true` bypasses R2 only
  - `granularity_exempt: true` bypasses R1/R2/R3 (Aiden gate D approval; logged)

Canonical key citations (per audit-dispatch checklist `_orchestrator.md`):

ceo:cutover_plan_v1 — full_retrieval_tier_ratify_2026_05_27_22Z.waves.wave_1_foundation:
    "Hindsight primitives complete (synthesize+trace+delete with source-atom
     pointers) + atom granularity spec + tenant scoping per-callsite + ..."

ceo:memory_abstraction_layer_v1 — eleven_agreed_positions #3:
    "Six query primitives: Ingest, Recall, Synthesize, Supersede, Trace, Delete"
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


# Multi-concept connectors that strongly signal "this atom describes two
# different things". One is usually transitional and fine; two or more is
# a multi-concept smell. Period-terminated to anchor at sentence boundary.
DEFAULT_MULTI_CONCEPT_CONNECTORS: tuple[str, ...] = (
    ". Additionally",
    ". Furthermore",
    ". Separately",
    ". On a different topic",
    ". Unrelated to the above",
    ". In other news",
)


@dataclass(frozen=True)
class GranularityRules:
    """Policy object — V1 defaults are the ratified starting points.

    Production deploys override per-tenant once tenant-config plumbing is
    ready (Phase 2). Per-topology overrides similarly Phase 2.
    """

    min_content_chars: int = 50
    max_content_chars: int = 2000
    max_sentences: int = 5
    max_multi_concept_connectors: int = 1
    max_h2_h3_headings: int = 3
    min_source_ref_chars: int = 7
    accepted_source_ref_keys: frozenset[str] = frozenset({"source_ref", "provenance.source"})
    multi_concept_connectors: tuple[str, ...] = DEFAULT_MULTI_CONCEPT_CONNECTORS


@dataclass(frozen=True)
class GranularityViolation:
    rule_id: str
    detail: str


@dataclass(frozen=True)
class ValidationOutcome:
    ok: bool
    atom_id: str
    violations: list[GranularityViolation] = field(default_factory=list)
    exempt_reason: str = ""
    schema_version: str = "1.0"


def _extract_source_ref(atom: dict[str, Any], rules: GranularityRules) -> str:
    """Pull the source pointer from any accepted field name.

    Accepts `source_ref` (string) or `provenance.source` (nested dict.source).
    Other field names (`origin`, `from`, `cited_from`) are NOT accepted —
    canonical names only (R4).
    """
    for key in rules.accepted_source_ref_keys:
        if "." in key:
            head, tail = key.split(".", 1)
            nested = atom.get(head)
            if isinstance(nested, dict):
                v = nested.get(tail)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        else:
            v = atom.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _count_sentences(content: str) -> int:
    """Approximate sentence count via period/?/! terminators.

    Defensive: collapses repeated punctuation ("..." counted as one) so
    code/list content doesn't inflate the count.
    """
    # Treat any cluster of .?! as one terminator.
    normalised = re.sub(r"[.?!]+", ".", content)
    parts = [p for p in normalised.split(".") if p.strip()]
    return len(parts)


def _count_multi_concept_connectors(content: str, connectors: tuple[str, ...]) -> int:
    """Sum occurrences of the multi-concept connector strings."""
    return sum(content.count(c) for c in connectors)


def _count_h2_h3_headings(content: str) -> int:
    """Count lines starting with ## or ### (markdown H2 / H3)."""
    n = 0
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("###") or (
            stripped.startswith("##") and not stripped.startswith("###")
        ):
            n += 1
    return n


def validate_atom(
    atom: dict[str, Any], *, rules: GranularityRules | None = None
) -> ValidationOutcome:
    """Apply the granularity spec to one atom. Returns ValidationOutcome.

    Atom shape — only the relevant fields are inspected:
      - `id` (or `atom_id` / `memory_id`) — identifier for reporting
      - `content` — the atom payload (string)
      - `source_ref` OR `provenance.source` — source pointer (R3/R4)
      - `single_concept_override: bool` — R2 escape
      - `granularity_exempt: bool` — all-rules escape (gated)
    """
    if not isinstance(atom, dict):
        raise ValueError(f"atom must be dict, got {type(atom).__name__}")
    if rules is None:
        rules = GranularityRules()
    atom_id = str(atom.get("id") or atom.get("atom_id") or atom.get("memory_id") or "<no-id>")

    if atom.get("granularity_exempt") is True:
        log.warning(
            "atom %s granularity_exempt=true — bypassing all rules (Aiden gate D approval required)",
            atom_id,
        )
        return ValidationOutcome(ok=True, atom_id=atom_id, exempt_reason="granularity_exempt")

    content_raw = atom.get("content")
    if not isinstance(content_raw, str):
        return ValidationOutcome(
            ok=False,
            atom_id=atom_id,
            violations=[
                GranularityViolation(rule_id="R0", detail="content missing or not a string")
            ],
        )
    content = content_raw.strip()
    violations: list[GranularityViolation] = []

    # R1 — content size bounds
    n_chars = len(content)
    if n_chars < rules.min_content_chars:
        violations.append(
            GranularityViolation(
                rule_id="R1.min",
                detail=f"content has {n_chars} chars; min {rules.min_content_chars}",
            )
        )
    if n_chars > rules.max_content_chars:
        violations.append(
            GranularityViolation(
                rule_id="R1.max",
                detail=f"content has {n_chars} chars; max {rules.max_content_chars}",
            )
        )

    # R2 — single-concept heuristics (skipped if override set)
    if not atom.get("single_concept_override"):
        n_sentences = _count_sentences(content)
        if n_sentences > rules.max_sentences:
            violations.append(
                GranularityViolation(
                    rule_id="R2.a",
                    detail=f"content has {n_sentences} sentences; max {rules.max_sentences}",
                )
            )
        n_connectors = _count_multi_concept_connectors(content, rules.multi_concept_connectors)
        if n_connectors > rules.max_multi_concept_connectors:
            violations.append(
                GranularityViolation(
                    rule_id="R2.b",
                    detail=(
                        f"content has {n_connectors} multi-concept connectors; "
                        f"max {rules.max_multi_concept_connectors}"
                    ),
                )
            )
        n_headings = _count_h2_h3_headings(content)
        if n_headings > rules.max_h2_h3_headings:
            violations.append(
                GranularityViolation(
                    rule_id="R2.c",
                    detail=(
                        f"content has {n_headings} H2/H3 headings; "
                        f"max {rules.max_h2_h3_headings} (document-shaped, not atom-shaped)"
                    ),
                )
            )

    # R3 + R4 — source-pointer present, non-trivial, canonical name
    source_ref = _extract_source_ref(atom, rules)
    if not source_ref:
        # Distinguish "field missing entirely" (R4) from "field present but short" (R3).
        any_known_field_present = any(
            atom.get(k) for k in rules.accepted_source_ref_keys if "." not in k
        ) or (isinstance(atom.get("provenance"), dict) and atom["provenance"].get("source"))
        if not any_known_field_present:
            violations.append(
                GranularityViolation(
                    rule_id="R4",
                    detail=(
                        "no canonical source-pointer field present (accepted: "
                        f"{sorted(rules.accepted_source_ref_keys)})"
                    ),
                )
            )
        else:
            violations.append(
                GranularityViolation(
                    rule_id="R3",
                    detail=(
                        f"source-pointer present but shorter than "
                        f"{rules.min_source_ref_chars} chars"
                    ),
                )
            )
    elif len(source_ref) < rules.min_source_ref_chars:
        violations.append(
            GranularityViolation(
                rule_id="R3",
                detail=(
                    f"source-pointer {source_ref!r} is {len(source_ref)} chars; "
                    f"min {rules.min_source_ref_chars}"
                ),
            )
        )

    return ValidationOutcome(
        ok=not violations,
        atom_id=atom_id,
        violations=violations,
        exempt_reason="single_concept_override" if atom.get("single_concept_override") else "",
    )


def validate_atoms(
    atoms: list[dict[str, Any]], *, rules: GranularityRules | None = None
) -> list[ValidationOutcome]:
    """Convenience batch validator — applies validate_atom to each row."""
    if not isinstance(atoms, list):
        raise ValueError(f"atoms must be list, got {type(atoms).__name__}")
    return [validate_atom(a, rules=rules) for a in atoms]
