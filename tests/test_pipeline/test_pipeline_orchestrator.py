"""Tests for PipelineOrchestrator — Directive #288."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator, ProspectCard, PipelineResult


def make_enrichment():
    return {
        "entity_type": "Company",
        "gst_registered": True,
        "is_running_ads": True,
        "ads_count": 8,
        "gmb_review_count": 55,
        "website_cms": "wordpress",
        "website_tracking_codes": ["ga4"],
        "website_team_names": ["Alice", "Bob", "Carol"],
        "email_maturity": "PROFESSIONAL",
        "abn_matched": True,
        "company_name": "Test Co Pty Ltd",
        "website_address": {"suburb": "Sydney"},
    }


def make_dm_result(name="Alice Owner"):
    dm = MagicMock()
    dm.name = name
    dm.title = "Owner"
    dm.linkedin_url = "https://linkedin.com/in/alice"
    dm.confidence = "HIGH"
    return dm


def make_score_result(passed=True, band="HIGH", score=10, gaps=None):
    result = MagicMock()
    result.passed_gate = passed
    result.band = band
    result.raw_score = score
    result.gaps = gaps or []
    return result


def make_orchestrator(discovery, free_enrichment, scorer, dm):
    return PipelineOrchestrator(
        discovery=discovery,
        free_enrichment=free_enrichment,
        affordability_scorer=scorer,
        dm_identification=dm,
    )


@pytest.mark.asyncio
async def test_orchestrator_stops_at_target():
    # 10 domains per batch, each passes all stages
    discovery = MagicMock()
    discovery.pull_batch = AsyncMock(return_value=[{"domain": f"domain{i}.com"} for i in range(10)])

    free_enrichment = MagicMock()
    free_enrichment.enrich = AsyncMock(return_value=make_enrichment())

    scorer = MagicMock()
    scorer.score = MagicMock(return_value=make_score_result())

    dm = MagicMock()
    dm.identify = AsyncMock(return_value=make_dm_result())

    orch = make_orchestrator(discovery, free_enrichment, scorer, dm)
    result = await orch.run("beauty_salon", target_count=5, batch_size=10)

    assert len(result.prospects) == 5


@pytest.mark.asyncio
async def test_orchestrator_stops_on_category_exhausted():
    call_count = 0

    async def pull_batch(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [{"domain": f"domain{i}.com"} for i in range(3)]
        return []

    discovery = MagicMock()
    discovery.pull_batch = pull_batch

    free_enrichment = MagicMock()
    free_enrichment.enrich = AsyncMock(return_value=make_enrichment())

    scorer = MagicMock()
    scorer.score = MagicMock(return_value=make_score_result())

    dm = MagicMock()
    dm.identify = AsyncMock(return_value=make_dm_result())

    orch = make_orchestrator(discovery, free_enrichment, scorer, dm)
    result = await orch.run("beauty_salon", target_count=100, batch_size=10)

    assert len(result.prospects) == 3


@pytest.mark.asyncio
async def test_orchestrator_tracks_stats():
    """
    5 domains:
      domain0 — enrich returns None → enrichment_failed
      domain1 — gate_failed
      domain2 — gate_failed
      domain3 — dm_failed (dm.name is None)
      domain4 — success
    """
    domains = [{"domain": f"domain{i}.com"} for i in range(5)]

    discovery = MagicMock()
    discovery.pull_batch = AsyncMock(side_effect=[domains, []])

    enrich_responses = [None, make_enrichment(), make_enrichment(), make_enrichment(), make_enrichment()]
    enrich_iter = iter(enrich_responses)

    async def enrich(domain):
        return next(enrich_iter)

    free_enrichment = MagicMock()
    free_enrichment.enrich = enrich

    score_responses = [
        make_score_result(passed=False),
        make_score_result(passed=False),
        make_score_result(passed=True),
        make_score_result(passed=True),
    ]
    score_iter = iter(score_responses)

    scorer = MagicMock()
    scorer.score = MagicMock(side_effect=lambda e: next(score_iter))

    dm_responses = [make_dm_result(name=None), make_dm_result(name="Alice")]
    dm_iter = iter(dm_responses)

    async def identify(**kwargs):
        return next(dm_iter)

    dm = MagicMock()
    dm.identify = identify

    orch = make_orchestrator(discovery, free_enrichment, scorer, dm)
    result = await orch.run("beauty_salon", target_count=10, batch_size=10)

    assert result.stats.discovered == 5
    assert result.stats.enrichment_failed == 1
    assert result.stats.gate_failed == 2
    assert result.stats.dm_failed == 1
    assert result.stats.dm_found == 1


@pytest.mark.asyncio
async def test_prospect_card_fields():
    domains = [{"domain": "example.com"}]

    discovery = MagicMock()
    discovery.pull_batch = AsyncMock(side_effect=[domains, []])

    enrichment = make_enrichment()
    free_enrichment = MagicMock()
    free_enrichment.enrich = AsyncMock(return_value=enrichment)

    scorer = MagicMock()
    scorer.score = MagicMock(return_value=make_score_result(band="HIGH", score=11, gaps=["Not running Google Ads"]))

    dm = MagicMock()
    dm.identify = AsyncMock(return_value=make_dm_result())

    orch = make_orchestrator(discovery, free_enrichment, scorer, dm)
    result = await orch.run("beauty_salon", target_count=1, batch_size=10)

    assert len(result.prospects) == 1
    card = result.prospects[0]

    assert card.domain == "example.com"
    assert isinstance(card.company_name, str) and card.company_name
    assert isinstance(card.location, str)
    assert isinstance(card.gaps, list)
    assert isinstance(card.affordability_band, str)
    assert isinstance(card.affordability_score, int)
    assert isinstance(card.dm_name, str) and card.dm_name
    # dm_title, dm_linkedin_url, dm_confidence may be any value (including None)
    assert hasattr(card, "dm_title")
    assert hasattr(card, "dm_linkedin_url")
    assert hasattr(card, "dm_confidence")
