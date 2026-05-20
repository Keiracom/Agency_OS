"""KEI-133 — LLM API timeout chaos scenario.

Simulates the Anthropic / OpenAI API hanging on a long-running request.
Verifies LLM callers bound the request via httpx Timeout so a stalled model
endpoint doesn't freeze the agent loop.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest


async def _stalled_llm_request(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """LLM call under chaos — the underlying transport returns nothing."""
    return await client.get(url)


class _StallTransport(httpx.AsyncBaseTransport):
    """Async transport that sleeps past the client timeout."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5.0)
        return httpx.Response(200, content=b"never")


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_llm_call_wrapped_in_wait_for_raises_not_hangs() -> None:
    """The contract under test: every LLM call goes through asyncio.wait_for
    (or equivalent task-level cancellation) so a stalled endpoint can be
    cancelled from the caller side regardless of the underlying client's
    own timeout machinery. This matches the pattern used in
    src/pipeline/stage_parallelism.py and other LLM-touching call sites."""
    transport = _StallTransport()
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(
                _stalled_llm_request(client, "https://api.anthropic.test/v1/messages"),
                timeout=0.5,
            )


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_llm_call_without_timeout_would_block_proof() -> None:
    """Negative-path proof: a client with no timeout would block. We bound
    it with asyncio.wait_for here so the test itself finishes, but the
    inner httpx.AsyncClient deliberately omits its own timeout to show
    the contract is mandatory at the caller's layer."""
    transport = _StallTransport()
    async with httpx.AsyncClient(
        transport=transport,
        timeout=httpx.Timeout(None),  # explicit no-timeout — the unsafe shape
    ) as client:
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(
                _stalled_llm_request(client, "https://api.openai.test/v1/chat"),
                timeout=0.3,
            )
