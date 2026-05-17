"""KEI-115E — tests for src/dispatcher/llm_router.

All HTTP is mocked at the _post_json helper boundary; no live LiteLLM
required. Backoff sleeps are also patched to zero so the test suite
doesn't actually wait through the retry ladder.
"""

from __future__ import annotations

import pytest

from src.dispatcher import llm_router
from src.dispatcher.llm_router import (
    CostEvent,
    LiteLLMRateLimitExhaustedError,
    LiteLLMRouterError,
    forward,
)


def _ok_payload(model: str = "claude-sonnet-4-6", in_tok: int = 12, out_tok: int = 34):
    return {
        "model": model,
        "usage": {"prompt_tokens": in_tok, "completion_tokens": out_tok},
        "response_cost": 0.000123,
        "choices": [{"message": {"role": "assistant", "content": "ok"}}],
    }


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Backoff sleeps are tested via the retry_count assertion, not by
    actually waiting — patch time.sleep to a no-op so the suite is fast."""
    monkeypatch.setattr(llm_router.time, "sleep", lambda _s: None)


# ─── happy path ────────────────────────────────────────────────────────────


def test_forward_returns_response_body_on_first_2xx(monkeypatch):
    """A clean 200 path returns the parsed body and never retries."""
    calls = {"n": 0}

    def fake_post(url, body, timeout_s):
        calls["n"] += 1
        return 200, _ok_payload()

    monkeypatch.setattr(llm_router, "_post_json", fake_post)
    out = forward(body={"model": "x"}, customer_id="c1", task_id="KEI-166")
    assert out["choices"][0]["message"]["content"] == "ok"
    assert calls["n"] == 1


def test_forward_invokes_cost_sink_with_event_shape(monkeypatch):
    """cost_sink receives a CostEvent with every documented field set."""
    monkeypatch.setattr(
        llm_router,
        "_post_json",
        lambda url, body, timeout_s: (200, _ok_payload(in_tok=10, out_tok=20)),
    )
    events: list[CostEvent] = []
    forward(
        body={},
        customer_id="cust-1",
        task_id="KEI-166",
        cost_sink=events.append,
    )
    assert len(events) == 1
    ev = events[0]
    assert ev.customer_id == "cust-1"
    assert ev.task_id == "KEI-166"
    assert ev.model == "claude-sonnet-4-6"
    assert ev.input_tokens == 10
    assert ev.output_tokens == 20
    assert ev.cost_aud == pytest.approx(0.000123)
    assert ev.retry_count == 0
    assert ev.success is True
    assert ev.error_message is None
    assert ev.duration_ms >= 0


def test_forward_no_sink_does_not_raise(monkeypatch):
    """cost_sink=None is a valid configuration — router must not require it."""
    monkeypatch.setattr(llm_router, "_post_json", lambda url, body, timeout_s: (200, _ok_payload()))
    # Should not raise:
    forward(body={}, customer_id="c", task_id="t", cost_sink=None)


# ─── 429 retry ─────────────────────────────────────────────────────────────


def test_forward_retries_on_429_then_succeeds(monkeypatch):
    """429 twice then 200 — router transparently retries and reports
    retry_count=2 on the success cost event."""
    responses = iter(
        [(429, {"error": "rate_limited"}), (429, {"error": "rate_limited"}), (200, _ok_payload())]
    )

    def fake_post(url, body, timeout_s):
        return next(responses)

    monkeypatch.setattr(llm_router, "_post_json", fake_post)
    events: list[CostEvent] = []
    out = forward(
        body={},
        customer_id="c",
        task_id="t",
        max_retries=3,
        cost_sink=events.append,
    )
    assert out["choices"][0]["message"]["content"] == "ok"
    assert events[0].retry_count == 2
    assert events[0].success is True


def test_forward_raises_rate_limit_exhausted_after_max_retries(monkeypatch):
    """Persistent 429 — raises LiteLLMRateLimitExhaustedError and emits a
    failure cost event with retry_count=max_retries."""
    monkeypatch.setattr(
        llm_router,
        "_post_json",
        lambda url, body, timeout_s: (429, {"error": "tier_limit"}),
    )
    events: list[CostEvent] = []
    with pytest.raises(LiteLLMRateLimitExhaustedError, match="after 3 retries"):
        forward(
            body={},
            customer_id="c",
            task_id="t",
            max_retries=3,
            cost_sink=events.append,
        )
    assert len(events) == 1
    assert events[0].success is False
    assert events[0].retry_count == 3
    assert events[0].error_message is not None
    assert "tier_limit" in events[0].error_message


# ─── non-2xx non-429 ───────────────────────────────────────────────────────


def test_forward_raises_router_error_on_500(monkeypatch):
    """5xx is non-retryable here (LiteLLM owns upstream retries); router
    fails the request immediately and emits a failure cost event."""
    monkeypatch.setattr(
        llm_router,
        "_post_json",
        lambda url, body, timeout_s: (500, {"error": "upstream"}),
    )
    events: list[CostEvent] = []
    with pytest.raises(LiteLLMRouterError, match="status 500"):
        forward(body={}, customer_id="c", task_id="t", cost_sink=events.append)
    assert len(events) == 1
    assert events[0].success is False
    assert events[0].retry_count == 0


def test_forward_propagates_transport_error_from_helper(monkeypatch):
    """_post_json raising LiteLLMRouterError (e.g. DNS / refused) surfaces
    to the caller; no cost event is emitted because we never got a response."""

    def boom(url, body, timeout_s):
        raise LiteLLMRouterError("transport: connection refused")

    monkeypatch.setattr(llm_router, "_post_json", boom)
    events: list[CostEvent] = []
    with pytest.raises(LiteLLMRouterError, match="connection refused"):
        forward(body={}, customer_id="c", task_id="t", cost_sink=events.append)
    assert events == []


# ─── cost-sink isolation ───────────────────────────────────────────────────


def test_cost_sink_exception_does_not_break_forwarding(monkeypatch, caplog):
    """A buggy cost_sink must not prevent the caller from receiving the
    successful response — ledger writes are a side-channel, not load-bearing."""
    monkeypatch.setattr(llm_router, "_post_json", lambda url, body, timeout_s: (200, _ok_payload()))

    def explode(_event):
        raise RuntimeError("ledger DB down")

    with caplog.at_level("WARNING"):
        out = forward(body={}, customer_id="c", task_id="t", cost_sink=explode)
    assert out["choices"][0]["message"]["content"] == "ok"
    assert any("ledger DB down" in r.message for r in caplog.records)


# ─── usage extraction edge cases ───────────────────────────────────────────


def test_forward_handles_missing_usage_block(monkeypatch):
    """A response without ``usage`` (or with partial fields) still produces
    a CostEvent — tokens default to 0, cost defaults to 0.0."""
    payload = {"model": "x", "choices": [{"message": {"role": "assistant", "content": "hi"}}]}
    monkeypatch.setattr(llm_router, "_post_json", lambda url, body, timeout_s: (200, payload))
    events: list[CostEvent] = []
    forward(body={}, customer_id="c", task_id="t", cost_sink=events.append)
    assert events[0].input_tokens == 0
    assert events[0].output_tokens == 0
    assert events[0].cost_aud == pytest.approx(0.0)
    assert events[0].model == "x"


def test_forward_handles_missing_model(monkeypatch):
    """A response without ``model`` — CostEvent.model falls back to 'unknown'
    so the ledger writer never sees None in a NOT NULL column."""
    payload = {"usage": {"prompt_tokens": 1, "completion_tokens": 2}}
    monkeypatch.setattr(llm_router, "_post_json", lambda url, body, timeout_s: (200, payload))
    events: list[CostEvent] = []
    forward(body={}, customer_id="c", task_id="t", cost_sink=events.append)
    assert events[0].model == "unknown"
