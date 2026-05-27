"""Decision sources — Phase Alpha atomization (Agency_OS-decisions-atomization).

Iterators over the 4 sources of ratified decision-class content per dispatch:
  (a) ceo_memory canonical keys with directive_NNNNN_complete pattern
  (b) docs/governance/CONSOLIDATED_RULES.md ratified decisions
  (c) docs/architecture/keiracom_architecture_v2_inventory.md ratified items
  (d) docs/MANUAL.md Section 13 directive entries

Each iterator yields `DecisionSource(source_ref, source_kind, source_text)`.
The atomizer takes it from there with the decision-class prompt + schema
(see decisions_atomizer.py).

Anchor: Cutover Readiness Gate STATE_SEPARATION.knowledge_atomized_pgvector.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

log = logging.getLogger(__name__)

# Source-kind constants for keiracom_atomizer_jobs.source_kind enum.
SOURCE_KIND_DIRECTIVE: str = "governance_doc"  # mirrors atom_schema_v1 enum
SOURCE_KIND_RULE: str = "governance_doc"
SOURCE_KIND_INVENTORY: str = "governance_doc"
SOURCE_KIND_MANUAL: str = "manual"

# Default Hindsight bank for decision atoms.
DEFAULT_DECISIONS_BANK: str = "fleet_decisions"

# Regex patterns used by source iterators.
_DIRECTIVE_KEY_PATTERN = re.compile(r"^ceo:directive_(\d+)_complete$")
_V2_INVENTORY_RATIFIED_ROW_RE = re.compile(
    r"^\|\s*([a-z0-9._-]+)\s*\|.*\|\s*RATIFIED-(?:CEO|DM)\s*\|.*\|.*\|.*\|\s*$",
    re.IGNORECASE,
)
_MANUAL_SECTION_13_HEADING_RE = re.compile(r"^###?\s+Directive\s+#(\d+)\b", re.IGNORECASE)
_CONSOLIDATED_RULES_RULE_HEADING_RE = re.compile(r"^##\s+RULE\s+(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True, kw_only=True)
class DecisionSource:
    """One ratified decision item — atomizer's input.

    `source_ref` is the canonical identifier (e.g. `ceo_memory:ceo:directive_10028_complete`).
    `source_kind` matches the atom_schema_v1 source_kind enum.
    `source_text` is the raw content the atomizer prompts on.
    """

    source_ref: str
    source_kind: str
    source_text: str


class _DBProtocol(Protocol):
    """Subset of a DB cursor — for ceo_memory iterator."""

    def execute(self, query: str, *params: Any) -> Any: ...
    def fetchall(self) -> Any: ...


# ───────────────────────────────────────────────────────────────────────
# (a) ceo_memory directives — iterate ceo:directive_NNNNN_complete keys
# ───────────────────────────────────────────────────────────────────────


def iter_ceo_memory_directives(db: _DBProtocol) -> Iterable[DecisionSource]:
    """Yield one DecisionSource per ceo:directive_NNNNN_complete key.

    The directive value is JSON — we hand the JSON-as-string to the atomizer
    which will extract the human-readable fields (title, ratify timestamp,
    deliberation_record, etc.) into atom content via Gemini's structured-
    output pass.
    """
    db.execute(
        "SELECT key, value::text FROM public.ceo_memory "
        "WHERE key LIKE 'ceo:directive_%_complete' "
        "ORDER BY key"
    )
    rows = db.fetchall() or []
    for row in rows:
        key, value = row[0], row[1]
        m = _DIRECTIVE_KEY_PATTERN.match(str(key))
        if not m:
            continue
        directive_id = m.group(1)
        yield DecisionSource(
            source_ref=f"ceo_memory:{key}",
            source_kind="governance_doc",
            source_text=(f"DIRECTIVE #{directive_id} — completion marker JSON:\n{value}"),
        )


# ───────────────────────────────────────────────────────────────────────
# (b) CONSOLIDATED_RULES.md — iterate ## RULE N blocks
# ───────────────────────────────────────────────────────────────────────


def iter_consolidated_rules(path: Path) -> Iterable[DecisionSource]:
    """Yield one DecisionSource per `## RULE N — <title>` block.

    Each block is the text from one rule heading down to the next rule
    heading (or EOF). Skips frontmatter and any content before the first
    `## RULE` heading.
    """
    if not path.is_file():
        log.warning("consolidated_rules: %s not present — skipping", path)
        return
    text = path.read_text(encoding="utf-8")
    blocks = _split_by_heading_regex(text, _CONSOLIDATED_RULES_RULE_HEADING_RE)
    for block_id, block_text in blocks:
        yield DecisionSource(
            source_ref=f"docs/governance/CONSOLIDATED_RULES.md#rule-{block_id}",
            source_kind="governance_doc",
            source_text=block_text,
        )


# ───────────────────────────────────────────────────────────────────────
# (c) V2 inventory — iterate RATIFIED-CEO / RATIFIED-DM table rows
# ───────────────────────────────────────────────────────────────────────


def iter_v2_inventory_ratified(path: Path) -> Iterable[DecisionSource]:
    """Yield one DecisionSource per row marked RATIFIED-CEO or RATIFIED-DM.

    The row format is the canonical inventory row shape (markdown pipe table).
    Yields the FULL row text + its element_id as the source_ref suffix.
    """
    if not path.is_file():
        log.warning("v2_inventory: %s not present — skipping", path)
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _V2_INVENTORY_RATIFIED_ROW_RE.match(line)
        if not m:
            continue
        element_id = m.group(1)
        yield DecisionSource(
            source_ref=f"docs/architecture/keiracom_architecture_v2_inventory.md#{element_id}",
            source_kind="governance_doc",
            source_text=f"V2 inventory ratified row:\n{line}",
        )


# ───────────────────────────────────────────────────────────────────────
# (d) MANUAL.md Section 13 — iterate Directive #NNNNN entries
# ───────────────────────────────────────────────────────────────────────


def iter_manual_section_13(path: Path) -> Iterable[DecisionSource]:
    """Yield one DecisionSource per `### Directive #NNNNN` heading block.

    Block = heading + body until the next `### Directive` heading or the
    section closes. MANUAL.md Section 13 is the durable Drive-mirrored
    record of every Dave directive ratification.
    """
    if not path.is_file():
        log.warning("manual_section_13: %s not present — skipping", path)
        return
    text = path.read_text(encoding="utf-8")
    blocks = _split_by_heading_regex(text, _MANUAL_SECTION_13_HEADING_RE)
    for directive_id, block_text in blocks:
        yield DecisionSource(
            source_ref=f"docs/MANUAL.md#directive-{directive_id}",
            source_kind="manual",
            source_text=block_text,
        )


# ───────────────────────────────────────────────────────────────────────
# Aggregator + helpers
# ───────────────────────────────────────────────────────────────────────


def iter_all_decision_sources(
    *,
    db: _DBProtocol | None = None,
    repo_root: Path = Path("."),
) -> Iterable[DecisionSource]:
    """Convenience iterator — walks all 4 sources in canonical order.

    `db` may be None — the ceo_memory iterator is then skipped (e.g. for
    docs-only smoke runs).
    """
    if db is not None:
        yield from iter_ceo_memory_directives(db)
    yield from iter_consolidated_rules(repo_root / "docs" / "governance" / "CONSOLIDATED_RULES.md")
    yield from iter_v2_inventory_ratified(
        repo_root / "docs" / "architecture" / "keiracom_architecture_v2_inventory.md"
    )
    yield from iter_manual_section_13(repo_root / "docs" / "MANUAL.md")


def _split_by_heading_regex(text: str, heading_re: re.Pattern[str]) -> Iterable[tuple[str, str]]:
    """Split markdown text into (heading_id, block_text) tuples on a heading regex.

    Block starts at a matching heading line; ends at the next matching
    heading OR EOF. The heading_id is the regex group(1) of the heading match.
    Lines BEFORE the first match are skipped (frontmatter / intro prose).
    """
    lines = text.splitlines(keepends=True)
    blocks: list[tuple[str, list[str]]] = []
    current_id: str | None = None
    current_lines: list[str] = []
    for line in lines:
        m = heading_re.match(line)
        if m is not None:
            # Close the previous block if any.
            if current_id is not None:
                blocks.append((current_id, current_lines))
            current_id = m.group(1)
            current_lines = [line]
        elif current_id is not None:
            current_lines.append(line)
    if current_id is not None:
        blocks.append((current_id, current_lines))
    for hid, hlines in blocks:
        yield hid, "".join(hlines)


def decision_composition_tags(directive_kind: str = "ratified_decision") -> dict[str, str]:
    """Recommended composition_tags for decision atoms.

    Tagging convention (per atomization vocabulary frozen at pilot scope):
    decisions atoms map to domain=internal + concern=compliance +
    applicable_context=audit_review. Caller can override via the atomizer
    prompt but the default keeps decision atoms retrievable as a class.
    """
    # Note: this maps to VALID_COMPOSITION_TAG_* frozensets in schema.py.
    return {
        "domain": "internal",
        "concern": "compliance",
        "applicable_context": "audit_review",
    }


def serialize_decision_source(source: DecisionSource) -> dict[str, Any]:
    """Render a DecisionSource as a JSON-serializable dict — useful for
    audit logs + dispatcher hand-off."""
    return {
        "source_ref": source.source_ref,
        "source_kind": source.source_kind,
        "source_text_preview": source.source_text[:400],
        "source_text_length": len(source.source_text),
    }


def parse_directive_json(source_text: str) -> dict[str, Any] | None:
    """If `source_text` carries a directive_NNNNN_complete JSON body, parse
    it. Returns None if the body isn't valid JSON (the atomizer still gets
    the raw text as input)."""
    # Strip the "DIRECTIVE #NNNNN — completion marker JSON:\n" prefix.
    body = source_text.split("\n", 1)[-1] if source_text.startswith("DIRECTIVE") else source_text
    body = body.strip()
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None
