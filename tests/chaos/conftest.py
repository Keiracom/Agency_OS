"""tests/chaos — chaos-engineering harness for Agency OS.

KEI-132 (framework + DB-timeout scenario) and KEI-133 (4 additional scenarios:
LLM API timeout, Slack API 429, network partition, Postgres OOM).

Acceptance from KEI-132/133:
- All 5 scenarios run in <60s in CI.
- Each scenario simulates a failure mode and asserts the system handles it
  correctly (timeout, retry, backoff, graceful degradation — not a crash).
- CI is blocked on chaos test failure (no `|| true` — runs under the main
  pytest job; KEI-222 made pytest a hard gate).

Design notes:
- Scenarios are self-contained: they mock the dependency at the boundary
  (psycopg/httpx/socket) rather than spinning up real failing infra. Mocks
  let the harness run in <1s per scenario instead of 5s+ for real latency.
- pytest-timeout enforces the 60s cap as a backstop — if a scenario regresses
  and starts hanging, the timeout fires and CI fails red.
- Each scenario verifies BOTH the simulated failure shape AND the caller's
  handling (raises a specific exception, retries N times, etc.) so the test
  is meaningful, not just "the mock returned what we told it to return".
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def chaos_scenario_timeout(request):
    """Backstop timeout for every chaos test. Per-test `@pytest.mark.timeout(N)`
    overrides this; an unmarked scenario gets the 30s default which leaves
    headroom under the 60s acceptance ceiling.
    """
    marker = request.node.get_closest_marker("timeout")
    if marker is None:
        request.node.add_marker(pytest.mark.timeout(30))
    yield
