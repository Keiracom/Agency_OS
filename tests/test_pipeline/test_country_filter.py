"""Tests for AU country filter — Directive #295 Task D."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.pipeline.free_enrichment import FreeEnrichment
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator


def make_fe() -> FreeEnrichment:
    """Instantiate FreeEnrichment without a real DB connection."""
    return FreeEnrichment.__new__(FreeEnrichment)


# ── _is_au_domain tests ───────────────────────────────────────────────────────


def test_au_domain_passes():
    fe = make_fe()
    assert fe._is_au_domain("dentist.com.au", "") is True


def test_state_in_html_passes():
    fe = make_fe()
    html = "<p>We serve patients across NSW and beyond.</p>"
    assert fe._is_au_domain("dentist.com", html) is True


def test_phone_in_html_passes():
    fe = make_fe()
    # Australian landline: 02 9999 8888 — stripped of spaces = 0299998888
    html = "<p>Call us on 0299998888 today</p>"
    assert fe._is_au_domain("dentist.com", html) is True


def test_foreign_domain_fails():
    fe = make_fe()
    # Turkish dental site with no AU indicators
    html = "<html><head><title>Dentatur Diş Kliniği</title></head><body>İstanbul</body></html>"
    assert fe._is_au_domain("dentatur.com", html) is False


# ── non_au in orchestrator affordability gate ──────────────────────────────────


def _make_orch_with_non_au(non_au: bool):
    disc = MagicMock()
    disc.pull_batch = AsyncMock(
        side_effect=[[{"domain": "example.com"}], []]
    )

    fe = MagicMock()
    fe.scrape_website = AsyncMock(return_value={"title": "Example", "_raw_html": ""})
    fe.enrich_from_spider = AsyncMock(return_value={
        "domain": "example.com",
        "company_name": "Example Co",
        "non_au": non_au,
        "website_contact_emails": [],
        "website_address": {},
    })

    scorer = MagicMock()
    afford = MagicMock()
    afford.passed_gate = True
    afford.band = "MEDIUM"
    afford.raw_score = 5
    scorer.score_affordability = MagicMock(return_value=afford)

    intent = MagicMock()
    intent.band = "TRYING"
    intent.raw_score = 5
    intent.evidence = []
    scorer.score_intent_free = MagicMock(return_value=intent)
    scorer.score_intent_full = MagicMock(return_value=intent)

    dm_id = MagicMock()
    dm_result = MagicMock()
    dm_result.name = "Jane Smith"
    dm_result.title = "Owner"
    dm_result.linkedin_url = "https://linkedin.com/in/jane"
    dm_result.confidence = "HIGH"
    dm_id.identify = AsyncMock(return_value=dm_result)

    return PipelineOrchestrator(
        discovery=disc,
        free_enrichment=fe,
        scorer=scorer,
        dm_identification=dm_id,
    ), scorer


@pytest.mark.asyncio
async def test_non_au_rejected_in_orchestrator():
    """non_au=True domain is rejected and counted in affordability_rejected."""
    orch, scorer = _make_orch_with_non_au(non_au=True)
    result = await orch.run(category_codes="dental", location="Sydney", target_count=10)

    assert result.stats.affordability_rejected == 1
    assert result.stats.viable_prospects == 0
    # score_affordability must NOT be called for non-AU domains
    scorer.score_affordability.assert_not_called()


@pytest.mark.asyncio
async def test_au_domain_not_rejected_in_orchestrator():
    """non_au=False domain passes the AU filter and proceeds to scoring."""
    orch, scorer = _make_orch_with_non_au(non_au=False)
    result = await orch.run(category_codes="dental", location="Sydney", target_count=10)

    # score_affordability is called (domain passed AU filter)
    scorer.score_affordability.assert_called_once()
