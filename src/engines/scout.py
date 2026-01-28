"""
Contract: src/engines/scout.py
Purpose: Enrich leads via Cache, Apollo, Apify, Clay waterfall
Layer: 3 - engines
Imports: models, integrations, agents.sdk_agents, services
Consumers: orchestration only

FILE: src/engines/scout.py
PURPOSE: Enrich leads via Cache → Apollo+Apify → Clay waterfall
PHASE: 4 (Engines), updated Phase 24A (Lead Pool), Phase 24F (Suppression)
TASK: ENG-002, POOL-008, CUST-010
DEPENDENCIES:
  - src/engines/base.py
  - src/integrations/redis.py
  - src/integrations/apollo.py
  - src/integrations/apify.py
  - src/integrations/clay.py
  - src/models/lead.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines
  - Rule 16: Cache versioning (v1 prefix)

PHASE 24A CHANGES:
  - Added enrich_to_pool method for pool-first enrichment
  - Added search_and_populate_pool for bulk pool population
  - Modified enrich_lead to optionally write to pool
  - All enrichment now uses Apollo's full 50+ field capture

PHASE 24F CHANGES:
  - Added filter_suppressed_leads method for client-specific filtering
  - Uses is_suppressed database function (no service import needed)
"""

import json
import logging
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from src.agents.sdk_agents.enrichment_agent import run_sdk_enrichment
from src.agents.sdk_agents.sdk_eligibility import should_use_sdk_enrichment
from src.agents.skills.research_skills import DeepResearchSkill
from src.engines.base import BaseEngine, EngineResult
from src.integrations.anthropic import AnthropicClient, get_anthropic_client
from src.integrations.apify import ApifyClient, get_apify_client
from src.integrations.apollo import ApolloClient, get_apollo_client
from src.integrations.clay import ClayClient, get_clay_client
from src.integrations.redis import enrichment_cache
from src.models.base import LeadStatus
from src.models.lead import Lead
from src.models.lead_social_post import LeadSocialPost
from src.services.sdk_usage_service import log_sdk_usage
from src.services.who_refinement_service import get_who_refined_criteria

# Sentry for error tracking
try:
    from sentry_sdk import capture_exception
except ImportError:

    def capture_exception(e):
        pass


# Minimum required fields for valid enrichment
REQUIRED_FIELDS = ["email", "first_name", "last_name", "company"]

# Confidence threshold (Rule 4)
CONFIDENCE_THRESHOLD = 0.70

# Max percentage for Clay fallback
CLAY_MAX_PERCENTAGE = 0.15


def parse_date_string(date_str: str | date | None) -> date | None:
    """
    Convert a date string (YYYY-MM-DD) to a Python date object.

    Args:
        date_str: Date string, date object, or None

    Returns:
        date object or None if invalid/empty
    """
    if date_str is None:
        return None
    if isinstance(date_str, date):
        return date_str
    if isinstance(date_str, str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    return None


class ScoutEngine(BaseEngine):
    """
    Scout engine for lead enrichment.

    Uses a waterfall approach:
    - Tier 0: Check cache (versioned key with soft validation)
    - Tier 1: Apollo + Apify hybrid
    - Tier 2: Clay fallback (max 15% of batch)

    Rule 4: Validation threshold is 0.70 for confidence.
    Rule 16: Cache keys use version prefix.
    """

    def __init__(
        self,
        apollo_client: ApolloClient | None = None,
        apify_client: ApifyClient | None = None,
        clay_client: ClayClient | None = None,
    ):
        """
        Initialize Scout engine with integration clients.

        Args:
            apollo_client: Optional Apollo client (uses singleton if not provided)
            apify_client: Optional Apify client (uses singleton if not provided)
            clay_client: Optional Clay client (uses singleton if not provided)
        """
        self._apollo = apollo_client
        self._apify = apify_client
        self._clay = clay_client

    @property
    def name(self) -> str:
        return "scout"

    @property
    def apollo(self) -> ApolloClient:
        if self._apollo is None:
            self._apollo = get_apollo_client()
        return self._apollo

    @property
    def apify(self) -> ApifyClient:
        if self._apify is None:
            self._apify = get_apify_client()
        return self._apify

    @property
    def clay(self) -> ClayClient:
        if self._clay is None:
            self._clay = get_clay_client()
        return self._clay

    async def enrich_lead(
        self,
        db: AsyncSession,
        lead_id: UUID,
        force_refresh: bool = False,
    ) -> EngineResult[dict[str, Any]]:
        """
        Enrich a single lead using the waterfall approach.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID to enrich
            force_refresh: Skip cache and force re-enrichment

        Returns:
            EngineResult with enrichment data

        Raises:
            NotFoundError: If lead not found
        """
        # Get lead
        lead = await self.get_lead_by_id(db, lead_id)

        # Get domain for cache lookup
        domain = lead.domain or self._extract_domain(lead.email)

        # Tier 0: Check cache (unless forcing refresh)
        if not force_refresh and domain:
            cached = await self._check_cache(domain)
            if cached and self._validate_enrichment(cached):
                # Update lead from cache
                await self._update_lead_from_enrichment(db, lead, cached, from_cache=True)
                return EngineResult.ok(
                    data=cached,
                    metadata={"source": "cache", "tier": 0},
                )

        # Tier 1: Apollo + Apify
        tier1_result = await self._enrich_tier1(lead, domain)
        if tier1_result and self._validate_enrichment(tier1_result):
            # Cache the result
            if domain:
                await enrichment_cache.set(domain, tier1_result)
            # Update lead
            await self._update_lead_from_enrichment(db, lead, tier1_result)
            return EngineResult.ok(
                data=tier1_result,
                metadata={"source": tier1_result.get("source", "apollo"), "tier": 1},
            )

        # Tier 2: Clay fallback
        tier2_result = await self._enrich_tier2(lead, domain)
        if tier2_result and self._validate_enrichment(tier2_result):
            # Cache the result
            if domain:
                await enrichment_cache.set(domain, tier2_result)
            # Update lead
            await self._update_lead_from_enrichment(db, lead, tier2_result)
            return EngineResult.ok(
                data=tier2_result,
                metadata={"source": "clay", "tier": 2},
            )

        # All tiers failed
        return EngineResult.fail(
            error="Enrichment failed: no tier returned valid data",
            metadata={
                "lead_id": str(lead_id),
                "domain": domain,
                "tier1_result": bool(tier1_result),
                "tier2_result": bool(tier2_result),
            },
        )

    async def enrich_batch(
        self,
        db: AsyncSession,
        lead_ids: list[UUID],
        force_refresh: bool = False,
    ) -> EngineResult[dict[str, Any]]:
        """
        Enrich a batch of leads using the waterfall approach.

        Clay is limited to 15% of the batch (Rule).

        Args:
            db: Database session (passed by caller)
            lead_ids: List of lead UUIDs to enrich
            force_refresh: Skip cache and force re-enrichment

        Returns:
            EngineResult with batch enrichment summary
        """
        results = {
            "total": len(lead_ids),
            "cache_hits": 0,
            "tier1_success": 0,
            "tier2_success": 0,
            "failures": 0,
            "clay_budget_used": 0,
            "enriched_leads": [],
            "failed_leads": [],
        }

        # Calculate Clay budget (15% of batch)
        clay_budget = int(len(lead_ids) * CLAY_MAX_PERCENTAGE)

        for lead_id in lead_ids:
            try:
                # Skip Clay if budget exhausted
                use_clay = results["clay_budget_used"] < clay_budget

                result = await self._enrich_single(
                    db=db,
                    lead_id=lead_id,
                    force_refresh=force_refresh,
                    use_clay=use_clay,
                )

                if result.success:
                    tier = result.metadata.get("tier", 1)
                    if tier == 0:
                        results["cache_hits"] += 1
                    elif tier == 1:
                        results["tier1_success"] += 1
                    elif tier == 2:
                        results["tier2_success"] += 1
                        results["clay_budget_used"] += 1

                    results["enriched_leads"].append(
                        {
                            "lead_id": str(lead_id),
                            "tier": tier,
                            "source": result.metadata.get("source"),
                        }
                    )
                else:
                    results["failures"] += 1
                    results["failed_leads"].append(
                        {
                            "lead_id": str(lead_id),
                            "error": result.error,
                        }
                    )

            except Exception as e:
                results["failures"] += 1
                results["failed_leads"].append(
                    {
                        "lead_id": str(lead_id),
                        "error": str(e),
                    }
                )

        return EngineResult.ok(
            data=results,
            metadata={
                "batch_size": len(lead_ids),
                "success_rate": (results["total"] - results["failures"]) / results["total"]
                if results["total"] > 0
                else 0,
            },
        )

    async def _enrich_single(
        self,
        db: AsyncSession,
        lead_id: UUID,
        force_refresh: bool = False,
        use_clay: bool = True,
    ) -> EngineResult[dict[str, Any]]:
        """Enrich a single lead with optional Clay usage."""
        lead = await self.get_lead_by_id(db, lead_id)
        domain = lead.domain or self._extract_domain(lead.email)

        # Tier 0: Cache
        if not force_refresh and domain:
            cached = await self._check_cache(domain)
            if cached and self._validate_enrichment(cached):
                await self._update_lead_from_enrichment(db, lead, cached, from_cache=True)
                return EngineResult.ok(
                    data=cached,
                    metadata={"source": "cache", "tier": 0},
                )

        # Tier 1: Apollo + Apify
        tier1_result = await self._enrich_tier1(lead, domain)
        if tier1_result and self._validate_enrichment(tier1_result):
            if domain:
                await enrichment_cache.set(domain, tier1_result)
            await self._update_lead_from_enrichment(db, lead, tier1_result)
            return EngineResult.ok(
                data=tier1_result,
                metadata={"source": tier1_result.get("source", "apollo"), "tier": 1},
            )

        # Tier 2: Clay (if allowed)
        if use_clay:
            tier2_result = await self._enrich_tier2(lead, domain)
            if tier2_result and self._validate_enrichment(tier2_result):
                if domain:
                    await enrichment_cache.set(domain, tier2_result)
                await self._update_lead_from_enrichment(db, lead, tier2_result)
                return EngineResult.ok(
                    data=tier2_result,
                    metadata={"source": "clay", "tier": 2},
                )

        return EngineResult.fail(
            error="All enrichment tiers failed",
            metadata={"lead_id": str(lead_id)},
        )

    async def _check_cache(self, domain: str) -> dict[str, Any] | None:
        """Check enrichment cache for domain."""
        try:
            return await enrichment_cache.get(domain)
        except Exception:
            return None

    async def _enrich_tier1(
        self,
        lead: Lead,
        domain: str | None,
    ) -> dict[str, Any] | None:
        """
        Tier 1 enrichment using Apollo + Apify.

        Tries Apollo first, then supplements with Apify if needed.
        """
        result = None

        # Try Apollo first
        try:
            apollo_result = await self.apollo.enrich_person(
                email=lead.email,
                linkedin_url=lead.linkedin_url,
                first_name=lead.first_name,
                last_name=lead.last_name,
                domain=domain,
            )

            if apollo_result.get("found"):
                result = apollo_result
        except Exception:
            pass

        # If Apollo didn't find enough, try to supplement with Apify
        if not result or not self._validate_enrichment(result):
            try:
                # If we have LinkedIn URL, scrape profile
                if lead.linkedin_url:
                    apify_results = await self.apify.scrape_linkedin_profiles([lead.linkedin_url])
                    if apify_results:
                        apify_data = apify_results[0]
                        # Merge with Apollo result if available
                        if result:
                            result = self._merge_enrichment(result, apify_data)
                        else:
                            result = apify_data
                            result["source"] = "apify"
            except Exception:
                pass

        return result

    async def _enrich_tier2(
        self,
        lead: Lead,
        domain: str | None,
    ) -> dict[str, Any] | None:
        """Tier 2 enrichment using Clay (premium fallback)."""
        try:
            clay_result = await self.clay.enrich_person(
                email=lead.email,
                linkedin_url=lead.linkedin_url,
                first_name=lead.first_name,
                last_name=lead.last_name,
                company=lead.company,
            )

            if clay_result.get("found"):
                return clay_result
        except Exception:
            pass

        return None

    # ============================================
    # SDK ENRICHMENT (Hot Leads with Signals)
    # ============================================

    async def _sdk_enrich(
        self,
        lead: Lead,
        enrichment_data: dict[str, Any],
        signals: list[str],
    ) -> dict[str, Any] | None:
        """
        Run SDK enrichment for Hot lead with priority signals.

        SDK enrichment performs deep web research to find:
        - Recent funding announcements
        - Current hiring activity
        - Recent news and press releases
        - Pain points and personalization hooks

        Args:
            lead: Lead model instance
            enrichment_data: Standard enrichment data (from Apollo/Clay)
            signals: Priority signals that triggered SDK eligibility

        Returns:
            Merged enrichment data with SDK findings, or None if SDK fails
        """
        try:
            # Build lead data dict for SDK agent
            lead_data = {
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "title": lead.title,
                "company_name": lead.company or enrichment_data.get("company"),
                "company_domain": lead.domain or enrichment_data.get("domain"),
                "company_industry": lead.organization_industry
                or enrichment_data.get("organization_industry"),
                "company_employee_count": lead.organization_employee_count
                or enrichment_data.get("organization_employee_count"),
                "linkedin_url": lead.linkedin_url or enrichment_data.get("linkedin_url"),
                "linkedin_headline": enrichment_data.get("linkedin_headline"),
                "linkedin_about": enrichment_data.get("linkedin_about"),
                "linkedin_recent_posts": enrichment_data.get("linkedin_recent_posts"),
            }

            logger.info(
                "Running SDK enrichment for Hot lead",
                extra={
                    "lead_id": str(lead.id),
                    "signals": signals,
                    "company": lead_data.get("company_name"),
                },
            )

            # Run SDK enrichment agent
            result = await run_sdk_enrichment(lead_data)

            if result.success and result.data:
                logger.info(
                    "SDK enrichment succeeded",
                    extra={
                        "lead_id": str(lead.id),
                        "cost_aud": result.cost_aud,
                        "turns": result.turns_used,
                        "tool_calls": len(result.tool_calls),
                    },
                )

                # Convert Pydantic model to dict if needed
                sdk_data = result.data
                if hasattr(sdk_data, "model_dump"):
                    sdk_data = sdk_data.model_dump()

                return {
                    "sdk_enrichment": sdk_data,
                    "sdk_signals": signals,
                    "sdk_cost_aud": result.cost_aud,
                    "sdk_turns_used": result.turns_used,
                    "sdk_tool_calls": result.tool_calls,
                }
            else:
                logger.warning(
                    "SDK enrichment failed",
                    extra={
                        "lead_id": str(lead.id),
                        "error": result.error,
                    },
                )
                return None

        except Exception as e:
            logger.exception(f"SDK enrichment error: {e}")
            capture_exception(e)
            return None

    async def enrich_lead_with_sdk(
        self,
        db: AsyncSession,
        lead_id: UUID,
        als_score: int | None = None,
        force_refresh: bool = False,
    ) -> EngineResult[dict[str, Any]]:
        """
        Enrich a lead with optional SDK enhancement for Hot leads.

        This method:
        1. Runs standard waterfall enrichment (cache -> Apollo+Apify -> Clay)
        2. If lead is Hot (ALS >= 85) AND has priority signals, runs SDK enrichment
        3. Merges SDK findings into enrichment data

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID to enrich
            als_score: Pre-calculated ALS score (optional, will be inferred from enrichment)
            force_refresh: Skip cache and force re-enrichment

        Returns:
            EngineResult with enrichment data (including SDK data if applicable)
        """
        # Run standard enrichment first
        standard_result = await self.enrich_lead(db, lead_id, force_refresh)

        if not standard_result.success:
            return standard_result

        # Get the lead to check for SDK eligibility
        lead = await self.get_lead_by_id(db, lead_id)
        enrichment_data = standard_result.data

        # Determine ALS score
        effective_als_score = als_score or lead.als_score or enrichment_data.get("als_score", 0)

        # Build lead data for eligibility check
        lead_data_for_check = {
            "als_score": effective_als_score,
            "company_latest_funding_date": enrichment_data.get("company_latest_funding_date"),
            "company_open_roles": enrichment_data.get("company_is_hiring")
            or enrichment_data.get("organization_is_hiring"),
            "company_employee_count": enrichment_data.get("organization_employee_count"),
            "linkedin_engagement_score": enrichment_data.get("linkedin_engagement_score"),
            "source": lead.source if hasattr(lead, "source") else None,
            "tech_stack_match_score": enrichment_data.get("tech_stack_match_score"),
        }

        # Check SDK eligibility
        sdk_eligible, signals = should_use_sdk_enrichment(lead_data_for_check)

        if sdk_eligible:
            logger.info(
                "Lead qualifies for SDK enrichment",
                extra={
                    "lead_id": str(lead_id),
                    "als_score": effective_als_score,
                    "signals": signals,
                },
            )

            # Run SDK enrichment
            sdk_result = await self._sdk_enrich(lead, enrichment_data, signals)

            # Log SDK usage to database for cost tracking
            if sdk_result:
                try:
                    await log_sdk_usage(
                        db,
                        client_id=lead.client_id,
                        agent_type="enrichment",
                        model_used="claude-sonnet-4-20250514",
                        input_tokens=sdk_result.get("sdk_tool_calls", [{}])[0].get(
                            "input_tokens", 0
                        )
                        if sdk_result.get("sdk_tool_calls")
                        else 0,
                        output_tokens=0,  # Not tracked at this level
                        cost_aud=sdk_result.get("sdk_cost_aud", 0),
                        turns_used=sdk_result.get("sdk_turns_used", 1),
                        tool_calls=sdk_result.get("sdk_tool_calls", []),
                        success=True,
                        lead_id=lead_id,
                    )
                except Exception as log_err:
                    logger.warning(f"Failed to log SDK usage: {log_err}")

            if sdk_result:
                # Merge SDK data into enrichment result
                enrichment_data["sdk_enrichment"] = sdk_result.get("sdk_enrichment")
                enrichment_data["sdk_signals"] = sdk_result.get("sdk_signals")
                enrichment_data["sdk_cost_aud"] = sdk_result.get("sdk_cost_aud", 0)
                enrichment_data["enrichment_source"] = (
                    f"{enrichment_data.get('source', 'unknown')}+sdk"
                )

                # Update the lead with SDK data
                await self._update_lead_sdk_enrichment(db, lead, sdk_result)

                return EngineResult.ok(
                    data=enrichment_data,
                    metadata={
                        **standard_result.metadata,
                        "sdk_enhanced": True,
                        "sdk_signals": signals,
                        "sdk_cost_aud": sdk_result.get("sdk_cost_aud", 0),
                    },
                )
            else:
                # SDK failed but standard enrichment succeeded
                return EngineResult.ok(
                    data=enrichment_data,
                    metadata={
                        **standard_result.metadata,
                        "sdk_enhanced": False,
                        "sdk_eligible": True,
                        "sdk_signals": signals,
                        "sdk_error": "SDK enrichment failed",
                    },
                )

        # Not eligible for SDK - return standard result
        return EngineResult.ok(
            data=enrichment_data,
            metadata={
                **standard_result.metadata,
                "sdk_enhanced": False,
                "sdk_eligible": False,
            },
        )

    async def _update_lead_sdk_enrichment(
        self,
        db: AsyncSession,
        lead: Lead,
        sdk_result: dict[str, Any],
    ) -> None:
        """
        Update lead record with SDK enrichment data.

        Args:
            db: Database session
            lead: Lead model instance
            sdk_result: SDK enrichment result dict
        """
        from sqlalchemy import update as sql_update

        sdk_data = sdk_result.get("sdk_enrichment", {})
        signals = sdk_result.get("sdk_signals", [])
        cost = sdk_result.get("sdk_cost_aud", 0)

        # Store SDK data in dedicated fields (added in migration 035)
        update_values = {
            "updated_at": datetime.utcnow(),
            "sdk_enrichment": sdk_data,
            "sdk_signals": signals,
            "sdk_cost_aud": cost,
            "sdk_enriched_at": datetime.utcnow(),
        }

        # Update enrichment source to indicate SDK enhancement
        current_source = lead.enrichment_source or "unknown"
        if "+sdk" not in current_source:
            update_values["enrichment_source"] = f"{current_source}+sdk"

        stmt = sql_update(Lead).where(Lead.id == lead.id).values(**update_values)
        await db.execute(stmt)
        await db.commit()

    def _validate_enrichment(self, data: dict[str, Any]) -> bool:
        """
        Validate enrichment result meets minimum requirements.

        Rule 4: Confidence threshold is 0.70.
        Required fields: email, first_name, last_name, company.
        """
        if not data.get("found"):
            return False

        # Check confidence threshold
        confidence = data.get("confidence", 0.0)
        if confidence < CONFIDENCE_THRESHOLD:
            return False

        # Check required fields
        return all(data.get(field) for field in REQUIRED_FIELDS)

    def _merge_enrichment(
        self,
        primary: dict[str, Any],
        secondary: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge two enrichment results, preferring primary."""
        merged = primary.copy()

        # Fill in missing fields from secondary
        for key, value in secondary.items():
            if key not in merged or merged[key] is None:
                merged[key] = value

        # Update source to indicate merge
        merged["source"] = (
            f"{primary.get('source', 'unknown')}+{secondary.get('source', 'unknown')}"
        )

        # Recalculate confidence as average
        primary_conf = primary.get("confidence", 0.5)
        secondary_conf = secondary.get("confidence", 0.5)
        merged["confidence"] = (primary_conf + secondary_conf) / 2

        return merged

    async def _update_lead_from_enrichment(
        self,
        db: AsyncSession,
        lead: Lead,
        enrichment: dict[str, Any],
        from_cache: bool = False,
    ) -> None:
        """Update lead record with enrichment data."""
        # Build update data
        update_data = {
            "first_name": enrichment.get("first_name") or lead.first_name,
            "last_name": enrichment.get("last_name") or lead.last_name,
            "title": enrichment.get("title") or lead.title,
            "company": enrichment.get("company") or lead.company,
            "phone": enrichment.get("phone") or lead.phone,
            "linkedin_url": enrichment.get("linkedin_url") or lead.linkedin_url,
            "domain": enrichment.get("domain") or lead.domain,
            "personal_email": enrichment.get("personal_email") or lead.personal_email,
            "seniority_level": enrichment.get("seniority") or lead.seniority_level,
            # Organization data
            "organization_industry": enrichment.get("organization_industry"),
            "organization_employee_count": enrichment.get("organization_employee_count"),
            "organization_country": enrichment.get("organization_country"),
            "organization_founded_year": enrichment.get("organization_founded_year"),
            "organization_is_hiring": enrichment.get("organization_is_hiring"),
            "organization_website": enrichment.get("organization_website"),
            "organization_linkedin_url": enrichment.get("organization_linkedin_url"),
            # Enrichment metadata
            "enrichment_source": enrichment.get("source"),
            "enrichment_confidence": enrichment.get("confidence"),
            "enrichment_version": enrichment.get("_cache_version") if from_cache else "v1",
            "enriched_at": datetime.utcnow(),
            "status": LeadStatus.ENRICHED,
            "updated_at": datetime.utcnow(),
        }

        # Handle employment start date
        if enrichment.get("employment_start_date"):
            try:
                from datetime import date as date_type

                if isinstance(enrichment["employment_start_date"], str):
                    update_data["employment_start_date"] = date_type.fromisoformat(
                        enrichment["employment_start_date"][:10]
                    )
            except (ValueError, TypeError):
                pass

        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}

        # Execute update
        stmt = update(Lead).where(Lead.id == lead.id).values(**update_data)
        await db.execute(stmt)
        await db.commit()

    def _extract_domain(self, email: str | None) -> str | None:
        """Extract domain from email address."""
        if not email or "@" not in email:
            return None
        return email.split("@")[1].lower()

    async def perform_deep_research(
        self,
        db: AsyncSession,
        lead_id: UUID,
        anthropic_client: AnthropicClient | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Perform deep research on a hot lead (ALS > 85).

        Scrapes LinkedIn posts and generates personalized icebreaker hooks.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID to research
            anthropic_client: Optional Anthropic client (uses singleton if not provided)

        Returns:
            EngineResult with deep research data including icebreaker hook
        """
        # Get lead
        lead = await self.get_lead_by_id(db, lead_id)

        # Validate lead has LinkedIn URL
        if not lead.linkedin_url:
            return EngineResult.fail(
                error="Lead does not have a LinkedIn URL",
                metadata={"lead_id": str(lead_id)},
            )

        # Get Anthropic client
        anthropic = anthropic_client or get_anthropic_client()

        # Initialize skill
        skill = DeepResearchSkill(apify_client=self.apify)

        # Execute deep research
        skill_input = skill.Input(
            linkedin_url=lead.linkedin_url,
            first_name=lead.first_name or "",
            last_name=lead.last_name or "",
            company=lead.company or "",
            title=lead.title or "",
        )

        result = await skill.run(skill_input, anthropic)

        if not result.success:
            return EngineResult.fail(
                error=result.error or "Deep research failed",
                metadata={"lead_id": str(lead_id), "skill_metadata": result.metadata},
            )

        # Save results to database
        output = result.data

        # Update lead with deep research data
        deep_research_data = {
            "icebreaker_hook": output.icebreaker_hook,
            "profile_summary": output.profile_summary,
            "recent_activity": output.recent_activity,
            "posts_found": output.posts_found,
            "confidence": result.confidence,
            "tokens_used": result.tokens_used,
            "cost_aud": result.cost_aud,
        }

        stmt = (
            update(Lead)
            .where(Lead.id == lead_id)
            .values(
                deep_research_data=deep_research_data,
                deep_research_run_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        await db.execute(stmt)

        # Save social posts to audit trail
        for post in output.posts:
            if post.get("type") == "profile_summary":
                continue  # Skip synthetic profile summaries

            post_date = None
            if post.get("date"):
                try:
                    if isinstance(post["date"], str):
                        post_date = datetime.fromisoformat(post["date"][:10]).date()
                    elif isinstance(post["date"], datetime):
                        post_date = post["date"].date()
                except (ValueError, TypeError):
                    pass

            social_post = LeadSocialPost(
                lead_id=lead_id,
                source="linkedin",
                post_content=post.get("content", "")[:2000],  # Limit content length
                post_date=post_date,
                summary_hook=output.icebreaker_hook if post == output.posts[0] else None,
            )
            db.add(social_post)

        await db.commit()

        return EngineResult.ok(
            data={
                "lead_id": str(lead_id),
                "icebreaker_hook": output.icebreaker_hook,
                "profile_summary": output.profile_summary,
                "posts_found": output.posts_found,
                "confidence": result.confidence,
            },
            metadata={
                "tokens_used": result.tokens_used,
                "cost_aud": result.cost_aud,
            },
        )

    # ============================================
    # PHASE 24A: Lead Pool Methods
    # ============================================

    async def enrich_to_pool(
        self,
        db: AsyncSession,
        email: str | None = None,
        linkedin_url: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        domain: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Enrich a person and write directly to lead_pool.

        This is the preferred method for new leads. It captures all
        50+ fields from Apollo and stores them in the pool.

        Args:
            db: Database session
            email: Email address
            linkedin_url: LinkedIn profile URL
            first_name: First name
            last_name: Last name
            domain: Company domain

        Returns:
            EngineResult with pool lead data including lead_pool_id
        """
        if not any([email, linkedin_url, (first_name and last_name and domain)]):
            return EngineResult.fail(
                error="Must provide email, LinkedIn URL, or name + domain",
                metadata={},
            )

        # Check if already in pool (by email)
        if email:
            existing = await self._get_pool_lead_by_email(db, email)
            if existing:
                return EngineResult.ok(
                    data=existing,
                    metadata={"source": "pool_cache", "already_exists": True},
                )

        # Enrich via Apollo (pool format)
        try:
            enriched = await self.apollo.enrich_person_for_pool(
                email=email,
                linkedin_url=linkedin_url,
                first_name=first_name,
                last_name=last_name,
                domain=domain,
            )

            if not enriched.get("found"):
                return EngineResult.fail(
                    error="Lead not found in Apollo",
                    metadata={"email": email, "linkedin_url": linkedin_url},
                )

            # Insert into pool
            pool_lead = await self._insert_into_pool(db, enriched)

            return EngineResult.ok(
                data=pool_lead,
                metadata={"source": "apollo", "tier": 1},
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Pool enrichment failed: {str(e)}",
                metadata={"email": email},
            )

    async def search_and_populate_pool(
        self,
        db: AsyncSession,
        icp_criteria: dict[str, Any],
        limit: int = 25,
        client_id: UUID | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Search Apollo for leads matching ICP and populate the pool.

        This is used to proactively fill the pool with matching leads.

        Phase 19: When client_id is provided, WHO conversion patterns are
        automatically applied to refine the search criteria. This improves
        lead quality based on what's actually converting for this client.

        Args:
            db: Database session
            icp_criteria: ICP matching criteria
            limit: Maximum leads to add
            client_id: Optional client ID to filter suppressed leads (Phase 24F)
                       and apply WHO refinements (Phase 19)

        Returns:
            EngineResult with population summary
        """
        # Phase 19: Apply WHO pattern refinements if client_id provided
        # This merges learned conversion patterns with the base ICP criteria
        search_criteria = icp_criteria
        who_refinements_applied = False

        if client_id:
            try:
                search_criteria = await get_who_refined_criteria(
                    db=db,
                    client_id=client_id,
                    base_criteria=icp_criteria,
                )
                who_refinements_applied = search_criteria != icp_criteria
                if who_refinements_applied:
                    logger.info(
                        f"WHO refinements applied for client {client_id}: "
                        f"titles={search_criteria.get('titles', [])[:3]}, "
                        f"industries={search_criteria.get('industries', [])[:3]}"
                    )
            except Exception as e:
                # Log but don't fail - fall back to base criteria
                logger.warning(f"WHO refinement failed for client {client_id}: {e}")
                search_criteria = icp_criteria

        # Search Apollo with pool-compatible format (using refined criteria)
        try:
            leads = await self.apollo.search_people_for_pool(
                domain=search_criteria.get("domain"),
                titles=search_criteria.get("titles"),
                seniorities=search_criteria.get("seniorities"),
                industries=search_criteria.get("industries"),
                employee_min=search_criteria.get("employee_min"),
                employee_max=search_criteria.get("employee_max"),
                countries=search_criteria.get("countries"),
                limit=limit,
            )

            if not leads:
                return EngineResult.ok(
                    data={"added": 0, "skipped": 0, "suppressed": 0, "total": 0},
                    metadata={
                        "criteria": search_criteria,
                        "base_criteria": icp_criteria,
                        "who_refinements_applied": who_refinements_applied,
                    },
                )

            added = 0
            skipped = 0
            suppressed = 0

            # Get suppressed emails if client_id provided (Phase 24F)
            suppressed_emails: set[str] = set()
            if client_id:
                emails = [l.get("email", "").lower() for l in leads if l.get("email")]
                suppressed_emails = await self._get_suppressed_emails(db, client_id, emails)

            for lead_data in leads:
                email = lead_data.get("email")
                if not email:
                    skipped += 1
                    continue

                # Check suppression (Phase 24F)
                if email.lower() in suppressed_emails:
                    logger.info(f"Filtered suppressed lead: {email}")
                    suppressed += 1
                    continue

                # Check if already exists
                existing = await self._get_pool_lead_by_email(db, email)
                if existing:
                    skipped += 1
                    continue

                # Insert into pool
                await self._insert_into_pool(db, lead_data)
                added += 1

            return EngineResult.ok(
                data={
                    "added": added,
                    "skipped": skipped,
                    "suppressed": suppressed,
                    "total": len(leads),
                    "who_refinements_applied": who_refinements_applied,
                },
                metadata={
                    "criteria": search_criteria,
                    "base_criteria": icp_criteria,
                    "who_refinements_applied": who_refinements_applied,
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Pool population failed: {str(e)}",
                metadata={"criteria": icp_criteria},
            )

    # ============================================
    # PHASE 24F: Suppression Filtering
    # ============================================

    async def filter_suppressed_leads(
        self,
        db: AsyncSession,
        client_id: UUID,
        leads: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Filter out suppressed leads for a specific client.

        Uses the is_suppressed database function directly (no service import).

        Args:
            db: Database session
            client_id: Client UUID to check suppression against
            leads: List of lead dicts with 'email' key

        Returns:
            List of non-suppressed leads
        """
        if not leads:
            return []

        # Extract emails
        emails = [l.get("email", "").lower() for l in leads if l.get("email")]
        if not emails:
            return leads

        # Get suppressed emails using database function
        suppressed_emails = await self._get_suppressed_emails(db, client_id, emails)

        # Filter out suppressed
        filtered = []
        for lead in leads:
            email = lead.get("email", "").lower()
            if email and email in suppressed_emails:
                logger.info(f"Filtered suppressed lead: {email}")
                continue
            filtered.append(lead)

        return filtered

    async def _get_suppressed_emails(
        self,
        db: AsyncSession,
        client_id: UUID,
        emails: list[str],
    ) -> set[str]:
        """
        Get set of suppressed emails for a client.

        Uses batch query for efficiency.

        Args:
            db: Database session
            client_id: Client UUID
            emails: List of emails to check

        Returns:
            Set of suppressed email addresses
        """
        if not emails:
            return set()

        suppressed: set[str] = set()

        # Extract domains for domain-level suppression
        domains: set[str] = set()
        email_domain_map: dict[str, str] = {}
        for email in emails:
            if "@" in email:
                domain = email.split("@")[1].lower()
                domains.add(domain)
                email_domain_map[email.lower()] = domain

        # Check domain-level suppression
        if domains:
            domain_result = await db.execute(
                text("""
                    SELECT domain FROM suppression_list
                    WHERE client_id = :client_id
                    AND domain = ANY(:domains)
                    AND (expires_at IS NULL OR expires_at > NOW())
                """),
                {"client_id": str(client_id), "domains": list(domains)},
            )
            suppressed_domains = {row.domain for row in domain_result.fetchall()}

            # Add emails with suppressed domains
            for email, domain in email_domain_map.items():
                if domain in suppressed_domains:
                    suppressed.add(email)

        # Check email-level suppression
        remaining_emails = [e for e in emails if e.lower() not in suppressed]
        if remaining_emails:
            email_result = await db.execute(
                text("""
                    SELECT email FROM suppression_list
                    WHERE client_id = :client_id
                    AND email = ANY(:emails)
                    AND (expires_at IS NULL OR expires_at > NOW())
                """),
                {"client_id": str(client_id), "emails": remaining_emails},
            )
            for row in email_result.fetchall():
                suppressed.add(row.email)

        return suppressed

    async def _get_pool_lead_by_email(self, db: AsyncSession, email: str) -> dict[str, Any] | None:
        """Get a lead from the pool by email."""
        query = text("""
            SELECT * FROM lead_pool
            WHERE email = :email
        """)
        result = await db.execute(query, {"email": email.lower().strip()})
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def _insert_into_pool(
        self, db: AsyncSession, lead_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Insert a lead into the pool."""
        import json

        # Map email_status to valid enum value
        email_status = lead_data.get("email_status", "unknown")
        if email_status not in ("verified", "guessed", "invalid", "catch_all", "unknown"):
            email_status = "unknown"

        query = text("""
            INSERT INTO lead_pool (
                apollo_id, email, linkedin_url,
                first_name, last_name, title, seniority,
                linkedin_headline, photo_url, twitter_url,
                phone, personal_email,
                city, state, country, timezone,
                departments, employment_history, current_role_start_date,
                company_name, company_domain, company_website,
                company_linkedin_url, company_description, company_logo_url,
                company_industry, company_sub_industry,
                company_employee_count, company_revenue, company_revenue_range,
                company_founded_year, company_country, company_city,
                company_state, company_postal_code,
                company_is_hiring, company_latest_funding_stage,
                company_latest_funding_date, company_total_funding,
                company_technologies, company_keywords,
                email_status, enrichment_source, enrichment_confidence,
                enriched_at, enrichment_data,
                pool_status
            ) VALUES (
                :apollo_id, :email, :linkedin_url,
                :first_name, :last_name, :title, :seniority,
                :linkedin_headline, :photo_url, :twitter_url,
                :phone, :personal_email,
                :city, :state, :country, :timezone,
                :departments, CAST(:employment_history AS jsonb), :current_role_start_date,
                :company_name, :company_domain, :company_website,
                :company_linkedin_url, :company_description, :company_logo_url,
                :company_industry, :company_sub_industry,
                :company_employee_count, :company_revenue, :company_revenue_range,
                :company_founded_year, :company_country, :company_city,
                :company_state, :company_postal_code,
                :company_is_hiring, :company_latest_funding_stage,
                :company_latest_funding_date, :company_total_funding,
                :company_technologies, :company_keywords,
                CAST(:email_status AS email_status_type), :enrichment_source, :enrichment_confidence,
                NOW(), CAST(:enrichment_data AS jsonb),
                'available'
            )
            ON CONFLICT (email) DO UPDATE SET
                last_enriched_at = NOW(),
                updated_at = NOW()
            RETURNING *
        """)

        params = {
            "apollo_id": lead_data.get("apollo_id"),
            "email": lead_data.get("email", "").lower().strip(),
            "linkedin_url": lead_data.get("linkedin_url"),
            "first_name": lead_data.get("first_name"),
            "last_name": lead_data.get("last_name"),
            "title": lead_data.get("title"),
            "seniority": lead_data.get("seniority"),
            "linkedin_headline": lead_data.get("linkedin_headline"),
            "photo_url": lead_data.get("photo_url"),
            "twitter_url": lead_data.get("twitter_url"),
            "phone": lead_data.get("phone"),
            "personal_email": lead_data.get("personal_email"),
            "city": lead_data.get("city"),
            "state": lead_data.get("state"),
            "country": lead_data.get("country"),
            "timezone": lead_data.get("timezone"),
            "departments": lead_data.get("departments", []),
            "employment_history": json.dumps(lead_data.get("employment_history"))
            if lead_data.get("employment_history")
            else None,
            "current_role_start_date": parse_date_string(lead_data.get("current_role_start_date")),
            "company_name": lead_data.get("company_name"),
            "company_domain": lead_data.get("company_domain"),
            "company_website": lead_data.get("company_website"),
            "company_linkedin_url": lead_data.get("company_linkedin_url"),
            "company_description": lead_data.get("company_description"),
            "company_logo_url": lead_data.get("company_logo_url"),
            "company_industry": lead_data.get("company_industry"),
            "company_sub_industry": lead_data.get("company_sub_industry"),
            "company_employee_count": lead_data.get("company_employee_count"),
            "company_revenue": lead_data.get("company_revenue"),
            "company_revenue_range": lead_data.get("company_revenue_range"),
            "company_founded_year": lead_data.get("company_founded_year"),
            "company_country": lead_data.get("company_country"),
            "company_city": lead_data.get("company_city"),
            "company_state": lead_data.get("company_state"),
            "company_postal_code": lead_data.get("company_postal_code"),
            "company_is_hiring": lead_data.get("company_is_hiring"),
            "company_latest_funding_stage": lead_data.get("company_latest_funding_stage"),
            "company_latest_funding_date": parse_date_string(
                lead_data.get("company_latest_funding_date")
            ),
            "company_total_funding": lead_data.get("company_total_funding"),
            "company_technologies": lead_data.get("company_technologies", []),
            "company_keywords": lead_data.get("company_keywords", []),
            "email_status": email_status,
            "enrichment_source": lead_data.get("enrichment_source", "apollo"),
            "enrichment_confidence": lead_data.get("confidence")
            or lead_data.get("enrichment_confidence"),
            "enrichment_data": json.dumps(lead_data.get("enrichment_data"))
            if lead_data.get("enrichment_data")
            else None,
        }

        result = await db.execute(query, params)
        row = result.fetchone()
        await db.commit()

        return dict(row._mapping) if row else {}

    # ============================================
    # PHASE 24A+: LinkedIn Enrichment for Assignments
    # ============================================

    async def enrich_linkedin_for_assignment(
        self,
        db: AsyncSession,
        assignment_id: UUID,
        linkedin_person_url: str | None = None,
        linkedin_company_url: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Enrich a lead assignment with full LinkedIn data.

        Scrapes both person and company LinkedIn profiles for
        hyper-personalization across all 5 channels.

        Args:
            db: Database session
            assignment_id: Lead assignment UUID
            linkedin_person_url: Person's LinkedIn URL
            linkedin_company_url: Company's LinkedIn URL

        Returns:
            EngineResult with LinkedIn data for person and company
        """
        import asyncio

        person_data = None
        company_data = None
        errors = []

        # Scrape person and company in parallel
        tasks = []

        if linkedin_person_url:
            tasks.append(self._scrape_person_linkedin(linkedin_person_url))
        else:
            tasks.append(asyncio.coroutine(lambda: None)())

        if linkedin_company_url:
            tasks.append(self._scrape_company_linkedin(linkedin_company_url))
        else:
            tasks.append(asyncio.coroutine(lambda: None)())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process person result
        if linkedin_person_url:
            if isinstance(results[0], Exception):
                errors.append(f"Person scrape failed: {results[0]}")
            else:
                person_data = results[0]

        # Process company result
        if linkedin_company_url:
            idx = 1 if linkedin_person_url else 0
            if isinstance(results[idx], Exception):
                errors.append(f"Company scrape failed: {results[idx]}")
            else:
                company_data = results[idx]

        # Update assignment with LinkedIn data
        update_query = text("""
            UPDATE lead_assignments
            SET
                linkedin_person_data = :person_data,
                linkedin_person_scraped_at = CASE WHEN :person_data IS NOT NULL THEN NOW() ELSE linkedin_person_scraped_at END,
                linkedin_company_data = :company_data,
                linkedin_company_scraped_at = CASE WHEN :company_data IS NOT NULL THEN NOW() ELSE linkedin_company_scraped_at END,
                enrichment_status = 'linkedin_complete',
                updated_at = NOW()
            WHERE id = :assignment_id
            RETURNING id
        """)

        await db.execute(
            update_query,
            {
                "assignment_id": str(assignment_id),
                "person_data": json.dumps(person_data) if person_data else None,
                "company_data": json.dumps(company_data) if company_data else None,
            },
        )
        await db.commit()

        return EngineResult.ok(
            data={
                "assignment_id": str(assignment_id),
                "person_data": person_data,
                "company_data": company_data,
                "person_posts_found": len(person_data.get("posts", [])) if person_data else 0,
                "company_posts_found": len(company_data.get("posts", [])) if company_data else 0,
            },
            metadata={
                "errors": errors if errors else None,
            },
        )

    async def _scrape_person_linkedin(self, linkedin_url: str) -> dict[str, Any]:
        """
        Scrape full LinkedIn person profile with posts.

        Returns:
            Dict with profile data, about, experience, and last 5 posts
        """
        try:
            profiles = await self.apify.scrape_linkedin_profiles([linkedin_url])
            if not profiles:
                return {"found": False, "url": linkedin_url}

            profile = profiles[0]

            # Extract posts if available
            posts = []
            raw_posts = profile.get("posts", []) or profile.get("activity", [])
            for post in raw_posts[:5]:  # Last 5 posts
                posts.append(
                    {
                        "content": post.get("text") or post.get("content", ""),
                        "date": post.get("date") or post.get("posted_date"),
                        "likes": post.get("likes", 0),
                        "comments": post.get("comments", 0),
                        "shares": post.get("shares", 0),
                    }
                )

            return {
                "found": True,
                "url": linkedin_url,
                "headline": profile.get("title") or profile.get("headline"),
                "about": profile.get("about") or profile.get("summary"),
                "location": profile.get("location"),
                "connections": profile.get("connections") or profile.get("connectionsCount"),
                "followers": profile.get("followers") or profile.get("followersCount"),
                "experience": profile.get("experience", [])[:5],  # Last 5 roles
                "education": profile.get("education", []),
                "skills": profile.get("skills", [])[:10],  # Top 10 skills
                "posts": posts,
                "posts_count": len(posts),
            }
        except Exception as e:
            logger.warning(f"LinkedIn person scrape failed for {linkedin_url}: {e}")
            return {"found": False, "url": linkedin_url, "error": str(e)}

    async def _scrape_company_linkedin(self, linkedin_url: str) -> dict[str, Any]:
        """
        Scrape full LinkedIn company profile with posts.

        Returns:
            Dict with company data, description, and last 5 posts
        """
        try:
            company_data = await self.apify.scrape_linkedin_company(linkedin_url)
            if not company_data.get("found"):
                return {"found": False, "url": linkedin_url}

            # Note: Company posts may need a separate actor or may be included
            # depending on the Apify actor used
            posts = company_data.get("posts", [])[:5]

            return {
                "found": True,
                "url": linkedin_url,
                "name": company_data.get("name"),
                "description": company_data.get("description"),
                "industry": company_data.get("industry"),
                "specialties": company_data.get("specialties", []),
                "headquarters": company_data.get("headquarters"),
                "website": company_data.get("website"),
                "employee_count": company_data.get("employee_count"),
                "employee_range": company_data.get("employee_range"),
                "followers": company_data.get("followers"),
                "founded_year": company_data.get("founded_year"),
                "posts": posts,
                "posts_count": len(posts),
            }
        except Exception as e:
            logger.warning(f"LinkedIn company scrape failed for {linkedin_url}: {e}")
            return {"found": False, "url": linkedin_url, "error": str(e)}


# Singleton instance
_scout_engine: ScoutEngine | None = None


def get_scout_engine() -> ScoutEngine:
    """Get or create Scout engine instance."""
    global _scout_engine
    if _scout_engine is None:
        _scout_engine = ScoutEngine()
    return _scout_engine


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] No imports from other engines (Rule 12)
# [x] Soft delete check inherited from BaseEngine
# [x] Cache versioning via enrichment_cache (Rule 16)
# [x] Validation threshold 0.70 (Rule 4)
# [x] Waterfall: Cache → Apollo+Apify → Clay
# [x] Clay limited to 15% of batch
# [x] Minimum fields validation
# [x] Lead update from enrichment
# [x] Batch enrichment support
# [x] EngineResult wrapper for responses
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] perform_deep_research method (Phase 21)
# [x] DeepResearchSkill integration
# [x] LeadSocialPost audit trail
# [x] filter_suppressed_leads method (Phase 24F)
# [x] _get_suppressed_emails batch helper (Phase 24F)
# [x] search_and_populate_pool supports client_id for suppression (Phase 24F)
# [x] enrich_linkedin_for_assignment method (Phase 24A+)
# [x] _scrape_person_linkedin helper (Phase 24A+)
# [x] _scrape_company_linkedin helper (Phase 24A+)
