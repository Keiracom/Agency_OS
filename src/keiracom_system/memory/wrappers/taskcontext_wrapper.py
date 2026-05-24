"""taskcontext_wrapper.py — TaskContext → Hindsight Observation.

DIRECT mapping per PR #1129 spike item vi: TaskContext content is ingested as
a memory; Hindsight's background consolidation engine derives an Observation
with evidence-grounding + freshness signal + supersession-via-evolution. The
wrapper's `recall()` queries observations specifically (not raw facts), since
TaskContext recall benefits from the deduplicated/consolidated view.

PR #1130 smoke-spike timing: consolidation runs <2min for ~50 source memories
(49 ops → 31 new + 13 updated). Observations queryable via recall thereafter.
"""

from __future__ import annotations

from typing import Any

from ._base import HindsightClient, TenantExtensionProtocol, stringify_metadata

_TAGS = ["mal_node:taskcontext"]


class TaskContextWrapper:
    def __init__(self, client: HindsightClient, tenant_extension: TenantExtensionProtocol) -> None:
        self.client = client
        self.tenants = tenant_extension

    def ingest(
        self,
        *,
        tenant_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not content:
            raise ValueError("TaskContext content must be non-empty")
        bank_id = self.tenants.get_bank_id(tenant_id)
        item = {
            "content": content,
            "tags": list(_TAGS),
            "metadata": stringify_metadata({**(metadata or {}), "mal_node": "taskcontext"}),
        }
        return self.client.retain(bank_id=bank_id, items=[item])

    def recall(
        self,
        *,
        tenant_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        # Recall by tag filters back to TaskContext-tagged memories; the engine's
        # consolidation surfaces them via observation refs in the result payload.
        bank_id = self.tenants.get_bank_id(tenant_id)
        return self.client.recall(bank_id=bank_id, query=query, tags=list(_TAGS), top_k=top_k)
