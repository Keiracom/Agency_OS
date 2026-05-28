"""Interceptor-side bounded-spawn hook tests (Agency_OS-gcpm / Audit RED-7).

Covers the per-model-call gate in src.dispatcher.interceptor_proxy that consults
the BoundedSpawnEnforcer via the injected accessor. Body must carry both
``bounded_spawn_callsign`` and ``bounded_spawn_task_id`` for the gate to fire.

Borrows the FakeValkey stub pattern from test_interceptor_proxy.py.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import src.dispatcher.interceptor_proxy as ip
from src.dispatcher.bounded_spawn_enforcer import BoundedSpawnEnforcer


class _FakeValkey:
    """Minimal in-memory async stub matching the subset of redis we touch."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        v = self.store.get(key)
        return str(v) if v is not None else None

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def incrby(self, key: str, amount: int) -> int:
        self.store[key] = self.store.get(key, 0) + amount
        return self.store[key]

    async def expire(self, key: str, _ttl: int) -> bool:
        return True

    async def aclose(self) -> None:
        return None


@pytest.fixture
def fake_valkey(monkeypatch: pytest.MonkeyPatch) -> _FakeValkey:
    fake = _FakeValkey()
    monkeypatch.setattr(ip, "get_valkey_client", lambda: fake)
    return fake


def _make_enforcer(tmp_path: Path) -> BoundedSpawnEnforcer:
    return BoundedSpawnEnforcer(
        terminate_cb=MagicMock(return_value=True),
        alerts_emitter=MagicMock(),
        audit_log_path=tmp_path / "v.jsonl",
    )


def _valid_body(**extra: object) -> dict:
    body: dict = {
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "prompt": "noop prompt",
        "max_tokens": 16,
        "model": "claude-sonnet-4-6",
        "tier": "starter",
    }
    body.update(extra)
    return body


async def _fake_forward(_body: dict) -> dict:
    return {"id": "resp-1", "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


async def _no_insert(_row: dict) -> None:
    return None


# ---------- no accessor wired = fail-open ----------


@pytest.mark.asyncio
async def test_no_accessor_means_hook_is_noop(fake_valkey: _FakeValkey) -> None:
    ip.set_bounded_spawn_enforcer_accessor(None)
    body = _valid_body(bounded_spawn_callsign="orion", bounded_spawn_task_id="t-different")
    decision = await ip.intercept_request(body, forward_fn=_fake_forward, insert_fn=_no_insert)
    assert decision.allowed is True
    assert decision.decision == "allow"


# ---------- missing metadata = no-op even with accessor ----------


@pytest.mark.asyncio
async def test_missing_metadata_means_hook_is_noop(
    fake_valkey: _FakeValkey, tmp_path: Path
) -> None:
    enforcer = _make_enforcer(tmp_path)
    enforcer.record_spawn(key="k1", callsign="orion", task_id="t-current", backend="tmux")
    ip.set_bounded_spawn_enforcer_accessor(lambda: enforcer)

    try:
        body = _valid_body()  # no bounded_spawn_* fields
        decision = await ip.intercept_request(body, forward_fn=_fake_forward, insert_fn=_no_insert)
        assert decision.allowed is True
        assert decision.decision == "allow"
    finally:
        ip.set_bounded_spawn_enforcer_accessor(None)


# ---------- matching metadata = allow ----------


@pytest.mark.asyncio
async def test_matching_metadata_allows(fake_valkey: _FakeValkey, tmp_path: Path) -> None:
    enforcer = _make_enforcer(tmp_path)
    enforcer.record_spawn(key="k1", callsign="orion", task_id="t-current", backend="tmux")
    ip.set_bounded_spawn_enforcer_accessor(lambda: enforcer)

    try:
        body = _valid_body(bounded_spawn_callsign="orion", bounded_spawn_task_id="t-current")
        decision = await ip.intercept_request(body, forward_fn=_fake_forward, insert_fn=_no_insert)
        assert decision.allowed is True
    finally:
        ip.set_bounded_spawn_enforcer_accessor(None)


# ---------- mismatched metadata = deny ----------


@pytest.mark.asyncio
async def test_mismatched_task_id_returns_409(fake_valkey: _FakeValkey, tmp_path: Path) -> None:
    enforcer = _make_enforcer(tmp_path)
    enforcer.record_spawn(key="k1", callsign="orion", task_id="t-current", backend="tmux")
    ip.set_bounded_spawn_enforcer_accessor(lambda: enforcer)

    try:
        # Body claims to be from task t-OLD — that's a violator (orphaned) spawn.
        body = _valid_body(bounded_spawn_callsign="orion", bounded_spawn_task_id="t-OLD")

        forward_called = MagicMock()

        async def _no_forward(_b: dict) -> dict:
            forward_called()
            return {"ok": True}

        decision = await ip.intercept_request(body, forward_fn=_no_forward, insert_fn=_no_insert)
        assert decision.allowed is False
        assert decision.decision == "deny_bounded_spawn"
        assert decision.status_code == 409
        assert "bounded_spawn_violator" in (decision.reason or "")
        forward_called.assert_not_called()
    finally:
        ip.set_bounded_spawn_enforcer_accessor(None)


# ---------- accessor raising = fail-open ----------


@pytest.mark.asyncio
async def test_accessor_raising_fails_open(fake_valkey: _FakeValkey) -> None:
    def _bad_accessor() -> object:
        raise RuntimeError("synthetic accessor failure")

    ip.set_bounded_spawn_enforcer_accessor(_bad_accessor)
    try:
        body = _valid_body(bounded_spawn_callsign="orion", bounded_spawn_task_id="anything")
        decision = await ip.intercept_request(body, forward_fn=_fake_forward, insert_fn=_no_insert)
        assert decision.allowed is True
    finally:
        ip.set_bounded_spawn_enforcer_accessor(None)
