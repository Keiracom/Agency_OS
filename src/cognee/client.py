"""client.py — sole Cognee call surface for Agency OS.

Per Cognee Phase 0 directive (Dave ts 1778562801, Elliot dispatch ts 1778562982):
all Cognee usage in this codebase MUST go through these four functions. Direct
imports of the cognee SDK outside this module are forbidden — keeps the multi-
tenant naming convention + agent-scoped node_set tagging consistent.

Tenant encoding (per Dave gap-3 resolution + Scout Q4 + Elliot ts 1778565xxx):
    user.email     = f"{org_id}@keiracom.local"        # mints per-tenant Cognee User
    user.tenant_id = org_id                            # propagates to dataset UUID derivation
    dataset_name   = f"{org_id}__{app_id}"             # e.g. "keiracom_platform__agency_os"
    node_set       = [f"agent:{agent_id}"] + extras    # e.g. ["agent:aiden", "test"]

Why per-tenant User minting (Scout Q4): Cognee derives
    dataset.id = uuid5(NAMESPACE_OID, f"{dataset_name}{user.id}{user.tenant_id}")
and scopes ops via set_database_global_context_variables(dataset.id, dataset.owner_id).
If every Keiracom tenant wrote as one shared default User, distinct dataset_names
would still share owner_id → Dave's Validation Query 4 (cross-namespace isolation)
would fail. Minting one User per org_id with tenant_id=org_id gives true isolation
at both the dataset-UUID and auth-permission layers.

Backing stores (per /home/elliotbot/.config/agency-os/.env LLM_*/EMBEDDING_*
block; Gemini amendment ts 1778563xxx swapped Ollama → Gemini):
    LLM       : Gemini 2.5 Flash via Google AI Studio (GEMINI_API_KEY)
    Embedding : Gemini text-embedding-004 (768 dims)
    Vector DB : pgvector on $SUPABASE_DB_URL
    Relational: sqlalchemy on $SUPABASE_DB_URL
    Graph DB  : Kuzu at /home/elliotbot/clawd/cognee_graph/
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import cognee

# Eager init: asyncio.Semaphore() constructor is loop-agnostic in Python 3.10+
# (attaches to loop on first acquire). Module-level eager-create eliminates any
# theoretical race in the prior lazy-init `if None: assign` pattern (single-loop
# asyncio is yield-point-atomic, but multi-loop test harnesses could theoretically
# pass both `is None` checks before either assigns). Audit-and-clean-up follow-up
# to PR #826 per Aiden+Max+Elliot triple-concur ts ~1778662900.
_LANCE_WRITE_SEM: asyncio.Semaphore = asyncio.Semaphore(1)


def _install_lance_writer_serialiser() -> None:
    """Serialise concurrent Lance writes from Cognee's pipeline scheduler.

    Cognee's cognee.tasks.storage.index_data_points fires batch index calls via
    asyncio.gather with no per-writer semaphore. With VECTOR_DB_PROVIDER=lancedb
    that races Lance's default single-writer policy (lance-4.0.0/src/dataset/
    write/retry.rs:48 — 2 retries / 30s timeout), causing "Too many concurrent
    writers" exceptions. Crash anchor: 2026-05-13T01:54:53 — see PR #825 +
    docs/wave2/kei23_stream2_crash_diagnosis.md.

    Patches LanceDBAdapter.index_data_points (the funnel all batch tasks flow
    through, delegating to create_data_points -> collection.merge_insert) with
    a module-level asyncio.Semaphore(1). Idempotent — sets __kei23_serialised__
    so repeated imports do not stack wrappers.

    Active only when VECTOR_DB_PROVIDER=lancedb. Other providers (pgvector,
    chromadb) handle their own writer concurrency. Remove this once Cognee
    upstream serialises or exposes a knob.
    """
    if os.environ.get("VECTOR_DB_PROVIDER", "").lower() != "lancedb":
        return
    try:
        from cognee.infrastructure.databases.vector.lancedb.LanceDBAdapter import LanceDBAdapter
    except ImportError:
        return
    orig = LanceDBAdapter.index_data_points
    if getattr(orig, "__kei23_serialised__", False):
        return

    async def serialised_index_data_points(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        async with _LANCE_WRITE_SEM:
            return await orig(self, *args, **kwargs)

    serialised_index_data_points.__kei23_serialised__ = True  # type: ignore[attr-defined]
    LanceDBAdapter.index_data_points = serialised_index_data_points


_install_lance_writer_serialiser()


def _access_control_enabled() -> bool:
    """True iff Cognee's multi-user access control is on (env: ENABLE_BACKEND_ACCESS_CONTROL).

    Per Dave's Option E ts 1778572400 + Aiden escalation-3 ts 1778571845: when
    access control is off the wrapper skips per-tenant Cognee User minting so
    the aiosqlite User-query path (segfault site on this server's Python 3.12.3
    / aiosqlite 0.22.1 stack) is not exercised. Trade-off: Validation Query #4
    cross-tenant isolation is not enforced at Phase 0 — Phase 0 is single-tenant
    API-surface verify anyway, consistent with the directive's Phase 0 framing.
    """
    return os.environ.get("ENABLE_BACKEND_ACCESS_CONTROL", "").lower() == "true"


# In-process cache so we mint each Cognee User exactly once per process. Cognee's
# user store is the SQLAlchemy Dataset/User DB, so this is purely a hot-path
# optimisation — cold lookups still go through get_user_by_email.
_USER_CACHE: dict[str, Any] = {}


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


def _tenant_email(org_id: str) -> str:
    """Synthetic email used as the Cognee User identifier for a Keiracom tenant.

    Not a real mailbox — Cognee uses email as the User primary lookup key.
    Convention: f"{org_id}@keiracom.local" so per-org isolation is deterministic.
    """
    if not org_id:
        raise ValueError(f"org_id required for tenant User minting (got {org_id!r})")
    return f"{org_id}@keiracom.local"


async def _get_or_create_user(org_id: str) -> Any:
    """Return the Cognee User scoped to this Keiracom tenant; mint if absent.

    Idempotent: caches the resolved User in-process; on cache miss, calls
    cognee.modules.users.methods.get_user_by_email; if that returns None, calls
    create_user with email + tenant_id=org_id. Subsequent calls hit the cache.
    """
    if org_id in _USER_CACHE:
        return _USER_CACHE[org_id]

    from cognee.modules.users.methods import create_user, get_user_by_email

    email = _tenant_email(org_id)
    user = await get_user_by_email(email)
    if user is None:
        user = await create_user(email=email, tenant_id=org_id, is_superuser=False)
    _USER_CACHE[org_id] = user
    return user


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
    Per-tenant Cognee User is auto-minted on first call for this org_id.
    """
    dataset = _dataset_name(org_id, app_id)
    tags = _agent_node_set(agent_id, node_set)
    kwargs: dict[str, Any] = {"dataset_name": dataset, "node_set": tags}
    if _access_control_enabled():
        kwargs["user"] = await _get_or_create_user(org_id)
    return await cognee.add(content, **kwargs)


async def cognify() -> Any:
    """Process pending added data into the knowledge graph + embeddings.

    Must be called after add() before search() can return new content.
    Cognee processes ALL pending datasets in one pass; per-tenant scoping
    is already baked into each dataset's owner_id via the User-on-add path.
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
    """Semantic search the per-org/app Cognee dataset, scoped to this tenant's User.

    agent_id is optional on read — when set, scopes results to chunks tagged
    `agent:<agent_id>`. When None, returns results across all agents in the
    org/app scope. Cross-tenant reads are blocked by Cognee's auth layer
    (per-User permission rows) because the User is org-specific.
    """
    dataset = _dataset_name(org_id, app_id)
    kwargs: dict[str, Any] = {"datasets": [dataset]}
    if _access_control_enabled():
        kwargs["user"] = await _get_or_create_user(org_id)
    if agent_id:
        kwargs["node_set"] = [f"agent:{agent_id}"]
    return await cognee.search(query, **kwargs)
