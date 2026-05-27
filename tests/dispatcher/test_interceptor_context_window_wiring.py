"""KEI-213 — context-window gate wiring tests for src.dispatcher.interceptor_proxy.

Covers the cutover-step-4.5 wiring of PR #1210 check_context_budget into
intercept_request:
  - disabled fail-open (rollout phase 1 default)
  - empty-context fail-open (body has no messages)
  - under-ceiling proceeds → forward called
  - over-ceiling REJECTED → InterceptorDecision(allowed=False, deny_context_window)
  - role derivation from body.dispatcher_role
  - body_to_context multi-message concat

bd: cutover-step-4.5-dispatcher-wiring-pr-C (KEI-213 mirror of PR #1219)
"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

import pytest

from src.dispatcher import interceptor_proxy
from src.relay.context_budget import ROLE_BUILDER, ROLE_CHAT


async def _fake_forward(_body: dict) -> dict:
    """Fake forward that returns a minimal allow-shaped response."""
    return {"usage": {"prompt_tokens": 1, "completion_tokens": 1}, "cost_cents_aud": 0}


async def _fake_insert(*_args: Any, **_kwargs: Any) -> Awaitable[None]:
    """Fake insert_fn for the _log_event sink — no-op."""
    return None  # type: ignore[return-value]


def _patch_pipeline_pass_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make governance + spend + rate checks all pass so we exercise the new gate."""
    from src.dispatcher import governance_proxy

    # interceptor_proxy imported `evaluate` by-name; patch THERE, not the source module
    monkeypatch.setattr(
        interceptor_proxy,
        "evaluate",
        lambda body: governance_proxy.ProxyDecision(allowed=True, reason=None),
    )

    async def _spend_ok(*_args: Any, **_kwargs: Any) -> tuple[bool, int]:
        return True, 0

    async def _rate_ok(*_args: Any, **_kwargs: Any) -> tuple[bool, int]:
        return True, 0

    monkeypatch.setattr(interceptor_proxy, "_check_spend_budget", _spend_ok)
    monkeypatch.setattr(interceptor_proxy, "_check_rate_limit", _rate_ok)


# ----- disabled fail-open -----


@pytest.mark.asyncio
async def test_disabled_proceeds_to_forward(monkeypatch: pytest.MonkeyPatch) -> None:
    """When context_window_enabled=False, gate is bypassed."""
    _patch_pipeline_pass_through(monkeypatch)
    monkeypatch.setattr(interceptor_proxy, "context_window_enabled", False)

    body = {
        "tenant_id": "t1",
        "model": "claude",
        "messages": [{"role": "user", "content": "x" * 100_000}],  # huge — would reject
    }
    decision = await interceptor_proxy.intercept_request(
        body, forward_fn=_fake_forward, insert_fn=_fake_insert
    )
    # Gate disabled → no context-window denial.
    assert decision.allowed is True
    assert decision.decision == "allow"


# ----- empty-context fail-open -----


@pytest.mark.asyncio
async def test_empty_context_proceeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Body without messages → gate skipped, forward called."""
    _patch_pipeline_pass_through(monkeypatch)
    monkeypatch.setattr(interceptor_proxy, "context_window_enabled", True)

    body = {"tenant_id": "t1", "model": "claude"}  # no messages
    decision = await interceptor_proxy.intercept_request(
        body, forward_fn=_fake_forward, insert_fn=_fake_insert
    )
    assert decision.allowed is True
    assert decision.decision == "allow"


# ----- under-ceiling proceeds -----


@pytest.mark.asyncio
async def test_under_ceiling_proceeds_to_forward(monkeypatch: pytest.MonkeyPatch) -> None:
    """Short context → SPAWN_OK → forward called."""
    _patch_pipeline_pass_through(monkeypatch)
    monkeypatch.setattr(interceptor_proxy, "context_window_enabled", True)

    body = {
        "tenant_id": "t1",
        "model": "claude",
        "dispatcher_role": ROLE_BUILDER,
        "messages": [{"role": "user", "content": "short message"}],
    }
    decision = await interceptor_proxy.intercept_request(
        body, forward_fn=_fake_forward, insert_fn=_fake_insert
    )
    assert decision.allowed is True
    assert decision.decision == "allow"


# ----- over-ceiling REJECTED -----


@pytest.mark.asyncio
async def test_over_ceiling_returns_deny_context_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """CHAT role ceiling 4K tokens; 60K chars > ceiling → REJECTED."""
    _patch_pipeline_pass_through(monkeypatch)
    monkeypatch.setattr(interceptor_proxy, "context_window_enabled", True)

    body = {
        "tenant_id": "t1",
        "model": "claude",
        "dispatcher_role": ROLE_CHAT,
        "messages": [{"role": "user", "content": "x" * 60_000}],
    }
    decision = await interceptor_proxy.intercept_request(
        body, forward_fn=_fake_forward, insert_fn=_fake_insert
    )
    assert decision.allowed is False
    assert decision.decision == "deny_context_window"
    assert decision.status_code == 413
    assert decision.payload is not None
    assert decision.payload["error"] == "context_window_exceeded"
    assert decision.payload["role"] == ROLE_CHAT
    assert decision.payload["initial_tokens"] > decision.payload["ceiling_tokens"]


# ----- role derivation -----


@pytest.mark.parametrize(
    "body,expected_role",
    [
        ({"dispatcher_role": "reviewer"}, "reviewer"),
        ({"dispatcher_role": "deliberator"}, "deliberator"),
        ({"dispatcher_role": "builder"}, "builder"),
        ({"dispatcher_role": "chat"}, "chat"),
        ({"dispatcher_role": "bogus"}, ROLE_BUILDER),
        ({}, ROLE_BUILDER),
    ],
)
def test_body_to_role(body: dict, expected_role: str) -> None:
    assert interceptor_proxy._body_to_role(body) == expected_role


# ----- body_to_context concat -----


def test_body_to_context_multi_message() -> None:
    body = {
        "messages": [
            {"role": "system", "content": "S"},
            {"role": "user", "content": "U"},
            {"role": "assistant", "content": "A"},
        ]
    }
    result = interceptor_proxy._body_to_context(body)
    assert "system: S" in result
    assert "user: U" in result
    assert "assistant: A" in result


def test_body_to_context_empty() -> None:
    assert interceptor_proxy._body_to_context({}) == ""
    assert interceptor_proxy._body_to_context({"messages": []}) == ""
    assert interceptor_proxy._body_to_context({"messages": "not-a-list"}) == ""


def test_body_to_context_multimodal_blocks() -> None:
    """OpenAI multimodal: content is a list of blocks; gate pulls text fields."""
    body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "block 1"},
                    {"type": "text", "text": "block 2"},
                    {"type": "image_url", "image_url": "https://x"},  # no text → skipped
                ],
            }
        ]
    }
    result = interceptor_proxy._body_to_context(body)
    assert "user: block 1" in result
    assert "user: block 2" in result
