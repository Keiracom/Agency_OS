"""
Contract: src/outreach/safety/send_pacer.py
Purpose:  Per-send jitter engine — randomises inter-send gaps per account/channel
          to break regular cadence patterns that trigger provider bot-detection.
Layer:    3 - engines
Imports:  stdlib only
Consumers: src/outreach/dispatcher.py, outreach orchestration flows

For each send, compute_delay() returns the seconds the caller should sleep before
the next outgoing message.  Voice is serialised globally (one active call at a
time across all accounts).  All other channels are per-account independent.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from src.outreach.safety.timing_engine import Channel


@dataclass
class PacerConfig:
    min_seconds: float
    max_seconds: float
    serialised: bool = False  # Voice: only one send at a time, regardless of account


DEFAULT_CONFIGS: dict[Channel, PacerConfig] = {
    Channel.LINKEDIN: PacerConfig(min_seconds=120, max_seconds=480),
    Channel.EMAIL: PacerConfig(min_seconds=30, max_seconds=90),
    Channel.VOICE: PacerConfig(min_seconds=30, max_seconds=60, serialised=True),
    Channel.SMS: PacerConfig(min_seconds=2, max_seconds=5),
}


class SendPacer:
    """Compute per-send jitter delay to break regular cadence patterns.

    Usage:
        pacer = SendPacer()
        delay = pacer.compute_delay(Channel.EMAIL, account_id="mailbox-1",
                                    last_send_at=datetime.utcnow() - timedelta(seconds=10))
        await asyncio.sleep(delay)

    Deterministic-random: when `rng_seed` is provided, delays are reproducible
    for tests.  Otherwise uses the system RNG.
    """

    _last_voice_send: datetime | None = None  # class-level voice serialisation lock

    def __init__(
        self,
        configs: dict[Channel, PacerConfig] | None = None,
        rng_seed: int | None = None,
        now_fn: Callable[[], datetime] = lambda: datetime.utcnow(),
    ) -> None:
        self._configs = configs if configs is not None else dict(DEFAULT_CONFIGS)
        self._rng = random.Random(rng_seed)
        self._now_fn = now_fn
        # Per-instance voice tracker (shadows class attr so tests stay isolated)
        self._last_voice_send: datetime | None = None  # type: ignore[assignment]
        # Per-account send tracker (optional, used by record_send for non-voice)
        self._last_send: dict[tuple[Channel, str], datetime] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_delay(
        self,
        channel: Channel,
        account_id: str,
        last_send_at: datetime | None = None,
    ) -> float:
        """Return seconds to wait before the next send."""
        cfg = self._configs[channel]
        now = self._now_fn()

        # Voice uses the instance-level voice tracker; ignore account_id
        if cfg.serialised:
            effective_last = self._last_voice_send
        else:
            effective_last = last_send_at or self._last_send.get((channel, account_id))

        return self._calculate(cfg, effective_last, now)

    def record_send(
        self,
        channel: Channel,
        account_id: str,
        at: datetime | None = None,
    ) -> None:
        """Record completion time of a send for future compute_delay calls."""
        ts = at or self._now_fn()
        cfg = self._configs[channel]
        if cfg.serialised:
            self._last_voice_send = ts
        else:
            self._last_send[(channel, account_id)] = ts

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calculate(
        self,
        cfg: PacerConfig,
        last_send_at: datetime | None,
        now: datetime,
    ) -> float:
        """Core delay arithmetic — kept small so each branch is readable."""
        base = self._rng.uniform(cfg.min_seconds, cfg.max_seconds)

        if last_send_at is None:
            return base

        elapsed = (now - last_send_at).total_seconds()

        # Already waited long enough — no enforced delay
        if elapsed >= cfg.min_seconds:
            return 0.0

        # Partially elapsed: reduce base by what has already passed
        remaining = base - elapsed
        return max(0.0, remaining)
