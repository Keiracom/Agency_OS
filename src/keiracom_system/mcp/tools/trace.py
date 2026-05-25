"""trace — Aiden Gate D audit-trail composition.

Scale tier only per the dispatch tier-router. Composes Hindsight's native
signals (OTel + tenant log + citation-validated Reflect) into an AuditRecord
shaped for HIPAA / legal_privilege / accounting / general purposes.

Delegates to compose_audit_record from PR #1134.
"""

from __future__ import annotations

from src.keiracom_system.memory.wrappers import AuditRecord, compose_audit_record
from src.keiracom_system.memory.wrappers._base import (
    HindsightClient,
    TenantExtensionProtocol,
)


def trace_audit(
    *,
    client: HindsightClient,
    tenant_extension: TenantExtensionProtocol,
    tenant_id: str,
    operation: str,
    query: str,
    audit_purpose: str = "general",
    redact_query: bool = False,
) -> AuditRecord:
    return compose_audit_record(
        client=client,
        tenant_extension=tenant_extension,
        tenant_id=tenant_id,
        operation=operation,
        query=query,
        audit_purpose=audit_purpose,
        redact_query=redact_query,
    )
