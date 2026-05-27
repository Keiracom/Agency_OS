"""idempotency — dispatcher-level dedup gate (Agency_OS-6c2k).

Cutover-blocker 5 / Viktor lever 26 (Cat 21) per Dave directive 2026-05-27.
Prevents double-execution on Slack webhook retries + transient retry-storms.

ALGORITHM:
  idempotency_key = sha256-prefix(source + content + time_window_60s_rounded)
  → Valkey SET NX EX with 5-minute TTL
  → if SET returned None (key already present): drop dispatch + log
  → if SET returned OK: spawn proceeds

The 60-second time window is wide enough to absorb retry storms (Slack
typically retries within 30s; the post-OK-200 confirmation often arrives
twice within seconds) but narrow enough that legitimate intentional resends
("hey try again") aren't deduplicated.

The 5-minute TTL is wide enough to absorb the SLACK_RETRY_TIMEOUT_SECONDS
(currently 3 min) + a safety margin. After TTL expires, the same
(source, content) tuple can be sent again — that's CORRECT behavior, not
a bug; permanent dedup would block legitimate re-sends.

DI: caller passes an async Redis client implementing the SET command. Use
existing `src/dispatcher/valkey_pool.get_valkey_client()` in production;
fakes inject in tests.

KEY NAMESPACE (extends valkey_pool.py's documented contract):
  idem:<sha256-prefix-16chars>

`idem:` slots alongside `rl:` (rate-limit, KEI-117), `q:` (queues, future),
`ses:` (sessions, future).
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

log = logging.getLogger(__name__)

# Dispatch defaults — per dispatch.
DEFAULT_WINDOW_SECONDS: int = 60
DEFAULT_TTL_SECONDS: int = 300  # 5 minutes per dispatch
IDEM_KEY_PREFIX: str = "idem:"
KEY_HASH_LENGTH: int = 16  # sha256 prefix bytes (16 hex chars = 64 bits)


class IdempotencyDecision(Enum):
    """Decision returned by the gate. Caller acts on this."""

    SPAWN_OK = "spawn_ok"
    DROP_DUPLICATE = "drop_duplicate"  # key was already present → already-dispatched


@dataclass(frozen=True, kw_only=True)
class IdempotencyResult:
    """Caller acts on this; the key is exposed for log + audit purposes."""

    decision: IdempotencyDecision
    key: str
    source: str
    window_start_unix: int
    reason: str = ""


class IdempotencyError(RuntimeError):
    """Raised on invalid input only — Redis errors fail-open by design."""


class _RedisProtocol(Protocol):
    """Subset of redis.asyncio.Redis we depend on for the gate.

    `set` with `nx=True, ex=<int>` returns None when the key already exists,
    truthy (typically True) when the SET succeeded.
    """

    def set(
        self,
        name: str,
        value: str,
        *,
        nx: bool = False,
        ex: int | None = None,
    ) -> Awaitable[Any]: ...


# Emitter signature — caller hooks alerts/logs via this.
LogEmitter = Callable[[dict[str, Any]], None]


def compute_idempotency_key(
    source: str,
    content: str,
    *,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    now: float | None = None,
) -> tuple[str, int]:
    """Compute the deterministic idempotency key for a (source, content) tuple.

    Returns (key, window_start_unix). The key is `idem:<sha256-prefix-16>`.
    The window_start_unix is exposed for log payloads.

    Algorithm:
      1. Compute rounded window: `floor(ts / window_seconds) * window_seconds`
      2. Hash `source|content|window` via SHA-256
      3. Prefix-truncate to 16 hex chars (64 bits — collision probability
         ~1 in 2^32 across simultaneous dispatches in a 60-second window,
         vanishingly small at fleet scale)
    """
    if not source:
        raise IdempotencyError("source must be non-empty")
    if not content:
        raise IdempotencyError("content must be non-empty")
    if window_seconds <= 0:
        raise IdempotencyError(f"window_seconds must be > 0; got {window_seconds}")
    ts = now if now is not None else time.time()
    window_start = (int(ts) // window_seconds) * window_seconds
    payload = f"{source}|{content}|{window_start}".encode()
    digest = hashlib.sha256(payload).hexdigest()[:KEY_HASH_LENGTH]
    return f"{IDEM_KEY_PREFIX}{digest}", window_start


def _default_log_emitter(payload: dict[str, Any]) -> None:
    """Default emitter — log at INFO. Caller wires Better Stack / JSONL via DI."""
    log.info("idempotency-gate: %s", payload)


class IdempotencyGate:
    """Dispatcher pre-spawn dedup gate.

    Caller invokes `check_and_claim(...)` BEFORE every spawn. If the returned
    decision is `SPAWN_OK`, proceed with the dispatch. If `DROP_DUPLICATE`,
    drop silently (one log emitted via the injected emitter).

    Fail-open by design: Redis transport failure → SPAWN_OK (returning
    DROP_DUPLICATE on a transient Valkey blip would block legitimate
    dispatches; better one extra spawn than a missed message).
    """

    def __init__(
        self,
        *,
        valkey_client: _RedisProtocol,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        log_emitter: LogEmitter | None = None,
        now_provider: Callable[[], float] | None = None,
    ):
        if window_seconds <= 0:
            raise IdempotencyError(f"window_seconds must be > 0; got {window_seconds}")
        if ttl_seconds <= 0:
            raise IdempotencyError(f"ttl_seconds must be > 0; got {ttl_seconds}")
        self._client = valkey_client
        self._window_seconds = window_seconds
        self._ttl_seconds = ttl_seconds
        self._log = log_emitter or _default_log_emitter
        self._now = now_provider or time.time

    @property
    def window_seconds(self) -> int:
        return self._window_seconds

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    async def check_and_claim(
        self,
        *,
        source: str,
        content: str,
    ) -> IdempotencyResult:
        """Pre-spawn dedup gate.

        Computes the deterministic key + attempts a Valkey SET NX EX. Returns
        SPAWN_OK on successful claim (no prior dispatch in window), or
        DROP_DUPLICATE when the key was already present (already dispatched
        within the 60-second window).

        Fail-open on Redis errors — returns SPAWN_OK so transient Valkey
        outages don't block dispatch.
        """
        key, window_start = compute_idempotency_key(
            source,
            content,
            window_seconds=self._window_seconds,
            now=self._now(),
        )
        try:
            # SET NX EX: returns truthy on successful new claim, None when key exists.
            set_result = await self._client.set(key, "1", nx=True, ex=self._ttl_seconds)
        except Exception:  # noqa: BLE001 — fail-open per design
            log.exception("idempotency-gate: Valkey SET NX failed; failing open")
            return IdempotencyResult(
                decision=IdempotencyDecision.SPAWN_OK,
                key=key,
                source=source,
                window_start_unix=window_start,
                reason="valkey unreachable — fail-open SPAWN_OK",
            )

        if set_result:
            return IdempotencyResult(
                decision=IdempotencyDecision.SPAWN_OK,
                key=key,
                source=source,
                window_start_unix=window_start,
                reason="claimed (no prior dispatch in window)",
            )

        # set_result is None → key already exists → already dispatched.
        try:
            self._log(
                {
                    "kind": "idempotency_drop_duplicate",
                    "key": key,
                    "source": source,
                    "window_start_unix": window_start,
                    "window_seconds": self._window_seconds,
                    "ttl_seconds": self._ttl_seconds,
                }
            )
        except Exception:  # noqa: BLE001 — log failure must not block
            log.exception("idempotency-gate: log emit failed (non-blocking)")
        return IdempotencyResult(
            decision=IdempotencyDecision.DROP_DUPLICATE,
            key=key,
            source=source,
            window_start_unix=window_start,
            reason="duplicate within window — already dispatched",
        )
