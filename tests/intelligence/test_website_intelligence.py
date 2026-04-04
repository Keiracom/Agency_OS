"""
Tests for src/intelligence/website_intelligence.py

All tests use mocked AnthropicClient — no real API calls.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import AISpendLimitError, APIError
from src.intelligence.website_intelligence import WebsiteIntelligence, WebsiteIntelligenceEngine


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_client(content: str = "{}", cost_aud: float = 0.001) -> MagicMock:
    """Return a mocked AnthropicClient whose complete() returns `content`."""
    client = MagicMock()
    client.complete = AsyncMock(
        return_value={
            "content": content,
            "cost_aud": cost_aud,
            "input_tokens": 100,
            "output_tokens": 50,
        }
    )
    return client


def make_engine(content: str = "{}") -> WebsiteIntelligenceEngine:
    return WebsiteIntelligenceEngine(make_client(content))


SAMPLE_HTML = """
<html>
<head>
  <title>Pymble Dental | Family Dentist</title>
  <meta name="description" content="Award-winning family dentistry in Pymble">
  <script>var ga = window.ga || function(){};</script>
  <style>body { color: red; }</style>
</head>
<body>
  <h1>Welcome to Pymble Dental</h1>
  <p>We offer teeth cleaning, whitening and implants.</p>
  <footer>Contact us at info@pymbledental.com.au</footer>
</body>
</html>
"""


# ── 1. _extract_visible_text strips scripts ────────────────────────────────────

def test_extract_visible_text_strips_scripts():
    html = "<html><script>var x = 'secret';</script><body><p>Visible text</p></body></html>"
    result = WebsiteIntelligenceEngine._extract_visible_text(html)
    assert "secret" not in result
    assert "Visible text" in result


# ── 2. _extract_visible_text truncates to max_chars ───────────────────────────

def test_extract_visible_text_truncates_to_3000():
    long_text = "A" * 50_000
    html = f"<html><body><p>{long_text}</p></body></html>"
    result = WebsiteIntelligenceEngine._extract_visible_text(html, max_chars=3000)
    # The Page text: section must not exceed 3000 chars of body text
    # Total output may be slightly larger due to prefix lines (Title/H1 etc)
    # but the body portion is capped at max_chars
    assert len(result) < 4000  # generous bound accounting for prefix


# ── 3. _parse_haiku_json handles markdown fences ──────────────────────────────

def test_parse_haiku_json_handles_markdown_fences():
    raw = '```json\n{"services": ["plumbing"], "business_type": "agency"}\n```'
    result = WebsiteIntelligenceEngine._parse_haiku_json(
        raw, ["services", "business_type"]
    )
    assert result["services"] == ["plumbing"]
    assert result["business_type"] == "agency"


# ── 4. _parse_haiku_json returns empty dict on bad JSON ───────────────────────

def test_parse_haiku_json_returns_defaults_on_bad_json():
    bad_inputs = [
        "not json at all",
        "",
        "```\nbroken { json\n```",
        '{"key": }',  # invalid
    ]
    for bad in bad_inputs:
        result = WebsiteIntelligenceEngine._parse_haiku_json(bad, ["services", "business_type"])
        assert isinstance(result, dict), f"Expected dict for input: {bad!r}"
        # No exception raised — safe defaults (empty dict)


# ── 5. analyze returns fallback on API error ──────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_returns_fallback_on_api_error():
    client = MagicMock()
    client.complete = AsyncMock(side_effect=APIError(
        service="anthropic", status_code=500, message="server error"
    ))
    engine = WebsiteIntelligenceEngine(client)
    result = await engine.analyze("example.com.au", SAMPLE_HTML, {})
    assert isinstance(result, WebsiteIntelligence)
    assert result.fallback_used is True
    assert result.intent_grade == "WARM"  # safe default


# ── 6. analyze returns fallback on spend limit ────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_returns_fallback_on_spend_limit():
    client = MagicMock()
    client.complete = AsyncMock(side_effect=AISpendLimitError(
        spent=10.0, limit=5.0, message="limit exceeded"
    ))
    engine = WebsiteIntelligenceEngine(client)
    result = await engine.analyze("example.com.au", SAMPLE_HTML, {})
    assert isinstance(result, WebsiteIntelligence)
    assert result.fallback_used is True
    assert result.gmb_opportunity_score == 50  # neutral fallback


# ── 7. comprehend_website parses services ─────────────────────────────────────

@pytest.mark.asyncio
async def test_comprehend_website_parses_services():
    payload = {
        "services": ["dental implants", "teeth whitening", "family dentistry"],
        "business_type": "unknown",
        "team_size_signal": "small",
        "is_actively_marketing": True,
        "comprehension_confidence": 0.9,
    }
    engine = make_engine(json.dumps(payload))
    result = await engine.comprehend_website("pymbledental.com.au", SAMPLE_HTML)
    assert result["services"] == ["dental implants", "teeth whitening", "family dentistry"]
    assert result["team_size_signal"] == "small"
    assert result["is_actively_marketing"] is True
    assert result["comprehension_confidence"] == pytest.approx(0.9)


# ── 8. grade_intent returns HOT, WARM, or COLD only ──────────────────────────

@pytest.mark.asyncio
async def test_grade_intent_returns_hot_warm_cold():
    valid_grades = ("HOT", "WARM", "COLD")

    for grade in valid_grades:
        payload = {"intent_grade": grade, "intent_reasoning": "some reason"}
        engine = make_engine(json.dumps(payload))
        result = await engine.grade_intent(
            "example.com.au",
            comprehension={"services": [], "business_type": "unknown",
                           "team_size_signal": "unknown", "is_actively_marketing": False},
            intent_signals={},
        )
        assert result["intent_grade"] == grade

    # Invalid grade should fall back to WARM
    engine = make_engine('{"intent_grade": "SCORCHING", "intent_reasoning": "test"}')
    result = await engine.grade_intent(
        "example.com.au",
        comprehension={"services": [], "business_type": "unknown",
                       "team_size_signal": "unknown", "is_actively_marketing": False},
        intent_signals={},
    )
    assert result["intent_grade"] == "WARM"


# ── 9. analyze_gmb handles missing review snippets ───────────────────────────

@pytest.mark.asyncio
async def test_analyze_gmb_handles_missing_review_snippets():
    payload = {"gmb_pain_themes": ["missing digital presence"], "gmb_opportunity_score": 72}
    engine = make_engine(json.dumps(payload))

    # gmb_data without gmb_review_snippets key
    gmb_data = {"gmb_rating": 3.8, "gmb_review_count": 4}
    result = await engine.analyze_gmb("example.com.au", gmb_data)

    assert result["gmb_pain_themes"] == ["missing digital presence"]
    assert result["gmb_opportunity_score"] == 72
    # Should not raise even though gmb_review_snippets is absent
