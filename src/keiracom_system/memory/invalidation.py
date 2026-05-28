"""invalidation.py — real-time supersede/delete invalidation across the three
memory-layer stores (Hindsight API, Weaviate vector store, Valkey cache).

Wave 1 CUTOVER GATE (Aiden audit + Dave ratify 2026-05-27, Agency_OS-q6ed):
when an atom is superseded or deleted, recall must immediately exclude it.
The hooks here are the wiring that fires invalidate-by-memory-id across all
three stores on supersede / delete events.

Canonical key citations (per audit-dispatch checklist `_orchestrator.md`):

ceo:cutover_plan_v1 — full_retrieval_tier_ratify_2026_05_27_22Z.waves.wave_1_foundation:
    "Hindsight primitives complete (synthesize+trace+delete with source-atom
     pointers) + atom granularity spec + tenant scoping per-callsite +
     bounded-spawn dispatcher-kill + Go sidecar deploy + real-time invalidation"

ceo:memory_abstraction_layer_v1 — eleven_agreed_positions #3:
    "Six query primitives: Ingest, Recall, Synthesize, Supersede, Trace, Delete"

DESIGN — three Protocol-typed adapters fronting the three stores. The
coordinator wires them and exposes `on_delete` / `on_supersede` hooks. Each
adapter is independently testable + injectable; no adapter imports another's
client surface. Cross-tenant boundary enforced at the Valkey adapter (mirrors
the read/write guard in ValkeyClient._enforce_tenant_prefix).

Stale-recall scenarios (`tests/keiracom_system/memory/test_invalidation.py`)
demonstrate the fail-test pattern: a baseline test shows recall returning a
stale atom WITHOUT the coordinator; the coordinator-on test shows the same
atom excluded after invalidate. The diff is the value of the hook.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

log = logging.getLogger(__name__)


class HindsightDeleteClient(Protocol):
    """Minimal Hindsight client surface for invalidation (delete only)."""

    def delete(self, *, bank_id: str, memory_id: str) -> dict[str, Any]: ...


class TenantBankResolver(Protocol):
    def get_bank_id(self, tenant_id: str) -> str: ...


class ValkeyBackpointerProtocol(Protocol):
    """Subset of the Valkey/Redis surface invalidation needs.

    Distinct from the read/write Protocol in ValkeyClient — invalidation
    requires set-membership ops (sadd/smembers) for the back-pointer index
    plus delete. Pre-aggregation at scale is a Phase 2 follow-up; V1 stores
    one back-pointer set per memory_id.
    """

    def sadd(self, key: str, *members: str) -> int: ...
    def smembers(self, key: str) -> set[bytes] | set[str]: ...
    def delete(self, *keys: str) -> int: ...


class WeaviateFilterDeleteProtocol(Protocol):
    """Vector-store surface for delete-by-metadata-filter.

    Weaviate v4 client exposes
    `collections.get(name).data.delete_many(where=Filter.by_property(...).equal(...))`.
    The adapter accepts a thin wrapper around that; tests inject a fake.
    """

    def delete_by_source_memory_id(
        self, *, collection: str, source_memory_id: str
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class StoreInvalidationOutcome:
    """Per-store outcome of an invalidate call."""

    ok: bool
    deleted_count: int = 0
    error: str = ""
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InvalidationResult:
    """Aggregate outcome of an on_delete / on_supersede call across all
    configured stores.

    `all_ok` short-circuits to False if any configured store failed; stores
    not configured (None at coordinator construction) are simply absent
    from the dict and do not block all_ok.
    """

    memory_id: str
    tenant_id: str
    trigger: str
    superseded_by: str | None = None
    per_store: dict[str, StoreInvalidationOutcome] = field(default_factory=dict)
    schema_version: str = "1.0"

    @property
    def all_ok(self) -> bool:
        return all(o.ok for o in self.per_store.values())


_VALID_TRIGGERS = frozenset({"delete", "supersede"})


class HindsightInvalidator:
    """Hindsight-engine invalidation — calls DELETE
    /v1/default/banks/{id}/memories/{id} via the injected client.

    On supersede triggers Hindsight is intentionally a no-op: the engine
    preserves history natively and recall filters by supersession edge
    (see ceo:memory_abstraction_layer_v1 #11 + AntiPattern.supersedes_memory_id).
    Hard-delete is reserved for explicit `delete` triggers.
    """

    def __init__(
        self,
        *,
        client: HindsightDeleteClient,
        tenant_extension: TenantBankResolver,
    ) -> None:
        self._client = client
        self._tenants = tenant_extension

    def invalidate(
        self, *, tenant_id: str, memory_id: str, trigger: str
    ) -> StoreInvalidationOutcome:
        if trigger == "supersede":
            # Engine preserves raw facts on supersede; recall excludes via
            # the supersedes edge written by AntiPatternWrapper.
            return StoreInvalidationOutcome(
                ok=True, deleted_count=0, detail={"skipped_reason": "engine_preserves_on_supersede"}
            )
        if trigger != "delete":
            return StoreInvalidationOutcome(ok=False, error=f"unknown trigger {trigger!r}")
        try:
            bank_id = self._tenants.get_bank_id(tenant_id)
        except KeyError as e:
            return StoreInvalidationOutcome(ok=False, error=f"unknown_tenant: {e}")
        try:
            resp = self._client.delete(bank_id=bank_id, memory_id=memory_id)
        except Exception as e:  # noqa: BLE001 — store boundary; surface as outcome
            log.warning("hindsight invalidate failed: %s", e, exc_info=True)
            return StoreInvalidationOutcome(ok=False, error=f"{type(e).__name__}: {e}")
        if isinstance(resp, dict) and resp.get("error"):
            return StoreInvalidationOutcome(ok=False, error=str(resp["error"]), detail=resp)
        return StoreInvalidationOutcome(ok=True, deleted_count=1, detail=resp or {})


class ValkeyInvalidator:
    """Valkey cache invalidation via back-pointer registry.

    `register_memory_ref(cache_key, memory_ids)` must be called by the
    cache writer at set() time so the back-pointer set exists; `invalidate`
    looks up the set keyed on memory_id and deletes every cache_key it
    contains, then deletes the back-pointer set itself.

    The registry key format is `v1:{tenant}:invref:{memory_id}` — namespaced
    under the same prefix as canonical cache keys so a tenant-scope sweep
    catches both.
    """

    BACKPOINTER_PREFIX = "v1:"
    BACKPOINTER_SEGMENT = ":invref:"

    def __init__(self, *, redis_client: ValkeyBackpointerProtocol, tenant_id: str) -> None:
        if not tenant_id:
            raise ValueError("tenant_id required (cross-tenant isolation invariant)")
        self._redis = redis_client
        self._tenant_id = tenant_id

    def _backpointer_key(self, memory_id: str) -> str:
        return f"{self.BACKPOINTER_PREFIX}{self._tenant_id}{self.BACKPOINTER_SEGMENT}{memory_id}"

    def register_memory_ref(self, *, cache_key: str, memory_ids: list[str]) -> int:
        """Register that `cache_key` was populated from `memory_ids`. Called
        by the cache writer at set() time. Returns total back-pointers added.
        """
        if not cache_key:
            raise ValueError("cache_key required")
        added = 0
        for mid in memory_ids:
            if not mid:
                continue
            added += int(self._redis.sadd(self._backpointer_key(mid), cache_key) or 0)
        return added

    def invalidate(
        self, *, tenant_id: str, memory_id: str, trigger: str
    ) -> StoreInvalidationOutcome:
        if tenant_id != self._tenant_id:
            return StoreInvalidationOutcome(
                ok=False,
                error=(
                    f"cross-tenant invalidate refused: invalidator bound to "
                    f"{self._tenant_id!r}, called with {tenant_id!r}"
                ),
            )
        if trigger not in _VALID_TRIGGERS:
            return StoreInvalidationOutcome(ok=False, error=f"unknown trigger {trigger!r}")
        ref_key = self._backpointer_key(memory_id)
        raw = self._redis.smembers(ref_key) or set()
        cache_keys = sorted({m.decode() if isinstance(m, bytes) else str(m) for m in raw})
        deleted = 0
        if cache_keys:
            deleted = int(self._redis.delete(*cache_keys) or 0)
        # Remove the back-pointer set itself last so a partial failure leaves
        # it for retry rather than orphaning cache keys.
        self._redis.delete(ref_key)
        return StoreInvalidationOutcome(
            ok=True, deleted_count=deleted, detail={"cache_keys": cache_keys}
        )


class WeaviateInvalidator:
    """Vector-store invalidation via metadata.source_memory_id filter delete.

    Objects in Weaviate carry a `source_memory_id` metadata key pointing at
    the Hindsight atom they were indexed from (by the indexer at write time).
    Invalidation deletes every object across the configured collections
    where that metadata field matches.
    """

    DEFAULT_COLLECTIONS = ("Decisions", "Discoveries", "Sessions", "Keis", "Codebase")

    def __init__(
        self,
        *,
        store: WeaviateFilterDeleteProtocol,
        collections: tuple[str, ...] = DEFAULT_COLLECTIONS,
    ) -> None:
        self._store = store
        self._collections = tuple(collections)

    def invalidate(
        self, *, tenant_id: str, memory_id: str, trigger: str
    ) -> StoreInvalidationOutcome:
        if trigger not in _VALID_TRIGGERS:
            return StoreInvalidationOutcome(ok=False, error=f"unknown trigger {trigger!r}")
        del tenant_id  # collection scoping handles isolation today; cross-tenant
        # boundary in Weaviate is collection-level not row-level. Accepted V1 limit.
        total = 0
        per_collection: dict[str, Any] = {}
        for c in self._collections:
            try:
                resp = self._store.delete_by_source_memory_id(
                    collection=c, source_memory_id=memory_id
                )
            except Exception as e:  # noqa: BLE001
                log.warning("weaviate invalidate failed for %s: %s", c, e, exc_info=True)
                per_collection[c] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
                continue
            count = int(resp.get("deleted_count", 0) if isinstance(resp, dict) else 0)
            total += count
            per_collection[c] = {"ok": True, "deleted_count": count}
        all_ok = all(v.get("ok") for v in per_collection.values())
        return StoreInvalidationOutcome(
            ok=all_ok, deleted_count=total, detail={"per_collection": per_collection}
        )


class InvalidationCoordinator:
    """Wires the three store adapters and fans out on_delete / on_supersede.

    Any adapter may be None — coordinator simply omits that store from the
    fan-out. This lets early-deploy environments (e.g. Weaviate not yet
    cut over) wire only Hindsight + Valkey and still exercise the hook.
    """

    def __init__(
        self,
        *,
        hindsight: HindsightInvalidator | None = None,
        valkey: ValkeyInvalidator | None = None,
        weaviate: WeaviateInvalidator | None = None,
    ) -> None:
        if hindsight is None and valkey is None and weaviate is None:
            raise ValueError(
                "at least one invalidator must be configured (hindsight/valkey/weaviate all None)"
            )
        self._hindsight = hindsight
        self._valkey = valkey
        self._weaviate = weaviate

    def _fan_out(
        self, *, tenant_id: str, memory_id: str, trigger: str, superseded_by: str | None
    ) -> InvalidationResult:
        if not tenant_id:
            raise ValueError("tenant_id required")
        if not memory_id:
            raise ValueError("memory_id required")
        if trigger not in _VALID_TRIGGERS:
            raise ValueError(f"unknown trigger {trigger!r}; allowed: {sorted(_VALID_TRIGGERS)}")
        per_store: dict[str, StoreInvalidationOutcome] = {}
        if self._hindsight is not None:
            per_store["hindsight"] = self._hindsight.invalidate(
                tenant_id=tenant_id, memory_id=memory_id, trigger=trigger
            )
        if self._valkey is not None:
            per_store["valkey"] = self._valkey.invalidate(
                tenant_id=tenant_id, memory_id=memory_id, trigger=trigger
            )
        if self._weaviate is not None:
            per_store["weaviate"] = self._weaviate.invalidate(
                tenant_id=tenant_id, memory_id=memory_id, trigger=trigger
            )
        result = InvalidationResult(
            memory_id=memory_id,
            tenant_id=tenant_id,
            trigger=trigger,
            superseded_by=superseded_by,
            per_store=per_store,
        )
        log.info(
            "invalidation %s: tenant=%s memory=%s ok=%s stores=%d",
            trigger,
            tenant_id,
            memory_id,
            result.all_ok,
            len(per_store),
        )
        return result

    def on_delete(self, *, tenant_id: str, memory_id: str) -> InvalidationResult:
        return self._fan_out(
            tenant_id=tenant_id, memory_id=memory_id, trigger="delete", superseded_by=None
        )

    def on_supersede(
        self, *, tenant_id: str, memory_id: str, superseded_by: str
    ) -> InvalidationResult:
        if not superseded_by:
            raise ValueError("superseded_by required on supersede trigger")
        return self._fan_out(
            tenant_id=tenant_id,
            memory_id=memory_id,
            trigger="supersede",
            superseded_by=superseded_by,
        )
