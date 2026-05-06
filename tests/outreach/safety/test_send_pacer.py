"""
Tests for src/outreach/safety/send_pacer.py

Coverage targets:
    1.  LinkedIn bounds
    2.  Email bounds
    3.  Voice bounds
    4.  SMS bounds
    5.  Respects last_send_at — recent (partial elapsed)
    6.  Respects last_send_at — fully elapsed (0.0 return)
    7.  Voice serialisation — different account must still wait
    8.  Voice serialisation elapsed — returns 0.0
    9.  Deterministic with seed
    10. Custom configs override defaults
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.outreach.safety.send_pacer import DEFAULT_CONFIGS, PacerConfig, SendPacer
from src.outreach.safety.timing_engine import Channel

_NOW = datetime(2026, 4, 22, 10, 0, 0)


def _pacer(seed: int = 42, now: datetime = _NOW, configs=None) -> SendPacer:
    return SendPacer(configs=configs, rng_seed=seed, now_fn=lambda: now)


# ---------------------------------------------------------------------------
# 1-4: channel bounds over 200 samples
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "channel,lo,hi",
    [
        (Channel.LINKEDIN, 120, 480),
        (Channel.EMAIL, 30, 90),
        (Channel.VOICE, 30, 60),
        (Channel.SMS, 2, 5),
    ],
)
def test_channel_bounds(channel, lo, hi):
    pacer = SendPacer(rng_seed=0, now_fn=lambda: _NOW)
    delays = [pacer.compute_delay(channel, "acct", None) for _ in range(200)]
    assert all(lo <= d <= hi for d in delays), (
        f"{channel}: some delays outside [{lo}, {hi}]: min={min(delays):.2f} max={max(delays):.2f}"
    )


# ---------------------------------------------------------------------------
# 5: recent last_send_at — partial elapsed, delay reduced not zero
# ---------------------------------------------------------------------------


def test_recent_last_send_reduces_delay():
    now = _NOW
    last_send = now - timedelta(seconds=10)
    pacer = _pacer(seed=99, now=now)
    cfg = DEFAULT_CONFIGS[Channel.EMAIL]  # min=30, max=90
    elapsed = 10.0

    delay = pacer.compute_delay(Channel.EMAIL, "box-1", last_send_at=last_send)

    # base was in [30,90]; delay = base - 10 so range is [20, 80]
    assert delay >= cfg.min_seconds - elapsed
    assert delay <= cfg.max_seconds - elapsed


# ---------------------------------------------------------------------------
# 6: fully elapsed — returns 0.0
# ---------------------------------------------------------------------------


def test_elapsed_last_send_returns_zero():
    now = _NOW
    last_send = now - timedelta(seconds=120)  # 120s ago; EMAIL min=30
    pacer = _pacer(now=now)

    delay = pacer.compute_delay(Channel.EMAIL, "box-2", last_send_at=last_send)
    assert delay == 0.0


# ---------------------------------------------------------------------------
# 7: voice serialisation — different account still waits
# ---------------------------------------------------------------------------


def test_voice_serialisation_different_account_must_wait():
    now = _NOW
    last_voice = now - timedelta(seconds=5)  # 5s ago; voice min=30
    pacer = _pacer(now=now)

    pacer.record_send(Channel.VOICE, "acct-A", at=last_voice)
    delay = pacer.compute_delay(Channel.VOICE, "acct-B", last_send_at=None)

    assert delay > 0, "Voice must serialise across all accounts"


# ---------------------------------------------------------------------------
# 8: voice serialisation elapsed — returns 0.0
# ---------------------------------------------------------------------------


def test_voice_serialisation_elapsed_returns_zero():
    now = _NOW
    last_voice = now - timedelta(seconds=120)  # 120s ago; voice min=30
    pacer = _pacer(now=now)

    pacer.record_send(Channel.VOICE, "acct-A", at=last_voice)
    delay = pacer.compute_delay(Channel.VOICE, "acct-B", last_send_at=None)

    assert delay == 0.0


# ---------------------------------------------------------------------------
# 9: deterministic with same seed
# ---------------------------------------------------------------------------


def test_deterministic_with_seed():
    p1 = _pacer(seed=7)
    p2 = _pacer(seed=7)
    d1 = [p1.compute_delay(Channel.EMAIL, "a", None) for _ in range(20)]
    d2 = [p2.compute_delay(Channel.EMAIL, "a", None) for _ in range(20)]
    assert d1 == d2


def test_different_seeds_differ():
    p1 = _pacer(seed=1)
    p2 = _pacer(seed=2)
    d1 = [p1.compute_delay(Channel.EMAIL, "a", None) for _ in range(20)]
    d2 = [p2.compute_delay(Channel.EMAIL, "a", None) for _ in range(20)]
    assert d1 != d2


# ---------------------------------------------------------------------------
# 10: custom configs override defaults
# ---------------------------------------------------------------------------


def test_custom_configs_override_defaults():
    custom = {Channel.EMAIL: PacerConfig(min_seconds=5, max_seconds=10)}
    pacer = SendPacer(configs=custom, rng_seed=0, now_fn=lambda: _NOW)

    delays = [pacer.compute_delay(Channel.EMAIL, "x", None) for _ in range(100)]
    assert all(5.0 <= d <= 10.0 for d in delays), (
        f"Custom config not respected: min={min(delays):.2f} max={max(delays):.2f}"
    )
