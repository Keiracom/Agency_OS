"""Tests for PipelineOrchestrator.run_parallel — Directive #295 Task E."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator, GLOBAL_SEM_DFS, GLOBAL_SEM_SCRAPE


# ── Helpers ──────────────────────────────────────────────────────────────────

def _afford_pass():
    r = MagicMock(); r.passed_gate = True; r.band = "HIGH"; r.raw_score = 9; r.gaps = []
    return r

def _intent_pass():
    r = MagicMock(); r.passed_free_gate = True; r.band = "TRYING"; r.raw_score = 5; r.evidence = ["Has website, no analytics"]
    return r

def _intent_full():
    r = MagicMock(); r.band = "TRYING"; r.raw_score = 6; r.evidence = ["Has website, no analytics"]
    return r

def _dm(name="Jane Owner"):
    d = MagicMock(); d.name = name; d.title = "Owner"
    d.linkedin_url = "https://au.linkedin.com/in/jane"; d.confidence = "HIGH"
    return d

def _enrichment(domain="x.com.au"):
    return {
        "domain": domain,
        "company_name": "Test Co",
        "entity_type": "Company",
        "gst_registered": True,
        "non_au": False,
        "website_contact_emails": ["info@x.com.au"],
        "website_address": {"suburb": "Sydney"},
    }

def _make_orch(domains_per_batch=5, target=3):
    """Build a PipelineOrchestrator with all dependencies mocked."""
    call_count = {"n": 0}

    async def pull_batch(**kwargs):
        call_count["n"] += 1
        if call_count["n"] > 3:
            return []
        return [{"domain": f"d{call_count['n']}x{i}.com.au"} for i in range(domains_per_batch)]

    discovery = MagicMock()
    discovery.pull_batch = pull_batch

    fe = MagicMock()
    fe.scrape_website = AsyncMock(return_value={"title": "Test"})
    fe.enrich_from_spider = AsyncMock(side_effect=lambda domain, spider_data: _enrichment(domain))

    scorer = MagicMock()
    scorer.score_affordability = MagicMock(return_value=_afford_pass())
    scorer.score_intent_free = MagicMock(return_value=_intent_pass())
    scorer.score_intent_full = MagicMock(return_value=_intent_full())

    dm_id = MagicMock()
    dm_id.identify = AsyncMock(return_value=_dm())

    return PipelineOrchestrator(
        discovery=discovery,
        free_enrichment=fe,
        scorer=scorer,
        dm_identification=dm_id,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_parallel_reaches_target():
    """With ample domains, run_parallel stops at target_count."""
    orch = _make_orch(domains_per_batch=10)
    result = await orch.run_parallel(
        category_codes=["10514"],
        location="Australia",
        target_count=3,
        num_workers=2,
        batch_size=10,
    )
    assert len(result.prospects) == 3
    assert result.stats.viable_prospects == 3


@pytest.mark.asyncio
async def test_run_parallel_deduplicates_domains():
    """Same domain appearing in multiple batches is processed only once."""
    discovery = MagicMock()
    call_n = {"n": 0}

    async def pull_batch(**kwargs):
        call_n["n"] += 1
        if call_n["n"] == 1:
            return [{"domain": "shared.com.au"}]
        if call_n["n"] == 2:
            return [{"domain": "shared.com.au"}]  # duplicate
        return []

    discovery.pull_batch = pull_batch

    fe = MagicMock()
    fe.scrape_website = AsyncMock(return_value={"title": "T"})
    fe.enrich_from_spider = AsyncMock(return_value=_enrichment("shared.com.au"))

    scorer = MagicMock()
    scorer.score_affordability = MagicMock(return_value=_afford_pass())
    scorer.score_intent_free = MagicMock(return_value=_intent_pass())
    scorer.score_intent_full = MagicMock(return_value=_intent_full())

    dm_id = MagicMock()
    dm_id.identify = AsyncMock(return_value=_dm())

    orch = PipelineOrchestrator(
        discovery=discovery, free_enrichment=fe, scorer=scorer, dm_identification=dm_id,
    )
    result = await orch.run_parallel(
        category_codes=["10514"], location="Australia",
        target_count=10, num_workers=2, batch_size=1,
    )
    # shared.com.au should only be counted once
    assert result.stats.discovered == 1


@pytest.mark.asyncio
async def test_run_parallel_stops_on_exhaustion():
    """When all batches are empty, workers stop and result is returned."""
    discovery = MagicMock()
    discovery.pull_batch = AsyncMock(return_value=[])

    fe = MagicMock()
    fe.scrape_website = AsyncMock(return_value={})
    fe.enrich_from_spider = AsyncMock(return_value=None)

    scorer = MagicMock()
    dm_id = MagicMock()

    orch = PipelineOrchestrator(
        discovery=discovery, free_enrichment=fe, scorer=scorer, dm_identification=dm_id,
    )
    result = await orch.run_parallel(
        category_codes=["10514"], location="Australia",
        target_count=100, num_workers=2, batch_size=10,
    )
    assert len(result.prospects) == 0
    assert result.stats.discovered == 0


@pytest.mark.asyncio
async def test_run_parallel_non_au_rejected():
    """Domains with non_au=True are counted in affordability_rejected."""
    discovery = MagicMock()
    discovery.pull_batch = AsyncMock(side_effect=[
        [{"domain": "dentatur.com"}],
        [],
    ])

    fe = MagicMock()
    fe.scrape_website = AsyncMock(return_value={"title": "Turkish Dental"})
    fe.enrich_from_spider = AsyncMock(return_value={
        "domain": "dentatur.com",
        "company_name": "Denta Tur",
        "non_au": True,
    })

    scorer = MagicMock()
    dm_id = MagicMock()

    orch = PipelineOrchestrator(
        discovery=discovery, free_enrichment=fe, scorer=scorer, dm_identification=dm_id,
    )
    result = await orch.run_parallel(
        category_codes=["10514"], location="Australia",
        target_count=10, num_workers=1, batch_size=5,
    )
    assert result.stats.affordability_rejected == 1
    assert len(result.prospects) == 0


@pytest.mark.asyncio
async def test_run_parallel_on_prospect_found_callback():
    """on_prospect_found callback is called for each prospect found."""
    orch = _make_orch(domains_per_batch=5)
    found = []

    async def capture(card):
        found.append(card.domain)

    result = await orch.run_parallel(
        category_codes=["10514"],
        location="Australia",
        target_count=2,
        num_workers=1,
        batch_size=5,
        on_prospect_found=capture,
    )
    assert len(found) == 2
    assert len(result.prospects) == 2


@pytest.mark.asyncio
async def test_global_semaphores_exist():
    """Global semaphore pool is module-level and accessible."""
    assert GLOBAL_SEM_DFS._value == 28
    assert GLOBAL_SEM_SCRAPE._value == 80
