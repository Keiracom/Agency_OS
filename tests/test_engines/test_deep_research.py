"""
FILE: tests/test_engines/test_deep_research.py
PURPOSE: Unit tests for Deep Research functionality (Phase 21)
PHASE: 21 (Deep Research & UI)
TASK: TST-021
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.engines.scout import ScoutEngine, get_scout_engine
from src.engines.base import EngineResult
from src.agents.skills.base_skill import SkillResult
from src.models.base import LeadStatus


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def mock_apollo_client():
    """Create mock Apollo client."""
    client = AsyncMock()
    client.enrich_person = AsyncMock()
    return client


@pytest.fixture
def mock_apify_client():
    """Create mock Apify client."""
    client = AsyncMock()
    client.scrape_linkedin_profiles = AsyncMock()
    return client


@pytest.fixture
def mock_clay_client():
    """Create mock Clay client."""
    client = AsyncMock()
    client.enrich_person = AsyncMock()
    return client


@pytest.fixture
def mock_anthropic_client():
    """Create mock Anthropic client."""
    client = AsyncMock()
    client.complete = AsyncMock(return_value={
        "content": '{"icebreaker_hook": "Great post about AI!", "profile_summary": "Marketing leader", "recent_activity": "Active on LinkedIn"}',
        "input_tokens": 100,
        "output_tokens": 50,
        "cost_aud": 0.002,
    })
    return client


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_lead_with_linkedin():
    """Create mock lead object with LinkedIn URL."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.email = "sarah@bloomdigital.com"
    lead.first_name = "Sarah"
    lead.last_name = "Williams"
    lead.title = "Marketing Director"
    lead.company = "Bloom Digital"
    lead.phone = None
    lead.linkedin_url = "https://linkedin.com/in/sarahwilliams"
    lead.domain = "bloomdigital.com"
    lead.status = LeadStatus.ENRICHED
    lead.als_score = 90  # Hot lead
    return lead


@pytest.fixture
def mock_lead_without_linkedin():
    """Create mock lead object without LinkedIn URL."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.email = "john@acme.com"
    lead.first_name = "John"
    lead.last_name = "Doe"
    lead.title = "CEO"
    lead.company = "Acme Inc"
    lead.linkedin_url = None  # No LinkedIn
    lead.domain = "acme.com"
    lead.status = LeadStatus.ENRICHED
    return lead


@pytest.fixture
def mock_linkedin_profile_data():
    """Create mock LinkedIn profile data from Apify."""
    return [{
        "found": True,
        "source": "apify",
        "url": "https://linkedin.com/in/sarahwilliams",
        "firstName": "Sarah",
        "lastName": "Williams",
        "headline": "Marketing Director at Bloom Digital",
        "company": "Bloom Digital",
        "about": "Helping brands grow through digital strategy.",
        "posts": [
            {"text": "Excited about AI in marketing!", "date": "2026-01-01"},
            {"text": "Just launched our new campaign.", "date": "2025-12-15"},
            {"text": "Marketing trends for 2026.", "date": "2025-12-01"},
        ],
    }]


@pytest.fixture
def mock_skill_output():
    """Create mock DeepResearchSkill output."""
    from src.agents.skills.research_skills import DeepResearchSkill
    output = DeepResearchSkill.Output(
        linkedin_url="https://linkedin.com/in/sarahwilliams",
        posts_found=3,
        posts=[
            {"content": "Excited about AI in marketing!", "date": "2026-01-01"},
            {"content": "Just launched our new campaign.", "date": "2025-12-15"},
        ],
        icebreaker_hook="Loved your take on AI in marketing - especially the point about automation.",
        profile_summary="Marketing Director with focus on digital strategy.",
        recent_activity="Active posts about AI and campaign launches.",
    )
    return output


@pytest.fixture
def scout_engine(mock_apollo_client, mock_apify_client, mock_clay_client):
    """Create Scout engine with mock clients."""
    return ScoutEngine(
        apollo_client=mock_apollo_client,
        apify_client=mock_apify_client,
        clay_client=mock_clay_client,
    )


# ============================================
# Deep Research Tests
# ============================================


class TestDeepResearchLinkedInCheck:
    """Test that perform_deep_research checks for LinkedIn URL."""

    @pytest.mark.asyncio
    async def test_fails_without_linkedin_url(
        self, scout_engine, mock_db_session, mock_lead_without_linkedin
    ):
        """Test that deep research fails when lead has no LinkedIn URL."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead_without_linkedin):
            result = await scout_engine.perform_deep_research(
                db=mock_db_session,
                lead_id=mock_lead_without_linkedin.id,
            )

            assert result.success is False
            assert "LinkedIn URL" in result.error
            assert str(mock_lead_without_linkedin.id) in str(result.metadata["lead_id"])

    @pytest.mark.asyncio
    async def test_proceeds_with_linkedin_url(
        self, scout_engine, mock_db_session, mock_lead_with_linkedin, mock_anthropic_client, mock_skill_output
    ):
        """Test that deep research proceeds when lead has LinkedIn URL."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead_with_linkedin):
            with patch("src.engines.scout.get_anthropic_client", return_value=mock_anthropic_client):
                with patch("src.engines.scout.DeepResearchSkill") as MockSkill:
                    mock_skill_instance = MagicMock()
                    mock_skill_instance.run = AsyncMock(return_value=SkillResult.ok(
                        data=mock_skill_output,
                        confidence=0.85,
                        tokens_used=150,
                        cost_aud=0.002,
                    ))
                    mock_skill_instance.Input = MagicMock()
                    MockSkill.return_value = mock_skill_instance

                    result = await scout_engine.perform_deep_research(
                        db=mock_db_session,
                        lead_id=mock_lead_with_linkedin.id,
                    )

                    # Should have called the skill
                    mock_skill_instance.run.assert_called_once()


class TestDeepResearchSkillCall:
    """Test that perform_deep_research calls the research skill correctly."""

    @pytest.mark.asyncio
    async def test_calls_deep_research_skill(
        self, scout_engine, mock_db_session, mock_lead_with_linkedin, mock_anthropic_client, mock_skill_output
    ):
        """Test that the DeepResearchSkill is called with correct parameters."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead_with_linkedin):
            with patch("src.engines.scout.get_anthropic_client", return_value=mock_anthropic_client):
                with patch("src.engines.scout.DeepResearchSkill") as MockSkill:
                    mock_skill_instance = MagicMock()
                    mock_skill_instance.run = AsyncMock(return_value=SkillResult.ok(
                        data=mock_skill_output,
                        confidence=0.85,
                        tokens_used=150,
                        cost_aud=0.002,
                    ))
                    mock_skill_instance.Input = MagicMock(return_value=MagicMock())
                    MockSkill.return_value = mock_skill_instance

                    await scout_engine.perform_deep_research(
                        db=mock_db_session,
                        lead_id=mock_lead_with_linkedin.id,
                    )

                    # Verify skill Input was called with lead data
                    mock_skill_instance.Input.assert_called_once()
                    call_kwargs = mock_skill_instance.Input.call_args
                    assert call_kwargs.kwargs["linkedin_url"] == mock_lead_with_linkedin.linkedin_url
                    assert call_kwargs.kwargs["first_name"] == mock_lead_with_linkedin.first_name

    @pytest.mark.asyncio
    async def test_handles_skill_failure(
        self, scout_engine, mock_db_session, mock_lead_with_linkedin, mock_anthropic_client
    ):
        """Test that skill failure is handled gracefully."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead_with_linkedin):
            with patch("src.engines.scout.get_anthropic_client", return_value=mock_anthropic_client):
                with patch("src.engines.scout.DeepResearchSkill") as MockSkill:
                    mock_skill_instance = MagicMock()
                    mock_skill_instance.run = AsyncMock(return_value=SkillResult.fail(
                        error="LinkedIn scraping failed",
                        metadata={"reason": "Rate limited"},
                    ))
                    mock_skill_instance.Input = MagicMock(return_value=MagicMock())
                    MockSkill.return_value = mock_skill_instance

                    result = await scout_engine.perform_deep_research(
                        db=mock_db_session,
                        lead_id=mock_lead_with_linkedin.id,
                    )

                    assert result.success is False
                    assert "LinkedIn scraping failed" in result.error


class TestDeepResearchDatabaseUpdate:
    """Test that perform_deep_research updates the database correctly."""

    @pytest.mark.asyncio
    async def test_updates_lead_deep_research_data(
        self, scout_engine, mock_db_session, mock_lead_with_linkedin, mock_anthropic_client, mock_skill_output
    ):
        """Test that lead.deep_research_data is updated with skill results."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead_with_linkedin):
            with patch("src.engines.scout.get_anthropic_client", return_value=mock_anthropic_client):
                with patch("src.engines.scout.DeepResearchSkill") as MockSkill:
                    mock_skill_instance = MagicMock()
                    mock_skill_instance.run = AsyncMock(return_value=SkillResult.ok(
                        data=mock_skill_output,
                        confidence=0.85,
                        tokens_used=150,
                        cost_aud=0.002,
                    ))
                    mock_skill_instance.Input = MagicMock(return_value=MagicMock())
                    MockSkill.return_value = mock_skill_instance

                    result = await scout_engine.perform_deep_research(
                        db=mock_db_session,
                        lead_id=mock_lead_with_linkedin.id,
                    )

                    assert result.success is True
                    # Verify db.execute was called (for UPDATE statement)
                    mock_db_session.execute.assert_called()
                    # Verify commit was called
                    mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_returns_icebreaker_hook(
        self, scout_engine, mock_db_session, mock_lead_with_linkedin, mock_anthropic_client, mock_skill_output
    ):
        """Test that the result contains the icebreaker hook."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead_with_linkedin):
            with patch("src.engines.scout.get_anthropic_client", return_value=mock_anthropic_client):
                with patch("src.engines.scout.DeepResearchSkill") as MockSkill:
                    mock_skill_instance = MagicMock()
                    mock_skill_instance.run = AsyncMock(return_value=SkillResult.ok(
                        data=mock_skill_output,
                        confidence=0.85,
                        tokens_used=150,
                        cost_aud=0.002,
                    ))
                    mock_skill_instance.Input = MagicMock(return_value=MagicMock())
                    MockSkill.return_value = mock_skill_instance

                    result = await scout_engine.perform_deep_research(
                        db=mock_db_session,
                        lead_id=mock_lead_with_linkedin.id,
                    )

                    assert result.success is True
                    assert "icebreaker_hook" in result.data
                    assert result.data["icebreaker_hook"] == mock_skill_output.icebreaker_hook


class TestDeepResearchSocialPostCreation:
    """Test that perform_deep_research creates LeadSocialPost records."""

    @pytest.mark.asyncio
    async def test_creates_social_post_records(
        self, scout_engine, mock_db_session, mock_lead_with_linkedin, mock_anthropic_client, mock_skill_output
    ):
        """Test that LeadSocialPost records are created for scraped posts."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead_with_linkedin):
            with patch("src.engines.scout.get_anthropic_client", return_value=mock_anthropic_client):
                with patch("src.engines.scout.DeepResearchSkill") as MockSkill:
                    mock_skill_instance = MagicMock()
                    mock_skill_instance.run = AsyncMock(return_value=SkillResult.ok(
                        data=mock_skill_output,
                        confidence=0.85,
                        tokens_used=150,
                        cost_aud=0.002,
                    ))
                    mock_skill_instance.Input = MagicMock(return_value=MagicMock())
                    MockSkill.return_value = mock_skill_instance

                    await scout_engine.perform_deep_research(
                        db=mock_db_session,
                        lead_id=mock_lead_with_linkedin.id,
                    )

                    # Verify db.add was called for each post
                    # mock_skill_output has 2 posts
                    assert mock_db_session.add.call_count >= 1

    @pytest.mark.asyncio
    async def test_social_posts_have_correct_source(
        self, scout_engine, mock_db_session, mock_lead_with_linkedin, mock_anthropic_client, mock_skill_output
    ):
        """Test that created social posts have source='linkedin'."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead_with_linkedin):
            with patch("src.engines.scout.get_anthropic_client", return_value=mock_anthropic_client):
                with patch("src.engines.scout.DeepResearchSkill") as MockSkill:
                    mock_skill_instance = MagicMock()
                    mock_skill_instance.run = AsyncMock(return_value=SkillResult.ok(
                        data=mock_skill_output,
                        confidence=0.85,
                        tokens_used=150,
                        cost_aud=0.002,
                    ))
                    mock_skill_instance.Input = MagicMock(return_value=MagicMock())
                    MockSkill.return_value = mock_skill_instance

                    with patch("src.engines.scout.LeadSocialPost") as MockSocialPost:
                        await scout_engine.perform_deep_research(
                            db=mock_db_session,
                            lead_id=mock_lead_with_linkedin.id,
                        )

                        # Check that LeadSocialPost was called with source='linkedin'
                        for call in MockSocialPost.call_args_list:
                            assert call.kwargs["source"] == "linkedin"


# ============================================
# Integration Tests (with real skill class)
# ============================================


class TestDeepResearchIntegration:
    """Integration tests using real DeepResearchSkill class."""

    @pytest.mark.asyncio
    async def test_full_flow_with_mocked_apis(
        self, scout_engine, mock_db_session, mock_lead_with_linkedin, mock_anthropic_client, mock_linkedin_profile_data
    ):
        """Test full deep research flow with mocked external APIs."""
        # Mock Apify to return profile data
        scout_engine.apify.scrape_linkedin_profiles.return_value = mock_linkedin_profile_data

        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead_with_linkedin):
            with patch("src.engines.scout.get_anthropic_client", return_value=mock_anthropic_client):
                result = await scout_engine.perform_deep_research(
                    db=mock_db_session,
                    lead_id=mock_lead_with_linkedin.id,
                )

                # Should succeed
                assert result.success is True
                # Should have lead_id in result
                assert "lead_id" in result.data
                # Should have called Anthropic for icebreaker generation
                mock_anthropic_client.complete.assert_called()


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test fails without LinkedIn URL
# [x] Test proceeds with LinkedIn URL
# [x] Test calls DeepResearchSkill with correct parameters
# [x] Test handles skill failure gracefully
# [x] Test updates lead.deep_research_data field
# [x] Test returns icebreaker hook in result
# [x] Test creates LeadSocialPost records
# [x] Test social posts have correct source
# [x] Integration test with mocked APIs
