"""
FILE: tests/test_flows/test_post_onboarding_flow.py
PURPOSE: Unit tests for post_onboarding_setup_flow — Directive #187 gaps G6/G7/G8/G9
PHASE: 37
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.engines.base import EngineResult


# ============================================
# G9: Campaign draft status
# ============================================


@pytest.mark.asyncio
async def test_campaign_suggester_creates_draft_status():
    """
    G9: create_suggested_campaigns with auto_activate=False must write status='draft' to DB.
    Guards against regression where campaign status is flipped to 'approved'/'active'.
    """
    from src.engines.campaign_suggester import CampaignSuggesterEngine

    client_id = uuid4()
    suggestions = [
        {
            "name": "Test Campaign",
            "description": "Test description",
            "ai_reasoning": "good fit",
            "lead_allocation_pct": 100,
            "target_industries": ["tech"],
            "target_titles": ["CEO"],
            "target_company_sizes": ["1-50"],
            "target_locations": ["AU"],
        }
    ]

    captured_status = []

    # Mock row with .id and .name attributes (SQLAlchemy row-style)
    mock_row = MagicMock()
    mock_row.id = uuid4()
    mock_row.name = "Test Campaign"

    async def fake_execute(query, params=None):
        if params and isinstance(params, dict) and "status" in params:
            captured_status.append(params["status"])
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        return mock_result

    mock_db = AsyncMock()
    mock_db.execute = fake_execute
    mock_db.commit = AsyncMock()

    engine = CampaignSuggesterEngine()
    result = await engine.create_suggested_campaigns(
        db=mock_db,
        client_id=client_id,
        suggestions=suggestions,
        auto_activate=False,  # must create as draft
    )

    assert captured_status, (
        "No DB execute called with a 'status' param — test fixture may be broken"
    )
    assert all(s == "draft" for s in captured_status), (
        f"Expected all statuses='draft' but got: {captured_status}. "
        "G9 REGRESSION: campaign_suggester is NOT creating campaigns as draft!"
    )


@pytest.mark.asyncio
async def test_campaign_suggester_creates_active_when_auto_activate():
    """
    G9 sanity check: auto_activate=True → status='active'.
    """
    from src.engines.campaign_suggester import CampaignSuggesterEngine

    client_id = uuid4()
    suggestions = [
        {
            "name": "Active Campaign",
            "description": "Test",
            "ai_reasoning": "perfect match",
            "lead_allocation_pct": 100,
            "target_industries": ["finance"],
            "target_titles": ["CFO"],
            "target_company_sizes": ["50-200"],
            "target_locations": ["US"],
        }
    ]

    captured_status = []

    mock_row = MagicMock()
    mock_row.id = uuid4()
    mock_row.name = "Active Campaign"

    async def fake_execute(query, params=None):
        if params and isinstance(params, dict) and "status" in params:
            captured_status.append(params["status"])
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        return mock_result

    mock_db = AsyncMock()
    mock_db.execute = fake_execute
    mock_db.commit = AsyncMock()

    engine = CampaignSuggesterEngine()
    await engine.create_suggested_campaigns(
        db=mock_db,
        client_id=client_id,
        suggestions=suggestions,
        auto_activate=True,
    )

    assert captured_status, "No DB execute called with 'status' param"
    assert all(s == "active" for s in captured_status), (
        f"Expected status='active' when auto_activate=True but got: {captured_status}"
    )


# ============================================
# G7/G8: score_promoted_leads_task unit tests
# ============================================


@pytest.mark.asyncio
async def test_score_promoted_leads_task_scores_unscored_leads():
    """
    G7/G8: score_promoted_leads_task should call ScorerEngine.score_lead
    for each unscored lead and update propensity_score + enriched_at.
    """
    from src.orchestration.flows.post_onboarding_flow import score_promoted_leads_task

    client_id = uuid4()
    lead_id_1 = uuid4()
    lead_id_2 = uuid4()

    # DB session 1: fetch unscored lead ids
    mock_db_fetch = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = [(lead_id_1,), (lead_id_2,)]
    mock_db_fetch.execute = AsyncMock(return_value=fetch_result)

    # DB session 2: per-lead score+update
    mock_db_score = AsyncMock()
    mock_db_score.execute = AsyncMock(return_value=MagicMock())
    mock_db_score.commit = AsyncMock()

    _sessions = [mock_db_fetch, mock_db_score]
    _idx = [0]

    @asynccontextmanager
    async def mock_get_session():
        db = _sessions[_idx[0]]
        _idx[0] = min(_idx[0] + 1, len(_sessions) - 1)  # reuse last for extra calls
        yield db

    mock_scorer_instance = MagicMock()
    mock_scorer_instance.score_lead = AsyncMock(
        return_value=EngineResult.ok(
            data={"propensity_score": 72, "als_tier": "warm"},
            metadata={},
        )
    )

    with patch(
        "src.orchestration.flows.post_onboarding_flow.get_db_session",
        mock_get_session,
    ), patch(
        "src.engines.scorer.ScorerEngine",
        return_value=mock_scorer_instance,
    ):
        result = await score_promoted_leads_task.fn(client_id=client_id)

    assert result["success"] is True
    assert result["scored"] == 2
    assert result["failed"] == 0
    assert mock_scorer_instance.score_lead.call_count == 2


@pytest.mark.asyncio
async def test_score_promoted_leads_task_no_leads():
    """
    G7/G8: score_promoted_leads_task handles no unscored leads gracefully.
    """
    from src.orchestration.flows.post_onboarding_flow import score_promoted_leads_task

    client_id = uuid4()

    mock_db = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = []
    mock_db.execute = AsyncMock(return_value=fetch_result)

    @asynccontextmanager
    async def mock_get_session():
        yield mock_db

    with patch(
        "src.orchestration.flows.post_onboarding_flow.get_db_session",
        mock_get_session,
    ):
        result = await score_promoted_leads_task.fn(client_id=client_id)

    assert result["success"] is True
    assert result["scored"] == 0
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_score_promoted_leads_task_handles_scorer_exception():
    """
    G7/G8: score_promoted_leads_task must not raise even if ScorerEngine throws.
    Failure is recorded per-lead; execution continues.
    """
    from src.orchestration.flows.post_onboarding_flow import score_promoted_leads_task

    client_id = uuid4()
    lead_id_1 = uuid4()

    mock_db_fetch = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = [(lead_id_1,)]
    mock_db_fetch.execute = AsyncMock(return_value=fetch_result)

    mock_db_score = AsyncMock()
    mock_db_score.execute = AsyncMock(return_value=MagicMock())
    mock_db_score.commit = AsyncMock()

    _sessions = [mock_db_fetch, mock_db_score]
    _idx = [0]

    @asynccontextmanager
    async def mock_get_session():
        db = _sessions[_idx[0]]
        _idx[0] = min(_idx[0] + 1, len(_sessions) - 1)
        yield db

    mock_scorer_instance = MagicMock()
    mock_scorer_instance.score_lead = AsyncMock(side_effect=RuntimeError("DB timeout"))

    with patch(
        "src.orchestration.flows.post_onboarding_flow.get_db_session",
        mock_get_session,
    ), patch(
        "src.engines.scorer.ScorerEngine",
        return_value=mock_scorer_instance,
    ):
        result = await score_promoted_leads_task.fn(client_id=client_id)

    assert result["success"] is True
    assert result["scored"] == 0
    assert result["failed"] == 1
    assert "DB timeout" in result["errors"][0]["error"]


@pytest.mark.asyncio
async def test_post_onboarding_flow_calls_scoring_after_promotion():
    """
    G7/G8: post_onboarding_setup_flow must invoke score_promoted_leads_task
    after promote_pool_leads_to_leads_task when leads_promoted > 0.
    Result dict must include leads_scored key.
    """
    from src.orchestration.flows.post_onboarding_flow import post_onboarding_setup_flow

    client_id = str(uuid4())

    mock_score = AsyncMock(return_value={"success": True, "scored": 5, "failed": 0})

    # TierConfig is a dataclass (not subscriptable). Mock the lookup to return a plain dict.
    mock_tier_config = {"leads_per_month": 100}
    mock_tier_cfg_map = {"velocity": mock_tier_config, "ignition": mock_tier_config}

    with patch(
        "src.orchestration.flows.post_onboarding_flow.verify_icp_ready_task",
        new=AsyncMock(return_value={"ready": True, "tier": "velocity", "icp": {"industries": ["tech"]}}),
    ), patch(
        "src.orchestration.flows.post_onboarding_flow.generate_campaign_suggestions_task",
        new=AsyncMock(return_value={"success": True, "suggestions": []}),
    ), patch(
        "src.orchestration.flows.post_onboarding_flow.promote_pool_leads_to_leads_task",
        new=AsyncMock(return_value={"success": True, "promoted": 5, "skipped": 0, "errors": []}),
    ), patch(
        "src.orchestration.flows.post_onboarding_flow.score_promoted_leads_task",
        new=mock_score,
    ), patch(
        "src.orchestration.flows.post_onboarding_flow.update_onboarding_status_task",
        new=AsyncMock(return_value=True),
    ), patch(
        "src.config.tiers.TIER_CONFIG",
        mock_tier_cfg_map,
    ), patch(
        "src.orchestration.flows.post_onboarding_flow.get_db_session",
    ) as mock_session:

        mock_db = AsyncMock()

        @asynccontextmanager
        async def _session():
            yield mock_db

        mock_session.side_effect = _session

        result = await post_onboarding_setup_flow.fn(
            client_id=client_id,
            auto_create_campaigns=False,
            auto_source_leads=False,
            bypass_gates=True,
        )

    # score_promoted_leads_task MUST have been called
    mock_score.assert_called_once()

    # result must include leads_scored
    assert result.get("leads_scored") == 5, (
        f"Expected leads_scored=5 in result but got: {result.get('leads_scored')}"
    )


# ============================================
# G6: Error attribution tests
# ============================================


@pytest.mark.asyncio
async def test_post_onboarding_error_has_failed_at_on_icp_failure():
    """
    G6: When verify_icp_ready_task returns not ready,
    result dict must include failed_at='verify_icp_ready_task'.
    """
    from src.orchestration.flows.post_onboarding_flow import post_onboarding_setup_flow

    client_id = str(uuid4())

    with patch(
        "src.orchestration.flows.post_onboarding_flow.verify_icp_ready_task",
        new=AsyncMock(return_value={"ready": False, "error": "No ICP data configured"}),
    ), patch(
        "src.orchestration.flows.post_onboarding_flow.get_db_session",
    ) as mock_session:
        mock_db = AsyncMock()

        @asynccontextmanager
        async def _session():
            yield mock_db

        mock_session.side_effect = _session

        result = await post_onboarding_setup_flow.fn(
            client_id=client_id,
            bypass_gates=True,
        )

    assert result["success"] is False
    assert result.get("failed_at") == "verify_icp_ready_task", (
        f"Expected failed_at='verify_icp_ready_task' but got: {result.get('failed_at')}"
    )


@pytest.mark.asyncio
async def test_post_onboarding_error_has_failed_at_on_exception():
    """
    G6: When an unexpected exception occurs in post_onboarding_setup_flow,
    result dict must include a 'failed_at' key.
    """
    from src.orchestration.flows.post_onboarding_flow import post_onboarding_setup_flow

    client_id = str(uuid4())

    with patch(
        "src.orchestration.flows.post_onboarding_flow.verify_icp_ready_task",
        new=AsyncMock(side_effect=RuntimeError("Unexpected DB error")),
    ), patch(
        "src.orchestration.flows.post_onboarding_flow.get_db_session",
    ) as mock_session:
        mock_db = AsyncMock()

        @asynccontextmanager
        async def _session():
            yield mock_db

        mock_session.side_effect = _session

        result = await post_onboarding_setup_flow.fn(
            client_id=client_id,
            bypass_gates=True,
        )

    assert result["success"] is False
    assert "failed_at" in result, (
        f"Expected 'failed_at' key in error result but got keys: {list(result.keys())}"
    )
    assert "Unexpected DB error" in result["error"]
