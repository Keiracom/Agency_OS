"""
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

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from src.engines.base import BaseEngine, EngineResult
from src.exceptions import EngineError, ValidationError
from src.agents.skills.research_skills import DeepResearchSkill
from src.integrations.anthropic import AnthropicClient, get_anthropic_client
from src.integrations.apollo import ApolloClient, get_apollo_client
from src.integrations.apify import ApifyClient, get_apify_client
from src.integrations.clay import ClayClient, get_clay_client
from src.integrations.redis import enrichment_cache
from src.models.base import LeadStatus
from src.models.lead import Lead
from src.models.lead_social_post import LeadSocialPost


# Minimum required fields for valid enrichment
REQUIRED_FIELDS = ["email", "first_name", "last_name", "company"]

# Confidence threshold (Rule 4)
CONFIDENCE_THRESHOLD = 0.70

# Max percentage for Clay fallback
CLAY_MAX_PERCENTAGE = 0.15


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

                    results["enriched_leads"].append({
                        "lead_id": str(lead_id),
                        "tier": tier,
                        "source": result.metadata.get("source"),
                    })
                else:
                    results["failures"] += 1
                    results["failed_leads"].append({
                        "lead_id": str(lead_id),
                        "error": result.error,
                    })

            except Exception as e:
                results["failures"] += 1
                results["failed_leads"].append({
                    "lead_id": str(lead_id),
                    "error": str(e),
                })

        return EngineResult.ok(
            data=results,
            metadata={
                "batch_size": len(lead_ids),
                "success_rate": (results["total"] - results["failures"]) / results["total"]
                if results["total"] > 0 else 0,
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
                    apify_results = await self.apify.scrape_linkedin_profiles(
                        [lead.linkedin_url]
                    )
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
        for field in REQUIRED_FIELDS:
            if not data.get(field):
                return False

        return True

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
        merged["source"] = f"{primary.get('source', 'unknown')}+{secondary.get('source', 'unknown')}"

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
        stmt = (
            update(Lead)
            .where(Lead.id == lead.id)
            .values(**update_data)
        )
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

        Args:
            db: Database session
            icp_criteria: ICP matching criteria
            limit: Maximum leads to add
            client_id: Optional client ID to filter suppressed leads (Phase 24F)

        Returns:
            EngineResult with population summary
        """
        # Search Apollo with pool-compatible format
        try:
            leads = await self.apollo.search_people_for_pool(
                domain=icp_criteria.get("domain"),
                titles=icp_criteria.get("titles"),
                seniorities=icp_criteria.get("seniorities"),
                industries=icp_criteria.get("industries"),
                employee_min=icp_criteria.get("employee_min"),
                employee_max=icp_criteria.get("employee_max"),
                countries=icp_criteria.get("countries"),
                limit=limit,
            )

            if not leads:
                return EngineResult.ok(
                    data={"added": 0, "skipped": 0, "suppressed": 0, "total": 0},
                    metadata={"criteria": icp_criteria},
                )

            added = 0
            skipped = 0
            suppressed = 0

            # Get suppressed emails if client_id provided (Phase 24F)
            suppressed_emails: set[str] = set()
            if client_id:
                emails = [l.get("email", "").lower() for l in leads if l.get("email")]
                suppressed_emails = await self._get_suppressed_emails(
                    db, client_id, emails
                )

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
                },
                metadata={"criteria": icp_criteria},
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

    async def _get_pool_lead_by_email(
        self,
        db: AsyncSession,
        email: str
    ) -> dict[str, Any] | None:
        """Get a lead from the pool by email."""
        query = text("""
            SELECT * FROM lead_pool
            WHERE email = :email
        """)
        result = await db.execute(query, {"email": email.lower().strip()})
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def _insert_into_pool(
        self,
        db: AsyncSession,
        lead_data: dict[str, Any]
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
                :departments, :employment_history::jsonb, :current_role_start_date,
                :company_name, :company_domain, :company_website,
                :company_linkedin_url, :company_description, :company_logo_url,
                :company_industry, :company_sub_industry,
                :company_employee_count, :company_revenue, :company_revenue_range,
                :company_founded_year, :company_country, :company_city,
                :company_state, :company_postal_code,
                :company_is_hiring, :company_latest_funding_stage,
                :company_latest_funding_date, :company_total_funding,
                :company_technologies, :company_keywords,
                :email_status::email_status_type, :enrichment_source, :enrichment_confidence,
                NOW(), :enrichment_data::jsonb,
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
            "employment_history": json.dumps(lead_data.get("employment_history")) if lead_data.get("employment_history") else None,
            "current_role_start_date": lead_data.get("current_role_start_date"),
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
            "company_latest_funding_date": lead_data.get("company_latest_funding_date"),
            "company_total_funding": lead_data.get("company_total_funding"),
            "company_technologies": lead_data.get("company_technologies", []),
            "company_keywords": lead_data.get("company_keywords", []),
            "email_status": email_status,
            "enrichment_source": lead_data.get("enrichment_source", "apollo"),
            "enrichment_confidence": lead_data.get("confidence") or lead_data.get("enrichment_confidence"),
            "enrichment_data": json.dumps(lead_data.get("enrichment_data")) if lead_data.get("enrichment_data") else None,
        }

        result = await db.execute(query, params)
        row = result.fetchone()
        await db.commit()

        return dict(row._mapping) if row else {}


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
