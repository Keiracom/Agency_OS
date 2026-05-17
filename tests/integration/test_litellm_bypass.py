"""
KEI-100 / Linear KEI-73 — T0.2 LiteLLM direct-provider bypass integration test.

Demonstrates the failure mode T0.1 Dispatcher (Elliot) will consume:
  1. LiteLLM proxy down → 127.0.0.1:4000 unreachable
  2. Caller logs marker `INTERCEPTOR_DEGRADED` to stdout
  3. Caller falls back to direct anthropic.messages.create()
  4. Proxy restarted → normal path resumes

The PERMANENT fallback wiring belongs to Dispatcher's interceptor_proxy.ts
(per Aiden gap 5 resolution). This test only proves the failure mode + log marker.

Gated by LITELLM_INTEGRATION_TEST=1 (CI skips by default — runs only on Vultr host
where systemctl --user can stop/start litellm.service).
"""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import time

import pytest

DEGRADED_MARKER = "INTERCEPTOR_DEGRADED"
LITELLM_HOST = "127.0.0.1"
LITELLM_PORT = 4000

_INTEGRATION = os.environ.get("LITELLM_INTEGRATION_TEST") == "1"
pytestmark = pytest.mark.skipif(
    not _INTEGRATION,
    reason="Integration test — set LITELLM_INTEGRATION_TEST=1 on Vultr host to run",
)


def _proxy_reachable(
    host: str = LITELLM_HOST, port: int = LITELLM_PORT, timeout: float = 1.0
) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _systemctl(action: str, unit: str = "litellm.service") -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", "--user", action, unit],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def call_with_bypass(prompt: str, logger: logging.Logger) -> str:
    """The pattern T0.1 Dispatcher consumes: try proxy → on failure, log marker + direct call."""
    if _proxy_reachable():
        # Normal path would go through proxy here. Stubbed for test focus on bypass.
        return f"PROXY_PATH: {prompt[:20]}"

    logger.warning(DEGRADED_MARKER)

    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}],
    )
    return f"DIRECT_PATH: {msg.content[0].text[:50]}"


@pytest.fixture
def restart_litellm():
    """Ensure litellm restored even on test failure."""
    yield
    _systemctl("start")
    for _ in range(15):
        if _proxy_reachable():
            return
        time.sleep(1)


def test_bypass_flow(caplog, restart_litellm):
    """Stop litellm → INTERCEPTOR_DEGRADED logged → direct anthropic call succeeds → restart → normal."""
    caplog.set_level(logging.WARNING)
    logger = logging.getLogger("test_litellm_bypass")

    # 1. Stop proxy
    stop = _systemctl("stop")
    assert stop.returncode == 0, f"stop failed: {stop.stderr}"
    for _ in range(10):
        if not _proxy_reachable():
            break
        time.sleep(0.5)
    assert not _proxy_reachable(), "litellm still reachable after stop"

    # 2. Caller detects down → logs marker → falls back
    result = call_with_bypass("Reply with the single word PONG.", logger)
    assert result.startswith("DIRECT_PATH:"), f"expected DIRECT_PATH, got {result}"
    assert any(DEGRADED_MARKER in r.message for r in caplog.records), (
        f"INTERCEPTOR_DEGRADED not in logs: {[r.message for r in caplog.records]}"
    )

    # 3. Restart proxy
    start = _systemctl("start")
    assert start.returncode == 0, f"start failed: {start.stderr}"
    for _ in range(15):
        if _proxy_reachable():
            break
        time.sleep(1)
    assert _proxy_reachable(), "litellm did not come back up"

    # 4. Normal path resumes
    result = call_with_bypass("Reply with the single word PONG.", logger)
    assert result.startswith("PROXY_PATH:"), f"expected PROXY_PATH, got {result}"
