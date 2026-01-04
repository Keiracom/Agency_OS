"""
FILE: tests/test_skills/test_icp_skills.py
TASK: ICP-018
PHASE: 11 (ICP Discovery System)
PURPOSE: Unit tests for ICP Discovery Skills
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.agents.skills.website_parser import (
    WebsiteParserSkill,
    PageContent,
)
from src.agents.skills.service_extractor import (
    ServiceExtractorSkill,
    ServiceInfo,
)
from src.agents.skills.value_prop_extractor import ValuePropExtractorSkill
from src.agents.skills.portfolio_extractor import (
    PortfolioExtractorSkill,
    PortfolioCompany,
)
from src.agents.skills.industry_classifier import (
    IndustryClassifierSkill,
    IndustryMatch,
    STANDARD_INDUSTRIES,
)
from src.agents.skills.company_size_estimator import (
    CompanySizeEstimatorSkill,
    LinkedInData,
)
from src.agents.skills.icp_deriver import (
    ICPDeriverSkill,
    EnrichedCompany,
    DerivedICP,
)
from src.agents.skills.als_weight_suggester import (
    ALSWeightSuggesterSkill,
    ALSWeights,
)
from src.agents.skills.base_skill import SkillResult


# ============================================
# Test WebsiteParserSkill
# ============================================


class TestWebsiteParserSkill:
    """Tests for WebsiteParserSkill."""

    def test_skill_properties(self):
        """Test skill has correct properties."""
        skill = WebsiteParserSkill()

        assert skill.name == "parse_website"
        assert "structured content" in skill.description.lower()
        assert skill.system_prompt != ""

    def test_input_validation(self):
        """Test input validation."""
        skill = WebsiteParserSkill()

        input_data = skill.validate_input({
            "html": "<html><body>Test</body></html>",
            "url": "https://example.com",
        })

        assert input_data.html == "<html><body>Test</body></html>"
        assert input_data.url == "https://example.com"

    def test_build_prompt(self):
        """Test prompt building."""
        skill = WebsiteParserSkill()
        input_data = skill.Input(
            html="<html>Test</html>",
            url="https://example.com",
            page_urls=["https://example.com/about"],
        )

        prompt = skill.build_prompt(input_data)

        assert "https://example.com" in prompt
        assert "https://example.com/about" in prompt

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful execution."""
        skill = WebsiteParserSkill()
        mock_anthropic = AsyncMock()
        mock_anthropic.complete = AsyncMock(return_value={
            "content": '{"company_name": "Test Corp", "domain": "test.com", "navigation": ["Home", "About"], "pages": [{"url": "https://test.com", "title": "Home", "page_type": "home", "headings": [], "content_summary": "Test", "key_points": [], "images_described": [], "ctas": [], "has_testimonials": false, "has_case_studies": false, "has_client_logos": false}], "meta_description": "", "social_links": [], "contact_info": {}}',
            "input_tokens": 100,
            "output_tokens": 200,
            "cost_aud": 0.01,
        })

        input_data = skill.Input(
            html="<html>Test</html>",
            url="https://test.com",
        )

        result = await skill.execute(input_data, mock_anthropic)

        assert result.success is True
        assert result.data.company_name == "Test Corp"
        assert result.data.domain == "test.com"


# ============================================
# Test ServiceExtractorSkill
# ============================================


class TestServiceExtractorSkill:
    """Tests for ServiceExtractorSkill."""

    def test_skill_properties(self):
        """Test skill has correct properties."""
        skill = ServiceExtractorSkill()

        assert skill.name == "extract_services"
        assert "services" in skill.description.lower()

    def test_input_with_pages(self):
        """Test input validation with pages."""
        skill = ServiceExtractorSkill()
        pages = [
            PageContent(
                url="https://test.com",
                title="Home",
                page_type="home",
                content_summary="We offer SEO services",
            )
        ]

        input_data = skill.Input(pages=pages, company_name="Test Corp")

        assert len(input_data.pages) == 1
        assert input_data.company_name == "Test Corp"

    @pytest.mark.asyncio
    async def test_empty_pages_fails(self):
        """Test that empty pages returns failure."""
        skill = ServiceExtractorSkill()
        mock_anthropic = MagicMock()

        input_data = skill.Input(pages=[])
        result = await skill.execute(input_data, mock_anthropic)

        assert result.success is False
        assert "No pages provided" in result.error


# ============================================
# Test ValuePropExtractorSkill
# ============================================


class TestValuePropExtractorSkill:
    """Tests for ValuePropExtractorSkill."""

    def test_skill_properties(self):
        """Test skill has correct properties."""
        skill = ValuePropExtractorSkill()

        assert skill.name == "extract_value_prop"
        assert "value proposition" in skill.description.lower()

    @pytest.mark.asyncio
    async def test_empty_pages_fails(self):
        """Test that empty pages returns failure."""
        skill = ValuePropExtractorSkill()
        mock_anthropic = MagicMock()

        input_data = skill.Input(pages=[])
        result = await skill.execute(input_data, mock_anthropic)

        assert result.success is False


# ============================================
# Test PortfolioExtractorSkill
# ============================================


class TestPortfolioExtractorSkill:
    """Tests for PortfolioExtractorSkill."""

    def test_skill_properties(self):
        """Test skill has correct properties."""
        skill = PortfolioExtractorSkill()

        assert skill.name == "extract_portfolio"
        assert "portfolio" in skill.description.lower() or "client" in skill.description.lower()

    def test_portfolio_company_model(self):
        """Test PortfolioCompany model."""
        company = PortfolioCompany(
            company_name="Acme Inc",
            source="case_study",
            industry_hint="tech",
        )

        assert company.company_name == "Acme Inc"
        assert company.source == "case_study"
        assert company.industry_hint == "tech"


# ============================================
# Test IndustryClassifierSkill
# ============================================


class TestIndustryClassifierSkill:
    """Tests for IndustryClassifierSkill."""

    def test_skill_properties(self):
        """Test skill has correct properties."""
        skill = IndustryClassifierSkill()

        assert skill.name == "classify_industries"
        assert "industries" in skill.description.lower()

    def test_standard_industries(self):
        """Test standard industries list exists."""
        assert len(STANDARD_INDUSTRIES) > 10
        assert "technology" in STANDARD_INDUSTRIES
        assert "saas" in STANDARD_INDUSTRIES
        assert "healthcare" in STANDARD_INDUSTRIES

    def test_industry_match_model(self):
        """Test IndustryMatch model."""
        match = IndustryMatch(
            industry="technology",
            confidence=0.9,
            evidence=["5 tech clients"],
            is_primary=True,
            client_count=5,
        )

        assert match.industry == "technology"
        assert match.confidence == 0.9
        assert match.is_primary is True

    @pytest.mark.asyncio
    async def test_no_data_fails(self):
        """Test that no data returns failure."""
        skill = IndustryClassifierSkill()
        mock_anthropic = MagicMock()

        input_data = skill.Input(services=[], portfolio_companies=[])
        result = await skill.execute(input_data, mock_anthropic)

        assert result.success is False
        assert "No services or portfolio" in result.error


# ============================================
# Test CompanySizeEstimatorSkill
# ============================================


class TestCompanySizeEstimatorSkill:
    """Tests for CompanySizeEstimatorSkill."""

    def test_skill_properties(self):
        """Test skill has correct properties."""
        skill = CompanySizeEstimatorSkill()

        assert skill.name == "estimate_company_size"
        assert "size" in skill.description.lower()

    def test_linkedin_data_model(self):
        """Test LinkedInData model."""
        data = LinkedInData(
            company_name="Acme Inc",
            employee_count=50,
            employee_range="11-50",
            headquarters="Sydney, Australia",
            founded_year=2015,
        )

        assert data.employee_count == 50
        assert data.founded_year == 2015

    @pytest.mark.asyncio
    async def test_no_data_fails(self):
        """Test that no data returns failure."""
        skill = CompanySizeEstimatorSkill()
        mock_anthropic = MagicMock()

        input_data = skill.Input()
        result = await skill.execute(input_data, mock_anthropic)

        assert result.success is False


# ============================================
# Test ICPDeriverSkill
# ============================================


class TestICPDeriverSkill:
    """Tests for ICPDeriverSkill."""

    def test_skill_properties(self):
        """Test skill has correct properties."""
        skill = ICPDeriverSkill()

        assert skill.name == "derive_icp"
        assert "icp" in skill.description.lower()

    def test_enriched_company_model(self):
        """Test EnrichedCompany model."""
        company = EnrichedCompany(
            company_name="Test Corp",
            domain="test.com",
            industry="technology",
            employee_count=100,
            location="Sydney",
            source="portfolio",
        )

        assert company.company_name == "Test Corp"
        assert company.industry == "technology"

    def test_derived_icp_model(self):
        """Test DerivedICP model."""
        icp = DerivedICP(
            icp_industries=["technology", "saas"],
            icp_company_sizes=["11-50", "51-200"],
            icp_locations=["Australia"],
            pattern_description="B2B SaaS companies",
            pattern_confidence=0.85,
        )

        assert len(icp.icp_industries) == 2
        assert icp.pattern_confidence == 0.85

    @pytest.mark.asyncio
    async def test_empty_portfolio_fails(self):
        """Test that empty portfolio returns failure."""
        skill = ICPDeriverSkill()
        mock_anthropic = MagicMock()

        input_data = skill.Input(enriched_portfolio=[])
        result = await skill.execute(input_data, mock_anthropic)

        assert result.success is False


# ============================================
# Test ALSWeightSuggesterSkill
# ============================================


class TestALSWeightSuggesterSkill:
    """Tests for ALSWeightSuggesterSkill."""

    def test_skill_properties(self):
        """Test skill has correct properties."""
        skill = ALSWeightSuggesterSkill()

        assert skill.name == "suggest_als_weights"
        assert "als" in skill.description.lower() or "weight" in skill.description.lower()

    def test_als_weights_model(self):
        """Test ALSWeights model."""
        weights = ALSWeights(
            data_quality=20,
            authority=25,
            company_fit=25,
            timing=15,
            risk=15,
        )

        assert weights.total() == 100

    def test_als_weights_validation(self):
        """Test ALSWeights validation rejects out-of-range values."""
        import pytest
        from pydantic import ValidationError

        # Test that out-of-range values raise ValidationError
        with pytest.raises(ValidationError):
            ALSWeights(
                data_quality=50,  # Too high (max 30)
                authority=25,
                company_fit=25,
                timing=15,
                risk=15,
            )

        with pytest.raises(ValidationError):
            ALSWeights(
                data_quality=20,
                authority=5,  # Too low (min 15)
                company_fit=25,
                timing=15,
                risk=15,
            )

        # Test that valid values work
        valid_weights = ALSWeights(
            data_quality=20,
            authority=25,
            company_fit=25,
            timing=15,
            risk=15,
        )
        assert valid_weights.data_quality == 20
        assert valid_weights.authority == 25

    def test_als_weights_sub_weights(self):
        """Test ALS sub-weights."""
        weights = ALSWeights(
            data_quality=20,
            authority=25,
            company_fit=25,
            timing=15,
            risk=15,
            industry_weight=10,
            size_weight=8,
            location_weight=7,
        )

        assert weights.industry_weight + weights.size_weight + weights.location_weight == 25


# ============================================
# Integration Test: Skill Registration
# ============================================


class TestSkillRegistration:
    """Test that all skills are registered correctly."""

    def test_all_skills_registered(self):
        """Test all ICP skills are registered."""
        from src.agents.skills import SkillRegistry

        # Import skills module to trigger registration
        import src.agents.skills

        expected_skills = [
            "parse_website",
            "extract_services",
            "extract_value_prop",
            "extract_portfolio",
            "classify_industries",
            "estimate_company_size",
            "derive_icp",
            "suggest_als_weights",
        ]

        for skill_name in expected_skills:
            skill = SkillRegistry.get(skill_name)
            assert skill is not None, f"Skill '{skill_name}' not registered"


"""
VERIFICATION CHECKLIST:
- [x] Tests for WebsiteParserSkill
- [x] Tests for ServiceExtractorSkill
- [x] Tests for ValuePropExtractorSkill
- [x] Tests for PortfolioExtractorSkill
- [x] Tests for IndustryClassifierSkill
- [x] Tests for CompanySizeEstimatorSkill
- [x] Tests for ICPDeriverSkill
- [x] Tests for ALSWeightSuggesterSkill
- [x] Tests for all model classes
- [x] Integration test for skill registration
- [x] Async tests with pytest.mark.asyncio
"""
