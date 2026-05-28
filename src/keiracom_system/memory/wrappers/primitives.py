"""primitives.py — Synthesize / Trace / complete Delete primitives.

Closes the YELLOW-3 audit gap (Aiden pre-cutover audit 2026-05-27):
3 of 6 MAL V1 primitives (Ingest/Recall/Supersede) ship via the 4 domain
wrappers. The remaining three are cross-cutting query primitives — they
operate on any memory regardless of MAL node type — and live here.

Canonical key (per audit-dispatch checklist `_orchestrator.md`):

ceo:memory_abstraction_layer_v1 — eleven_agreed_positions #3:
    "Six query primitives: Ingest, Recall, Synthesize, Supersede, Trace, Delete"

ceo:cutover_plan_v1 — wave_1_foundation:
    "Hindsight primitives complete (synthesize+trace+delete with source-atom
     pointers) + atom granularity spec + tenant scoping per-callsite +
     bounded-spawn dispatcher-kill + Go sidecar deploy + real-time invalidation"

Synthesize MUST retain source-atom pointers (Aiden Phase-2 mitigation against
synthesis drift) — `SynthesisResult.source_atom_ids` is non-empty by
construction; empty citations fail loud rather than silently returning a
floating answer.

Trace returns the provenance chain for a memory_id — supersedes edges + the
target's own ingest event — as an ordered `ProvenanceChain`. Distinct from
`trace_composition.compose_audit_record` (single-reflect AuditRecord for
HIPAA/legal-privilege/accounting one-shot audit).

Complete delete = hard-delete via the engine's DELETE endpoint + structured
`DeleteRecord` audit-log entry. The partial delete (operation valid in
AuditRecord shape but no method to execute it) is what this primitive
completes.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ._base import HindsightClient, TenantExtensionProtocol

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SynthesisResult:
    """LLM-composed synthesis with mandatory source-atom pointers.

    Aiden Phase-2 drift mitigation: `source_atom_ids` must be non-empty so
    every synthesised answer is traceable back to the ground-truth memories
    that grounded it. Empty citations indicate the engine did not retrieve
    supporting evidence — fail loud instead of returning a floating answer.
    """

    synthesized_answer: str
    source_atom_ids: list[str]
    reasoning_chain: list[dict[str, Any]] = field(default_factory=list)
    otel_trace_id: str = ""
    schema_version: str = "1.0"


@dataclass(frozen=True)
class ProvenanceEvent:
    timestamp: str
    event_type: str
    actor: str
    memory_id: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProvenanceChain:
    """Ordered provenance for a target memory_id.

    - `events`: ingest + supersede events ordered oldest -> newest.
    - `supersedes`: memory_ids the target itself supersedes (from its own
      metadata.supersedes edge).
    - `superseded_by`: memory_ids whose metadata.supersedes == target
      (AntiPatterns or supersession-via-evolution facts pointing at it).
    """

    target_memory_id: str
    tenant_id: str
    events: list[ProvenanceEvent] = field(default_factory=list)
    supersedes: list[str] = field(default_factory=list)
    superseded_by: list[str] = field(default_factory=list)
    schema_version: str = "1.0"


@dataclass(frozen=True)
class DeleteRecord:
    """Structured audit-log entry for a hard-delete.

    `audit_purpose` mirrors the AuditRecord taxonomy so compliance pipelines
    consume a uniform shape across single-reflect audits and delete events.
    """

    memory_id: str
    tenant_id: str
    actor: str
    deleted_at: str
    reason: str
    audit_purpose: str = "general"
    otel_trace_id: str = ""
    engine_response: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0"


_VALID_AUDIT_PURPOSES = frozenset({"hipaa", "legal_privilege", "accounting", "general"})


def synthesize(
    *,
    client: HindsightClient,
    tenant_extension: TenantExtensionProtocol,
    tenant_id: str,
    query: str,
) -> SynthesisResult:
    """Compose a multi-source synthesis via Hindsight reflect with source-atom
    pointers retained.

    Fail-loud: empty `tenant_id` / `query` / zero-citation reflect raise
    ValueError. The zero-citation guard is the Aiden drift mitigation — a
    synthesis with no traceable atoms is exactly the failure mode V1 must
    prevent.
    """
    if not tenant_id:
        raise ValueError("tenant_id required for synthesize (BYOK boundary)")
    if not query:
        raise ValueError("query required for synthesize")
    bank_id = tenant_extension.get_bank_id(tenant_id)
    resp = client.reflect(bank_id=bank_id, query=query)
    raw_cites = resp.get("citations", []) or resp.get("cited_memory_ids", [])
    source_atom_ids = [c if isinstance(c, str) else str(c.get("id", "")) for c in raw_cites]
    source_atom_ids = [c for c in source_atom_ids if c]
    if not source_atom_ids:
        raise ValueError(
            "synthesize produced zero source-atom pointers — synthesis drift "
            "guard (Aiden Phase-2 mitigation). Either no relevant memories in "
            "bank or engine returned an ungrounded answer."
        )
    answer = resp.get("answer") or resp.get("synthesised_answer") or ""
    reasoning_chain = resp.get("reasoning_chain", []) or resp.get("trace", [])
    otel_trace_id = resp.get("otel_trace_id") or str(uuid.uuid4())
    log.info(
        "synthesize composed: tenant=%s atoms=%d query_len=%d",
        tenant_id,
        len(source_atom_ids),
        len(query),
    )
    return SynthesisResult(
        synthesized_answer=answer,
        source_atom_ids=source_atom_ids,
        reasoning_chain=reasoning_chain,
        otel_trace_id=otel_trace_id,
    )


def trace(
    *,
    client: HindsightClient,
    tenant_extension: TenantExtensionProtocol,
    tenant_id: str,
    memory_id: str,
    walk_top_k: int = 20,
) -> ProvenanceChain:
    """Walk supersedes/superseded-by edges around a memory_id and return the
    ordered provenance chain.

    V1 implementation: a single recall query keyed on memory_id surfaces
    memories that cite or are cited by the target via metadata.supersedes
    edges (AntiPatternWrapper writes that key when superseding). The chain
    is reconstructed from the returned metadata.
    """
    if not tenant_id:
        raise ValueError("tenant_id required for trace (BYOK boundary)")
    if not memory_id:
        raise ValueError("memory_id required for trace")
    bank_id = tenant_extension.get_bank_id(tenant_id)
    related = client.recall(bank_id=bank_id, query=memory_id, top_k=walk_top_k)
    events: list[ProvenanceEvent] = []
    supersedes: list[str] = []
    superseded_by: list[str] = []
    for m in related:
        if not isinstance(m, dict):
            continue
        meta_raw = m.get("metadata", {}) or {}
        meta = {str(k): str(v) for k, v in meta_raw.items()}
        mid = str(m.get("id", "") or m.get("memory_id", ""))
        if not mid:
            continue
        timestamp = meta.get("timestamp") or meta.get("created_at") or ""
        actor = meta.get("author") or meta.get("actor") or "unknown"
        # Edge: this memory supersedes the target.
        if meta.get("supersedes") == memory_id:
            superseded_by.append(mid)
            events.append(
                ProvenanceEvent(
                    timestamp=timestamp,
                    event_type="supersede",
                    actor=actor,
                    memory_id=mid,
                    metadata=meta,
                )
            )
        # Self: the target's own ingest event + its outbound supersedes edge.
        if mid == memory_id:
            outbound = meta.get("supersedes")
            if outbound:
                supersedes.append(outbound)
            events.append(
                ProvenanceEvent(
                    timestamp=timestamp,
                    event_type="ingest",
                    actor=actor,
                    memory_id=mid,
                    metadata=meta,
                )
            )
    events.sort(key=lambda e: (e.timestamp, e.event_type))
    return ProvenanceChain(
        target_memory_id=memory_id,
        tenant_id=tenant_id,
        events=events,
        supersedes=supersedes,
        superseded_by=superseded_by,
    )


def complete_delete(
    *,
    client: HindsightClient,
    tenant_extension: TenantExtensionProtocol,
    tenant_id: str,
    memory_id: str,
    actor: str,
    reason: str,
    audit_purpose: str = "general",
) -> DeleteRecord:
    """Hard-delete a memory via the engine's DELETE endpoint and emit a
    structured DeleteRecord for the audit log.

    Fail-loud on missing tenant / memory_id / actor / reason — a delete with
    no actor or reason is exactly the audit-trail gap regulatory verticals
    must prevent.
    """
    if not tenant_id:
        raise ValueError("tenant_id required for complete_delete (BYOK boundary)")
    if not memory_id:
        raise ValueError("memory_id required for complete_delete")
    if not actor:
        raise ValueError("actor required for complete_delete (audit-trail invariant)")
    if not reason:
        raise ValueError("reason required for complete_delete (audit-trail invariant)")
    if audit_purpose not in _VALID_AUDIT_PURPOSES:
        raise ValueError(
            f"unknown audit_purpose {audit_purpose!r}; allowed: {sorted(_VALID_AUDIT_PURPOSES)}"
        )
    bank_id = tenant_extension.get_bank_id(tenant_id)
    engine_resp = client.delete(bank_id=bank_id, memory_id=memory_id)
    otel_trace_id = ""
    if isinstance(engine_resp, dict):
        otel_trace_id = str(engine_resp.get("otel_trace_id", "") or "")
    if not otel_trace_id:
        otel_trace_id = str(uuid.uuid4())
    rec = DeleteRecord(
        memory_id=memory_id,
        tenant_id=tenant_id,
        actor=actor,
        deleted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        reason=reason,
        audit_purpose=audit_purpose,
        otel_trace_id=otel_trace_id,
        engine_response=engine_resp if isinstance(engine_resp, dict) else {},
    )
    log.info(
        "complete_delete: tenant=%s memory=%s actor=%s purpose=%s",
        tenant_id,
        memory_id,
        actor,
        audit_purpose,
    )
    return rec
