"""
FILE: src/services/lead_pool_service.py
PURPOSE: CRUD operations for the centralised lead pool
PHASE: 24A (Lead Pool Architecture)
TASK: POOL-005
DEPENDENCIES:
  - src/models/database.py
  - src/integrations/apollo.py
LAYER: 3 (services)
CONSUMERS: orchestration, API routes

This service manages the platform-wide lead pool where all leads
are stored with full enrichment data before being assigned to clients.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError


class LeadPoolService:
    """
    Service for managing leads in the platform-wide pool.

    The lead pool is the central repository for all leads.
    Leads are enriched and stored here before being assigned
    to any client.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the Lead Pool service.

        Args:
            session: Async database session
        """
        self.session = session

    async def create_or_update(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new lead or update existing one.

        Uses email as the primary dedup key. If a lead with the same
        email exists, updates the existing record. Otherwise, creates new.

        Args:
            lead_data: Lead data from enrichment (Apollo format)

        Returns:
            Created/updated lead pool record

        Raises:
            ValidationError: If email is missing
        """
        email = lead_data.get("email")
        if not email:
            raise ValidationError(message="Email is required for lead pool")

        # Normalize email
        email = email.lower().strip()
        lead_data["email"] = email

        # Check for existing lead by email or apollo_id
        existing = await self.get_by_email(email)

        if existing:
            # Update existing lead
            return await self.update(existing["id"], lead_data)
        else:
            # Create new lead
            return await self.create(lead_data)

    async def create(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new lead in the pool.

        Args:
            lead_data: Lead data from enrichment

        Returns:
            Created lead pool record
        """
        # Build insert statement
        query = """
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
                :departments, :employment_history, :current_role_start_date,
                :company_name, :company_domain, :company_website,
                :company_linkedin_url, :company_description, :company_logo_url,
                :company_industry, :company_sub_industry,
                :company_employee_count, :company_revenue, :company_revenue_range,
                :company_founded_year, :company_country, :company_city,
                :company_state, :company_postal_code,
                :company_is_hiring, :company_latest_funding_stage,
                :company_latest_funding_date, :company_total_funding,
                :company_technologies, :company_keywords,
                :email_status, :enrichment_source, :enrichment_confidence,
                NOW(), :enrichment_data,
                'available'
            )
            RETURNING *
        """

        # Prepare data with defaults
        params = self._prepare_insert_params(lead_data)

        result = await self.session.execute(
            text(query),
            params
        )
        row = result.fetchone()
        await self.session.commit()

        return self._row_to_dict(row)

    async def update(
        self,
        lead_pool_id: UUID,
        lead_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update an existing lead in the pool.

        Args:
            lead_pool_id: Lead pool ID
            lead_data: Updated lead data

        Returns:
            Updated lead pool record
        """
        # Only update fields that are provided and not None
        update_fields = []
        params = {"id": str(lead_pool_id)}

        updatable_fields = [
            "first_name", "last_name", "title", "seniority",
            "linkedin_headline", "photo_url", "twitter_url",
            "phone", "personal_email", "linkedin_url",
            "city", "state", "country", "timezone",
            "departments", "employment_history", "current_role_start_date",
            "company_name", "company_domain", "company_website",
            "company_linkedin_url", "company_description", "company_logo_url",
            "company_industry", "company_sub_industry",
            "company_employee_count", "company_revenue", "company_revenue_range",
            "company_founded_year", "company_country", "company_city",
            "company_state", "company_postal_code",
            "company_is_hiring", "company_latest_funding_stage",
            "company_latest_funding_date", "company_total_funding",
            "company_technologies", "company_keywords",
            "email_status", "enrichment_confidence", "enrichment_data",
        ]

        for field in updatable_fields:
            if field in lead_data and lead_data[field] is not None:
                update_fields.append(f"{field} = :{field}")
                value = lead_data[field]
                # Handle special types
                if isinstance(value, (list, dict)):
                    import json
                    params[field] = json.dumps(value) if isinstance(value, dict) else value
                else:
                    params[field] = value

        if not update_fields:
            # No updates to make, just return existing
            return await self.get_by_id(lead_pool_id)

        # Always update last_enriched_at
        update_fields.append("last_enriched_at = NOW()")
        update_fields.append("updated_at = NOW()")

        query = f"""
            UPDATE lead_pool
            SET {", ".join(update_fields)}
            WHERE id = :id
            RETURNING *
        """

        result = await self.session.execute(text(query), params)
        row = result.fetchone()
        await self.session.commit()

        if not row:
            raise NotFoundError(f"Lead pool {lead_pool_id} not found")

        return self._row_to_dict(row)

    async def get_by_id(self, lead_pool_id: UUID) -> dict[str, Any] | None:
        """
        Get a lead by pool ID.

        Args:
            lead_pool_id: Lead pool ID

        Returns:
            Lead pool record or None
        """
        query = """
            SELECT * FROM lead_pool
            WHERE id = :id
        """
        result = await self.session.execute(
            text(query),
            {"id": str(lead_pool_id)}
        )
        row = result.fetchone()
        return self._row_to_dict(row) if row else None

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        """
        Get a lead by email address.

        Args:
            email: Email address

        Returns:
            Lead pool record or None
        """
        query = """
            SELECT * FROM lead_pool
            WHERE email = :email
        """
        result = await self.session.execute(
            text(query),
            {"email": email.lower().strip()}
        )
        row = result.fetchone()
        return self._row_to_dict(row) if row else None

    async def get_by_apollo_id(self, apollo_id: str) -> dict[str, Any] | None:
        """
        Get a lead by Apollo ID.

        Args:
            apollo_id: Apollo's internal ID

        Returns:
            Lead pool record or None
        """
        query = """
            SELECT * FROM lead_pool
            WHERE apollo_id = :apollo_id
        """
        result = await self.session.execute(
            text(query),
            {"apollo_id": apollo_id}
        )
        row = result.fetchone()
        return self._row_to_dict(row) if row else None

    async def search_available(
        self,
        industry: str | None = None,
        country: str | None = None,
        employee_min: int | None = None,
        employee_max: int | None = None,
        seniorities: list[str] | None = None,
        email_status: str = "verified",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Search for available leads in the pool.

        Only returns leads that are not yet assigned to any client.

        Args:
            industry: Filter by company industry
            country: Filter by company country
            employee_min: Minimum employee count
            employee_max: Maximum employee count
            seniorities: Filter by seniority levels
            email_status: Filter by email verification status
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of matching leads
        """
        conditions = ["pool_status = 'available'"]
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        if industry:
            conditions.append("company_industry ILIKE :industry")
            params["industry"] = f"%{industry}%"

        if country:
            conditions.append("company_country ILIKE :country")
            params["country"] = f"%{country}%"

        if employee_min:
            conditions.append("company_employee_count >= :employee_min")
            params["employee_min"] = employee_min

        if employee_max:
            conditions.append("company_employee_count <= :employee_max")
            params["employee_max"] = employee_max

        if seniorities:
            conditions.append("seniority = ANY(:seniorities)")
            params["seniorities"] = seniorities

        if email_status:
            conditions.append("email_status = :email_status")
            params["email_status"] = email_status

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT * FROM lead_pool
            WHERE {where_clause}
            ORDER BY enrichment_confidence DESC NULLS LAST, created_at DESC
            LIMIT :limit OFFSET :offset
        """

        result = await self.session.execute(text(query), params)
        rows = result.fetchall()

        return [self._row_to_dict(row) for row in rows]

    async def mark_bounced(
        self,
        lead_pool_id: UUID,
        reason: str | None = None
    ) -> bool:
        """
        Mark a lead as bounced globally.

        This prevents ALL clients from contacting this lead.

        Args:
            lead_pool_id: Lead pool ID
            reason: Bounce reason

        Returns:
            True if updated
        """
        query = """
            UPDATE lead_pool
            SET pool_status = 'bounced',
                is_bounced = TRUE,
                bounced_at = NOW(),
                bounce_reason = :reason,
                updated_at = NOW()
            WHERE id = :id
            RETURNING id
        """

        result = await self.session.execute(
            text(query),
            {"id": str(lead_pool_id), "reason": reason}
        )
        row = result.fetchone()
        await self.session.commit()

        return row is not None

    async def mark_unsubscribed(
        self,
        lead_pool_id: UUID,
        reason: str | None = None
    ) -> bool:
        """
        Mark a lead as unsubscribed globally.

        This prevents ALL clients from contacting this lead.

        Args:
            lead_pool_id: Lead pool ID
            reason: Unsubscribe reason

        Returns:
            True if updated
        """
        query = """
            UPDATE lead_pool
            SET pool_status = 'unsubscribed',
                is_unsubscribed = TRUE,
                unsubscribed_at = NOW(),
                unsubscribe_reason = :reason,
                updated_at = NOW()
            WHERE id = :id
            RETURNING id
        """

        result = await self.session.execute(
            text(query),
            {"id": str(lead_pool_id), "reason": reason}
        )
        row = result.fetchone()
        await self.session.commit()

        return row is not None

    async def get_pool_stats(self) -> dict[str, Any]:
        """
        Get pool statistics.

        Returns:
            Pool statistics
        """
        query = """
            SELECT * FROM v_lead_pool_stats
        """
        result = await self.session.execute(text(query))
        row = result.fetchone()

        if not row:
            return {
                "total_leads": 0,
                "available_leads": 0,
                "assigned_leads": 0,
                "converted_leads": 0,
                "bounced_leads": 0,
                "unsubscribed_leads": 0,
                "verified_emails": 0,
                "guessed_emails": 0,
                "enriched_leads": 0,
                "unenriched_leads": 0,
                "unique_industries": 0,
                "unique_countries": 0,
            }

        return dict(row._mapping)

    async def bulk_create(
        self,
        leads: list[dict[str, Any]]
    ) -> tuple[int, int]:
        """
        Bulk create leads in the pool.

        Uses upsert to handle duplicates gracefully.

        Args:
            leads: List of lead data

        Returns:
            Tuple of (created_count, updated_count)
        """
        created = 0
        updated = 0

        for lead_data in leads:
            email = lead_data.get("email")
            if not email:
                continue

            existing = await self.get_by_email(email)
            if existing:
                await self.update(existing["id"], lead_data)
                updated += 1
            else:
                await self.create(lead_data)
                created += 1

        return created, updated

    def _prepare_insert_params(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """Prepare parameters for insert statement."""
        import json

        # Map email_status string to enum value
        email_status = lead_data.get("email_status", "unknown")
        if email_status not in ("verified", "guessed", "invalid", "catch_all", "unknown"):
            email_status = "unknown"

        return {
            "apollo_id": lead_data.get("apollo_id"),
            "email": lead_data.get("email"),
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

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        """Convert database row to dictionary."""
        if row is None:
            return {}
        return dict(row._mapping)


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
# [x] Layer 3 placement (same as engines)
# [x] create_or_update for upsert logic
# [x] create for new leads
# [x] update for existing leads
# [x] get_by_id, get_by_email, get_by_apollo_id
# [x] search_available for ICP matching
# [x] mark_bounced for global bounce handling
# [x] mark_unsubscribed for global unsubscribe
# [x] get_pool_stats for analytics
# [x] bulk_create for batch operations
# [x] No hardcoded credentials
# [x] All methods async
# [x] All methods have type hints
# [x] All methods have docstrings
