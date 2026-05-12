"""client.py — sole Cognee call surface for Agency OS.

Per Cognee Phase 0 directive (Dave ts 1778562801, Elliot dispatch ts 1778562982):
all Cognee usage in this codebase MUST go through these four functions. Direct
imports of the cognee SDK outside this module are forbidden — keeps the multi-
tenant naming convention + agent-scoped node_set tagging consistent.

Tenant encoding (per Dave gap-3 resolution):
    dataset_name = f"{org_id}__{app_id}"      # e.g. "keiracom_platform__agency_os"
    node_set     = [f"agent:{agent_id}"] + extras  # e.g. ["agent:aiden", "test"]

Backing stores (per /home/elliotbot/.config/agency-os/.env COGNEE_* block):
    LLM       : Ollama llama3.2 (local)
    Embedding : fastembed
    Vector DB : pgvector on $SUPABASE_DB_URL
    Relational: sqlalchemy on $SUPABASE_DB_URL
    Graph DB  : Kuzu at /home/elliotbot/clawd/cognee_graph/
"""

from __future__ import annotations

from typing import Any

import cognee


def _dataset_name(org_id: str, app_id: str) -> str:
    """Compose the Cognee dataset name from org + app scopes."""
    if not org_id or not app_id:
        raise ValueError(f"org_id + app_id required (got org_id={org_id!r}, app_id={app_id!r})")
    return f"{org_id}__{app_id}"


def _agent_node_set(agent_id: str, extras: list[str] | None) -> list[str]:
    """Prepend agent:<agent_id> tag onto caller-supplied node_set."""
    if not agent_id:
        raise ValueError(f"agent_id required for node_set encoding (got {agent_id!r})")
    return [f"agent:{agent_id}", *(extras or [])]


async def add(
    content: str,
    *,
    org_id: str,
    app_id: str,
    agent_id: str,
    node_set: list[str] | None = None,
) -> Any:
    """Add content to the per-org/app Cognee dataset with agent-scoped node_set.

    agent_id is required so every chunk is tagged with the writing agent —
    enables agent-scoped retrieval + audit trail for memory provenance.
    """
    dataset = _dataset_name(org_id, app_id)
    tags = _agent_node_set(agent_id, node_set)
    return await cognee.add(content, dataset_name=dataset, node_set=tags)


async def cognify() -> Any:
    """Process pending added data into the knowledge graph + embeddings.

    Must be called after add() before search() can return new content.
    Cognee processes ALL pending datasets in one pass.
    """
    return await cognee.cognify()


async def memify() -> Any:
    """Run memory-layer enrichment over the cognified graph.

    Distinct from cognify(): memify operates on already-cognified data to
    extract higher-order memory structures (entity links, recurring themes).
    No-op safely if there's no cognified data yet.
    """
    return await cognee.memify()


async def search(
    query: str,
    *,
    org_id: str,
    app_id: str,
    agent_id: str | None = None,
) -> Any:
    """Semantic search the per-org/app Cognee dataset.

    agent_id is optional on read — when set, scopes results to chunks tagged
    `agent:<agent_id>`. When None, returns results across all agents in the
    org/app scope.
    """
    dataset = _dataset_name(org_id, app_id)
    kwargs: dict[str, Any] = {"datasets": [dataset]}
    if agent_id:
        kwargs["node_set"] = [f"agent:{agent_id}"]
    return await cognee.search(query, **kwargs)
