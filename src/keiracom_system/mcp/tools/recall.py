"""recall — polymorphic MAL Recall primitive over the 4 node-type wrappers.

`node_type=None` recalls across all four; otherwise filters to the specified
type. AntiPattern Graveyard view available via `node_type='antipattern'` +
`empty_query=True` (mirrors AntiPatternWrapper.graveyard()).
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

_WRAPPER_BY_NODE = {
    "decision": DecisionWrapper,
    "artifact": ArtifactWrapper,
    "taskcontext": TaskContextWrapper,
    "antipattern": AntiPatternWrapper,
}


def recall_memories(
    *,
    client: HindsightClient,
    tenant_extension: TenantExtensionProtocol,
    tenant_id: str,
    query: str,
    node_type: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    if node_type is None:
        # Aggregate recall across all four — one round-trip per wrapper.
        # Caller can rank/dedupe downstream; engine itself returns relevance
        # within each tagged subset.
        out: list[dict[str, Any]] = []
        for wrapper_cls in _WRAPPER_BY_NODE.values():
            w = wrapper_cls(client, tenant_extension)
            out.extend(w.recall(tenant_id=tenant_id, query=query, top_k=top_k))
        return out
    if node_type not in _WRAPPER_BY_NODE:
        raise ValueError(f"unknown node_type {node_type!r}; allowed: {sorted(_WRAPPER_BY_NODE)}")
    wrapper = _WRAPPER_BY_NODE[node_type](client, tenant_extension)
    return wrapper.recall(tenant_id=tenant_id, query=query, top_k=top_k)
