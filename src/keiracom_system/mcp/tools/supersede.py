"""supersede — explicit supersession-via-AntiPattern.

eleven_agreed_positions #4 — "Synthesis: supersession-via-AntiPattern V1".
This tool is a constrained alias of `ingest_memory(node_type='antipattern',
supersedes_memory_id=...)` — it makes the supersession semantics explicit
in the MCP tool surface rather than buried in an optional ingest kwarg.

Pro tier and above per the dispatch tier-router.
"""

from __future__ import annotations

from typing import Any

from src.keiracom_system.memory.wrappers import AntiPatternWrapper
from src.keiracom_system.memory.wrappers._base import (
    HindsightClient,
    TenantExtensionProtocol,
)


def supersede_memory(
    *,
    client: HindsightClient,
    tenant_extension: TenantExtensionProtocol,
    tenant_id: str,
    superseded_memory_id: str,
    context: str,
    failed_path: str,
    verified_path: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not superseded_memory_id:
        raise ValueError("supersede requires superseded_memory_id (id of the superseded fact)")
    w = AntiPatternWrapper(client, tenant_extension)
    return w.ingest(
        tenant_id=tenant_id,
        context=context,
        failed_path=failed_path,
        verified_path=verified_path,
        supersedes_memory_id=superseded_memory_id,
        metadata=metadata,
    )
