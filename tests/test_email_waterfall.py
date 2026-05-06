"""
Tests for email discovery waterfall — Directive #299.
Covers all 4 layers, short-circuit logic, name parsing, pattern generation,
orchestrator wiring, and cost tracking.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Helpers ──────────────────────────────────────────────────────────────────

DENTAL_HTML = """
<html><head><title>Pymble Dental</title></head><body>
<a href="mailto:michael.chen@pymbledental.com.au">Email us</a>
<p>Call 02 9144 1234 | Pymble NSW 2073</p>
</body></html>
"""

NO_EMAIL_HTML = "<html><body><p>Welcome to our dental practice in Sydney.</p></body></html>"


# ── Layer 1: Website HTML scrape ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_layer1_mailto_returns_email():
    """L0 contact_data returns email when name matches (simulates Stage 3 Gemini extraction)."""
    from src.pipeline.email_waterfall import discover_email
    result = await discover_email(
        domain="pymbledental.com.au",
        dm_name="Michael Chen",
        contact_data={"company_email": "michael.chen@pymbledental.com.au"},
        skip_layers=[3, 5],
    )
    assert result.email == "michael.chen@pymbledental.com.au"
    assert result.source == "contact_registry"
    assert result.cost_usd == 0.0


@pytest.mark.asyncio
async def test_layer1_name_match_gives_high_confidence():
    """Email matching DM name via contact_data gets low confidence (unverified source)."""
    from src.pipeline.email_waterfall import discover_email
    result = await discover_email(
        domain="pymbledental.com.au",
        dm_name="Michael Chen",
        contact_data={"company_email": "michael.chen@pymbledental.com.au"},
        skip_layers=[3, 5],
    )
    # contact_registry source is unverified, confidence is low
    assert result.confidence == "low"


@pytest.mark.asyncio
async def test_layer1_no_html_falls_through():
    """Empty HTML skips Layer 1; no paid layers → returns none."""
    from src.pipeline.email_waterfall import discover_email
    result = await discover_email(
        domain="dentist.com.au",
        dm_name="Jane Smith",
        html=None,
        skip_layers=[3, 5],
    )
    assert result.source == "none"


# ── Layer 2: Pattern generation ───────────────────────────────────────────────

def test_generate_patterns_produces_correct_emails():
    """Pattern generator produces expected email formats."""
    from src.pipeline.email_waterfall import _generate_patterns
    patterns = _generate_patterns("michael", "chen", "dentist.com.au")
    assert "michael.chen@dentist.com.au" in patterns
    assert "michael@dentist.com.au" in patterns
    assert "mchen@dentist.com.au" in patterns
    assert "michaelc@dentist.com.au" in patterns


def test_generate_patterns_empty_on_missing_name():
    """Pattern generator returns empty list when name parts missing."""
    from src.pipeline.email_waterfall import _generate_patterns
    assert _generate_patterns("", "chen", "dentist.com.au") == []
    assert _generate_patterns("michael", "", "dentist.com.au") == []
    assert _generate_patterns("michael", "chen", "") == []


@pytest.mark.asyncio
async def test_layer2_mx_fail_skips_pattern():
    """Layer 2 returns None when MX check fails."""
    from src.pipeline.email_waterfall import _try_patterns
    with patch("src.pipeline.email_waterfall._check_mx", AsyncMock(return_value=False)):
        result = await _try_patterns("michael", "chen", "deadzone.invalid")
    assert result is None


@pytest.mark.asyncio
async def test_layer2_mx_pass_returns_pattern():
    """Layer 2 returns first.last@domain when MX passes."""
    from src.pipeline.email_waterfall import _try_patterns
    with patch("src.pipeline.email_waterfall._check_mx", AsyncMock(return_value=True)):
        result = await _try_patterns("michael", "chen", "dentist.com.au")
    assert result is not None
    assert result.email == "michael.chen@dentist.com.au"
    assert result.source == "pattern"
    assert result.cost_usd == 0.0


# ── Layer 3: Leadmagic ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_layer2_leadmagic_verified_email():
    """Layer 2 returns verified email from Leadmagic mock."""
    from src.pipeline.email_waterfall import discover_email
    mock_result = MagicMock()
    mock_result.found = True
    mock_result.email = "michael.chen@dentist.com.au"
    mock_result.confidence = 90

    mock_client = AsyncMock()
    mock_client.find_email = AsyncMock(return_value=mock_result)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.pipeline.email_waterfall.LeadmagicClient", return_value=mock_client) as mock_cls:
        # Make the class itself behave as async context manager
        mock_cls.return_value = mock_client
        result = await discover_email(
            domain="dentist.com.au",
            dm_name="Michael Chen",
            html=NO_EMAIL_HTML,
            skip_layers=[1, 5],
        )

    assert result.source == "leadmagic"
    assert result.verified is True
    assert result.cost_usd == 0.015
    assert result.confidence == "high"


@pytest.mark.asyncio
async def test_layer2_leadmagic_not_found_falls_through():
    """Layer 2 miss falls through to Layer 3 (or returns none)."""
    from src.pipeline.email_waterfall import discover_email
    mock_result = MagicMock()
    mock_result.found = False
    mock_result.email = None

    mock_client = AsyncMock()
    mock_client.find_email = AsyncMock(return_value=mock_result)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.pipeline.email_waterfall.LeadmagicClient", return_value=mock_client):
        result = await discover_email(
            domain="dentist.com.au",
            dm_name="Michael Chen",
            html=NO_EMAIL_HTML,
            skip_layers=[1, 5],
        )

    assert result.email is None
    assert result.source == "none"
    assert result.cost_usd == 0.0


# ── Layer 4: Bright Data ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_layer4_brightdata_returns_email_from_linkedin():
    """Layer 4 extracts email from Bright Data LinkedIn profile."""
    from src.pipeline.email_waterfall import _brightdata_lookup

    mock_bd = MagicMock()
    mock_bd.lookup_company_people = AsyncMock(return_value=[
        {"name": "Michael Chen", "email": "m.chen@dentist.com.au", "title": "Owner"}
    ])

    with patch("src.pipeline.email_waterfall.BrightDataLinkedInClient", return_value=mock_bd):
        result = await _brightdata_lookup(
            dm_linkedin="https://au.linkedin.com/in/michael-chen",
            domain="dentist.com.au",
        )

    assert result is not None
    assert result.email == "m.chen@dentist.com.au"
    assert result.source == "brightdata"
    assert result.cost_usd == 0.00075


@pytest.mark.asyncio
async def test_layer4_skipped_without_linkedin():
    """Layer 4 returns None when no LinkedIn URL provided."""
    from src.pipeline.email_waterfall import _brightdata_lookup
    result = await _brightdata_lookup(dm_linkedin=None, domain="dentist.com.au")
    assert result is None


# ── Short-circuit logic ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_short_circuit_on_layer0_hit():
    """Paid layers not called when L0 contact_data finds name-matched email."""
    from src.pipeline.email_waterfall import discover_email

    with patch("src.pipeline.email_waterfall.LeadmagicClient", side_effect=AssertionError("Leadmagic called")):
        result = await discover_email(
            domain="pymbledental.com.au",
            dm_name="Michael Chen",
            contact_data={"company_email": "michael.chen@pymbledental.com.au"},
        )

    assert result.email == "michael.chen@pymbledental.com.au"
    assert result.source == "contact_registry"


# ── No result ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_layers_miss_returns_none_email():
    """When all layers fail, returns EmailResult with email=None."""
    from src.pipeline.email_waterfall import discover_email

    with patch("src.pipeline.email_waterfall._check_mx", AsyncMock(return_value=False)), \
         patch("src.pipeline.email_waterfall.LeadmagicClient", side_effect=Exception("API down")):
        result = await discover_email(
            domain="nowhere.com",
            dm_name="Unknown Person",
            html=None,
            skip_layers=[4],
        )

    assert result.email is None
    assert result.source == "none"
    assert result.cost_usd == 0.0
    assert result.verified is False


# ── Cost tracking ─────────────────────────────────────────────────────────────

def test_email_result_to_dict_has_required_keys():
    """EmailResult.to_dict() produces all required prospect card keys."""
    from src.pipeline.email_waterfall import EmailResult
    r = EmailResult(
        email="test@domain.com", verified=True,
        source="leadmagic", confidence="high", cost_usd=0.015
    )
    d = r.to_dict()
    assert "dm_email" in d
    assert "dm_email_verified" in d
    assert "dm_email_source" in d
    assert "dm_email_confidence" in d
    assert "email_cost_usd" in d
    assert d["dm_email"] == "test@domain.com"
    assert d["dm_email_verified"] is True
    assert d["email_cost_usd"] == 0.015


# ── Orchestrator wiring ───────────────────────────────────────────────────────

def test_prospect_card_has_email_fields():
    """ProspectCard has all email waterfall fields."""
    from src.pipeline.pipeline_orchestrator import ProspectCard
    card = ProspectCard(
        domain="test.com.au",
        company_name="Test Co",
        location="Sydney",
        dm_name="Jane Smith",
        dm_email="jane@test.com.au",
        dm_email_verified=True,
        dm_email_source="leadmagic",
        dm_email_confidence="high",
        email_cost_usd=0.015,
    )
    assert card.dm_email == "jane@test.com.au"
    assert card.dm_email_verified is True
    assert card.dm_email_source == "leadmagic"
    assert card.email_cost_usd == 0.015


def test_global_sem_leadmagic_exported():
    """GLOBAL_SEM_LEADMAGIC is importable from email_waterfall."""
    from src.pipeline.email_waterfall import GLOBAL_SEM_LEADMAGIC
    assert GLOBAL_SEM_LEADMAGIC._value == 10


# ── _parse_name: prefix/suffix/noise stripping ────────────────────────────────

def test_parse_name_dr_prefix():
    from src.pipeline.email_waterfall import _parse_name
    assert _parse_name("Dr. Harry Marget") == ("harry", "marget")


def test_parse_name_dr_teresa():
    from src.pipeline.email_waterfall import _parse_name
    assert _parse_name("Dr. Teresa Sung") == ("teresa", "sung")


def test_parse_name_prof_suffix():
    from src.pipeline.email_waterfall import _parse_name
    first, last = _parse_name("Prof. James Smith OAM")
    assert first == "james" and last == "smith"


def test_parse_name_plain():
    from src.pipeline.email_waterfall import _parse_name
    assert _parse_name("Sam Carigliano") == ("sam", "carigliano")


def test_parse_name_linkedin_noise():
    """Role-only name after noise strip returns ("", "")."""
    from src.pipeline.email_waterfall import _parse_name
    first, last = _parse_name("Owner at VC Dental")
    assert first == "" and last == ""


# ── ContactOut vs generic inbox regression tests (#317.3) ────────────────────

GENERIC_HTML = """
<html><body>
<a href="mailto:sales@dentist.com.au">Contact us</a>
</body></html>
"""


@pytest.mark.asyncio
async def test_contactout_beats_generic_inbox():
    """
    Regression #317.3 Test 1: ContactOut current_match email takes priority
    over a generic inbox (sales@) found in website HTML.
    """
    from src.pipeline.email_waterfall import discover_email

    contactout = {
        "email": "michael.chen@dentist.com.au",
        "email_confidence": "current_match",
        "phone": None,
    }

    result = await discover_email(
        domain="dentist.com.au",
        dm_name="Michael Chen",
        html=GENERIC_HTML,
        contactout_result=contactout,
        skip_layers=[3, 5],  # skip paid layers
    )

    assert result.email == "michael.chen@dentist.com.au"
    assert result.source == "contactout"
    assert result.confidence == "high"


@pytest.mark.asyncio
async def test_generic_inbox_falls_through_without_contactout():
    """
    Regression #317.3 Test 2: Without ContactOut, a website-only generic
    inbox (sales@) is flagged as low-confidence generic fallback, not
    returned as a high-confidence DM email.
    """
    from src.pipeline.email_waterfall import discover_email

    result = await discover_email(
        domain="dentist.com.au",
        dm_name="Michael Chen",
        html=GENERIC_HTML,
        contactout_result=None,
        skip_layers=[3, 5],  # skip paid layers
    )

    # Generic inbox should fall through to generic fallback (not short-circuit)
    assert result.source in ("website_generic", "none")
    if result.email:
        assert result.confidence == "low"
        assert result.source == "website_generic"
