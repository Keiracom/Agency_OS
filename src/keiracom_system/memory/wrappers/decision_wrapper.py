"""decision_wrapper.py — Decision → Hindsight World.

DIRECT mapping per PR #1129 spike item vi: Hindsight `retain()` accepts a
content payload; type-inference at the engine layer produces `world` facts
for content describing decisions made about external state. The wrapper adds
the MAL classification tag (`mal_node:decision`) so recall can filter cleanly.
"""

from __future__ import annotations

from typing import Any

from ._base import HindsightClient, TenantExtensionProtocol, stringify_metadata

_TAGS = ["mal_node:decision"]


class DecisionWrapper:
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
            raise ValueError("Decision content must be non-empty")
        bank_id = self.tenants.get_bank_id(tenant_id)
        item = {
            "content": content,
            "tags": list(_TAGS),
            "metadata": stringify_metadata({**(metadata or {}), "mal_node": "decision"}),
        }
        return self.client.retain(bank_id=bank_id, items=[item])

    def recall(
        self,
        *,
        tenant_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        bank_id = self.tenants.get_bank_id(tenant_id)
        return self.client.recall(bank_id=bank_id, query=query, tags=list(_TAGS), top_k=top_k)
