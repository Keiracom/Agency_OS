"""KEI-133 — Network partition chaos scenario.

Simulates a network partition: the remote endpoint is unreachable. socket
errors propagate from the transport layer as `ConnectionRefusedError` or
`ConnectionError`. The contract: services that depend on external endpoints
(NATS, Supabase, Slack, Weaviate, Linear) must catch the connection error
and report it via the agreed channel — not crash the calling agent.
"""

from __future__ import annotations

import pytest


def _attempt_external_call_with_circuit_break(
    call_fn,
    on_failure_fn,
) -> bool:
    """Canonical contract for any external-service call:
    1. Run the call.
    2. On ConnectionError (transport layer) — report via on_failure_fn,
       return False, do NOT propagate.
    3. On unexpected exception — re-raise (don't mask real bugs).

    Returns True iff the call succeeded.
    """
    try:
        call_fn()
        return True
    except (ConnectionRefusedError, ConnectionError) as exc:
        on_failure_fn(repr(exc))
        return False


@pytest.mark.timeout(10)
def test_connection_refused_is_reported_not_raised() -> None:
    """Partition simulated by raising ConnectionRefusedError. The contract
    catches it, reports via the failure handler, returns False — caller
    does not crash."""
    failures_seen: list[str] = []

    def fake_call() -> None:
        raise ConnectionRefusedError("network unreachable (simulated)")

    ok = _attempt_external_call_with_circuit_break(fake_call, failures_seen.append)

    assert ok is False
    assert len(failures_seen) == 1
    assert "network unreachable" in failures_seen[0]


@pytest.mark.timeout(10)
def test_generic_connection_error_also_caught() -> None:
    """ConnectionError parent class catches socket-level errors that don't
    raise the narrower ConnectionRefusedError (e.g. DNS resolve failures,
    SSL handshake failures, route to host failures)."""
    failures_seen: list[str] = []

    def fake_call() -> None:
        raise ConnectionError("no route to host (simulated)")

    ok = _attempt_external_call_with_circuit_break(fake_call, failures_seen.append)

    assert ok is False
    assert "no route to host" in failures_seen[0]


@pytest.mark.timeout(10)
def test_unexpected_exception_still_propagates() -> None:
    """Negative-path: a non-network exception (e.g. AttributeError on a
    typo) must propagate so the bug surfaces — circuit breaker only
    swallows transport-layer failures, not logic errors."""

    def fake_call() -> None:
        raise AttributeError("typo in call signature — real bug")

    with pytest.raises(AttributeError, match="typo in call signature"):
        _attempt_external_call_with_circuit_break(fake_call, lambda _: None)
