"""ingest — polymorphic MAL Ingest primitive over the 4 node-type wrappers.

Routes by `node_type` (decision | artifact | taskcontext | antipattern) to the
appropriate wrapper from PR #1134. AntiPattern requires extra fields per
CLAUDE.md Discovery Log v2 (context + failed_path + verified_path).
"""

from __future__ import annotations

from typing import Any

from src.keiracom_system.memory.wrappers import (
    AntiPatternWrapper,
    ArtifactWrapper,
    DecisionWrapper,
    TaskContextWrapper,
)
from src.keiracom_system.memory.wrappers._base import (
    HindsightClient,
    TenantExtensionProtocol,
)

_VALID_NODE_TYPES = ("decision", "artifact", "taskcontext", "antipattern")


def ingest_memory(
    *,
    client: HindsightClient,
    tenant_extension: TenantExtensionProtocol,
    tenant_id: str,
    node_type: str,
    content: str = "",
    metadata: dict[str, Any] | None = None,
    # Artifact-specific (mandatory if node_type=artifact)
    author: str | None = None,
    artifact_ref: str | None = None,
    # AntiPattern-specific (mandatory if node_type=antipattern)
    context: str | None = None,
    failed_path: str | None = None,
    verified_path: str | None = None,
    supersedes_memory_id: str | None = None,
) -> dict[str, Any]:
    if node_type not in _VALID_NODE_TYPES:
        raise ValueError(f"unknown node_type {node_type!r}; allowed: {_VALID_NODE_TYPES}")
    if node_type == "decision":
        w = DecisionWrapper(client, tenant_extension)
        return w.ingest(tenant_id=tenant_id, content=content, metadata=metadata)
    if node_type == "artifact":
        if author is None or artifact_ref is None:
            raise ValueError("artifact ingest requires author + artifact_ref")
        w_artifact = ArtifactWrapper(client, tenant_extension)
        return w_artifact.ingest(
            tenant_id=tenant_id,
            content=content,
            author=author,
            artifact_ref=artifact_ref,
            metadata=metadata,
        )
    if node_type == "taskcontext":
        w_task = TaskContextWrapper(client, tenant_extension)
        return w_task.ingest(tenant_id=tenant_id, content=content, metadata=metadata)
    # antipattern
    if not (context and failed_path and verified_path):
        raise ValueError(
            "antipattern ingest requires context + failed_path + verified_path "
            "(CLAUDE.md Discovery Log v2)"
        )
    w_anti = AntiPatternWrapper(client, tenant_extension)
    return w_anti.ingest(
        tenant_id=tenant_id,
        context=context,
        failed_path=failed_path,
        verified_path=verified_path,
        supersedes_memory_id=supersedes_memory_id,
        metadata=metadata,
    )
