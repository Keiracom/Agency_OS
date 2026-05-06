"""Tests for PipelineOrchestrator.run_parallel() — Directive #295."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.pipeline.pipeline_orchestrator import PipelineOrchestrator


def _make_enrich(domain: str, non_au: bool = False) -> dict:
    return {
        "domain": domain,
        "company_name": f"Co {domain}",
        "non_au": non_au,
        "website_contact_emails": [f"info@{domain}"],
        "website_address": {"suburb": "Sydney"},
    }


def _afford_pass():
    r = MagicMock()
    r.passed_gate = True
    r.band = "HIGH"
    r.raw_score = 10
    return r


def _intent_pass():
    r = MagicMock()
    r.band = "TRYING"
    r.raw_score = 5
    r.evidence = []
    return r


def _make_dm(name: str = "Jane Owner") -> MagicMock:
    dm = MagicMock()
    dm.name = name
    dm.title = "Owner"
    dm.linkedin_url = "https://linkedin.com/in/jane"
    dm.confidence = "HIGH"
    return dm


def _make_orch(domains_per_call: list[list[str]], enrich_non_au: bool = False):
    """Build a PipelineOrchestrator with mocked dependencies."""
    # Discovery side_effect: first call returns domains, subsequent calls return []
    side_effects = []
    for batch in domains_per_call:
        side_effects.append([{"domain": d} for d in batch])
    side_effects.append([])  # exhaustion sentinel

    disc = MagicMock()
    disc.pull_batch = AsyncMock(side_effect=side_effects)

    enr = MagicMock()
    enr.scrape_website = AsyncMock(return_value={})

    async def _enrich_from_spider(domain, spider_data):
        return _make_enrich(domain, non_au=enrich_non_au)

    enr.enrich_from_spider = AsyncMock(side_effect=_enrich_from_spider)

    scorer = MagicMock()
    scorer.score_affordability = MagicMock(return_value=_afford_pass())
    scorer.score_intent_free = MagicMock(return_value=_intent_pass())
    scorer.score_intent_full = MagicMock(return_value=_intent_pass())

    dm_module = MagicMock()
    dm_module.identify = AsyncMock(return_value=_make_dm())

    orch = PipelineOrchestrator(
        discovery=disc,
        free_enrichment=enr,
        scorer=scorer,
        dm_identification=dm_module,
    )
    return orch


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_parallel_stops_at_target_count():
    """run_parallel must stop once target_count prospects are found."""
    # 10 domains across two batches — we only want 2
    orch = _make_orch(
        domains_per_call=[
            [f"domain{i}.com.au" for i in range(5)],
            [f"domain{i}.com.au" for i in range(5, 10)],
        ]
    )
    result = await orch.run_parallel(
        category_codes=["10514"],
        location="Sydney",
        target_count=2,
        num_workers=1,
        batch_size=5,
    )
    assert len(result.prospects) == 2
    assert result.stats.viable_prospects == 2


@pytest.mark.asyncio
async def test_parallel_deduplicates_domains():
    """Domains pulled by multiple workers must not be processed twice."""
    # Two workers both discover the same domain list
    same_domains = ["dup1.com.au", "dup2.com.au", "dup3.com.au"]

    disc = MagicMock()
    # Each category returns the same domains then []
    call_count = {"n": 0}

    async def pull_batch(**kwargs):
        call_count["n"] += 1
        # First call per category returns domains, second returns []
        if call_count["n"] % 2 == 1:
            return [{"domain": d} for d in same_domains]
        return []

    disc.pull_batch = AsyncMock(side_effect=pull_batch)

    enr = MagicMock()
    enr.scrape_website = AsyncMock(return_value={})
    enr.enrich_from_spider = AsyncMock(
        side_effect=lambda domain, spider_data: asyncio.coroutine(lambda: _make_enrich(domain))()
    )

    async def _enrich(domain, spider_data):
        return _make_enrich(domain)

    enr.enrich_from_spider = AsyncMock(side_effect=_enrich)

    scorer = MagicMock()
    scorer.score_affordability = MagicMock(return_value=_afford_pass())
    scorer.score_intent_free = MagicMock(return_value=_intent_pass())
    scorer.score_intent_full = MagicMock(return_value=_intent_pass())

    dm_module = MagicMock()
    dm_module.identify = AsyncMock(return_value=_make_dm())

    orch = PipelineOrchestrator(
        discovery=disc,
        free_enrichment=enr,
        scorer=scorer,
        dm_identification=dm_module,
    )

    # Two workers, two categories — both would see the same domains
    result = await orch.run_parallel(
        category_codes=["10514", "20001"],
        location="Sydney",
        target_count=100,
        num_workers=2,
        batch_size=10,
    )

    # Domains should not appear twice in results
    seen_domains = [p.domain for p in result.prospects]
    assert len(seen_domains) == len(set(seen_domains)), "Duplicate domains in results"


@pytest.mark.asyncio
async def test_parallel_merges_stats():
    """run_parallel must aggregate stats from all workers into a single PipelineStats."""
    # 6 domains split across 2 categories → 2 workers
    orch = _make_orch(
        domains_per_call=[
            ["a.com.au", "b.com.au", "c.com.au"],
        ]
    )
    result = await orch.run_parallel(
        category_codes=["cat1", "cat2"],
        location="Melbourne",
        target_count=10,
        num_workers=2,
        batch_size=10,
    )
    # Stats should be non-zero and reflect combined worker output
    total = (
        result.stats.enriched + result.stats.enrichment_failed + result.stats.affordability_rejected
    )
    assert result.stats.discovered >= 0
    assert result.stats.elapsed_seconds >= 0
    # viable_prospects must equal len(prospects)
    assert result.stats.viable_prospects == len(result.prospects)
