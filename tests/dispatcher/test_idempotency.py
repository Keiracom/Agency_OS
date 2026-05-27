"""idempotency unit tests — cutover-blocker 5 (Agency_OS-6c2k).

Acceptance criteria per dispatch (Dave 2026-05-27 / Viktor lever 26):
  (1) idempotency_key computed deterministically from source+content
  (2) Valkey SET NX EX with 5-minute TTL
  (3) dispatch dropped with log when key already present
  (4) verbatim test showing double-dispatch dedupes to single spawn
"""

from __future__ import annotations

from typing import Any

import pytest

from src.dispatcher.idempotency import (
    DEFAULT_TTL_SECONDS,
    DEFAULT_WINDOW_SECONDS,
    IDEM_KEY_PREFIX,
    KEY_HASH_LENGTH,
    IdempotencyDecision,
    IdempotencyError,
    IdempotencyGate,
    compute_idempotency_key,
)


class _FakeRedis:
    """Async-shaped Redis fake. Records SET calls + lets tests script the
    "key already exists" branch.
    """

    def __init__(self) -> None:
        self.set_calls: list[dict[str, Any]] = []
        self._existing_keys: set[str] = set()
        self._raise_on_set: bool = False

    def add_existing(self, key: str) -> None:
        self._existing_keys.add(key)

    def fail_next_set(self) -> None:
        self._raise_on_set = True

    async def set(
        self,
        name: str,
        value: str,
        *,
        nx: bool = False,
        ex: int | None = None,
    ) -> Any:
        if self._raise_on_set:
            self._raise_on_set = False
            raise ConnectionError("simulated Valkey transport failure")
        self.set_calls.append({"name": name, "value": value, "nx": nx, "ex": ex})
        if nx and name in self._existing_keys:
            return None  # SET NX returns None when key exists
        self._existing_keys.add(name)
        return True


def _fixed_now() -> float:
    """Anchor at a unix timestamp that rounds cleanly on 60s window."""
    return 1779854400.0  # 2026-05-27T03:20:00Z (multiple of 60)


# ────────────────────────────────────────────────────────────────────────────
# Acceptance (1) — deterministic key from source+content
# ────────────────────────────────────────────────────────────────────────────


def test_compute_idempotency_key_deterministic_same_inputs_same_key():
    k1, _ = compute_idempotency_key("slack:#ceo", "ship the build", now=_fixed_now())
    k2, _ = compute_idempotency_key("slack:#ceo", "ship the build", now=_fixed_now())
    assert k1 == k2


def test_compute_idempotency_key_different_source_different_key():
    k1, _ = compute_idempotency_key("slack:#ceo", "ship the build", now=_fixed_now())
    k2, _ = compute_idempotency_key("slack:#execution", "ship the build", now=_fixed_now())
    assert k1 != k2


def test_compute_idempotency_key_different_content_different_key():
    k1, _ = compute_idempotency_key("slack:#ceo", "ship the build", now=_fixed_now())
    k2, _ = compute_idempotency_key("slack:#ceo", "ship something else", now=_fixed_now())
    assert k1 != k2


def test_compute_idempotency_key_prefix_and_length():
    """`idem:<16-hex-chars>` shape."""
    key, _ = compute_idempotency_key("s", "c", now=_fixed_now())
    assert key.startswith(IDEM_KEY_PREFIX)
    digest = key[len(IDEM_KEY_PREFIX) :]
    assert len(digest) == KEY_HASH_LENGTH
    # All hex chars
    int(digest, 16)


def test_compute_idempotency_key_rounds_to_window():
    """Timestamps within the same 60s window → same key."""
    k1, w1 = compute_idempotency_key("s", "c", now=_fixed_now())
    k2, w2 = compute_idempotency_key("s", "c", now=_fixed_now() + 30)
    k3, w3 = compute_idempotency_key("s", "c", now=_fixed_now() + 59)
    assert k1 == k2 == k3
    assert w1 == w2 == w3


def test_compute_idempotency_key_window_boundary_different_key():
    """Crossing the 60s window boundary → different key."""
    k1, w1 = compute_idempotency_key("s", "c", now=_fixed_now())
    k2, w2 = compute_idempotency_key("s", "c", now=_fixed_now() + 60)
    assert k1 != k2
    assert w1 != w2
    assert w2 - w1 == 60


def test_compute_idempotency_key_custom_window_seconds():
    """Caller can change the window granularity."""
    k1, _ = compute_idempotency_key("s", "c", window_seconds=300, now=_fixed_now())
    k2, _ = compute_idempotency_key("s", "c", window_seconds=300, now=_fixed_now() + 200)
    assert k1 == k2  # both inside the same 5-min bucket


def test_compute_idempotency_key_rejects_empty_source():
    with pytest.raises(IdempotencyError, match="source must be non-empty"):
        compute_idempotency_key("", "content", now=_fixed_now())


def test_compute_idempotency_key_rejects_empty_content():
    with pytest.raises(IdempotencyError, match="content must be non-empty"):
        compute_idempotency_key("source", "", now=_fixed_now())


def test_compute_idempotency_key_rejects_zero_window():
    with pytest.raises(IdempotencyError, match="window_seconds must be > 0"):
        compute_idempotency_key("s", "c", window_seconds=0, now=_fixed_now())


# ────────────────────────────────────────────────────────────────────────────
# Acceptance (2) — Valkey SET NX EX with 5-minute TTL
# ────────────────────────────────────────────────────────────────────────────


def test_default_ttl_is_300_seconds():
    """5-minute TTL per dispatch."""
    assert DEFAULT_TTL_SECONDS == 300


def test_default_window_is_60_seconds():
    """60-second time window per dispatch."""
    assert DEFAULT_WINDOW_SECONDS == 60


@pytest.mark.asyncio
async def test_check_and_claim_calls_set_nx_ex_5_minute_ttl():
    redis = _FakeRedis()
    gate = IdempotencyGate(valkey_client=redis, now_provider=_fixed_now)
    result = await gate.check_and_claim(source="slack:#ceo", content="hello")
    assert result.decision == IdempotencyDecision.SPAWN_OK
    assert len(redis.set_calls) == 1
    call = redis.set_calls[0]
    assert call["nx"] is True
    assert call["ex"] == DEFAULT_TTL_SECONDS
    assert call["name"].startswith(IDEM_KEY_PREFIX)


@pytest.mark.asyncio
async def test_gate_rejects_zero_window_seconds():
    with pytest.raises(IdempotencyError, match="window_seconds must be > 0"):
        IdempotencyGate(valkey_client=_FakeRedis(), window_seconds=0)


@pytest.mark.asyncio
async def test_gate_rejects_zero_ttl_seconds():
    with pytest.raises(IdempotencyError, match="ttl_seconds must be > 0"):
        IdempotencyGate(valkey_client=_FakeRedis(), ttl_seconds=0)


# ────────────────────────────────────────────────────────────────────────────
# Acceptance (3) — dispatch dropped with log when key already present
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_and_claim_drops_duplicate_when_key_present():
    redis = _FakeRedis()
    # Pre-seed the key as if a prior dispatch already claimed it
    expected_key, _ = compute_idempotency_key("slack:#ceo", "hello", now=_fixed_now())
    redis.add_existing(expected_key)

    captured_logs: list[dict] = []
    gate = IdempotencyGate(
        valkey_client=redis,
        now_provider=_fixed_now,
        log_emitter=captured_logs.append,
    )
    result = await gate.check_and_claim(source="slack:#ceo", content="hello")
    assert result.decision == IdempotencyDecision.DROP_DUPLICATE
    assert "duplicate within window" in result.reason
    # Log was emitted
    assert len(captured_logs) == 1
    assert captured_logs[0]["kind"] == "idempotency_drop_duplicate"
    assert captured_logs[0]["key"] == expected_key
    assert captured_logs[0]["source"] == "slack:#ceo"


@pytest.mark.asyncio
async def test_log_emit_failure_does_not_block_decision():
    """Log emitter raising must not block the DROP_DUPLICATE return."""
    redis = _FakeRedis()
    expected_key, _ = compute_idempotency_key("s", "c", now=_fixed_now())
    redis.add_existing(expected_key)

    def _raising_emit(payload):
        raise RuntimeError("simulated log channel down")

    gate = IdempotencyGate(
        valkey_client=redis,
        now_provider=_fixed_now,
        log_emitter=_raising_emit,
    )
    result = await gate.check_and_claim(source="s", content="c")
    # Decision still returned despite emit failure
    assert result.decision == IdempotencyDecision.DROP_DUPLICATE


# ────────────────────────────────────────────────────────────────────────────
# Acceptance (4) — verbatim test showing double-dispatch dedupes to single spawn
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_double_dispatch_dedupes_to_single_spawn():
    """The canonical end-to-end test per acceptance criterion (4).

    Two consecutive dispatches with the same (source, content) within the
    60-second window → first returns SPAWN_OK, second returns DROP_DUPLICATE.
    Verbatim:
      - call 1: dispatch arrives → check_and_claim → SPAWN_OK → spawn fires
      - call 2: identical retry within window → check_and_claim → DROP_DUPLICATE
                → spawn does NOT fire
    """
    redis = _FakeRedis()
    captured_logs: list[dict] = []
    gate = IdempotencyGate(
        valkey_client=redis,
        now_provider=_fixed_now,
        log_emitter=captured_logs.append,
    )

    # Dispatch 1 — webhook fires.
    result1 = await gate.check_and_claim(
        source="slack:#ceo:U091TGTPB9U",
        content="Dispatch: build the Atlas review fix",
    )
    assert result1.decision == IdempotencyDecision.SPAWN_OK

    # Dispatch 2 — webhook retry fires the SAME payload within 60s.
    # (Slack often retries within 30s of a delayed 200.)
    result2 = await gate.check_and_claim(
        source="slack:#ceo:U091TGTPB9U",
        content="Dispatch: build the Atlas review fix",
    )
    assert result2.decision == IdempotencyDecision.DROP_DUPLICATE
    assert result2.key == result1.key  # same key, same window

    # Drop was logged
    assert len(captured_logs) == 1
    assert captured_logs[0]["kind"] == "idempotency_drop_duplicate"

    # Net: only ONE Valkey SET call was made
    # (first is the claim; second is also a SET but the gate returned None — counts as 2 SET calls
    # but only ONE spawn would have proceeded — the test verifies the DECISION)
    spawn_ok_count = sum(
        1 for r in [result1, result2] if r.decision == IdempotencyDecision.SPAWN_OK
    )
    assert spawn_ok_count == 1, "exactly one SPAWN_OK expected for double-dispatch dedup"


@pytest.mark.asyncio
async def test_window_boundary_resets_dedup():
    """After the 60s window expires, the same (source, content) CAN dispatch again."""
    redis = _FakeRedis()

    now_value = [_fixed_now()]

    def _now_provider():
        return now_value[0]

    gate = IdempotencyGate(valkey_client=redis, now_provider=_now_provider)

    # Dispatch 1 at t=0
    result1 = await gate.check_and_claim(source="s", content="c")
    assert result1.decision == IdempotencyDecision.SPAWN_OK

    # Move forward 61 seconds → new 60s window
    now_value[0] += 61
    result2 = await gate.check_and_claim(source="s", content="c")
    assert result2.decision == IdempotencyDecision.SPAWN_OK
    # Different keys (different window)
    assert result2.key != result1.key


# ────────────────────────────────────────────────────────────────────────────
# Fail-open — Valkey transport failures must not block dispatch
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_redis_set_failure_fails_open_to_spawn_ok():
    """ConnectionError from Valkey → SPAWN_OK (better one extra spawn than
    missed message on transient blip)."""
    redis = _FakeRedis()
    redis.fail_next_set()
    gate = IdempotencyGate(valkey_client=redis, now_provider=_fixed_now)
    result = await gate.check_and_claim(source="s", content="c")
    assert result.decision == IdempotencyDecision.SPAWN_OK
    assert "fail-open" in result.reason


# ────────────────────────────────────────────────────────────────────────────
# Result shape invariants
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_idempotency_result_exposes_key_and_window():
    redis = _FakeRedis()
    gate = IdempotencyGate(valkey_client=redis, now_provider=_fixed_now)
    result = await gate.check_and_claim(source="s", content="c")
    assert result.key.startswith(IDEM_KEY_PREFIX)
    assert result.source == "s"
    # Window start aligns with the fixed_now rounded to 60s
    expected_window = int(_fixed_now() // 60) * 60
    assert result.window_start_unix == expected_window
