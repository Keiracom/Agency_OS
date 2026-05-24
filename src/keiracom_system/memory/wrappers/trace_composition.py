"""trace_composition.py — Aiden Gate D Trace primitive composition.

Trace is one of the six MAL V1 primitives (`eleven_agreed_positions` #3):
    "Six query primitives: Ingest, Recall, Synthesize, Supersede, Trace, Delete"

V1 scope is regulatory necessity (HIPAA / legal-privilege / accounting audit-
trail), per `five_converged_decisions_locked.trace_primitive`. The PR #1129
spike item-vi finding confirms Hindsight delivers the building blocks
NATIVELY — no new infrastructure needed:

  - OTel distributed tracing on every retain/recall/reflect (`monitoring.md`)
  - hindsight.operation.duration Histogram with bank_id/source/success labels
  - tenant JSON-log field (`HINDSIGHT_API_LOG_JSON_FIELDS`) for per-tenant audit
  - Reflect outputs are citation-validated (only IDs actually retrieved citable)
  - Observations preserve raw facts — supersession history reconstructible

This module COMPOSES those signals into an `AuditRecord` shape downstream
compliance pipelines (HIPAA, legal review, billing) can consume directly.
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
class AuditRecord:
    """Structured audit-trail entry. One per Trace call.

    Fields chosen for HIPAA / legal-privilege / accounting fit:
    - timestamp:   when the audited operation occurred (UTC ISO-8601)
    - actor:       tenant_id (BYOK-sovereign — never cross-tenant)
    - tenant_id:   redundant with actor for filter-by-column readability
    - otel_trace_id: span id for cross-system correlation
    - operation:   one of `ingest|recall|reflect|delete`
    - query:       the reflect/recall query (redacted for sensitive verticals)
    - citations:   memory ids actually retrieved by the engine (citation-validated)
    - reasoning_chain: per-step Reflect tool calls; supports "why was this
                      decided?" reconstruction
    - audit_purpose: 'hipaa' | 'legal_privilege' | 'accounting' | 'general'
    - schema_version: bumped if AuditRecord shape changes; compliance consumers
                      key off this
    """

    timestamp: str
    actor: str
    tenant_id: str
    otel_trace_id: str
    operation: str
    query: str
    citations: list[str] = field(default_factory=list)
    reasoning_chain: list[dict[str, Any]] = field(default_factory=list)
    audit_purpose: str = "general"
    schema_version: str = "1.0"


_VALID_OPERATIONS = frozenset({"ingest", "recall", "reflect", "delete"})
_VALID_AUDIT_PURPOSES = frozenset({"hipaa", "legal_privilege", "accounting", "general"})


def compose_audit_record(
    *,
    client: HindsightClient,
    tenant_extension: TenantExtensionProtocol,
    tenant_id: str,
    operation: str,
    query: str,
    audit_purpose: str = "general",
    redact_query: bool = False,
) -> AuditRecord:
    """Run a Hindsight reflect against the tenant's bank and compose the
    resulting span + citations + reasoning chain into an AuditRecord.

    Fail-loud: invalid operation / audit_purpose / tenant raise ValueError.
    These are governance-shape errors, not transient ones — a silent fallback
    here would defeat the regulatory-audit purpose.
    """
    if operation not in _VALID_OPERATIONS:
        raise ValueError(f"unknown operation {operation!r}; allowed: {sorted(_VALID_OPERATIONS)}")
    if audit_purpose not in _VALID_AUDIT_PURPOSES:
        raise ValueError(
            f"unknown audit_purpose {audit_purpose!r}; allowed: {sorted(_VALID_AUDIT_PURPOSES)}"
        )
    if not tenant_id:
        raise ValueError("tenant_id required for Trace composition (BYOK boundary)")
    if not query:
        raise ValueError("query required for Trace composition")
    bank_id = tenant_extension.get_bank_id(tenant_id)
    reflect_resp = client.reflect(bank_id=bank_id, query=query)
    # Extract citation memory ids (Hindsight returns either ["id1","id2"] or
    # [{id:..,content:..}] depending on version — handle both shapes).
    raw_cites = reflect_resp.get("citations", []) or reflect_resp.get("cited_memory_ids", [])
    citations = [c if isinstance(c, str) else str(c.get("id", "")) for c in raw_cites]
    citations = [c for c in citations if c]
    reasoning_chain = reflect_resp.get("reasoning_chain", []) or reflect_resp.get("trace", [])
    otel_trace_id = reflect_resp.get("otel_trace_id") or str(uuid.uuid4())
    rec = AuditRecord(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        actor=tenant_id,
        tenant_id=tenant_id,
        otel_trace_id=otel_trace_id,
        operation=operation,
        query="<redacted>" if redact_query else query,
        citations=citations,
        reasoning_chain=reasoning_chain,
        audit_purpose=audit_purpose,
    )
    log.info(
        "audit_record composed: tenant=%s op=%s purpose=%s citations=%d",
        tenant_id,
        operation,
        audit_purpose,
        len(citations),
    )
    return rec
