"""
Contract: src/services/customer_import_service.py
Purpose: Import customer data from CRM or CSV, manage suppression and buyer signals
Layer: 3 - services
Imports: models, config, services
Consumers: orchestration, API routes

FILE: src/services/customer_import_service.py
TASK: CUST-004 to CUST-007
PHASE: 24F - Customer Import
PURPOSE: Import customer data from CRM or CSV, manage suppression and buyer signals
LAYER: 3 - services
IMPORTS: models, config, services/crm_push_service
CONSUMERS: orchestration, API routes
"""

from __future__ import annotations

import contextlib
import csv
import io
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.crm_push_service import CRMConfig, CRMPushService

logger = logging.getLogger(__name__)

# CRM API base URLs
HUBSPOT_API = "https://api.hubapi.com"
PIPEDRIVE_API = "https://api.pipedrive.com/v1"
CLOSE_API = "https://api.close.com/api/v1"


# ============================================================================
# DATA MODELS
# ============================================================================


class CustomerData(BaseModel):
    """Customer data for import."""

    company_name: str
    domain: str | None = None
    industry: str | None = None
    employee_count_range: str | None = None
    contact_email: str | None = None
    contact_name: str | None = None
    contact_title: str | None = None
    status: str = "active"
    customer_since: datetime | None = None
    deal_value: float | None = None
    crm_id: str | None = None


class ImportResult(BaseModel):
    """Result of customer import."""

    success: bool = True
    imported: int = 0
    skipped: int = 0
    errors: list[str] = []
    source: str = ""


class ColumnMapping(BaseModel):
    """CSV column mapping configuration."""

    company_name: str | None = None
    domain: str | None = None
    email: str | None = None  # Used to extract domain
    contact_name: str | None = None
    industry: str | None = None
    deal_value: str | None = None


# ============================================================================
# CUSTOMER IMPORT SERVICE
# ============================================================================


class CustomerImportService:
    """
    Import and manage client customers.

    Handles:
    - CRM import (HubSpot, Pipedrive, Close)
    - CSV upload with column mapping
    - Suppression list management
    - Platform buyer signal aggregation
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.http = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()

    # =========================================================================
    # CRM IMPORT
    # =========================================================================

    async def import_from_crm(self, client_id: UUID) -> ImportResult:
        """
        Import customers from connected CRM.
        Pulls all closed-won deals.
        """
        crm_service = CRMPushService(self.db)
        try:
            config = await crm_service.get_config(client_id)

            if not config or not config.is_active:
                return ImportResult(
                    success=False,
                    errors=["No CRM connected. Connect a CRM first."],
                )

            # Refresh token if needed (HubSpot)
            if config.crm_type == "hubspot":
                config = await crm_service._refresh_hubspot_token_if_needed(config)

            # Fetch customers from CRM
            if config.crm_type == "hubspot":
                customers = await self._fetch_hubspot_customers(config)
            elif config.crm_type == "pipedrive":
                customers = await self._fetch_pipedrive_customers(config)
            elif config.crm_type == "close":
                customers = await self._fetch_close_customers(config)
            else:
                return ImportResult(
                    success=False,
                    errors=[f"Unsupported CRM type: {config.crm_type}"],
                )

            # Process each customer
            imported = 0
            skipped = 0
            errors: list[str] = []

            for customer in customers:
                try:
                    await self.process_customer(client_id, customer, source=config.crm_type)
                    imported += 1
                except Exception as e:
                    logger.warning(f"Error processing customer {customer.company_name}: {e}")
                    errors.append(f"{customer.company_name}: {str(e)}")
                    skipped += 1

            return ImportResult(
                success=True,
                imported=imported,
                skipped=skipped,
                errors=errors,
                source=config.crm_type,
            )

        finally:
            await crm_service.close()

    async def _fetch_hubspot_customers(self, config: CRMConfig) -> list[CustomerData]:
        """Fetch closed-won deals from HubSpot."""
        headers = {"Authorization": f"Bearer {config.oauth_access_token}"}
        customers: list[CustomerData] = []

        # Search for closed-won deals
        url = f"{HUBSPOT_API}/crm/v3/objects/deals/search"
        body = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "dealstage",
                            "operator": "EQ",
                            "value": "closedwon",
                        }
                    ]
                }
            ],
            "properties": [
                "dealname",
                "amount",
                "closedate",
                "company",
                "hs_object_id",
            ],
            "limit": 100,
        }

        after = None
        while True:
            if after:
                body["after"] = after

            response = await self.http.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()

            for deal in data.get("results", []):
                props = deal.get("properties", {})

                # Try to get associated company
                company_name = props.get("company") or props.get("dealname", "Unknown")
                domain = None
                contact_email = None
                industry = None

                # Get associated contacts/companies for more details
                assoc_url = f"{HUBSPOT_API}/crm/v3/objects/deals/{deal['id']}/associations/contacts"
                try:
                    assoc_response = await self.http.get(assoc_url, headers=headers)
                    if assoc_response.status_code == 200:
                        contacts = assoc_response.json().get("results", [])
                        if contacts:
                            contact_id = contacts[0].get("id")
                            contact_response = await self.http.get(
                                f"{HUBSPOT_API}/crm/v3/objects/contacts/{contact_id}",
                                params={"properties": "email,firstname,lastname,company"},
                                headers=headers,
                            )
                            if contact_response.status_code == 200:
                                contact_props = contact_response.json().get("properties", {})
                                contact_email = contact_props.get("email")
                                if contact_email:
                                    domain = self._extract_domain(contact_email)
                                if not company_name or company_name == "Unknown":
                                    company_name = contact_props.get("company", company_name)
                except Exception as e:
                    logger.debug(f"Failed to get contact details: {e}")

                customers.append(
                    CustomerData(
                        company_name=company_name,
                        domain=domain,
                        contact_email=contact_email,
                        industry=industry,
                        status="active",
                        deal_value=float(props.get("amount", 0) or 0),
                        crm_id=str(deal["id"]),
                        customer_since=datetime.fromisoformat(
                            props["closedate"].replace("Z", "+00:00")
                        ) if props.get("closedate") else None,
                    )
                )

            # Pagination
            paging = data.get("paging", {})
            if paging.get("next"):
                after = paging["next"].get("after")
            else:
                break

        logger.info(f"Fetched {len(customers)} customers from HubSpot")
        return customers

    async def _fetch_pipedrive_customers(self, config: CRMConfig) -> list[CustomerData]:
        """Fetch won deals from Pipedrive."""
        customers: list[CustomerData] = []

        # Get won deals
        url = f"{PIPEDRIVE_API}/deals"
        params = {
            "api_token": config.api_key,
            "status": "won",
            "limit": 100,
        }

        start = 0
        while True:
            params["start"] = start
            response = await self.http.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get("data"):
                break

            for deal in data["data"]:
                # Get organization details
                org_name = deal.get("org_name") or deal.get("title", "Unknown")
                domain = None
                contact_email = None

                # Get person email for domain
                if deal.get("person_id"):
                    try:
                        person_response = await self.http.get(
                            f"{PIPEDRIVE_API}/persons/{deal['person_id']}",
                            params={"api_token": config.api_key},
                        )
                        if person_response.status_code == 200:
                            person = person_response.json().get("data", {})
                            emails = person.get("email", [])
                            if emails and isinstance(emails, list) and emails[0].get("value"):
                                contact_email = emails[0]["value"]
                                domain = self._extract_domain(contact_email)
                    except Exception as e:
                        logger.debug(f"Failed to get person details: {e}")

                customers.append(
                    CustomerData(
                        company_name=org_name,
                        domain=domain,
                        contact_email=contact_email,
                        status="active",
                        deal_value=float(deal.get("value", 0) or 0),
                        crm_id=str(deal["id"]),
                        customer_since=datetime.fromisoformat(
                            deal["won_time"]
                        ) if deal.get("won_time") else None,
                    )
                )

            # Pagination
            if data.get("additional_data", {}).get("pagination", {}).get("more_items_in_collection"):
                start += 100
            else:
                break

        logger.info(f"Fetched {len(customers)} customers from Pipedrive")
        return customers

    async def _fetch_close_customers(self, config: CRMConfig) -> list[CustomerData]:
        """Fetch won opportunities from Close."""
        customers: list[CustomerData] = []
        auth = (config.api_key or "", "")

        # Get won opportunities
        url = f"{CLOSE_API}/opportunity"
        params: dict[str, str | int] = {
            "status_type": "won",
            "_limit": 100,
            "_skip": 0,
        }

        while True:
            response = await self.http.get(url, params=params, auth=auth)  # type: ignore[arg-type]
            response.raise_for_status()
            data = response.json()

            if not data.get("data"):
                break

            for opp in data["data"]:
                lead_id = opp.get("lead_id")
                company_name = "Unknown"
                domain = None
                contact_email = None

                # Get lead details
                if lead_id:
                    try:
                        lead_response = await self.http.get(
                            f"{CLOSE_API}/lead/{lead_id}",
                            auth=auth,
                        )
                        if lead_response.status_code == 200:
                            lead = lead_response.json()
                            company_name = lead.get("display_name") or lead.get("name", "Unknown")
                            # Get first contact email
                            contacts = lead.get("contacts", [])
                            if contacts and contacts[0].get("emails"):
                                emails = contacts[0]["emails"]
                                if emails:
                                    contact_email = emails[0].get("email")
                                    domain = self._extract_domain(contact_email)
                    except Exception as e:
                        logger.debug(f"Failed to get lead details: {e}")

                customers.append(
                    CustomerData(
                        company_name=company_name,
                        domain=domain,
                        contact_email=contact_email,
                        status="active",
                        deal_value=float(opp.get("value", 0) or 0) / 100,  # Close uses cents
                        crm_id=opp["id"],
                        customer_since=datetime.fromisoformat(
                            opp["date_won"].replace("Z", "+00:00")
                        ) if opp.get("date_won") else None,
                    )
                )

            # Pagination
            if data.get("has_more"):
                current_skip = params.get("_skip", 0)
                params["_skip"] = int(current_skip) + 100 if current_skip else 100
            else:
                break

        logger.info(f"Fetched {len(customers)} customers from Close")
        return customers

    # =========================================================================
    # CSV IMPORT
    # =========================================================================

    async def import_from_csv(
        self,
        client_id: UUID,
        file_content: bytes,
        mapping: ColumnMapping,
    ) -> ImportResult:
        """
        Import customers from CSV file.
        """
        imported = 0
        skipped = 0
        errors: list[str] = []

        try:
            # Parse CSV
            content = file_content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(content))

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                try:
                    # Extract data using mapping
                    company_name = row.get(mapping.company_name or "", "").strip()
                    email = row.get(mapping.email or "", "").strip()
                    domain = row.get(mapping.domain or "", "").strip()

                    # Extract domain from email if not provided
                    if not domain and email:
                        domain = self._extract_domain(email)

                    # Skip rows without identifier
                    if not domain and not email:
                        skipped += 1
                        continue

                    # Default company name to domain
                    if not company_name:
                        company_name = domain or email

                    # Parse deal value
                    deal_value = None
                    if mapping.deal_value:
                        value_str = row.get(mapping.deal_value, "").strip()
                        if value_str:
                            # Remove currency symbols and commas
                            value_str = value_str.replace("$", "").replace(",", "").replace(" ", "")
                            with contextlib.suppress(ValueError):
                                deal_value = float(value_str)

                    customer = CustomerData(
                        company_name=company_name,
                        domain=domain,
                        contact_email=email if email else None,
                        contact_name=row.get(mapping.contact_name or "", "").strip() or None,
                        industry=row.get(mapping.industry or "", "").strip() or None,
                        deal_value=deal_value,
                        status="active",
                    )

                    await self.process_customer(client_id, customer, source="csv")
                    imported += 1

                except Exception as e:
                    logger.warning(f"Error processing CSV row {row_num}: {e}")
                    errors.append(f"Row {row_num}: {str(e)}")
                    skipped += 1

        except Exception as e:
            logger.error(f"Failed to parse CSV: {e}")
            return ImportResult(
                success=False,
                errors=[f"Failed to parse CSV: {str(e)}"],
            )

        return ImportResult(
            success=True,
            imported=imported,
            skipped=skipped,
            errors=errors,
            source="csv",
        )

    # =========================================================================
    # CUSTOMER PROCESSING
    # =========================================================================

    async def process_customer(
        self,
        client_id: UUID,
        customer: CustomerData,
        source: str,
    ):
        """
        Process a single customer:
        1. Upsert to client_customers
        2. Add to suppression_list
        3. Update platform_buyer_signals
        """
        # Normalize domain
        domain = customer.domain.lower() if customer.domain else None

        # 1. Upsert customer record
        customer_id = await self._upsert_customer(client_id, customer, source, domain)

        # 2. Add to suppression list (if domain exists)
        if domain:
            await self._add_suppression(
                client_id=client_id,
                domain=domain,
                reason="existing_customer",
                source=f"{source}_import",
                customer_id=customer_id,
            )

        # 3. Update platform buyer signals (if domain exists)
        if domain:
            # Get client's primary service type
            service_type = await self._get_client_service_type(client_id)

            await self.db.execute(
                text("SELECT upsert_buyer_signal(:domain, :company_name, :industry, :deal_value, :service_type)"),
                {
                    "domain": domain,
                    "company_name": customer.company_name,
                    "industry": customer.industry,
                    "deal_value": customer.deal_value,
                    "service_type": service_type,
                },
            )
            await self.db.commit()

    async def _upsert_customer(
        self,
        client_id: UUID,
        customer: CustomerData,
        source: str,
        domain: str | None,
    ) -> UUID:
        """Upsert customer record."""
        result = await self.db.execute(
            text("""
                INSERT INTO client_customers (
                    client_id, company_name, domain, industry, employee_count_range,
                    contact_email, contact_name, contact_title, status,
                    customer_since, deal_value, source, crm_id, imported_at
                ) VALUES (
                    :client_id, :company_name, :domain, :industry, :employee_count_range,
                    :contact_email, :contact_name, :contact_title, :status,
                    :customer_since, :deal_value, :source, :crm_id, NOW()
                )
                ON CONFLICT (client_id, domain) DO UPDATE SET
                    company_name = COALESCE(EXCLUDED.company_name, client_customers.company_name),
                    industry = COALESCE(EXCLUDED.industry, client_customers.industry),
                    contact_email = COALESCE(EXCLUDED.contact_email, client_customers.contact_email),
                    contact_name = COALESCE(EXCLUDED.contact_name, client_customers.contact_name),
                    deal_value = COALESCE(EXCLUDED.deal_value, client_customers.deal_value),
                    updated_at = NOW()
                RETURNING id
            """),
            {
                "client_id": str(client_id),
                "company_name": customer.company_name,
                "domain": domain,
                "industry": customer.industry,
                "employee_count_range": customer.employee_count_range,
                "contact_email": customer.contact_email,
                "contact_name": customer.contact_name,
                "contact_title": customer.contact_title,
                "status": customer.status,
                "customer_since": customer.customer_since,
                "deal_value": customer.deal_value,
                "source": source,
                "crm_id": customer.crm_id,
            },
        )
        row = result.fetchone()
        await self.db.commit()
        if not row:
            raise ValueError(f"Failed to insert customer for client {client_id}")
        return row.id

    async def _add_suppression(
        self,
        client_id: UUID,
        domain: str,
        reason: str,
        source: str,
        customer_id: UUID | None = None,
    ):
        """Add domain to suppression list."""
        await self.db.execute(
            text("""
                INSERT INTO suppression_list (client_id, domain, reason, source, customer_id)
                VALUES (:client_id, :domain, :reason, :source, :customer_id)
                ON CONFLICT (client_id, domain) DO UPDATE SET
                    reason = EXCLUDED.reason,
                    source = EXCLUDED.source,
                    customer_id = EXCLUDED.customer_id
            """),
            {
                "client_id": str(client_id),
                "domain": domain,
                "reason": reason,
                "source": source,
                "customer_id": str(customer_id) if customer_id else None,
            },
        )
        await self.db.commit()

    async def _get_client_service_type(self, client_id: UUID) -> str | None:
        """Get client's primary service type for buyer signals."""
        result = await self.db.execute(
            text("SELECT primary_service FROM clients WHERE id = :client_id"),
            {"client_id": str(client_id)},
        )
        row = result.fetchone()
        return row.primary_service if row else None

    # =========================================================================
    # CUSTOMER MANAGEMENT
    # =========================================================================

    async def list_customers(
        self,
        client_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List imported customers for a client."""
        query = """
            SELECT id, company_name, domain, industry, contact_email, contact_name,
                   status, customer_since, deal_value, can_use_as_reference,
                   case_study_url, testimonial, logo_approved, source, imported_at
            FROM client_customers
            WHERE client_id = :client_id AND deleted_at IS NULL
        """

        if status:
            query += " AND status = :status"

        query += " ORDER BY imported_at DESC LIMIT :limit OFFSET :offset"

        result = await self.db.execute(
            text(query),
            {
                "client_id": str(client_id),
                "status": status,
                "limit": limit,
                "offset": offset,
            },
        )
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    async def delete_customer(self, client_id: UUID, customer_id: UUID) -> bool:
        """Soft delete a customer and its suppression entry (Rule 14)."""
        # Get domain before soft delete
        result = await self.db.execute(
            text("SELECT domain FROM client_customers WHERE id = :id AND client_id = :client_id AND deleted_at IS NULL"),
            {"id": str(customer_id), "client_id": str(client_id)},
        )
        row = result.fetchone()

        if not row:
            return False

        domain = row.domain

        # Soft delete customer (Rule 14)
        await self.db.execute(
            text("UPDATE client_customers SET deleted_at = NOW() WHERE id = :id AND client_id = :client_id AND deleted_at IS NULL"),
            {"id": str(customer_id), "client_id": str(client_id)},
        )

        # Soft delete associated suppression (if domain-based)
        if domain:
            await self.db.execute(
                text("""
                    UPDATE suppression_list
                    SET deleted_at = NOW()
                    WHERE client_id = :client_id AND domain = :domain AND customer_id = :customer_id AND deleted_at IS NULL
                """),
                {"client_id": str(client_id), "domain": domain, "customer_id": str(customer_id)},
            )

        await self.db.commit()
        return True

    async def update_social_proof(
        self,
        client_id: UUID,
        customer_id: UUID,
        can_use_as_reference: bool | None = None,
        case_study_url: str | None = None,
        testimonial: str | None = None,
        logo_approved: bool | None = None,
    ) -> dict[str, Any]:
        """Update social proof settings for a customer."""
        result = await self.db.execute(
            text("""
                UPDATE client_customers
                SET can_use_as_reference = COALESCE(:can_use_as_reference, can_use_as_reference),
                    case_study_url = COALESCE(:case_study_url, case_study_url),
                    testimonial = COALESCE(:testimonial, testimonial),
                    logo_approved = COALESCE(:logo_approved, logo_approved),
                    updated_at = NOW()
                WHERE id = :id AND client_id = :client_id AND deleted_at IS NULL
                RETURNING *
            """),
            {
                "id": str(customer_id),
                "client_id": str(client_id),
                "can_use_as_reference": can_use_as_reference,
                "case_study_url": case_study_url,
                "testimonial": testimonial,
                "logo_approved": logo_approved,
            },
        )
        row = result.fetchone()
        await self.db.commit()

        if not row:
            return {}

        return dict(row._mapping)

    async def get_referenceable_customers(self, client_id: UUID) -> list[dict[str, Any]]:
        """Get customers available for social proof."""
        result = await self.db.execute(
            text("""
                SELECT id, company_name, domain, industry, case_study_url, testimonial
                FROM client_customers
                WHERE client_id = :client_id AND can_use_as_reference = true AND deleted_at IS NULL
                ORDER BY company_name
            """),
            {"client_id": str(client_id)},
        )
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    # =========================================================================
    # UTILITY
    # =========================================================================

    def _extract_domain(self, email: str) -> str | None:
        """Extract domain from email address."""
        if not email or "@" not in email:
            return None
        return email.split("@")[1].lower()
