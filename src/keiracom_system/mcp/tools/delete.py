"""delete — single-memory delete from a tenant's Hindsight bank.

Scale tier only per the dispatch tier-router. Bulk tenant GDPR-delete is
the deprovisioning path (PR #1131 `deprovision_tenant`); this tool is the
finer-grained per-memory erasure surface a tenant operator can call directly.
"""

from __future__ import annotations

from typing import Any, Protocol

from src.keiracom_system.memory.wrappers._base import TenantExtensionProtocol


class _DeletingClient(Protocol):
    def delete_memory(self, *, bank_id: str, memory_id: str) -> dict[str, Any]: ...


def delete_memory(
    *,
    client: _DeletingClient,
    tenant_extension: TenantExtensionProtocol,
    tenant_id: str,
    memory_id: str,
) -> dict[str, Any]:
    if not tenant_id:
        raise ValueError("tenant_id required for delete")
    if not memory_id:
        raise ValueError("memory_id required for delete")
    bank_id = tenant_extension.get_bank_id(tenant_id)
    return client.delete_memory(bank_id=bank_id, memory_id=memory_id)
