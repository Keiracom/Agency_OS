"""
Campaign Discovery Trigger

Automatically triggers discovery when a campaign becomes active.
Wired to Supabase campaign status changes via webhook/function.
"""

import traceback

import structlog

from src.integrations.abn_client import ABNClient
from src.integrations.bright_data_client import BrightDataClient
from src.integrations.supabase import get_async_supabase_service_client
from src.pipeline.discovery_filters import DiscoveryFilters
from src.pipeline.keyword_expander import KeywordExpander
from src.pipeline.location_expander import LocationExpander
from src.pipeline.query_translator import CampaignConfig, QueryTranslator
from src.pipeline.waterfall_v2 import LeadRecord, WaterfallV2

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
        leadmagic_client=None,
    ):
        self.supabase = supabase_client
        self.abn = abn_client
        self.bd = bright_data_client
        self.leadmagic = leadmagic_client

        # Initialize components
        self.keyword_expander = KeywordExpander(supabase_client=supabase_client)
        self.location_expander = LocationExpander(
            supabase_client=supabase_client, bright_data_client=bright_data_client
        )
        self.filters = DiscoveryFilters()

        self.query_translator = QueryTranslator(
            abn_client=abn_client,
            bright_data_client=bright_data_client,
            keyword_expander=self.keyword_expander,
            location_expander=self.location_expander,
            filters=self.filters,
            supabase_client=supabase_client,
        )

        self.waterfall = WaterfallV2(
            bright_data_client=bright_data_client,
            abn_client=abn_client,
            leadmagic_client=leadmagic_client,
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
        logger.info(
            "starting_discovery",
            campaign_id=campaign_id,
            industry=config.industry_slug,
            location=config.location,
        )

        discovery_results = await self.query_translator.run(config)

        # 4. Filter to passed results
        passed_results = [r for r in discovery_results if r.passed_filters]

        logger.info("discovery_complete", total=len(discovery_results), passed=len(passed_results))

        # 5. Store discovery results
        await self._store_discovery_results(campaign_id, discovery_results)

        # 6. Run waterfall enrichment on passed results
        enriched_leads = []
        logger.info("waterfall_start", leads_to_process=len(passed_results[: config.lead_volume]))
        for result in passed_results[: config.lead_volume]:  # Limit to target volume
            try:
                lead_record = self._convert_to_lead_record(result)

                # Run through waterfall tiers
                lead_record = await self._enrich_lead(lead_record, config)
                enriched_leads.append(lead_record)
            except Exception as e:
                logger.error(
                    "waterfall_lead_failed",
                    business=result.business_name,
                    error=str(e),
                    traceback=traceback.format_exc(),
                )
                continue

        # 7. Create leads in database
        leads_created = await self._create_leads(campaign_id, enriched_leads)

        # 8. Update campaign stats
        await self._update_campaign_stats(campaign_id, leads_created)

        return {
            "campaign_id": campaign_id,
            "discovered": len(discovery_results),
            "passed_filters": len(passed_results),
            "leads_created": leads_created,
            "total_cost_aud": self.bd.get_total_cost(),
        }

    async def _fetch_campaign(self, campaign_id: str) -> dict | None:
        """Fetch campaign from database."""
        try:
            supabase = await get_async_supabase_service_client()
            result = (
                await supabase.table("campaigns")
                .select("*")
                .eq("id", campaign_id)
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error("fetch_campaign_failed", error=str(e))
            return None

    def _build_config(self, campaign: dict) -> CampaignConfig:
        """Convert campaign record to CampaignConfig."""
        # Lazy import to avoid circular dependency (Directive #163)
        from src.services.campaign_config_builder import CampaignConfigBuilder

        # Build a minimal Campaign-like object for the builder
        # Note: campaign is a raw dict from Supabase, not ORM

        class CampaignProxy:
            """Proxy object to allow CampaignConfigBuilder to work with dict."""

            def __init__(self, data: dict):
                self.id = data.get("id")
                self.industry_slug = data.get("industry_slug")
                self.state = data.get("state")
                self.lead_volume = data.get("lead_volume") or 150
                self.target_industries = data.get("target_industries") or []
                self.target_locations = data.get("target_locations") or []
                self.target_titles = data.get("target_titles") or []
                self.target_company_sizes = data.get("target_company_sizes") or []

        proxy = CampaignProxy(campaign)
        return CampaignConfigBuilder.build(proxy)

    def _infer_state(self, location: str) -> str:
        """Infer state from location name."""
        return self.location_expander.get_state_from_city(location)

    def _get_discovery_tiers(self, source: str) -> list[str]:
        """
        Credit enrichment tiers based on discovery source.

        Discovery sources already represent completed enrichment work:
        - abn_api/abn_lookup: T1 ABN enrichment already done
        - maps_serp/google_maps: T1 ABN + T1.5a Maps already done

        This ensures ALS data_quality component correctly reflects
        the enrichment work completed during discovery phase.
        """
        if source in ("abn_api", "abn_lookup"):
            return ["tier_1"]
        elif source in ("maps_serp", "google_maps", "both"):
            return ["tier_1", "tier_1_5a"]
        return []

    def _convert_to_lead_record(self, discovery_result) -> LeadRecord:
        """
        Convert DiscoveryResult to LeadRecord for waterfall.

        Extracts all available fields from raw_data (Maps SERP or ABN API)
        to maximize ALS score calculation accuracy before enrichment tiers run.
        """
        raw = discovery_result.raw_data or {}

        # Extract category from Maps SERP (first category title)
        category = None
        if raw.get("category") and isinstance(raw["category"], list) and len(raw["category"]) > 0:
            first_cat = raw["category"][0]
            if isinstance(first_cat, dict):
                category = first_cat.get("title")
            elif isinstance(first_cat, str):
                category = first_cat

        # Extract reviews_count (Maps SERP uses reviews_cnt)
        reviews_count = raw.get("reviews_cnt") or raw.get("reviews_count")
        if reviews_count is not None:
            try:
                reviews_count = int(reviews_count)
            except (ValueError, TypeError):
                reviews_count = None

        # Extract rating
        rating = raw.get("rating")
        if rating is not None:
            try:
                rating = float(rating)
            except (ValueError, TypeError):
                rating = None

        return LeadRecord(
            # Core identifiers
            abn=discovery_result.abn,
            business_name=discovery_result.business_name or raw.get("title"),
            legal_name=discovery_result.trading_name,
            discovery_source=discovery_result.source,
            # ABN Registry fields (from ABN API raw_data)
            state=raw.get("state"),
            gst_registered=raw.get("gst_registered", False),
            entity_type=raw.get("entity_type"),
            # GMB fields (from Maps SERP raw_data)
            phone=raw.get("phone"),
            website=raw.get("link") or raw.get("website"),
            address=raw.get("address"),
            rating=rating,
            reviews_count=reviews_count,
            category=category,
            gmb_place_id=raw.get("map_id") or raw.get("fid"),
            # Credit discovery tiers based on source
            # This ensures ALS data_quality component reflects work already done
            enrichment_tiers_completed=self._get_discovery_tiers(discovery_result.source),
        )

    async def _enrich_lead(self, lead: LeadRecord, config: CampaignConfig) -> LeadRecord:
        """Run lead through waterfall enrichment tiers."""
        supabase = await get_async_supabase_service_client()
        campaign_id = config.campaign_id

        # Tier 1: ABN (if not already from ABN discovery)
        if not lead.abn:
            lead = await self.waterfall.enrich_tier_1(lead)

        # Tier 1.25: ABR Entity Lookup (trading name for ABN-sourced leads)
        lead = await self.waterfall.enrich_tier_1_25(lead)

        # Tier 1.5a: SERP Maps (if missing phone/website)
        if not lead.phone or not lead.website:
            lead = await self.waterfall.enrich_tier_1_5a(lead)

        # Tier 1.5b: SERP LinkedIn Discovery
        lead = await self.waterfall.enrich_tier_1_5b(lead)

        # Audit: T1.5b complete
        await self._write_audit_log(
            supabase,
            campaign_id,
            "tier_1_5b_complete",
            {
                "linkedin_url_found": bool(lead.linkedin_company_url),
                "business_name": lead.business_name,
            },
        )

        # Tier 2: LinkedIn Company (if URL found)
        if lead.linkedin_company_url:
            lead = await self.waterfall.enrich_tier_2(lead)
            # Audit: T2 complete
            await self._write_audit_log(
                supabase,
                campaign_id,
                "tier_2_complete",
                {
                    "business_name": lead.business_name,
                    "industry": getattr(lead, "industry", None),
                    "company_size": getattr(lead, "company_size", None),
                },
            )
        else:
            # Audit: T2 skipped
            await self._write_audit_log(
                supabase,
                campaign_id,
                "tier_2_skipped",
                {
                    "business_name": lead.business_name,
                    "reason": "no_linkedin_url",
                },
            )

        # Calculate propensity score
        lead.propensity_score = self.waterfall.calculate_als(lead)
        gate_passed = lead.propensity_score >= self.waterfall.PRE_ALS_GATE

        # Audit: propensity calculated
        await self._write_audit_log(
            supabase,
            campaign_id,
            "propensity_calculated",
            {
                "business_name": lead.business_name,
                "score": lead.propensity_score,
                "breakdown": lead.propensity_components,
                "gate_passed": gate_passed,
                "gate_threshold": self.waterfall.PRE_ALS_GATE,
            },
        )

        # Gate check for further enrichment
        if gate_passed:
            try:
                lead = await self.waterfall.enrich_tier_2_5(lead)
                lead = await self.waterfall.enrich_tier_3(lead)
                lead = await self.waterfall.enrich_tier_5(lead)
                # Recalculate propensity after enrichment
                lead.propensity_score = self.waterfall.calculate_als(lead)
            except Exception as e:
                logger.warning(
                    "enrichment_post_gate_failed",
                    business=lead.business_name,
                    error=str(e),
                )
                await self._write_audit_log(
                    supabase,
                    campaign_id,
                    "post_gate_enrichment_failed",
                    {
                        "business_name": lead.business_name,
                        "error": str(e),
                        "propensity_score": lead.propensity_score,
                    },
                )

        return lead

    async def _write_audit_log(self, supabase, campaign_id: str, operation: str, details: dict):
        """Write enrichment audit log entry."""
        try:
            await (
                supabase.table("audit_logs")
                .insert(
                    {
                        "action": "create",
                        "resource_type": "lead",
                        "operation": operation,
                        "campaign_id": campaign_id,
                        "success": True,
                        "metadata": details,
                    }
                )
                .execute()
            )
        except Exception as e:
            logger.warning(f"audit_log_write_failed: {operation} - {e}")

    async def _store_discovery_results(self, campaign_id: str, results: list):
        """Store discovery results in discovery_results table."""
        if not results:
            return

        try:
            records = []
            for r in results:
                records.append(
                    {
                        "campaign_id": campaign_id,
                        "abn": r.abn,
                        "business_name": r.business_name,
                        "trading_name": r.trading_name,
                        "source": r.source,
                        "raw_data": r.raw_data,
                        "dedup_hash": r.dedup_hash,
                        "passed_filters": r.passed_filters,
                        "filter_reason": r.filter_reason,
                    }
                )

            # Batch insert
            supabase = await get_async_supabase_service_client()
            await supabase.table("discovery_results").insert(records).execute()

        except Exception as e:
            logger.error("store_discovery_results_failed", error=str(e))

    async def _create_leads(self, campaign_id: str, leads: list) -> int:
        """Create leads in leads table."""
        created = 0
        skipped = 0
        supabase = await get_async_supabase_service_client()

        for lead in leads:
            try:
                # Gate: Skip leads without email (NOT NULL constraint)
                # Unenriched leads without email have low value
                if not lead.email:
                    logger.info(
                        "lead_skipped_no_email",
                        business=lead.business_name,
                        reason="email required but not discovered during enrichment",
                    )
                    # Audit: lead skipped
                    await self._write_audit_log(
                        supabase,
                        campaign_id,
                        "lead_skipped",
                        {
                            "business_name": lead.business_name,
                            "reason": "no_email",
                            "propensity_score": lead.propensity_score,
                        },
                    )
                    skipped += 1
                    continue

                # Get campaign's client_id
                campaign = await self._fetch_campaign(campaign_id)
                client_id = campaign.get("client_id") if campaign else None

                # Extract decision maker fields from T2.5 enrichment
                first_name = None
                last_name = None
                title = None
                dm_linkedin_url = None

                if lead.decision_makers:
                    dm = lead.decision_makers[0]  # Use primary decision maker
                    first_name = dm.get("first_name")
                    last_name = dm.get("last_name")
                    title = dm.get("title")
                    dm_linkedin_url = dm.get("link")

                    # Parse name from "name" field if first/last not available
                    if not first_name and not last_name and dm.get("name"):
                        name_parts = dm["name"].split()
                        if len(name_parts) >= 1:
                            first_name = name_parts[0]
                        if len(name_parts) >= 2:
                            last_name = " ".join(name_parts[1:])

                lead_data = {
                    "campaign_id": campaign_id,
                    "client_id": client_id,
                    "email": lead.email,
                    "company": lead.business_name,
                    "phone": lead.phone,
                    "first_name": first_name,
                    "last_name": last_name,
                    "title": title,
                    "organization_website": lead.website,
                    "linkedin_url": dm_linkedin_url or lead.linkedin_company_url,
                    "propensity_score": lead.propensity_score,
                    "als_components": lead.propensity_components,
                    "cost_basis": lead.cost_aud,
                }

                await supabase.table("leads").insert(lead_data).execute()
                created += 1

            except Exception as e:
                logger.warning("create_lead_failed", error=str(e), business=lead.business_name)
                await self._write_audit_log(
                    supabase,
                    campaign_id,
                    "lead_insert_failed",
                    {
                        "business_name": lead.business_name,
                        "error": str(e),
                        "propensity_score": lead.propensity_score,
                    },
                )

        if skipped > 0:
            logger.info("leads_skipped_summary", skipped=skipped, reason="no_email")

        return created

    async def _update_campaign_stats(self, campaign_id: str, leads_created: int):
        """Update campaign with lead count."""
        try:
            supabase = await get_async_supabase_service_client()
            await (
                supabase.table("campaigns")
                .update({"lead_count": leads_created})
                .eq("id", campaign_id)
                .execute()
            )
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
    if payload.get("type") != "UPDATE":
        return

    old_status = payload.get("old_record", {}).get("status")
    new_status = payload.get("record", {}).get("status")

    # Only trigger on status change to 'active'
    if old_status != "active" and new_status == "active":
        campaign_id = payload["record"]["id"]

        # Initialize clients (would come from env/config in production)
        # trigger = CampaignDiscoveryTrigger(...)
        # result = await trigger.on_campaign_activated(campaign_id)

        logger.info("campaign_activation_handled", campaign_id=campaign_id)
