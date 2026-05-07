"""
CampaignConfigBuilder — Campaign to CampaignConfig translation layer.

CEO Directive #163: Builds CampaignConfig from Campaign ORM for QueryTranslator.
"""

from src.models.campaign import Campaign
from src.pipeline.query_translator import CampaignConfig


class CampaignConfigBuilder:
    """
    Translates Campaign ORM to CampaignConfig for QueryTranslator.run().

    Handles fallback logic when optional fields are not populated:
    - industry_slug: falls back to target_industries[0] or "general"
    - location: falls back to target_locations[0] or "Melbourne"
    - state: falls back to "VIC"
    - lead_volume: uses campaign.lead_volume (tier-dependent volume from tiers.py)
    """

    @staticmethod
    def build(campaign: Campaign) -> CampaignConfig:
        """
        Build CampaignConfig from Campaign ORM.

        Args:
            campaign: Campaign ORM instance

        Returns:
            CampaignConfig ready for QueryTranslator.run()
        """
        # Industry: prefer industry_slug, fall back to target_industries[0]
        industry_slug = campaign.industry_slug
        if not industry_slug and campaign.target_industries:
            industry_slug = campaign.target_industries[0]
        if not industry_slug:
            industry_slug = "general"

        # Location: prefer target_locations[0], default Melbourne
        location = "Melbourne"
        if campaign.target_locations:
            location = campaign.target_locations[0]

        # State: prefer campaign.state, default VIC
        state = campaign.state or "VIC"

        # Lead volume: use campaign field (tier-dependent volume from tiers.py)
        lead_volume = campaign.lead_volume

        # Filters: build from target fields
        filters = {
            "titles": campaign.target_titles or [],
            "sizes": campaign.target_company_sizes or [],
            "industries": campaign.target_industries or [],
        }

        return CampaignConfig(
            campaign_id=str(campaign.id),
            industry_slug=industry_slug,
            location=location,
            state=state,
            lead_volume=lead_volume,
            filters=filters,
            discovery_mode=None,  # Auto-detect
        )
