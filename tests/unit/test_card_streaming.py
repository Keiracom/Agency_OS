"""
Unit tests for ProspectCard streaming callback (Task 3.1).

Tests that:
  - on_card callback receives each card as it is built (before run() returns)
  - Order matches production order (first domain processed = first emitted)
  - SSECardStreamer puts serialized events onto asyncio.Queue
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.pipeline.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineResult,
    PipelineStats,
    ProspectCard,
    SSECardStreamer,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

DOMAINS = ["alpha.com.au", "beta.com.au", "gamma.com.au"]


def _make_card(domain: str) -> ProspectCard:
    return ProspectCard(
        domain=domain,
        company_name=f"Company {domain}",
        location="Sydney, NSW",
    )


def _make_fake_cards() -> list[ProspectCard]:
    return [_make_card(d) for d in DOMAINS]


def _build_orchestrator(on_card=None):
    """Build a PipelineOrchestrator with on_card wired.

    run_streaming is patched at the test level to simulate card emission —
    the legacy free_enrichment/scorer/dm_identification constructor path was
    removed in CD Player v1 (Directive #293 refactor).
    """
    return PipelineOrchestrator(
        dfs_client=MagicMock(),
        gemini_client=MagicMock(),
        on_card=on_card,
    )


async def _fake_run_streaming(self, **kwargs) -> PipelineResult:
    """Drop-in replacement for run_streaming that emits 3 cards via on_card."""
    cards = _make_fake_cards()
    for card in cards:
        if self._on_card is not None:
            try:
                self._on_card(card)
            except Exception:
                pass
    return PipelineResult(prospects=cards, stats=PipelineStats())


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_all_three_cards_emitted_via_callback():
    """All 3 ProspectCards are emitted via on_card before run_streaming() returns."""
    emitted: list[ProspectCard] = []

    orch = _build_orchestrator(on_card=emitted.append)
    with patch.object(PipelineOrchestrator, "run_streaming", _fake_run_streaming):
        result = await orch.run_streaming(
            categories=["plumbers"], location="Sydney", target_cards=10
        )

    # run_streaming() should have returned 3 cards
    assert len(result.prospects) == 3
    # callback should have received the same 3 cards
    assert len(emitted) == 3


@pytest.mark.asyncio
async def test_emission_order_matches_production_order():
    """Cards are emitted in the same order they appear in the final result list."""
    emitted: list[ProspectCard] = []

    orch = _build_orchestrator(on_card=emitted.append)
    with patch.object(PipelineOrchestrator, "run_streaming", _fake_run_streaming):
        result = await orch.run_streaming(
            categories=["plumbers"], location="Sydney", target_cards=10
        )

    assert [c.domain for c in emitted] == [c.domain for c in result.prospects]


@pytest.mark.asyncio
async def test_emitted_cards_are_same_objects_as_result():
    """on_card receives the exact ProspectCard objects stored in result.prospects."""
    emitted: list[ProspectCard] = []

    orch = _build_orchestrator(on_card=emitted.append)
    with patch.object(PipelineOrchestrator, "run_streaming", _fake_run_streaming):
        result = await orch.run_streaming(
            categories=["plumbers"], location="Sydney", target_cards=10
        )

    for emitted_card, result_card in zip(emitted, result.prospects):
        assert emitted_card is result_card


@pytest.mark.asyncio
async def test_callback_exception_does_not_break_pipeline():
    """A crashing on_card callback must not prevent run_streaming() from completing."""

    def bad_callback(card):
        raise RuntimeError("dashboard down")

    orch = _build_orchestrator(on_card=bad_callback)
    with patch.object(PipelineOrchestrator, "run_streaming", _fake_run_streaming):
        result = await orch.run_streaming(
            categories=["plumbers"], location="Sydney", target_cards=10
        )

    # All prospects still collected despite callback failure
    assert len(result.prospects) == 3


@pytest.mark.asyncio
async def test_sse_card_streamer_puts_events_onto_queue():
    """SSECardStreamer.emit() puts a serialized event dict onto the asyncio queue."""
    queue: asyncio.Queue = asyncio.Queue()
    streamer = SSECardStreamer(queue)

    orch = _build_orchestrator(on_card=streamer.emit)
    with patch.object(PipelineOrchestrator, "run_streaming", _fake_run_streaming):
        result = await orch.run_streaming(
            categories=["plumbers"], location="Sydney", target_cards=10
        )

    assert queue.qsize() == len(result.prospects)

    # Check shape of first event
    event = queue.get_nowait()
    assert event["event"] == "prospect_card"
    import json

    data = json.loads(event["data"])
    assert "domain" in data
    assert "company_name" in data
