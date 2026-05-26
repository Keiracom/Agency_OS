"""ValkeyClient — Phase A7 sub-task 1.

Per-tenant Valkey semantic cache client. Wraps the redis-py / valkey-protocol
connection with:
  - canonical_cache_key()  — deterministic key construction across spawns
  - tenant prefix guard    — read/write boundary check (CB-Atlas)
  - instrumentation hook   — Better Stack lookup metric emission (sub-task 4)

CANONICAL DESIGN — docs/architecture/design/a7_cache_architecture.md §4 + §13
(PR #1156 + PR #1165 merged 2026-05-26).

DESIGN DECISIONS folded in per build-time clarifications (§13):
  CB-1 — uses redis>=5.0.0 (already in requirements.txt; not valkey-py)
  CB-2 — dependency-injection of redis.Redis + TEIClient at __init__
  CB-10 — all key construction MUST go through canonical_cache_key()
  CB-Atlas — _enforce_tenant_prefix() at read/write boundary (defence-in-depth)

TESTABILITY: redis client + TEI client + metric emitter are all injectable so
unit tests don't need a live Valkey or TEI container. The runtime caller (LLM
workflow #2 activity factory) constructs the real instances from env config
and injects.

CONSUMERS:
  - LLM-call workflow #2 (separate dispatch) — wraps each LLM call's cache_check
  - 48h baseline observation script (sub-task 5) — reads cache_lookup metrics
"""

from __future__ import annotations

import hashlib
import json
import logging
import struct
from collections.abc import Callable
from typing import Any, Protocol

from src.keiracom_system.cache.constants import (
    EMBEDDING_BUCKET_COUNT,
    VALKEY_KEY_NAMESPACE_PREFIX,
)
from src.keiracom_system.embeddings.tei_client import TEIClient

log = logging.getLogger(__name__)

# Outcome label for cache_lookup metric (per design §4 instrumentation).
OUTCOME_HIT = "hit"
OUTCOME_MISS = "miss"


class _RedisProtocol(Protocol):
    """Subset of redis.Redis we depend on. Lets unit tests inject a fake."""

    def get(self, key: str) -> bytes | None: ...
    def set(self, key: str, value: str | bytes) -> Any: ...
    def setex(self, key: str, time: int, value: str | bytes) -> Any: ...
    def delete(self, *keys: str) -> Any: ...


# Metric emitter: caller-injected callable. None = no instrumentation.
# Signature: (metric_name, tags_dict) -> None. Pre-aggregation at scale is a
# Phase 2 follow-up per CB-5 (cardinality cap on tenant_id × tool_name × outcome).
MetricEmitter = Callable[[str, dict[str, str]], None]


class ValkeyClientError(RuntimeError):
    """Raised on any Valkey-side or tenant-isolation violation."""


class ValkeyClient:
    """Per-tenant cache client.

    Each instance is bound to a single tenant_id. Cross-tenant access raises
    ValkeyClientError via _enforce_tenant_prefix() — read/write boundary guard.
    """

    def __init__(
        self,
        *,
        redis_client: _RedisProtocol,
        tei_client: TEIClient,
        tenant_id: str,
        metric_emitter: MetricEmitter | None = None,
    ):
        if not tenant_id:
            raise ValkeyClientError("tenant_id is required (cross-tenant isolation invariant)")
        self._redis = redis_client
        self._tei = tei_client
        self._tenant_id = tenant_id
        self._metric_emitter = metric_emitter
        self._expected_prefix = f"{VALKEY_KEY_NAMESPACE_PREFIX}{tenant_id}:"

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def canonical_cache_key(
        self,
        *,
        tool_name: str,
        args: dict[str, Any],
        query_text: str | None = None,
    ) -> str:
        """Construct the canonical Valkey key for a tool call.

        Deterministic across spawns — same (tenant_id, tool_name, args,
        query_text) always yields the same key, so ephemeral agent #2 hits
        the cache populated by ephemeral agent #1.

        With query_text, includes a semantic bucket component derived from the
        BGE-small-en-v1.5 embedding (via TEIClient). Without query_text,
        falls back to args-hash only.
        """
        if not tool_name:
            raise ValkeyClientError("tool_name is required")
        args_normalised = json.dumps(args, sort_keys=True, separators=(",", ":"))
        args_hash = hashlib.sha256(args_normalised.encode("utf-8")).hexdigest()[:16]
        if query_text:
            embedding = self._tei.embed([query_text])[0]
            bucket = self._quantise_to_bucket(embedding)
            return f"{self._expected_prefix}{tool_name}:{args_hash}:b{bucket}"
        return f"{self._expected_prefix}{tool_name}:{args_hash}"

    @staticmethod
    def _quantise_to_bucket(
        embedding: list[float], num_buckets: int = EMBEDDING_BUCKET_COUNT
    ) -> int:
        """Map a 384-dim embedding to a bucket index in [0, num_buckets).

        V1 — sign-bit hash projection. Stable per (embedding, num_buckets).
        Phase 2 may swap to a learned hash (e.g. LSH); the canonical key
        format is stable across implementations because the bucket index is
        a single integer.
        """
        # Pack floats deterministically, hash, then modulo into the bucket space.
        packed = struct.pack(f"{len(embedding)}f", *embedding)
        digest = hashlib.sha256(packed).digest()
        # Take leading 4 bytes as unsigned int, modulo num_buckets.
        leading = int.from_bytes(digest[:4], byteorder="big", signed=False)
        return leading % num_buckets

    def _enforce_tenant_prefix(self, key: str) -> None:
        """Reject any key not matching v1:{self._tenant_id}:* at the read/write boundary.

        Defence-in-depth: even if a caller bypasses canonical_cache_key(), this
        guard catches it. Complements the PR-linter pattern in
        scripts/ci/check_no_raw_valkey_outside_client.sh (per CB-10 + CB-Atlas).
        """
        if not key.startswith(self._expected_prefix):
            raise ValkeyClientError(
                f"valkey key {key!r} does not match expected tenant prefix "
                f"{self._expected_prefix!r} — all keys MUST go through "
                "ValkeyClient.canonical_cache_key()"
            )

    def get(self, key: str, *, tool_name: str | None = None) -> bytes | None:
        """Read from Valkey. Emits cache_lookup{outcome=hit|miss} metric."""
        self._enforce_tenant_prefix(key)
        value = self._redis.get(key)
        outcome = OUTCOME_HIT if value is not None else OUTCOME_MISS
        if self._metric_emitter is not None:
            self._metric_emitter(
                "keiracom.cache.valkey.lookup",
                {
                    "tenant_id": self._tenant_id,
                    "tool_name": tool_name or "unknown",
                    "outcome": outcome,
                },
            )
        return value

    def set(self, key: str, value: str | bytes, *, ttl_seconds: int = 0) -> None:
        """Write to Valkey with optional TTL. ttl_seconds=0 means no expiry.

        Per design §4 per-tool-type TTL — caller passes the right TTL from
        constants.py (VALKEY_TTL_READ_MOSTLY / DEFINITION_FETCH / MUTATION).
        Mutation tools should never reach set() because TTL=0 + caller
        contract — but the client doesn't enforce that here (caller's
        responsibility).
        """
        self._enforce_tenant_prefix(key)
        if ttl_seconds > 0:
            self._redis.setex(key, ttl_seconds, value)
        else:
            self._redis.set(key, value)

    def delete(self, key: str) -> None:
        """Explicit invalidation — rare path (Composio webhook handler etc.)."""
        self._enforce_tenant_prefix(key)
        self._redis.delete(key)
