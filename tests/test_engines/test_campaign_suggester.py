"""
FILE: tests/test_engines/test_campaign_suggester.py
PURPOSE: Unit tests for CampaignSuggesterEngine — prompt hardening, parse retry,
         sparse ICP handling (Directive #189)
PHASE: 37
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.engines.campaign_suggester import CampaignSuggesterEngine, CampaignSuggestion


# ============================================
# Helpers
# ============================================

VALID_SUGGESTIONS_JSON = json.dumps([
    {
        "name": "C-Suite Decision Makers",
        "description": "CEOs and MDs at SMBs",
        "target_industries": ["Professional Services"],
        "target_titles": ["CEO", "MD"],
        "target_company_sizes": ["11-50"],
        "target_locations": ["Australia"],
        "lead_allocation_pct": 60,
        "ai_reasoning": "High budget authority",
        "priority": 1,
    },
    {
        "name": "Operations Leaders",
        "description": "COOs at mid-market companies",
        "target_industries": ["Professional Services"],
        "target_titles": ["COO"],
        "target_company_sizes": ["51-200"],
        "target_locations": ["Australia"],
        "lead_allocation_pct": 40,
        "ai_reasoning": "Fast decision cycles",
        "priority": 2,
    },
])

PROSE_PLUS_JSON = (
    "Here are my campaign suggestions based on the provided ICP data:\n\n"
    + VALID_SUGGESTIONS_JSON
    + "\n\nI hope these suggestions are helpful!"
)

FENCED_JSON = f"```json\n{VALID_SUGGESTIONS_JSON}\n```"

UNPARSEABLE_RESPONSE = "I'm sorry, I cannot generate campaign suggestions without more data."


def _make_client(
    *,
    industries=None,
    titles=None,
    company_sizes=None,
    locations=None,
    pain_points=None,
    keywords=None,
    exclusions=None,
    services=None,
    value_prop=None,
):
    """Build a mock Client with controllable ICP fields."""
    client = MagicMock()
    client.id = uuid4()
    client.name = "Test Agency"
    client.tier = MagicMock()
    client.tier.value = "ignition"
    client.icp_industries = industries
    client.icp_titles = titles
    client.icp_company_sizes = company_sizes
    client.icp_locations = locations
    client.icp_pain_points = pain_points
    client.icp_keywords = keywords
    client.icp_exclusions = exclusions
    client.services_offered = services
    client.value_proposition = value_prop
    return client


def _make_anthropic_response(text: str):
    """Build a mock Anthropic response object."""
    msg = MagicMock()
    content_block = MagicMock()
    content_block.text = text
    msg.content = [content_block]
    return msg


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def engine():
    return CampaignSuggesterEngine()


# ============================================
# _parse_suggestions — FIX 4 (response cleaning)
# ============================================

class TestParseSuggestions:
    def test_parses_clean_json_array(self, engine):
        result = engine._parse_suggestions(VALID_SUGGESTIONS_JSON, 2)
        assert result is not None
        assert len(result) == 2
        assert result[0].name == "C-Suite Decision Makers"
        assert result[0].lead_allocation_pct == 60

    def test_parses_fenced_json(self, engine):
        """Already handled by existing fence-stripping logic."""
        result = engine._parse_suggestions(FENCED_JSON, 2)
        assert result is not None
        assert len(result) == 2

    def test_parses_prose_plus_json(self, engine):
        """FIX 4: Claude adds preamble/postamble — must extract array."""
        result = engine._parse_suggestions(PROSE_PLUS_JSON, 2)
        assert result is not None, "Should extract JSON array from prose-wrapped response"
        assert len(result) == 2
        assert result[1].name == "Operations Leaders"

    def test_returns_none_for_unparseable(self, engine):
        result = engine._parse_suggestions(UNPARSEABLE_RESPONSE, 2)
        assert result is None

    def test_returns_none_for_empty_string(self, engine):
        result = engine._parse_suggestions("", 2)
        assert result is None

    def test_truncates_to_expected_count(self, engine):
        """Slices to expected_count even if Claude returns more."""
        result = engine._parse_suggestions(VALID_SUGGESTIONS_JSON, 1)
        assert result is not None
        assert len(result) == 1

    def test_field_defaults_on_missing_keys(self, engine):
        """Each field uses .get() with sensible defaults."""
        minimal = json.dumps([{"lead_allocation_pct": 100}])
        result = engine._parse_suggestions(minimal, 1)
        assert result is not None
        assert result[0].name == "Campaign 1"
        assert result[0].target_locations == ["Australia"]
        assert result[0].priority == 1

    def test_logs_warning_on_preamble(self, engine, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="src.engines.campaign_suggester"):
            engine._parse_suggestions(PROSE_PLUS_JSON, 2)
        assert any("preamble" in r.message for r in caplog.records)


# ============================================
# _build_prompt — FIX 2 (sparse ICP note)
# ============================================

class TestBuildPrompt:
    def test_no_sparse_note_when_data_rich(self, engine):
        client = _make_client(
            industries=["SaaS"],
            titles=["CEO"],
            company_sizes=["11-50"],
            locations=["Australia"],
            pain_points=["lead gen"],
            keywords=["growth"],
            exclusions=["enterprise"],
            services=["SEO"],
            value_prop="We grow revenue",
        )
        prompt = engine._build_prompt(client, 3)
        assert "limited ICP data" not in prompt

    def test_sparse_note_injected_when_5_plus_fields_empty(self, engine):
        """Only industries populated — 7 fields empty → sparse note required."""
        client = _make_client(industries=["Digital Marketing"])
        prompt = engine._build_prompt(client, 3)
        assert "limited ICP data" in prompt
        assert "Prioritise practical over specific" in prompt

    def test_no_sparse_note_when_exactly_4_empty(self, engine):
        """4 empty fields — just below threshold, no sparse note."""
        client = _make_client(
            industries=["SaaS"],
            titles=["CEO"],
            company_sizes=["11-50"],
            locations=["Australia"],
            services=["CRM"],
            # pain_points, keywords, exclusions, value_prop all None → 4 empty
        )
        prompt = engine._build_prompt(client, 3)
        assert "limited ICP data" not in prompt

    def test_prompt_contains_critical_instruction(self, engine):
        """FIX 1: CRITICAL JSON-only instruction must be in every prompt."""
        client = _make_client(industries=["SaaS"], titles=["CEO"])
        prompt = engine._build_prompt(client, 2)
        assert "CRITICAL: Respond with ONLY a valid JSON array" in prompt
        assert "json.loads()" in prompt

    def test_fallback_values_used_for_none_fields(self, engine):
        client = _make_client(industries=["Tech"])
        prompt = engine._build_prompt(client, 2)
        assert "Decision makers" in prompt  # icp_titles fallback
        assert "Australia" in prompt         # icp_locations fallback


# ============================================
# _get_ai_suggestions — FIX 3 (parse retry)
# ============================================

class TestGetAiSuggestions:
    @pytest.mark.asyncio
    async def test_returns_suggestions_on_clean_first_response(self, engine):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_anthropic_response(VALID_SUGGESTIONS_JSON)
        )
        with patch("src.engines.campaign_suggester.get_anthropic_client", return_value=mock_client):
            result = await engine._get_ai_suggestions("test prompt", 2)
        assert result is not None
        assert len(result) == 2
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_on_first_parse_failure(self, engine):
        """FIX 3: First call returns garbage, second returns valid JSON → retry fires."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=[
            _make_anthropic_response(UNPARSEABLE_RESPONSE),
            _make_anthropic_response(VALID_SUGGESTIONS_JSON),
        ])
        with patch("src.engines.campaign_suggester.get_anthropic_client", return_value=mock_client):
            result = await engine._get_ai_suggestions("test prompt", 2)
        assert result is not None
        assert len(result) == 2
        assert mock_client.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_prompt_contains_nudge(self, engine):
        """Retry call must include the explicit 'only JSON array' nudge."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=[
            _make_anthropic_response(UNPARSEABLE_RESPONSE),
            _make_anthropic_response(VALID_SUGGESTIONS_JSON),
        ])
        with patch("src.engines.campaign_suggester.get_anthropic_client", return_value=mock_client):
            await engine._get_ai_suggestions("base prompt", 2)
        retry_call_kwargs = mock_client.messages.create.call_args_list[1]
        retry_content = retry_call_kwargs[1]["messages"][0]["content"]
        assert "could not be parsed as JSON" in retry_content
        assert "Return ONLY a JSON array" in retry_content

    @pytest.mark.asyncio
    async def test_returns_none_when_both_attempts_fail(self, engine):
        """FIX 3: Both calls garbage → return None (existing fallback takes over)."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_anthropic_response(UNPARSEABLE_RESPONSE)
        )
        with patch("src.engines.campaign_suggester.get_anthropic_client", return_value=mock_client):
            result = await engine._get_ai_suggestions("test prompt", 2)
        assert result is None
        assert mock_client.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_prose_wrapped_response_succeeds_without_retry(self, engine):
        """FIX 4 saves a retry call: prose+JSON parsed successfully on first attempt."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_anthropic_response(PROSE_PLUS_JSON)
        )
        with patch("src.engines.campaign_suggester.get_anthropic_client", return_value=mock_client):
            result = await engine._get_ai_suggestions("test prompt", 2)
        assert result is not None
        assert len(result) == 2
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self, engine):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("Network error"))
        with patch("src.engines.campaign_suggester.get_anthropic_client", return_value=mock_client):
            result = await engine._get_ai_suggestions("test prompt", 2)
        assert result is None


# ============================================
# Integration: sparse ICP end-to-end
# ============================================

class TestSparseIcpIntegration:
    @pytest.mark.asyncio
    async def test_sparse_icp_returns_valid_suggestions(self, engine):
        """
        Directive #189 core case: only icp_industries populated, everything else None.
        Must return valid suggestions, not None.
        """
        mock_db = AsyncMock()
        sparse_client = _make_client(industries=["Digital Marketing"])
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sparse_client)))

        mock_anthropic = AsyncMock()
        mock_anthropic.messages.create = AsyncMock(
            return_value=_make_anthropic_response(VALID_SUGGESTIONS_JSON)
        )

        with (
            patch("src.engines.campaign_suggester.get_anthropic_client", return_value=mock_anthropic),
            patch("src.config.tiers.get_campaign_slots", return_value=(2, 2)),
        ):
            result = await engine.suggest_campaigns(mock_db, sparse_client.id)

        assert result.success
        assert result.data is not None
        assert len(result.data["suggestions"]) == 2

    @pytest.mark.asyncio
    async def test_sparse_icp_prompt_includes_broad_note(self, engine):
        """Sparse ICP prompt must tell Claude to be broad, not specific."""
        sparse_client = _make_client(industries=["Digital Marketing"])
        prompt = engine._build_prompt(sparse_client, 2)
        assert "limited ICP data" in prompt
        assert "Prioritise practical over specific" in prompt
        assert "CRITICAL: Respond with ONLY a valid JSON array" in prompt
