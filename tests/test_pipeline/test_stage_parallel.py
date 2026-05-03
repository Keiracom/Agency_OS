"""Tests for stage-parallel PipelineOrchestrator — Directive #293."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.pipeline.pipeline_orchestrator import (
    PipelineOrchestrator, ProspectCard, PipelineStats, SEM_SPIDER, SEM_ABN, SEM_PAID, SEM_DM
)


def _make_dm(name="Jane Smith", linkedin="https://au.linkedin.com/in/jane"):
    dm = MagicMock()
    dm.name = name
    dm.title = "Owner"
    dm.linkedin_url = linkedin
    dm.confidence = "HIGH"
    return dm


def _afford_pass(band="MEDIUM"):
    r = MagicMock()
    r.passed_gate = True
    r.band = band
    r.raw_score = 5
    r.gaps = []
    return r


def _intent_pass(band="TRYING"):
    r = MagicMock()
    r.passed_free_gate = True
    r.band = band
    r.raw_score = 6
    r.evidence = ["Has website but no analytics"]
    return r


def _intent_not_trying():
    r = MagicMock()
    r.passed_free_gate = False
    r.band = "NOT_TRYING"
    r.raw_score = 0
    r.evidence = []
    return r


def _make_orch(
    discovery_domains=None,
    spider_result=None,
    enrich_result=None,
    afford=None,
    intent_free=None,
    intent_full=None,
    dm=None,
    ads_client=None,
    gmb_client=None,
):
    disc = MagicMock()
    disc.pull_batch = AsyncMock(
        side_effect=[discovery_domains or [{"domain": "dental.com.au"}], []]
    )

    fe = MagicMock()
    fe.scrape_website = AsyncMock(return_value=spider_result or {"title": "Dental Clinic"})
    fe.enrich_from_spider = AsyncMock(
        return_value=enrich_result or {
            "domain": "dental.com.au",
            "company_name": "Dental Clinic",
            "website_contact_emails": ["info@dental.com.au"],
        }
    )

    scorer = MagicMock()
    scorer.score_affordability = MagicMock(return_value=afford or _afford_pass())
    scorer.score_intent_free = MagicMock(return_value=intent_free or _intent_pass())
    scorer.score_intent_full = MagicMock(return_value=intent_full or _intent_pass())

    dm_id = MagicMock()
    dm_id.identify = AsyncMock(return_value=dm or _make_dm())

    return PipelineOrchestrator(
        discovery=disc,
        free_enrichment=fe,
        scorer=scorer,
        dm_identification=dm_id,
        gmb_client=gmb_client,
        ads_client=ads_client,
    )


@pytest.mark.asyncio
async def test_semaphore_constants_defined():
    assert SEM_SPIDER == 15
    assert SEM_ABN == 50
    assert SEM_PAID == 20
    assert SEM_DM == 20


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_stage_parallel_produces_prospect():
    orch = _make_orch()
    result = await orch.run("10514", target_count=1, batch_size=5)
    assert len(result.prospects) == 1
    card = result.prospects[0]
    assert card.domain == "dental.com.au"
    assert card.dm_name == "Jane Smith"


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_batch_of_10_all_concurrent():
    """10 domains in batch — all spider calls should be issued concurrently."""
    domains = [{"domain": f"d{i}.com.au"} for i in range(10)]
    call_times = []

    async def mock_scrape(domain):
        call_times.append(asyncio.get_event_loop().time())
        await asyncio.sleep(0.01)
        return {"title": f"Clinic {domain}"}

    disc = MagicMock()
    disc.pull_batch = AsyncMock(side_effect=[domains, []])

    fe = MagicMock()
    fe.scrape_website = mock_scrape
    fe.enrich_from_spider = AsyncMock(return_value={
        "domain": "d0.com.au", "company_name": "Clinic",
        "website_contact_emails": ["a@b.com"]
    })

    scorer = MagicMock()
    scorer.score_affordability = MagicMock(return_value=_afford_pass())
    scorer.score_intent_free = MagicMock(return_value=_intent_pass())
    scorer.score_intent_full = MagicMock(return_value=_intent_pass())

    dm_id = MagicMock()
    dm_id.identify = AsyncMock(return_value=_make_dm())

    orch = PipelineOrchestrator(discovery=disc, free_enrichment=fe,
                                scorer=scorer, dm_identification=dm_id)
    await orch.run("10514", target_count=5, batch_size=10)

    # All 10 spider calls should have started within a short window (concurrent)
    assert len(call_times) == 10
    time_range = max(call_times) - min(call_times)
    assert time_range < 0.1, f"Calls not concurrent: spread={time_range:.3f}s"


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_spider_failure_doesnt_block_others():
    """If Spider fails for one domain, others still process."""
    fail_count = 0

    async def mock_scrape(domain):
        nonlocal fail_count
        if domain == "fail.com.au":
            fail_count += 1
            raise Exception("Spider timeout")
        return {"title": f"Clinic {domain}"}

    domains = [{"domain": "fail.com.au"}, {"domain": "ok.com.au"}]
    disc = MagicMock()
    disc.pull_batch = AsyncMock(side_effect=[domains, []])

    async def enrich_from_spider(domain, spider_data):
        # fail.com.au got empty spider_data → return None to simulate enrichment failure
        if not spider_data:
            return None
        return {"domain": domain, "company_name": "OK Dental", "website_contact_emails": ["a@b.com"]}

    fe = MagicMock()
    fe.scrape_website = mock_scrape
    fe.enrich_from_spider = enrich_from_spider

    scorer = MagicMock()
    scorer.score_affordability = MagicMock(return_value=_afford_pass())
    scorer.score_intent_free = MagicMock(return_value=_intent_pass())
    scorer.score_intent_full = MagicMock(return_value=_intent_pass())

    dm_id = MagicMock()
    dm_id.identify = AsyncMock(return_value=_make_dm())

    orch = PipelineOrchestrator(discovery=disc, free_enrichment=fe,
                                scorer=scorer, dm_identification=dm_id)
    result = await orch.run("10514", target_count=5, batch_size=2)

    # fail.com.au spider returned {} → enrich_from_spider returned None → enrichment_failed
    # ok.com.au still produced a prospect
    assert result.stats.enrichment_failed >= 1
    assert result.stats.discovered == 2


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_affordability_gate_filters_between_stages():
    orch = _make_orch(afford=MagicMock(passed_gate=False, band="LOW", raw_score=0, gaps=[]))
    result = await orch.run("10514", target_count=5, batch_size=1)
    assert result.stats.affordability_rejected >= 1
    assert len(result.prospects) == 0


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_not_trying_skips_paid_enrichment():
    ads_mock = AsyncMock(return_value={"is_running_ads": True})
    orch = _make_orch(intent_free=_intent_not_trying(), ads_client=ads_mock)
    result = await orch.run("10514", target_count=5, batch_size=1)
    assert result.stats.intent_rejected >= 1
    # ads_client should not have been called
    ads_mock.assert_not_called()


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_stops_at_target_count():
    domains = [{"domain": f"d{i}.com.au"} for i in range(20)]
    disc = MagicMock()
    disc.pull_batch = AsyncMock(return_value=domains)  # infinite supply

    fe = MagicMock()
    fe.scrape_website = AsyncMock(return_value={"title": "Dental"})
    fe.enrich_from_spider = AsyncMock(return_value={
        "domain": "d0.com.au", "company_name": "Dental",
        "website_contact_emails": ["a@b.com"]
    })

    scorer = MagicMock()
    scorer.score_affordability = MagicMock(return_value=_afford_pass())
    scorer.score_intent_free = MagicMock(return_value=_intent_pass())
    scorer.score_intent_full = MagicMock(return_value=_intent_pass())

    dm_id = MagicMock()
    dm_id.identify = AsyncMock(return_value=_make_dm())

    orch = PipelineOrchestrator(discovery=disc, free_enrichment=fe,
                                scorer=scorer, dm_identification=dm_id)
    result = await orch.run("10514", target_count=3, batch_size=20)
    assert len(result.prospects) == 3


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_stats_track_all_rejection_reasons():
    """Verify all stats counters work end-to-end."""
    orch = _make_orch()
    result = await orch.run("10514", target_count=1, batch_size=1)
    stats = result.stats
    assert stats.discovered >= 1
    assert stats.enriched >= 0
    assert stats.viable_prospects == len(result.prospects)


@pytest.mark.asyncio
async def test_empty_discovery_returns_empty():
    disc = MagicMock()
    disc.pull_batch = AsyncMock(return_value=[])
    fe = MagicMock()
    scorer = MagicMock()
    dm_id = MagicMock()
    orch = PipelineOrchestrator(discovery=disc, free_enrichment=fe,
                                scorer=scorer, dm_identification=dm_id)
    result = await orch.run("10514", target_count=10)
    assert result.prospects == []
    assert result.stats.discovered == 0
