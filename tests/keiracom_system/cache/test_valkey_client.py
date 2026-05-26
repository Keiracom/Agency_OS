"""ValkeyClient unit tests — Phase A7 sub-task 1.

Covers:
  - canonical_cache_key() determinism (same inputs → same key across calls)
  - cross-tenant isolation (key namespace prefix per tenant_id)
  - _enforce_tenant_prefix() rejects wrong-tenant + missing-prefix keys
  - metric emission on get() hit/miss
  - canonical_cache_key() with vs without query_text (embedding bucket)

DI fakes — no live Redis, no live TEI sidecar.
"""

from typing import Any

import pytest

from src.keiracom_system.cache.valkey_client import (
    OUTCOME_HIT,
    OUTCOME_MISS,
    ValkeyClient,
    ValkeyClientError,
)
from src.keiracom_system.embeddings.tei_client import TEIClient, _HTTPResponse


class _FakeRedis:
    def __init__(self, store: dict[str, bytes] | None = None):
        self.store = store or {}
        self.set_calls: list[tuple[str, str | bytes]] = []
        self.setex_calls: list[tuple[str, int, str | bytes]] = []
        self.delete_calls: list[str] = []

    def get(self, key: str) -> bytes | None:
        return self.store.get(key)

    def set(self, key: str, value: str | bytes) -> None:
        self.set_calls.append((key, value))
        self.store[key] = value if isinstance(value, bytes) else value.encode("utf-8")

    def setex(self, key: str, time: int, value: str | bytes) -> None:
        self.setex_calls.append((key, time, value))
        self.store[key] = value if isinstance(value, bytes) else value.encode("utf-8")

    def delete(self, *keys: str) -> None:
        for k in keys:
            self.delete_calls.append(k)
            self.store.pop(k, None)


def _fake_tei() -> TEIClient:
    # Deterministic embed: returns a fixed vector regardless of input.
    def fake_post(url: str, payload: dict[str, Any], timeout: float) -> _HTTPResponse:
        inputs = payload["inputs"]
        body = (
            b"["
            + b",".join(b"[" + b",".join(b"0.1" for _ in range(384)) + b"]" for _ in inputs)
            + b"]"
        )
        return _HTTPResponse(200, body)

    def fake_get(url: str, timeout: float) -> _HTTPResponse:
        return _HTTPResponse(200, b'{"status":"ok"}')

    return TEIClient(http_get=fake_get, http_post=fake_post)


def test_init_rejects_empty_tenant_id():
    with pytest.raises(ValkeyClientError, match="tenant_id is required"):
        ValkeyClient(redis_client=_FakeRedis(), tei_client=_fake_tei(), tenant_id="")


def test_canonical_cache_key_deterministic_without_query_text():
    client = ValkeyClient(redis_client=_FakeRedis(), tei_client=_fake_tei(), tenant_id="t1")
    k1 = client.canonical_cache_key(tool_name="hubspot.companies.list", args={"limit": 10})
    k2 = client.canonical_cache_key(tool_name="hubspot.companies.list", args={"limit": 10})
    assert k1 == k2
    assert k1.startswith("v1:t1:hubspot.companies.list:")


def test_canonical_cache_key_args_order_stable():
    """Different dict insertion orders produce the same canonical key."""
    client = ValkeyClient(redis_client=_FakeRedis(), tei_client=_fake_tei(), tenant_id="t1")
    k1 = client.canonical_cache_key(tool_name="t", args={"a": 1, "b": 2})
    k2 = client.canonical_cache_key(tool_name="t", args={"b": 2, "a": 1})
    assert k1 == k2


def test_canonical_cache_key_includes_bucket_with_query_text():
    client = ValkeyClient(redis_client=_FakeRedis(), tei_client=_fake_tei(), tenant_id="t1")
    k = client.canonical_cache_key(tool_name="search", args={}, query_text="hello world")
    assert ":b" in k
    assert k.startswith("v1:t1:search:")


def test_cross_tenant_keys_differ_for_same_inputs():
    """Cache-isolation invariant: tenant A and tenant B never share a key."""
    cli_a = ValkeyClient(redis_client=_FakeRedis(), tei_client=_fake_tei(), tenant_id="alpha")
    cli_b = ValkeyClient(redis_client=_FakeRedis(), tei_client=_fake_tei(), tenant_id="beta")
    k_a = cli_a.canonical_cache_key(tool_name="x", args={"q": 1})
    k_b = cli_b.canonical_cache_key(tool_name="x", args={"q": 1})
    assert k_a != k_b
    assert k_a.startswith("v1:alpha:")
    assert k_b.startswith("v1:beta:")


def test_get_rejects_wrong_tenant_prefix():
    client = ValkeyClient(redis_client=_FakeRedis(), tei_client=_fake_tei(), tenant_id="t1")
    with pytest.raises(ValkeyClientError, match="does not match expected tenant prefix"):
        client.get("v1:t2:tool:abc")


def test_get_rejects_missing_namespace_prefix():
    client = ValkeyClient(redis_client=_FakeRedis(), tei_client=_fake_tei(), tenant_id="t1")
    with pytest.raises(ValkeyClientError, match="does not match expected tenant prefix"):
        client.get("raw-key-no-prefix")


def test_set_rejects_wrong_tenant_prefix():
    client = ValkeyClient(redis_client=_FakeRedis(), tei_client=_fake_tei(), tenant_id="t1")
    with pytest.raises(ValkeyClientError):
        client.set("v1:t2:tool:abc", "value")


def test_delete_rejects_wrong_tenant_prefix():
    client = ValkeyClient(redis_client=_FakeRedis(), tei_client=_fake_tei(), tenant_id="t1")
    with pytest.raises(ValkeyClientError):
        client.delete("v1:t2:tool:abc")


def test_get_accepts_canonical_key():
    redis_fake = _FakeRedis(store={"v1:t1:tool:hash": b"cached"})
    client = ValkeyClient(redis_client=redis_fake, tei_client=_fake_tei(), tenant_id="t1")
    key = client.canonical_cache_key(tool_name="tool", args={"a": 1})
    # The constructed key uses hash of args, so we directly construct a known-good
    # canonical key to test the get path:
    assert client.get("v1:t1:tool:hash") == b"cached"
    # And canonical_cache_key returns something we could probe (its hash varies):
    assert key.startswith("v1:t1:tool:")


def test_set_with_ttl_uses_setex():
    redis_fake = _FakeRedis()
    client = ValkeyClient(redis_client=redis_fake, tei_client=_fake_tei(), tenant_id="t1")
    client.set("v1:t1:tool:abc", "value", ttl_seconds=60)
    assert len(redis_fake.setex_calls) == 1
    assert redis_fake.setex_calls[0] == ("v1:t1:tool:abc", 60, "value")
    assert len(redis_fake.set_calls) == 0


def test_set_without_ttl_uses_plain_set():
    redis_fake = _FakeRedis()
    client = ValkeyClient(redis_client=redis_fake, tei_client=_fake_tei(), tenant_id="t1")
    client.set("v1:t1:tool:abc", "value", ttl_seconds=0)
    assert len(redis_fake.set_calls) == 1
    assert len(redis_fake.setex_calls) == 0


def test_get_emits_hit_metric():
    redis_fake = _FakeRedis(store={"v1:t1:tool:hash": b"cached"})
    captured: list[tuple[str, dict[str, str]]] = []

    def emit(name: str, tags: dict[str, str]) -> None:
        captured.append((name, tags))

    client = ValkeyClient(
        redis_client=redis_fake,
        tei_client=_fake_tei(),
        tenant_id="t1",
        metric_emitter=emit,
    )
    client.get("v1:t1:tool:hash", tool_name="hubspot.companies.list")
    assert len(captured) == 1
    name, tags = captured[0]
    assert name == "keiracom.cache.valkey.lookup"
    assert tags["outcome"] == OUTCOME_HIT
    assert tags["tenant_id"] == "t1"
    assert tags["tool_name"] == "hubspot.companies.list"


def test_get_emits_miss_metric():
    captured: list[tuple[str, dict[str, str]]] = []

    def emit(name: str, tags: dict[str, str]) -> None:
        captured.append((name, tags))

    client = ValkeyClient(
        redis_client=_FakeRedis(),
        tei_client=_fake_tei(),
        tenant_id="t1",
        metric_emitter=emit,
    )
    result = client.get("v1:t1:tool:missing")
    assert result is None
    assert captured[0][1]["outcome"] == OUTCOME_MISS


def test_quantise_to_bucket_in_range():
    """Bucket index always in [0, num_buckets)."""
    client = ValkeyClient(redis_client=_FakeRedis(), tei_client=_fake_tei(), tenant_id="t1")
    embedding = [0.5] * 384
    bucket = client._quantise_to_bucket(embedding, num_buckets=4096)
    assert 0 <= bucket < 4096


def test_quantise_to_bucket_deterministic():
    client = ValkeyClient(redis_client=_FakeRedis(), tei_client=_fake_tei(), tenant_id="t1")
    embedding = [0.5] * 384
    assert client._quantise_to_bucket(embedding, num_buckets=4096) == client._quantise_to_bucket(
        embedding, num_buckets=4096
    )
