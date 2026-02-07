"""
Test suite for SIEGE Discovery Enhancements.

Tests:
1. domain_search integration in Tier 3 (Hunter)
2. Audit logging for all enrichment operations
3. AU leads do not fall back to Apollo
4. Mock data validation

TASK: SIEGE Discovery Enhancement
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Patch Kaspr before importing siege_waterfall to avoid API key errors
with patch.dict("os.environ", {"KASPR_API_KEY": "mock_key"}):
    pass

# Import the modules under test
from src.integrations.siege_waterfall import (
    SiegeWaterfall,
    EnrichmentTier,
    TierResult,
    HunterClientAdapter,
)
from src.engines.scout import ScoutEngine


class MockLead:
    """Mock Lead model for testing."""
    
    def __init__(
        self,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company: str | None = None,
        domain: str | None = None,
        linkedin_url: str | None = None,
        title: str | None = None,
        organization_country: str | None = None,
        abn: str | None = None,
        phone: str | None = None,
    ):
        self.id = uuid4()
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.company = company
        self.domain = domain
        self.linkedin_url = linkedin_url
        self.title = title
        self.organization_country = organization_country
        self.abn = abn
        self.phone = phone


class TestDomainSearchIntegration:
    """Test Tier 3 Hunter domain_search for decision-maker discovery."""
    
    @pytest.fixture
    def mock_hunter_adapter(self):
        """Create a mock Hunter adapter (not client) that returns lists directly."""
        adapter = AsyncMock()
        # domain_search returns list of dicts
        adapter.domain_search.return_value = [
            {
                "email": "john.smith@acme.com.au",
                "first_name": "John",
                "last_name": "Smith",
                "position": "Managing Director",
                "seniority": "executive",
                "department": "executive",
                "confidence": 95,
                "linkedin_url": "https://linkedin.com/in/johnsmith",
                "phone_number": "+61 2 9999 1234",
            },
            {
                "email": "jane.doe@acme.com.au",
                "first_name": "Jane",
                "last_name": "Doe",
                "position": "Marketing Manager",
                "seniority": "senior",
                "department": "marketing",
                "confidence": 87,
            },
        ]
        # Also mock verify_email and find_email in case they're called
        adapter.verify_email.return_value = {"status": "valid", "score": 90}
        adapter.find_email.return_value = {"found": False}
        return adapter
    
    @pytest.fixture
    def mock_kaspr_client(self):
        """Create a mock Kaspr client."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_domain_search_finds_decision_makers(self, mock_hunter_adapter, mock_kaspr_client):
        """Test that domain_search finds and prioritizes decision-makers."""
        # Lead with only company/domain, no email or name
        lead_data = {
            "company_name": "Acme Pty Ltd",
            "domain": "acme.com.au",
        }
        
        # Create waterfall with mock hunter adapter AND mock kaspr
        waterfall = SiegeWaterfall(hunter_client=mock_hunter_adapter, kaspr_client=mock_kaspr_client)
        
        # Patch the audit logging to avoid DB calls
        with patch.object(waterfall, "_log_enrichment_operation", new_callable=AsyncMock):
            # Run tier 3
            result = await waterfall.tier3_hunter(lead_data)
        
        # Verify success
        assert result.success is True
        assert result.tier == EnrichmentTier.HUNTER
        
        # Verify we got the executive (highest priority)
        assert result.data["email"] == "john.smith@acme.com.au"
        assert result.data["first_name"] == "John"
        assert result.data["last_name"] == "Smith"
        assert result.data["title"] == "Managing Director"
        assert result.data["seniority_level"] == "executive"
        assert result.data["email_source"] == "hunter_domain_search"
        assert result.data["decision_makers_found"] == 2
        
        # Verify domain_search was called
        mock_hunter_adapter.domain_search.assert_called_once_with(
            domain="acme.com.au",
            limit=5,
        )
    
    @pytest.mark.asyncio
    async def test_domain_search_no_contacts_found(self, mock_hunter_adapter, mock_kaspr_client):
        """Test graceful handling when no contacts found."""
        # Mock empty result
        mock_hunter_adapter.domain_search.return_value = []
        
        lead_data = {
            "domain": "unknown-company.com.au",
        }
        
        waterfall = SiegeWaterfall(hunter_client=mock_hunter_adapter, kaspr_client=mock_kaspr_client)
        
        # Patch the audit logging
        with patch.object(waterfall, "_log_enrichment_operation", new_callable=AsyncMock):
            result = await waterfall.tier3_hunter(lead_data)
        
        # Verify failure with appropriate message
        assert result.success is False
        assert result.error == "No contacts found for domain"
        assert result.cost_aud == 0.15  # Still charged for attempt


class TestAuditLogging:
    """Test audit logging for all enrichment operations."""
    
    @pytest.fixture
    def mock_kaspr_client(self):
        """Create a mock Kaspr client."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_tier3_logs_successful_operation(self, mock_kaspr_client):
        """Test that successful Hunter operations are logged."""
        # Create mock Hunter that returns success
        mock_hunter = AsyncMock()
        mock_hunter.verify_email.return_value = {
            "email": "test@example.com",
            "status": "valid",
            "score": 95,
        }
        
        adapter = HunterClientAdapter()
        adapter._client = mock_hunter
        
        waterfall = SiegeWaterfall(hunter_client=adapter, kaspr_client=mock_kaspr_client)
        
        # Track if audit logging was called
        audit_calls = []
        
        async def mock_log(*args, **kwargs):
            audit_calls.append(kwargs)
        
        with patch.object(waterfall, "_log_enrichment_operation", side_effect=mock_log):
            lead_data = {"email": "test@example.com"}
            result = await waterfall.tier3_hunter(lead_data)
        
        assert result.success is True
        
        # Verify audit log was called with correct data
        assert len(audit_calls) == 1
        call_args = audit_calls[0]
        assert call_args["operation"] == "verify_email"
        assert call_args["success"] is True
        assert call_args["tier"] == EnrichmentTier.HUNTER


class TestAustralianLeadNoApolloFallback:
    """Test that AU leads do not fall back to Apollo."""
    
    @pytest.fixture
    def mock_apollo(self):
        """Mock Apollo client."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_siege_waterfall(self):
        """Mock Siege Waterfall."""
        mock = AsyncMock()
        # Return a result with some sources used
        mock.enrich_lead.return_value = MagicMock(
            sources_used=2,
            enriched_data={
                "email": "found@company.com.au",
                "first_name": "Test",
                "found": True,
            },
            total_cost_aud=0.018,
            tier_results=[
                MagicMock(tier=EnrichmentTier.ABN, success=True),
                MagicMock(tier=EnrichmentTier.GMB, success=True),
            ],
        )
        return mock
    
    @pytest.mark.asyncio
    async def test_au_lead_uses_siege_no_apollo(
        self, mock_apollo, mock_siege_waterfall
    ):
        """Test that Australian leads use SIEGE and don't fall back to Apollo."""
        # Create AU lead
        lead = MockLead(
            email=None,  # No email, needs enrichment
            first_name="Bruce",
            last_name="Wayne",
            company="Wayne Enterprises",
            domain="wayne.com.au",  # .au domain = Australian
        )
        
        # Create scout engine with mocks
        engine = ScoutEngine(
            apollo_client=mock_apollo,
            siege_waterfall=mock_siege_waterfall,
        )
        
        # Patch the audit logging to avoid DB calls
        with patch.object(engine, "_log_enrichment_audit", new_callable=AsyncMock):
            result = await engine._enrich_tier1(lead, "wayne.com.au")
        
        # Verify SIEGE was called
        mock_siege_waterfall.enrich_lead.assert_called_once()
        
        # Verify Apollo was NOT called
        mock_apollo.enrich_person.assert_not_called()
        
        # Verify we got SIEGE result
        assert result["found"] is True
        assert "siege_waterfall" in result["source"]
    
    @pytest.mark.asyncio
    async def test_au_lead_siege_fails_no_apollo_fallback(self, mock_apollo):
        """Test that when SIEGE fails for AU lead, we DON'T fall back to Apollo."""
        # Create mock siege that returns no sources
        mock_siege = AsyncMock()
        mock_siege.enrich_lead.return_value = MagicMock(
            sources_used=0,  # No sources found
            enriched_data={},
            total_cost_aud=0.0,
            tier_results=[],
        )
        
        lead = MockLead(
            first_name="Unknown",
            last_name="Person",
            company="Obscure Company",
            domain="obscure.com.au",  # .au domain
        )
        
        engine = ScoutEngine(
            apollo_client=mock_apollo,
            siege_waterfall=mock_siege,
        )
        
        with patch.object(engine, "_log_enrichment_audit", new_callable=AsyncMock):
            result = await engine._enrich_tier1(lead, "obscure.com.au")
        
        # Verify SIEGE was called
        mock_siege.enrich_lead.assert_called_once()
        
        # Verify Apollo was NOT called even though SIEGE found nothing
        mock_apollo.enrich_person.assert_not_called()
        
        # Result should be None (no data found)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_non_au_lead_uses_apollo(self, mock_apollo):
        """Test that non-Australian leads use Apollo (not SIEGE)."""
        # Mock Apollo success
        mock_apollo.enrich_person.return_value = {
            "found": True,
            "email": "john@acme.com",
            "first_name": "John",
            "last_name": "Doe",
            "company": "Acme Inc",
        }
        
        mock_siege = AsyncMock()
        
        # Non-AU lead
        lead = MockLead(
            email=None,
            first_name="John",
            last_name="Doe",
            company="Acme Inc",
            domain="acme.com",  # .com, not .com.au
            organization_country="United States",
        )
        
        engine = ScoutEngine(
            apollo_client=mock_apollo,
            siege_waterfall=mock_siege,
            apify_client=AsyncMock(),  # Mock Apify to prevent errors
        )
        
        with patch.object(engine, "_log_enrichment_audit", new_callable=AsyncMock):
            result = await engine._enrich_tier1(lead, "acme.com")
        
        # Verify SIEGE was NOT called
        mock_siege.enrich_lead.assert_not_called()
        
        # Verify Apollo WAS called
        mock_apollo.enrich_person.assert_called_once()
        
        # Verify we got Apollo result
        assert result["found"] is True


class TestAustralianLeadDetection:
    """Test detection of Australian leads."""
    
    def test_au_domain_detected(self):
        """Test .au domain is detected as Australian."""
        lead = MockLead(domain="company.com.au")
        engine = ScoutEngine()
        assert engine._is_australian_lead(lead, "company.com.au") is True
    
    def test_au_country_detected(self):
        """Test Australia country is detected."""
        lead = MockLead(
            domain="company.com",
            organization_country="Australia",
        )
        engine = ScoutEngine()
        assert engine._is_australian_lead(lead, "company.com") is True
    
    def test_abn_detected(self):
        """Test ABN presence indicates Australian."""
        lead = MockLead(
            domain="company.com",
            abn="12345678901",
        )
        engine = ScoutEngine()
        assert engine._is_australian_lead(lead, "company.com") is True
    
    def test_au_phone_detected(self):
        """Test +61 phone number indicates Australian."""
        lead = MockLead(
            domain="company.com",
            phone="+61 2 9999 1234",
        )
        engine = ScoutEngine()
        assert engine._is_australian_lead(lead, "company.com") is True
    
    def test_non_au_not_detected(self):
        """Test non-Australian leads are not flagged."""
        lead = MockLead(
            domain="company.com",
            organization_country="United States",
        )
        engine = ScoutEngine()
        assert engine._is_australian_lead(lead, "company.com") is False


class TestMockDataEnrichment:
    """Test full enrichment flow with mock data."""
    
    @pytest.fixture
    def mock_au_lead_data(self):
        """Sample Australian lead for testing."""
        return {
            "id": str(uuid4()),
            "company_name": "Brisbane Marketing Agency",
            "domain": "brismarketing.com.au",
            "city": "Brisbane",
            "state": "QLD",
            "country": "Australia",
        }
    
    @pytest.fixture
    def mock_non_au_lead_data(self):
        """Sample non-Australian lead for testing."""
        return {
            "id": str(uuid4()),
            "email": "contact@uscompany.com",
            "first_name": "Mike",
            "last_name": "Johnson",
            "company_name": "US Marketing Inc",
            "domain": "uscompany.com",
            "country": "United States",
        }
    
    @pytest.fixture
    def mock_kaspr_client(self):
        """Create a mock Kaspr client."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_au_lead_siege_enrichment(self, mock_au_lead_data, mock_kaspr_client):
        """Test Australian lead goes through SIEGE waterfall."""
        # Create mocked hunter adapter (returns lists directly, like the adapter does)
        mock_hunter = AsyncMock()
        mock_hunter.domain_search.return_value = [
            {
                "email": "sarah@brismarketing.com.au",
                "first_name": "Sarah",
                "last_name": "Thompson",
                "position": "CEO",
                "seniority": "executive",
                "department": "executive",
                "confidence": 92,
            }
        ]
        mock_hunter.verify_email.return_value = {"status": "valid", "score": 90}
        mock_hunter.find_email.return_value = {"found": False}
        
        waterfall = SiegeWaterfall(hunter_client=mock_hunter, kaspr_client=mock_kaspr_client)
        
        # Patch audit logging
        with patch.object(waterfall, "_log_enrichment_operation", new_callable=AsyncMock):
            # Run full waterfall (skip tiers that need real API keys)
            result = await waterfall.enrich_lead(
                mock_au_lead_data,
                skip_tiers=[
                    EnrichmentTier.ABN,  # Skip ABN (needs real client)
                    EnrichmentTier.GMB,  # Skip GMB (needs real client)
                    EnrichmentTier.PROXYCURL,  # Skip Proxycurl (needs API key)
                    EnrichmentTier.IDENTITY,  # Skip expensive tier
                ],
            )
        
        # Verify enrichment succeeded via Hunter
        assert result.sources_used >= 1
        assert result.total_cost_aud >= 0
        
        # Check enriched data contains Hunter discovery
        assert result.enriched_data.get("email") == "sarah@brismarketing.com.au"
        assert result.enriched_data.get("first_name") == "Sarah"


# ============================================
# RUN TESTS
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
