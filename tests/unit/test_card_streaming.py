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
from unittest.mock import AsyncMock, MagicMock

from src.pipeline.pipeline_orchestrator import (
    PipelineOrchestrator,
    ProspectCard,
    SSECardStreamer,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_domain_dict(domain: str) -> dict:
    return {"domain": domain}


def _make_enrichment(domain: str) -> dict:
    return {
        "company_name": f"Company {domain}",
        "website_address": {"suburb": "Sydney"},
        "website_contact_emails": ["hello@example.com"],
    }


def _make_afford(passed: bool = True):
    a = MagicMock()
    a.passed_gate = passed
    a.band = "MID"
    a.raw_score = 50
    return a


def _make_intent(band: str = "STRUGGLING"):
    i = MagicMock()
    i.band = band
    i.raw_score = 8
    i.evidence = ["signal A"]
    i.signals = {}
    return i


def _make_dm(domain: str):
    dm = MagicMock()
    dm.name = f"Owner of {domain}"
    dm.title = "Director"
    dm.linkedin_url = f"https://linkedin.com/in/{domain}"
    dm.confidence = "HIGH"
    return dm


# ── Fixtures ─────────────────────────────────────────────────────────────────

DOMAINS = ["alpha.com.au", "beta.com.au", "gamma.com.au"]


def _build_orchestrator(on_card=None):
    """Build a PipelineOrchestrator wired with mocks that produce 3 prospect cards."""

    # Discovery: returns 3 domains then empty
    call_count = {"n": 0}

    async def pull_batch(category_code, location, limit, offset):
        if call_count["n"] == 0:
            call_count["n"] += 1
            return [_make_domain_dict(d) for d in DOMAINS]
        return []

    discovery = MagicMock()
    discovery.pull_batch = pull_batch

    # Free enrichment
    async def scrape_website(domain):
        return {"_raw_html": f"<html>{domain}</html>"}

    async def enrich_from_spider(domain, spider_data):
        return _make_enrichment(domain)

    fe = MagicMock()
    fe.scrape_website = scrape_website
    fe.enrich_from_spider = enrich_from_spider

    # Scorer — all domains pass both gates
    afford = _make_afford(passed=True)
    intent = _make_intent(band="STRUGGLING")

    scorer = MagicMock()
    scorer.score_affordability = MagicMock(return_value=afford)
    scorer.score_intent_free = MagicMock(return_value=intent)
    scorer.score_intent_full = MagicMock(return_value=intent)

    # DM identification — every domain gets a DM
    async def identify(domain, company_name, spider_data, abn_data):
        return _make_dm(domain)

    dm = MagicMock()
    dm.identify = identify

    return PipelineOrchestrator(
        discovery=discovery,
        free_enrichment=fe,
        scorer=scorer,
        dm_identification=dm,
        on_card=on_card,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_three_cards_emitted_via_callback():
    """All 3 ProspectCards are emitted via on_card before run() returns."""
    emitted: list[ProspectCard] = []

    orch = _build_orchestrator(on_card=emitted.append)
    result = await orch.run(category_codes="plumbers", location="Sydney", target_count=10)

    # run() should have returned 3 cards
    assert len(result.prospects) == 3
    # callback should have received the same 3 cards
    assert len(emitted) == 3


@pytest.mark.asyncio
async def test_emission_order_matches_production_order():
    """Cards are emitted in the same order they appear in the final result list."""
    emitted: list[ProspectCard] = []

    orch = _build_orchestrator(on_card=emitted.append)
    result = await orch.run(category_codes="plumbers", location="Sydney", target_count=10)

    assert [c.domain for c in emitted] == [c.domain for c in result.prospects]


@pytest.mark.asyncio
async def test_emitted_cards_are_same_objects_as_result():
    """on_card receives the exact ProspectCard objects stored in result.prospects."""
    emitted: list[ProspectCard] = []

    orch = _build_orchestrator(on_card=emitted.append)
    result = await orch.run(category_codes="plumbers", location="Sydney", target_count=10)

    for emitted_card, result_card in zip(emitted, result.prospects):
        assert emitted_card is result_card


@pytest.mark.asyncio
async def test_callback_exception_does_not_break_pipeline():
    """A crashing on_card callback must not prevent run() from completing."""
    def bad_callback(card):
        raise RuntimeError("dashboard down")

    orch = _build_orchestrator(on_card=bad_callback)
    result = await orch.run(category_codes="plumbers", location="Sydney", target_count=10)

    # All prospects still collected despite callback failure
    assert len(result.prospects) == 3


@pytest.mark.asyncio
async def test_sse_card_streamer_puts_events_onto_queue():
    """SSECardStreamer.emit() puts a serialized event dict onto the asyncio queue."""
    queue: asyncio.Queue = asyncio.Queue()
    streamer = SSECardStreamer(queue)

    orch = _build_orchestrator(on_card=streamer.emit)
    result = await orch.run(category_codes="plumbers", location="Sydney", target_count=10)

    assert queue.qsize() == len(result.prospects)

    # Check shape of first event
    event = queue.get_nowait()
    assert event["event"] == "prospect_card"
    import json
    data = json.loads(event["data"])
    assert "domain" in data
    assert "company_name" in data
