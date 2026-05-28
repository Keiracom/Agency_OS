"""tests for keiracom_system.memory.invalidation — Wave 1 CUTOVER GATE q6ed.

Coverage matrix (Aiden gate-validator discipline: >=4 negatives per primitive):
- HindsightInvalidator   — 3 positive + 4 negative
- ValkeyInvalidator      — 3 positive + 4 negative
- WeaviateInvalidator    — 2 positive + 3 negative
- InvalidationCoordinator — 3 positive + 4 negative
- stale-recall fail-tests — 3 scenarios (one per store)

Stale-recall pattern: a baseline test demonstrates recall returning a stale
atom WITHOUT the coordinator wired in; the coordinator-on test shows the
same atom excluded after invalidate. The diff is the value of the hook.

All store clients mocked; no live Hindsight / Weaviate / Valkey required.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.keiracom_system.memory.invalidation import (
    HindsightInvalidator,
    InvalidationCoordinator,
    InvalidationResult,
    StoreInvalidationOutcome,
    ValkeyInvalidator,
    WeaviateInvalidator,
)


class _FakeHindsightClient:
    def __init__(self) -> None:
        self.delete_calls: list[dict[str, Any]] = []
        self.bank_state: dict[tuple[str, str], dict[str, Any]] = {}
        self.delete_response: dict[str, Any] = {"ok": True}

    def retain(self, *, bank_id: str, memory_id: str, content: str) -> None:
        self.bank_state[(bank_id, memory_id)] = {"content": content}

    def recall(self, *, bank_id: str) -> list[dict[str, Any]]:
        return [
            {"id": mid, **payload} for (b, mid), payload in self.bank_state.items() if b == bank_id
        ]

    def delete(self, *, bank_id: str, memory_id: str) -> dict[str, Any]:
        self.delete_calls.append({"bank_id": bank_id, "memory_id": memory_id})
        self.bank_state.pop((bank_id, memory_id), None)
        return dict(self.delete_response)


class _FakeTenants:
    def __init__(self, bank_map: dict[str, str] | None = None) -> None:
        self.bank_map = bank_map or {"tenant-acme": "bank-acme"}

    def get_bank_id(self, tenant_id: str) -> str:
        if tenant_id not in self.bank_map:
            raise KeyError(f"unknown tenant {tenant_id}")
        return self.bank_map[tenant_id]


class _FakeRedis:
    def __init__(self) -> None:
        self.sets: dict[str, set[str]] = {}
        self.kv: dict[str, str] = {}

    def sadd(self, key: str, *members: str) -> int:
        s = self.sets.setdefault(key, set())
        added = 0
        for m in members:
            if m not in s:
                s.add(m)
                added += 1
        return added

    def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))

    def delete(self, *keys: str) -> int:
        n = 0
        for k in keys:
            if k in self.sets:
                del self.sets[k]
                n += 1
            if k in self.kv:
                del self.kv[k]
                n += 1
        return n

    # Cache-side ops used only by the stale-recall scenario fixtures.
    def setkv(self, key: str, value: str) -> None:
        self.kv[key] = value

    def get(self, key: str) -> str | None:
        return self.kv.get(key)


class _FakeWeaviateStore:
    def __init__(self) -> None:
        self.objects: list[dict[str, Any]] = []
        self.delete_calls: list[dict[str, Any]] = []
        self.raise_on_collection: str | None = None

    def insert(self, *, collection: str, source_memory_id: str, text: str) -> None:
        self.objects.append(
            {"collection": collection, "source_memory_id": source_memory_id, "text": text}
        )

    def recall(self, *, collection: str) -> list[dict[str, Any]]:
        return [o for o in self.objects if o["collection"] == collection]

    def delete_by_source_memory_id(
        self, *, collection: str, source_memory_id: str
    ) -> dict[str, Any]:
        self.delete_calls.append({"collection": collection, "source_memory_id": source_memory_id})
        if collection == self.raise_on_collection:
            raise RuntimeError("simulated weaviate outage")
        before = len(self.objects)
        self.objects = [
            o
            for o in self.objects
            if not (o["collection"] == collection and o["source_memory_id"] == source_memory_id)
        ]
        return {"deleted_count": before - len(self.objects)}


@pytest.fixture
def hindsight_client():
    return _FakeHindsightClient()


@pytest.fixture
def tenants():
    return _FakeTenants()


@pytest.fixture
def redis_client():
    return _FakeRedis()


@pytest.fixture
def weaviate_store():
    return _FakeWeaviateStore()


# ============== HindsightInvalidator ==============


def test_hindsight_invalidator_calls_delete_on_delete_trigger(hindsight_client, tenants):
    inv = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-X", trigger="delete")
    assert out.ok
    assert out.deleted_count == 1
    assert hindsight_client.delete_calls == [{"bank_id": "bank-acme", "memory_id": "mem-X"}]


def test_hindsight_invalidator_skips_on_supersede_trigger(hindsight_client, tenants):
    # Engine preserves raw facts on supersede; recall excludes via supersedes edge.
    inv = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-X", trigger="supersede")
    assert out.ok
    assert out.deleted_count == 0
    assert hindsight_client.delete_calls == []
    assert out.detail.get("skipped_reason") == "engine_preserves_on_supersede"


def test_hindsight_invalidator_surfaces_engine_error(hindsight_client, tenants):
    hindsight_client.delete_response = {"error": "HTTP_500", "body": "engine down"}
    inv = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-X", trigger="delete")
    assert not out.ok
    assert "HTTP_500" in out.error


def test_hindsight_invalidator_rejects_unknown_trigger(hindsight_client, tenants):
    inv = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-X", trigger="purge")
    assert not out.ok
    assert "unknown trigger" in out.error


def test_hindsight_invalidator_unknown_tenant_surfaces_as_outcome(hindsight_client, tenants):
    # Unknown tenant must NOT raise — it's a per-store outcome that the
    # coordinator aggregates into all_ok=False. Fail-soft at store boundary.
    inv = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    out = inv.invalidate(tenant_id="tenant-ghost", memory_id="mem-X", trigger="delete")
    assert not out.ok
    assert "unknown_tenant" in out.error
    assert hindsight_client.delete_calls == []


def test_hindsight_invalidator_swallows_client_exception_as_outcome(hindsight_client, tenants):
    class _RaisingClient:
        def delete(self, *, bank_id: str, memory_id: str) -> dict[str, Any]:
            raise RuntimeError("connection refused")

    inv = HindsightInvalidator(client=_RaisingClient(), tenant_extension=tenants)
    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-X", trigger="delete")
    assert not out.ok
    assert "RuntimeError" in out.error


# ============== ValkeyInvalidator ==============


def test_valkey_invalidator_deletes_cache_keys_from_back_pointer(redis_client):
    inv = ValkeyInvalidator(redis_client=redis_client, tenant_id="tenant-acme")
    # Register two cache keys that referenced memory mem-X.
    inv.register_memory_ref(cache_key="v1:tenant-acme:tool-a:hash1", memory_ids=["mem-X", "mem-Y"])
    inv.register_memory_ref(cache_key="v1:tenant-acme:tool-b:hash2", memory_ids=["mem-X"])
    redis_client.setkv("v1:tenant-acme:tool-a:hash1", "cached-payload-1")
    redis_client.setkv("v1:tenant-acme:tool-b:hash2", "cached-payload-2")

    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-X", trigger="delete")
    assert out.ok
    assert out.deleted_count == 2
    assert redis_client.get("v1:tenant-acme:tool-a:hash1") is None
    assert redis_client.get("v1:tenant-acme:tool-b:hash2") is None
    # back-pointer for mem-Y untouched (different memory)
    assert "v1:tenant-acme:invref:mem-Y" in redis_client.sets


def test_valkey_invalidator_no_op_when_no_back_pointers_registered(redis_client):
    inv = ValkeyInvalidator(redis_client=redis_client, tenant_id="tenant-acme")
    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-Z", trigger="delete")
    assert out.ok
    assert out.deleted_count == 0
    assert out.detail.get("cache_keys") == []


def test_valkey_invalidator_register_skips_empty_memory_ids(redis_client):
    inv = ValkeyInvalidator(redis_client=redis_client, tenant_id="tenant-acme")
    added = inv.register_memory_ref(cache_key="ck", memory_ids=["mem-A", "", "mem-B"])
    assert added == 2


def test_valkey_invalidator_rejects_empty_tenant_at_construct(redis_client):
    with pytest.raises(ValueError, match="tenant_id required"):
        ValkeyInvalidator(redis_client=redis_client, tenant_id="")


def test_valkey_invalidator_refuses_cross_tenant_invalidate(redis_client):
    inv = ValkeyInvalidator(redis_client=redis_client, tenant_id="tenant-acme")
    out = inv.invalidate(tenant_id="tenant-other", memory_id="mem-X", trigger="delete")
    assert not out.ok
    assert "cross-tenant" in out.error


def test_valkey_invalidator_rejects_unknown_trigger(redis_client):
    inv = ValkeyInvalidator(redis_client=redis_client, tenant_id="tenant-acme")
    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-X", trigger="purge")
    assert not out.ok
    assert "unknown trigger" in out.error


def test_valkey_invalidator_register_rejects_empty_cache_key(redis_client):
    inv = ValkeyInvalidator(redis_client=redis_client, tenant_id="tenant-acme")
    with pytest.raises(ValueError, match="cache_key required"):
        inv.register_memory_ref(cache_key="", memory_ids=["mem-A"])


# ============== WeaviateInvalidator ==============


def test_weaviate_invalidator_deletes_across_all_collections(weaviate_store):
    weaviate_store.insert(collection="Decisions", source_memory_id="mem-X", text="d1")
    weaviate_store.insert(collection="Discoveries", source_memory_id="mem-X", text="d2")
    weaviate_store.insert(collection="Decisions", source_memory_id="mem-Y", text="d3")
    inv = WeaviateInvalidator(store=weaviate_store, collections=("Decisions", "Discoveries"))
    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-X", trigger="delete")
    assert out.ok
    assert out.deleted_count == 2
    # mem-Y untouched
    assert any(o["source_memory_id"] == "mem-Y" for o in weaviate_store.objects)


def test_weaviate_invalidator_on_supersede_runs_same_path(weaviate_store):
    # Supersede on Weaviate also deletes — the supersession edge is engine-side
    # not vector-store-side. The vector index is rebuilt from atoms; superseded
    # atoms should drop out of recall, hence delete.
    weaviate_store.insert(collection="Decisions", source_memory_id="mem-X", text="d1")
    inv = WeaviateInvalidator(store=weaviate_store, collections=("Decisions",))
    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-X", trigger="supersede")
    assert out.ok
    assert out.deleted_count == 1


def test_weaviate_invalidator_partial_failure_marks_outcome_not_ok(weaviate_store):
    weaviate_store.raise_on_collection = "Discoveries"
    weaviate_store.insert(collection="Decisions", source_memory_id="mem-X", text="d1")
    weaviate_store.insert(collection="Discoveries", source_memory_id="mem-X", text="d2")
    inv = WeaviateInvalidator(store=weaviate_store, collections=("Decisions", "Discoveries"))
    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-X", trigger="delete")
    assert not out.ok
    # Decisions deletion happened even though Discoveries failed.
    assert out.deleted_count == 1


def test_weaviate_invalidator_rejects_unknown_trigger(weaviate_store):
    inv = WeaviateInvalidator(store=weaviate_store)
    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-X", trigger="purge")
    assert not out.ok
    assert "unknown trigger" in out.error


def test_weaviate_invalidator_no_matching_objects_returns_zero_count(weaviate_store):
    inv = WeaviateInvalidator(store=weaviate_store, collections=("Decisions",))
    out = inv.invalidate(tenant_id="tenant-acme", memory_id="mem-NONE", trigger="delete")
    assert out.ok
    assert out.deleted_count == 0


# ============== InvalidationCoordinator ==============


def test_coordinator_fans_out_to_all_three_stores(
    hindsight_client, tenants, redis_client, weaviate_store
):
    weaviate_store.insert(collection="Decisions", source_memory_id="mem-X", text="d1")
    h = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    v = ValkeyInvalidator(redis_client=redis_client, tenant_id="tenant-acme")
    v.register_memory_ref(cache_key="v1:tenant-acme:t:h", memory_ids=["mem-X"])
    redis_client.setkv("v1:tenant-acme:t:h", "cached")
    w = WeaviateInvalidator(store=weaviate_store, collections=("Decisions",))
    coord = InvalidationCoordinator(hindsight=h, valkey=v, weaviate=w)
    result = coord.on_delete(tenant_id="tenant-acme", memory_id="mem-X")
    assert isinstance(result, InvalidationResult)
    assert result.all_ok
    assert set(result.per_store.keys()) == {"hindsight", "valkey", "weaviate"}
    assert result.per_store["hindsight"].deleted_count == 1
    assert result.per_store["valkey"].deleted_count == 1
    assert result.per_store["weaviate"].deleted_count == 1


def test_coordinator_supersede_requires_superseded_by(hindsight_client, tenants):
    h = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    coord = InvalidationCoordinator(hindsight=h)
    with pytest.raises(ValueError, match="superseded_by required"):
        coord.on_supersede(tenant_id="tenant-acme", memory_id="mem-X", superseded_by="")


def test_coordinator_supersede_records_superseded_by_in_result(hindsight_client, tenants):
    h = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    coord = InvalidationCoordinator(hindsight=h)
    result = coord.on_supersede(tenant_id="tenant-acme", memory_id="mem-X", superseded_by="mem-Y")
    assert result.superseded_by == "mem-Y"
    assert result.trigger == "supersede"


def test_coordinator_omits_stores_not_configured(hindsight_client, tenants):
    h = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    # Only Hindsight configured — valkey + weaviate absent from result.
    coord = InvalidationCoordinator(hindsight=h)
    result = coord.on_delete(tenant_id="tenant-acme", memory_id="mem-X")
    assert set(result.per_store.keys()) == {"hindsight"}
    assert result.all_ok


def test_coordinator_rejects_zero_invalidators():
    with pytest.raises(ValueError, match="at least one invalidator"):
        InvalidationCoordinator()


def test_coordinator_rejects_empty_tenant(hindsight_client, tenants):
    h = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    coord = InvalidationCoordinator(hindsight=h)
    with pytest.raises(ValueError, match="tenant_id required"):
        coord.on_delete(tenant_id="", memory_id="mem-X")


def test_coordinator_rejects_empty_memory_id(hindsight_client, tenants):
    h = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    coord = InvalidationCoordinator(hindsight=h)
    with pytest.raises(ValueError, match="memory_id required"):
        coord.on_delete(tenant_id="tenant-acme", memory_id="")


def test_coordinator_all_ok_false_when_any_store_fails(
    hindsight_client, tenants, redis_client, weaviate_store
):
    weaviate_store.raise_on_collection = "Decisions"
    weaviate_store.insert(collection="Decisions", source_memory_id="mem-X", text="d1")
    h = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    v = ValkeyInvalidator(redis_client=redis_client, tenant_id="tenant-acme")
    w = WeaviateInvalidator(store=weaviate_store, collections=("Decisions",))
    coord = InvalidationCoordinator(hindsight=h, valkey=v, weaviate=w)
    result = coord.on_delete(tenant_id="tenant-acme", memory_id="mem-X")
    assert not result.all_ok
    assert result.per_store["hindsight"].ok
    assert result.per_store["valkey"].ok
    assert not result.per_store["weaviate"].ok


# ============== Stale-recall fail-test scenarios ==============


def test_stale_recall_hindsight_without_coordinator(hindsight_client, tenants):
    """BASELINE: without the coordinator wired in, deleting a memory at the
    wrapper layer does NOT propagate — the engine still returns it on recall.

    This is the fail-test that motivates the coordinator. PR q6ed exists so
    we can flip this from baseline-stale to coordinator-clean.
    """
    hindsight_client.retain(bank_id="bank-acme", memory_id="mem-STALE", content="old")
    # Simulate a "supersede at the wrapper layer" that does NOT invalidate the engine.
    # (Equivalent to the pre-q6ed world where supersedes_memory_id was a metadata
    # tag with no enforcement on the recall path.)
    assert any(m["id"] == "mem-STALE" for m in hindsight_client.recall(bank_id="bank-acme"))


def test_stale_recall_hindsight_with_coordinator_excludes_atom(hindsight_client, tenants):
    """COORDINATOR-ON: on_delete fires Hindsight invalidator → engine drops
    the atom → recall no longer returns it.
    """
    hindsight_client.retain(bank_id="bank-acme", memory_id="mem-STALE", content="old")
    h = HindsightInvalidator(client=hindsight_client, tenant_extension=tenants)
    coord = InvalidationCoordinator(hindsight=h)
    coord.on_delete(tenant_id="tenant-acme", memory_id="mem-STALE")
    assert not any(m["id"] == "mem-STALE" for m in hindsight_client.recall(bank_id="bank-acme"))


def test_stale_recall_valkey_cache_returns_old_payload_without_coordinator(redis_client):
    """BASELINE: a cached recall result for memory mem-STALE survives a
    delete that doesn't fire the invalidator — the cache returns the
    pre-delete payload (stale)."""
    redis_client.setkv("v1:tenant-acme:tool-a:hash1", "stale-cached-payload-referencing-mem-STALE")
    # Nothing invalidates the cache. Lookup still returns the stale payload.
    assert redis_client.get("v1:tenant-acme:tool-a:hash1") == (
        "stale-cached-payload-referencing-mem-STALE"
    )


def test_stale_recall_valkey_with_coordinator_drops_cached_payload(redis_client):
    """COORDINATOR-ON: with the back-pointer registered + on_delete fired,
    the cache key is gone → next lookup misses → recall is recomputed."""
    redis_client.setkv("v1:tenant-acme:tool-a:hash1", "stale-cached-payload-referencing-mem-STALE")
    v = ValkeyInvalidator(redis_client=redis_client, tenant_id="tenant-acme")
    v.register_memory_ref(cache_key="v1:tenant-acme:tool-a:hash1", memory_ids=["mem-STALE"])
    coord = InvalidationCoordinator(valkey=v)
    coord.on_delete(tenant_id="tenant-acme", memory_id="mem-STALE")
    assert redis_client.get("v1:tenant-acme:tool-a:hash1") is None


def test_stale_recall_weaviate_vector_still_returns_atom_without_coordinator(weaviate_store):
    """BASELINE: a Weaviate-indexed object survives a wrapper-layer supersede
    that doesn't invalidate the vector store — semantic search returns it."""
    weaviate_store.insert(collection="Decisions", source_memory_id="mem-STALE", text="old")
    assert any(
        o["source_memory_id"] == "mem-STALE" for o in weaviate_store.recall(collection="Decisions")
    )


def test_stale_recall_weaviate_with_coordinator_purges_vector(weaviate_store):
    """COORDINATOR-ON: on_supersede fires Weaviate invalidator → object dropped."""
    weaviate_store.insert(collection="Decisions", source_memory_id="mem-STALE", text="old")
    w = WeaviateInvalidator(store=weaviate_store, collections=("Decisions",))
    coord = InvalidationCoordinator(weaviate=w)
    coord.on_supersede(tenant_id="tenant-acme", memory_id="mem-STALE", superseded_by="mem-NEW")
    assert not any(
        o["source_memory_id"] == "mem-STALE" for o in weaviate_store.recall(collection="Decisions")
    )


def test_store_invalidation_outcome_default_detail_is_empty_dict():
    # Defensive: dataclass default_factory wiring must produce isolated dicts
    # per instance (no shared mutable default trap).
    a = StoreInvalidationOutcome(ok=True)
    b = StoreInvalidationOutcome(ok=True)
    a.detail["x"] = 1  # type: ignore[index]
    assert "x" not in b.detail
