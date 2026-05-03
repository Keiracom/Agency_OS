"""Tests for new gated PipelineOrchestrator flow — Directive #291."""
import pytest
from unittest.mock import AsyncMock, MagicMock, call
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator
from src.pipeline.prospect_scorer import ProspectScorer


def _afford_pass():
    r = MagicMock(); r.passed_gate = True; r.band = "MEDIUM"; r.raw_score = 5; r.gaps = []
    return r

def _afford_fail():
    r = MagicMock(); r.passed_gate = False; r.band = "LOW"; r.raw_score = 0; r.gaps = ["sole_trader"]
    return r

def _intent_pass():
    r = MagicMock(); r.passed_free_gate = True; r.band = "TRYING"; r.raw_score = 5; r.evidence = ["Has website but no analytics"]
    return r

def _intent_fail():
    r = MagicMock(); r.passed_free_gate = False; r.band = "NOT_TRYING"; r.raw_score = 0; r.evidence = []
    return r

def _make_orch(afford=None, intent_free=None, intent_full=None, dm=None):
    disc = MagicMock(); disc.pull_batch = AsyncMock(side_effect=[[{"domain": "dental.com.au"}], []])
    enr = MagicMock()
    enr.scrape_website = AsyncMock(return_value={"title": "Dental"})
    enr.enrich_from_spider = AsyncMock(return_value={"domain": "dental.com.au", "company_name": "Dental", "entity_type": "Company", "gst_registered": True})
    scorer = MagicMock()
    scorer.score_affordability = MagicMock(return_value=afford or _afford_pass())
    scorer.score_intent_free = MagicMock(return_value=intent_free or _intent_pass())
    scorer.score_intent_full = MagicMock(return_value=intent_full or _intent_pass())
    dm_mock = MagicMock()
    if dm is None:
        dm_res = MagicMock(); dm_res.name = "Jane"; dm_res.title = "Owner"
        dm_res.linkedin_url = "https://au.linkedin.com/in/jane"; dm_res.confidence = "HIGH"
        dm_mock.identify = AsyncMock(return_value=dm_res)
    else:
        dm_mock.identify = AsyncMock(return_value=dm)
    return PipelineOrchestrator(discovery=disc, free_enrichment=enr,
                                prospect_scorer=scorer, dm_identification=dm_mock), scorer


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_affordability_rejected_counted():
    orch, scorer = _make_orch(afford=_afford_fail())
    result = await orch.run("10514", target_count=5)
    assert result.stats.affordability_rejected == 1
    assert result.stats.intent_rejected == 0


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_intent_not_trying_skips_paid_enrichment():
    ads_client = AsyncMock()
    orch, scorer = _make_orch(intent_free=_intent_fail())
    orch._ads_client = ads_client
    result = await orch.run("10514", target_count=5)
    assert result.stats.intent_rejected == 1
    ads_client.assert_not_called()


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_full_prospect_card_with_evidence():
    orch, scorer = _make_orch()
    result = await orch.run("10514", target_count=1, batch_size=1)
    assert len(result.prospects) == 1
    card = result.prospects[0]
    assert card.dm_name == "Jane"
    assert card.intent_band in ("NOT_TRYING", "DABBLING", "TRYING", "STRUGGLING", "UNKNOWN")


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_dm_not_found_counted():
    disc = MagicMock(); disc.pull_batch = AsyncMock(side_effect=[[{"domain":"x.com"}],[]])
    enr = MagicMock()
    enr.scrape_website = AsyncMock(return_value={"title": "X"})
    enr.enrich_from_spider = AsyncMock(return_value={"domain":"x.com","company_name":"X","entity_type":"Company","gst_registered":True})
    scorer = MagicMock()
    scorer.score_affordability = MagicMock(return_value=_afford_pass())
    scorer.score_intent_free = MagicMock(return_value=_intent_pass())
    scorer.score_intent_full = MagicMock(return_value=_intent_pass())
    dm_mock = MagicMock(); dm_mock.identify = AsyncMock(return_value=None)
    orch2 = PipelineOrchestrator(discovery=disc, free_enrichment=enr,
                                 prospect_scorer=scorer, dm_identification=dm_mock)
    result = await orch2.run("10514", target_count=5)
    assert result.stats.dm_not_found == 1


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_stops_at_target_count():
    disc = MagicMock()
    disc.pull_batch = AsyncMock(return_value=[{"domain": f"d{i}.com.au"} for i in range(20)])
    enr = MagicMock()
    enr.scrape_website = AsyncMock(return_value={"title": "D"})
    enr.enrich_from_spider = AsyncMock(return_value={"domain":"d.com.au","company_name":"D","entity_type":"Company","gst_registered":True,"website_contact_emails":["a@b.com"]})
    scorer = MagicMock()
    scorer.score_affordability = MagicMock(return_value=_afford_pass())
    scorer.score_intent_free = MagicMock(return_value=_intent_pass())
    scorer.score_intent_full = MagicMock(return_value=_intent_pass())
    dm_res = MagicMock(); dm_res.name = "Jane"; dm_res.title = ""; dm_res.linkedin_url = "https://li.com/in/j"; dm_res.confidence = "HIGH"
    dm_mock = MagicMock(); dm_mock.identify = AsyncMock(return_value=dm_res)
    orch = PipelineOrchestrator(discovery=disc, free_enrichment=enr,
                                prospect_scorer=scorer, dm_identification=dm_mock)
    result = await orch.run("10514", target_count=3, batch_size=20)
    assert len(result.prospects) == 3
