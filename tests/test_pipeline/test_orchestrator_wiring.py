"""Tests for orchestrator wiring — Directive #290, updated for #293."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator


def _make_scorer(afford_pass=True):
    scorer = MagicMock()
    afford = MagicMock()
    afford.passed_gate = afford_pass
    afford.band = "MEDIUM" if afford_pass else "LOW"
    afford.raw_score = 5 if afford_pass else 0
    afford.gaps = []
    scorer.score_affordability = MagicMock(return_value=afford)
    intent = MagicMock()
    intent.passed_free_gate = True
    intent.band = "TRYING"
    intent.raw_score = 5
    intent.evidence = []
    scorer.score_intent_free = MagicMock(return_value=intent)
    scorer.score_intent_full = MagicMock(return_value=intent)
    return scorer


def _make_orch(**overrides):
    disc = MagicMock(); disc.pull_batch = AsyncMock(return_value=[])
    enr = MagicMock()
    enr.scrape_website = AsyncMock(return_value={})
    enr.enrich_from_spider = AsyncMock(return_value=None)
    scr = MagicMock()
    dm = MagicMock(); dm.identify = AsyncMock(return_value=None)
    kw = dict(discovery=disc, free_enrichment=enr, scorer=scr, dm_identification=dm)
    kw.update(overrides)
    return PipelineOrchestrator(**kw)


@pytest.mark.asyncio
async def test_empty_discovery_returns_empty():
    result = await _make_orch().run("10514", target_count=5)
    assert result.prospects == []
    assert result.stats.discovered == 0


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_enrichment_failure_counted():
    disc = MagicMock(); disc.pull_batch = AsyncMock(side_effect=[[{"domain":"x.com"}], []])
    enr = MagicMock()
    enr.scrape_website = AsyncMock(return_value={})
    enr.enrich_from_spider = AsyncMock(return_value=None)
    orch = PipelineOrchestrator(discovery=disc, free_enrichment=enr,
                                scorer=MagicMock(), dm_identification=MagicMock())
    result = await orch.run("10514", target_count=5, batch_size=1)
    assert result.stats.enrichment_failed == 1


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_gate_failure_counted():
    disc = MagicMock(); disc.pull_batch = AsyncMock(side_effect=[[{"domain":"x.com"}], []])
    enr = MagicMock()
    enr.scrape_website = AsyncMock(return_value={})
    enr.enrich_from_spider = AsyncMock(return_value={"domain":"x.com","company_name":"X"})
    score = MagicMock(); score.passed_gate = False; score.gaps = []; score.band = "LOW"; score.raw_score = 2
    scr = MagicMock(); scr.score_affordability = MagicMock(return_value=score)
    orch = PipelineOrchestrator(discovery=disc, free_enrichment=enr,
                                scorer=scr, dm_identification=MagicMock())
    result = await orch.run("10514", target_count=5, batch_size=1)
    assert result.stats.affordability_rejected == 1


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_full_prospect_card_built():
    disc = MagicMock(); disc.pull_batch = AsyncMock(side_effect=[[{"domain":"dental.com.au"}], []])
    enr = MagicMock()
    enr.scrape_website = AsyncMock(return_value={})
    enr.enrich_from_spider = AsyncMock(return_value={
        "domain":"dental.com.au","company_name":"Dental",
        "website_address":{"suburb":"Sydney"},
        "website_contact_emails": ["info@dental.com.au"],
    })
    score = MagicMock(); score.passed_gate = True; score.gaps = []; score.band = "MEDIUM"; score.raw_score = 6
    scr = MagicMock(); scr.score_affordability = MagicMock(return_value=score)
    dm_r = MagicMock(); dm_r.name = "Jane"; dm_r.title = "Owner"
    dm_r.linkedin_url = "https://au.linkedin.com/in/jane"; dm_r.confidence = "HIGH"
    dm = MagicMock(); dm.identify = AsyncMock(return_value=dm_r)
    orch = PipelineOrchestrator(discovery=disc, free_enrichment=enr,
                                scorer=scr, dm_identification=dm)
    result = await orch.run("10514", target_count=1, batch_size=1)
    assert len(result.prospects) == 1
    assert result.prospects[0].dm_name == "Jane"


@pytest.mark.asyncio
async def test_gmb_client_none_backwards_compatible():
    orch = _make_orch()
    assert orch._gmb_client is None
    result = await orch.run("10514", target_count=1)
    assert result.prospects == []


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_pull_batch_called_correct_args():
    disc = MagicMock(); disc.pull_batch = AsyncMock(return_value=[])
    enr = MagicMock()
    enr.scrape_website = AsyncMock(return_value={})
    enr.enrich_from_spider = AsyncMock(return_value=None)
    orch = PipelineOrchestrator(discovery=disc, free_enrichment=enr,
                                scorer=MagicMock(), dm_identification=MagicMock())
    await orch.run("10514", location="Australia", target_count=5, batch_size=10)
    disc.pull_batch.assert_called_once_with(
        category_code="10514", location="Australia", limit=10, offset=0)
