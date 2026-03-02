"""
Campaign Discovery Trigger

Automatically triggers discovery when a campaign becomes active.
Wired to Supabase campaign status changes via webhook/function.
"""
import structlog

from enrichment.discovery_filters import DiscoveryFilters
from enrichment.keyword_expander import KeywordExpander
from enrichment.location_expander import LocationExpander
from enrichment.query_translator import CampaignConfig, QueryTranslator
from enrichment.waterfall_v2 import LeadRecord, WaterfallV2
from integrations.abn_client import ABNClient
from integrations.bright_data_client import BrightDataClient

logger = structlog.get_logger()


class CampaignDiscoveryTrigger:
    """
    Triggers discovery pipeline when campaign status changes to 'active'.

    Flow:
    1. Campaign submitted (status: draft → active)
    2. This trigger fires
    3. Query Translator generates discovery queries
    4. Results flow into Waterfall v2 for enrichment
    5. Leads are created in leads table
    """

    def __init__(
        self,
        supabase_client,
        abn_client: ABNClient,
        bright_data_client: BrightDataClient,
        hunter_client=None,
        kaspr_client=None
    ):
        self.supabase = supabase_client
        self.abn = abn_client
        self.bd = bright_data_client
        self.hunter = hunter_client
        self.kaspr = kaspr_client

        # Initialize components
        self.keyword_expander = KeywordExpander(supabase_client=supabase_client)
        self.location_expander = LocationExpander(
            supabase_client=supabase_client,
            bright_data_client=bright_data_client
        )
        self.filters = DiscoveryFilters()

        self.query_translator = QueryTranslator(
            abn_client=abn_client,
            bright_data_client=bright_data_client,
            keyword_expander=self.keyword_expander,
            location_expander=self.location_expander,
            filters=self.filters,
            supabase_client=supabase_client
        )

        self.waterfall = WaterfallV2(
            bright_data_client=bright_data_client,
            hunter_client=hunter_client,
            kaspr_client=kaspr_client
        )

    async def on_campaign_activated(self, campaign_id: str) -> dict:
        """
        Handle campaign activation event.

        Args:
            campaign_id: UUID of the activated campaign

        Returns:
            dict with discovery stats
        """
        logger.info("campaign_activated", campaign_id=campaign_id)

        # 1. Fetch campaign details
        campaign = await self._fetch_campaign(campaign_id)
        if not campaign:
            logger.error("campaign_not_found", campaign_id=campaign_id)
            return {"error": "Campaign not found"}

        # 2. Build config from campaign
        config = self._build_config(campaign)

        # 3. Run discovery
        logger.info("starting_discovery",
                   campaign_id=campaign_id,
                   industry=config.industry_slug,
                   location=config.location)

        discovery_results = await self.query_translator.run(config)

        # 4. Filter to passed results
        passed_results = [r for r in discovery_results if r.passed_filters]

        logger.info("discovery_complete",
                   total=len(discovery_results),
                   passed=len(passed_results))

        # 5. Store discovery results
        await self._store_discovery_results(campaign_id, discovery_results)

        # 6. Run waterfall enrichment on passed results
        enriched_leads = []
        for result in passed_results[:config.lead_volume]:  # Limit to target volume
            lead_record = self._convert_to_lead_record(result)

            # Run through waterfall tiers
            lead_record = await self._enrich_lead(lead_record, config)
            enriched_leads.append(lead_record)

        # 7. Create leads in database
        leads_created = await self._create_leads(campaign_id, enriched_leads)

        # 8. Update campaign stats
        await self._update_campaign_stats(campaign_id, leads_created)

        return {
            "campaign_id": campaign_id,
            "discovered": len(discovery_results),
            "passed_filters": len(passed_results),
            "leads_created": leads_created,
            "total_cost_aud": self.bd.get_total_cost()
        }

    async def _fetch_campaign(self, campaign_id: str) -> dict | None:
        """Fetch campaign from database."""
        try:
            result = await self.supabase.table('campaigns') \
                .select('*') \
                .eq('id', campaign_id) \
                .single() \
                .execute()
            return result.data
        except Exception as e:
            logger.error("fetch_campaign_failed", error=str(e))
            return None

    def _build_config(self, campaign: dict) -> CampaignConfig:
        """Convert campaign record to CampaignConfig."""
        # Extract industry from target_industries (assuming first one)
        industries = campaign.get('target_industries') or []
        industry_slug = industries[0] if industries else 'general'

        # Extract location from ICP config or default
        icp = campaign.get('icp_config') or {}
        location = icp.get('location') or icp.get('city') or 'Melbourne'
        state = icp.get('state') or self._infer_state(location)

        # Lead volume from campaign or default
        lead_count = campaign.get('lead_count') or 100

        return CampaignConfig(
            campaign_id=campaign['id'],
            industry_slug=industry_slug,
            location=location,
            state=state,
            lead_volume=lead_count,
            filters=icp.get('filters', {})
        )

    def _infer_state(self, location: str) -> str:
        """Infer state from location name."""
        return self.location_expander.get_state_from_city(location)

    def _convert_to_lead_record(self, discovery_result) -> LeadRecord:
        """Convert DiscoveryResult to LeadRecord for waterfall."""
        return LeadRecord(
            abn=discovery_result.abn,
            business_name=discovery_result.business_name,
            enrichment_tiers_completed=[]
        )

    async def _enrich_lead(self, lead: LeadRecord, config: CampaignConfig) -> LeadRecord:
        """Run lead through waterfall enrichment tiers."""
        # Tier 1: ABN (if not already from ABN discovery)
        if not lead.abn:
            lead = await self.waterfall.enrich_tier_1(lead)

        # Tier 1.5a: SERP Maps (if missing phone/website)
        if not lead.phone or not lead.website:
            lead = await self.waterfall.enrich_tier_1_5a(lead)

        # Tier 1.5b: SERP LinkedIn Discovery
        lead = await self.waterfall.enrich_tier_1_5b(lead)

        # Tier 2: LinkedIn Company (if URL found)
        if lead.linkedin_company_url:
            lead = await self.waterfall.enrich_tier_2(lead)

        # Calculate ALS
        lead.als_score = self.waterfall.calculate_als(lead)

        # Gate check for further enrichment
        if lead.als_score >= self.waterfall.PRE_ALS_GATE:
            lead = await self.waterfall.enrich_tier_2_5(lead)
            lead = await self.waterfall.enrich_tier_3(lead)
            lead = await self.waterfall.enrich_tier_5(lead)
            # Recalculate ALS after enrichment
            lead.als_score = self.waterfall.calculate_als(lead)

        return lead

    async def _store_discovery_results(self, campaign_id: str, results: list):
        """Store discovery results in discovery_results table."""
        if not results:
            return

        try:
            records = []
            for r in results:
                records.append({
                    'campaign_id': campaign_id,
                    'abn': r.abn,
                    'business_name': r.business_name,
                    'trading_name': r.trading_name,
                    'source': r.source,
                    'raw_data': r.raw_data,
                    'dedup_hash': r.dedup_hash,
                    'passed_filters': r.passed_filters,
                    'filter_reason': r.filter_reason
                })

            # Batch insert
            await self.supabase.table('discovery_results').insert(records).execute()

        except Exception as e:
            logger.error("store_discovery_results_failed", error=str(e))

    async def _create_leads(self, campaign_id: str, leads: list) -> int:
        """Create leads in leads table."""
        created = 0

        for lead in leads:
            try:
                # Get campaign's client_id
                campaign = await self._fetch_campaign(campaign_id)
                client_id = campaign.get('client_id') if campaign else None

                lead_data = {
                    'campaign_id': campaign_id,
                    'client_id': client_id,
                    'company': lead.business_name,
                    'als_score': lead.als_score,
                    'als_components': lead.als_breakdown,
                    'cost_basis': lead.cost_aud
                }

                await self.supabase.table('leads').insert(lead_data).execute()
                created += 1

            except Exception as e:
                logger.warning("create_lead_failed", error=str(e), business=lead.business_name)

        return created

    async def _update_campaign_stats(self, campaign_id: str, leads_created: int):
        """Update campaign with lead count."""
        try:
            await self.supabase.table('campaigns') \
                .update({'lead_count': leads_created}) \
                .eq('id', campaign_id) \
                .execute()
        except Exception as e:
            logger.warning("update_campaign_stats_failed", error=str(e))


# Webhook handler for Supabase edge function
async def handle_campaign_status_change(payload: dict):
    """
    Handle campaign status change webhook.

    Payload format (Supabase webhook):
    {
        "type": "UPDATE",
        "table": "campaigns",
        "record": {...},
        "old_record": {...}
    }
    """
    if payload.get('type') != 'UPDATE':
        return

    old_status = payload.get('old_record', {}).get('status')
    new_status = payload.get('record', {}).get('status')

    # Only trigger on status change to 'active'
    if old_status != 'active' and new_status == 'active':
        campaign_id = payload['record']['id']

        # Initialize clients (would come from env/config in production)
        # trigger = CampaignDiscoveryTrigger(...)
        # result = await trigger.on_campaign_activated(campaign_id)

        logger.info("campaign_activation_handled", campaign_id=campaign_id)
