"""AtomV1 dataclass + frozen vocabularies — atomization pilot Week 1.

CANONICAL ANCHOR — ceo:atomization_architecture_v1 v1 (RATIFIED-CEO 2026-05-26T11:25:00Z):
  atom_schema_v1.fields = [
    "trigger_condition", "content", "anti_pattern", "example",
    "provenance (source/freshness/confidence/last_validated)",
    "supersession_edges",
    "composition_tags (domain/concern/applicable_context)"
  ]

VOCABULARY PLACEHOLDERS — the dispatch references "288 combinations + 7
relationship types" as Elliot's 48-hour design report deliverable. As of
2026-05-26 11:39Z the report was not yet in the Drive Manual (queried; zero
matches). Vocabularies below are PILOT-PLACEHOLDER values that match the
dispatch shape (single-digit relationship-type count + domain×concern×context
factors). REPLACE with Elliot's authored vocabulary when the report lands.

The vocabulary lookup is a single-file swap — atom storage uses JSONB so a
vocabulary swap doesn't require migration data movement, only an updated
frozenset + a re-validation pass on existing rows (Week 2 if needed).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

# atom_schema_v1 lives at schema_version = 1 in the migration.
SCHEMA_VERSION: int = 1

# State enum — mirrors the SQL CHECK in keiracom_atoms.state.
VALID_STATES: frozenset[str] = frozenset({"active", "superseded", "cold_archive"})

# Source kind enum — mirrors the SQL CHECK in keiracom_atomizer_jobs.source_kind.
VALID_SOURCE_KINDS: frozenset[str] = frozenset(
    {"skill", "manual", "governance_doc", "discovery_log", "session"}
)

# Trigger condition `kind` enum — structured predicate vocabulary.
# PLACEHOLDER per dispatch B1 — Elliot 48hr design report names the canonical
# set. Pilot uses these 6 kinds covering the obvious base cases. The atomizer
# REJECTS free-text triggers via this whitelist; switching the set is one-file.
VALID_TRIGGER_KINDS: frozenset[str] = frozenset(
    {
        "tenant_attribute",  # e.g. tier=pro AND tenant has X integration
        "request_shape",  # e.g. user message matches "summarize X"
        "time_window",  # e.g. before/after a clock condition
        "tool_invocation",  # e.g. before/after a specific tool call
        "system_event",  # e.g. a webhook or scheduled event fires
        "context_predicate",  # e.g. specific data structurally present
    }
)

# Relationship-type enum for supersession edges — capped single-digit per hard
# constraint. Pilot uses these 7 covering the deliberation shapes Atlas + I
# have surfaced across recent PRs.
VALID_RELATIONSHIP_TYPES: frozenset[str] = frozenset(
    {
        "supersedes",  # successor fully replaces predecessor
        "refines",  # successor narrows or refines predecessor scope
        "extends",  # successor adds to predecessor without replacing
        "contradicts",  # successor and predecessor mutually exclude
        "scopes",  # successor scopes predecessor to a subset
        "deprecates",  # successor marks predecessor as obsolete-but-kept
        "reinterprets",  # successor reframes predecessor (e.g. policy update)
    }
)

# Composition tag axes per canonical schema field "(domain/concern/applicable_context)".
# Each axis has 8 values → 8 × 6 × 6 = 288 combinations. PLACEHOLDER values
# pending Elliot's report; the cardinality matches dispatch reference exactly.
VALID_COMPOSITION_TAG_DOMAINS: frozenset[str] = frozenset(
    {
        "sales",
        "support",
        "marketing",
        "operations",
        "engineering",
        "finance",
        "legal",
        "internal",
    }
)
VALID_COMPOSITION_TAG_CONCERNS: frozenset[str] = frozenset(
    {
        "compliance",
        "performance",
        "cost",
        "user_experience",
        "data_quality",
        "security",
    }
)
VALID_COMPOSITION_TAG_CONTEXTS: frozenset[str] = frozenset(
    {
        "chat_realtime",
        "background_job",
        "audit_review",
        "incident_response",
        "onboarding",
        "billing",
    }
)

# Union of all valid composition tags as flat list (288 = 8 × 6 × 6).
VALID_COMPOSITION_TAGS: frozenset[tuple[str, str, str]] = frozenset(
    (d, c, x)
    for d in VALID_COMPOSITION_TAG_DOMAINS
    for c in VALID_COMPOSITION_TAG_CONCERNS
    for x in VALID_COMPOSITION_TAG_CONTEXTS
)

# Provenance JSONB field key whitelist (per canonical schema parenthetical).
PROVENANCE_REQUIRED_KEYS: frozenset[str] = frozenset(
    {"source", "freshness", "confidence", "last_validated"}
)

# UUID v4 shape — used for atom_id / tenant_id / edge_id validation outside DB.
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_valid_uuid_str(value: str) -> bool:
    """True iff `value` is a UUID-shaped string."""
    return bool(_UUID_RE.match(value))


def is_valid_composition_tag(tag: dict[str, Any]) -> bool:
    """True iff `tag` is a `{domain, concern, applicable_context}` dict whose
    values are all in the frozen vocabularies."""
    if not isinstance(tag, dict):
        return False
    return (
        tag.get("domain") in VALID_COMPOSITION_TAG_DOMAINS
        and tag.get("concern") in VALID_COMPOSITION_TAG_CONCERNS
        and tag.get("applicable_context") in VALID_COMPOSITION_TAG_CONTEXTS
    )


@dataclass(frozen=True, kw_only=True)
class AtomV1:
    """In-memory representation of one atom row in keiracom_atoms.

    Frozen dataclass — atoms are immutable values. Edits produce supersession
    edges, not in-place mutations (per content-level supersession invariant).
    """

    atom_id: UUID
    tenant_id: UUID
    trigger_condition: dict[str, Any]
    content: str
    anti_pattern: str | None
    example: str | None
    provenance: dict[str, Any]
    composition_tags: dict[str, Any] = field(default_factory=dict)
    content_embedding: list[float] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION
    state: str = "active"

    def __post_init__(self) -> None:
        # Trigger condition: structured predicate only — reject free-text.
        if not isinstance(self.trigger_condition, dict):
            raise ValueError(
                "trigger_condition must be a structured predicate dict, not "
                f"{type(self.trigger_condition).__name__} — atomizer rejects "
                "free-text triggers per hard constraint"
            )
        kind = self.trigger_condition.get("kind")
        if kind not in VALID_TRIGGER_KINDS:
            raise ValueError(
                f"trigger_condition.kind {kind!r} not in {sorted(VALID_TRIGGER_KINDS)}"
            )
        if "params" not in self.trigger_condition or not isinstance(
            self.trigger_condition["params"], dict
        ):
            raise ValueError("trigger_condition must include a 'params' dict")

        # Content non-empty (also CHECK'd in DB).
        if not self.content:
            raise ValueError("content must be non-empty")

        # Provenance required keys.
        missing = PROVENANCE_REQUIRED_KEYS - set(self.provenance.keys())
        if missing:
            raise ValueError(f"provenance missing required keys: {sorted(missing)}")
        conf = self.provenance.get("confidence")
        if not isinstance(conf, int | float) or not (0 <= float(conf) <= 1):
            raise ValueError(f"provenance.confidence must be a float in [0, 1]; got {conf!r}")

        # Composition tags — validate against frozen vocabulary if present.
        # Empty dict {} is allowed (some sources may not yet carry tags).
        if self.composition_tags and not is_valid_composition_tag(self.composition_tags):
            raise ValueError(
                f"composition_tags {self.composition_tags!r} not in frozen vocabulary "
                "(see schema.VALID_COMPOSITION_TAG_* sets)"
            )

        # State enum.
        if self.state not in VALID_STATES:
            raise ValueError(f"state {self.state!r} not in {sorted(VALID_STATES)}")

        # Schema version positive int.
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ValueError("schema_version must be a positive int")


@dataclass(frozen=True, kw_only=True)
class SupersessionEdgeV1:
    """One row in keiracom_atom_supersession_edges.

    Content-level only — schema migration does NOT trigger edge rewrite; it
    triggers re-atomization with new schema_version.
    """

    edge_id: UUID
    tenant_id: UUID
    predecessor_atom: UUID
    successor_atom: UUID
    relationship_type: str
    confidence: float

    def __post_init__(self) -> None:
        if self.predecessor_atom == self.successor_atom:
            raise ValueError("predecessor_atom and successor_atom must differ")
        if self.relationship_type not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(
                f"relationship_type {self.relationship_type!r} not in "
                f"{sorted(VALID_RELATIONSHIP_TYPES)}"
            )
        if not (0 <= self.confidence <= 1):
            raise ValueError(f"confidence must be in [0, 1]; got {self.confidence!r}")
