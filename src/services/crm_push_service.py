"""
Contract: src/services/crm_push_service.py
Purpose: Push meetings to client's CRM (HubSpot, Pipedrive, Close)
Layer: 3 - services
Imports: models, config
Consumers: orchestration, API routes, closer engine

FILE: src/services/crm_push_service.py
TASK: CRM-003 to CRM-007
PHASE: 24E - CRM Push
PURPOSE: Push meetings to client's CRM (HubSpot, Pipedrive, Close)
LAYER: 3 - services
IMPORTS: models, config
CONSUMERS: orchestration, API routes, Closer Engine
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlencode
from uuid import UUID

import httpx
from pydantic import BaseModel

from src.config.settings import settings

logger = logging.getLogger(__name__)

# CRM API base URLs
HUBSPOT_API = "https://api.hubapi.com"
HUBSPOT_OAUTH = "https://app.hubspot.com/oauth"
PIPEDRIVE_API = "https://api.pipedrive.com/v1"
CLOSE_API = "https://api.close.com/api/v1"


# ============================================================================
# DATA MODELS
# ============================================================================


class CRMPushResult(BaseModel):
    """Result of a CRM push operation."""

    success: bool = False
    skipped: bool = False
    reason: str | None = None
    crm_contact_id: str | None = None
    crm_deal_id: str | None = None
    crm_org_id: str | None = None
    error: str | None = None


class CRMConfig(BaseModel):
    """CRM configuration for a client."""

    id: UUID
    client_id: UUID
    crm_type: Literal["hubspot", "pipedrive", "close"]
    api_key: str | None = None
    oauth_access_token: str | None = None
    oauth_refresh_token: str | None = None
    oauth_expires_at: datetime | None = None
    hubspot_portal_id: str | None = None
    pipeline_id: str | None = None
    stage_id: str | None = None
    owner_id: str | None = None
    is_active: bool = True


class CRMPipeline(BaseModel):
    """Pipeline from CRM."""

    id: str
    name: str
    stages: list[CRMStage] = []


class CRMStage(BaseModel):
    """Stage within a pipeline."""

    id: str
    name: str
    probability: float | None = None


class CRMUser(BaseModel):
    """User/owner from CRM."""

    id: str
    name: str
    email: str | None = None


class LeadData(BaseModel):
    """Lead data for CRM push (simplified from full Lead model)."""

    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    phone: str | None = None
    title: str | None = None
    organization_name: str | None = None
    organization_website: str | None = None
    organization_industry: str | None = None
    linkedin_url: str | None = None


class MeetingData(BaseModel):
    """Meeting data for CRM push (simplified from full Meeting model)."""

    id: UUID
    scheduled_at: datetime | None = None
    duration_minutes: int = 30
    meeting_link: str | None = None
    notes: str | None = None


# ============================================================================
# CRM PUSH SERVICE
# ============================================================================


class CRMPushService:
    """
    Push meetings to client's CRM.
    One-way: Agency OS -> Client CRM

    Supported CRMs:
    - HubSpot (OAuth)
    - Pipedrive (API key)
    - Close (API key)
    """

    def __init__(self, db):
        """Initialize with database session."""
        self.db = db
        self.http = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()

    # =========================================================================
    # CONFIG MANAGEMENT
    # =========================================================================

    async def get_config(self, client_id: UUID) -> CRMConfig | None:
        """Get CRM config for a client."""
        result = await self.db.execute(
            """
            SELECT id, client_id, crm_type, api_key, oauth_access_token,
                   oauth_refresh_token, oauth_expires_at, hubspot_portal_id,
                   pipeline_id, stage_id, owner_id, is_active
            FROM client_crm_configs
            WHERE client_id = :client_id AND is_active = true
            """,
            {"client_id": str(client_id)},
        )
        row = result.fetchone()
        if not row:
            return None

        return CRMConfig(
            id=row.id,
            client_id=row.client_id,
            crm_type=row.crm_type,
            api_key=row.api_key,
            oauth_access_token=row.oauth_access_token,
            oauth_refresh_token=row.oauth_refresh_token,
            oauth_expires_at=row.oauth_expires_at,
            hubspot_portal_id=row.hubspot_portal_id,
            pipeline_id=row.pipeline_id,
            stage_id=row.stage_id,
            owner_id=row.owner_id,
            is_active=row.is_active,
        )

    async def save_config(self, config: CRMConfig) -> CRMConfig:
        """Save or update CRM config."""
        await self.db.execute(
            """
            INSERT INTO client_crm_configs (
                id, client_id, crm_type, api_key, oauth_access_token,
                oauth_refresh_token, oauth_expires_at, hubspot_portal_id,
                pipeline_id, stage_id, owner_id, is_active,
                connection_status, connected_at
            ) VALUES (
                :id, :client_id, :crm_type, :api_key, :oauth_access_token,
                :oauth_refresh_token, :oauth_expires_at, :hubspot_portal_id,
                :pipeline_id, :stage_id, :owner_id, :is_active,
                'connected', NOW()
            )
            ON CONFLICT (client_id) DO UPDATE SET
                crm_type = EXCLUDED.crm_type,
                api_key = EXCLUDED.api_key,
                oauth_access_token = EXCLUDED.oauth_access_token,
                oauth_refresh_token = EXCLUDED.oauth_refresh_token,
                oauth_expires_at = EXCLUDED.oauth_expires_at,
                hubspot_portal_id = EXCLUDED.hubspot_portal_id,
                pipeline_id = EXCLUDED.pipeline_id,
                stage_id = EXCLUDED.stage_id,
                owner_id = EXCLUDED.owner_id,
                is_active = EXCLUDED.is_active,
                connection_status = 'connected',
                updated_at = NOW()
            """,
            {
                "id": str(config.id),
                "client_id": str(config.client_id),
                "crm_type": config.crm_type,
                "api_key": config.api_key,
                "oauth_access_token": config.oauth_access_token,
                "oauth_refresh_token": config.oauth_refresh_token,
                "oauth_expires_at": config.oauth_expires_at,
                "hubspot_portal_id": config.hubspot_portal_id,
                "pipeline_id": config.pipeline_id,
                "stage_id": config.stage_id,
                "owner_id": config.owner_id,
                "is_active": config.is_active,
            },
        )
        await self.db.commit()
        return config

    async def disconnect(self, client_id: UUID) -> bool:
        """Disconnect CRM for a client."""
        await self.db.execute(
            """
            UPDATE client_crm_configs
            SET is_active = false, connection_status = 'disconnected', updated_at = NOW()
            WHERE client_id = :client_id
            """,
            {"client_id": str(client_id)},
        )
        await self.db.commit()
        return True

    # =========================================================================
    # LOGGING
    # =========================================================================

    async def log_push(
        self,
        client_id: UUID,
        operation: str,
        status: str,
        lead_id: UUID | None = None,
        meeting_id: UUID | None = None,
        crm_contact_id: str | None = None,
        crm_deal_id: str | None = None,
        crm_org_id: str | None = None,
        request_payload: dict | None = None,
        response_payload: dict | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        duration_ms: int | None = None,
        crm_config_id: UUID | None = None,
    ):
        """Log a CRM push operation."""
        import json

        await self.db.execute(
            """
            INSERT INTO crm_push_log (
                client_id, crm_config_id, operation, lead_id, meeting_id,
                crm_contact_id, crm_deal_id, crm_org_id,
                request_payload, response_payload,
                status, error_code, error_message, duration_ms
            ) VALUES (
                :client_id, :crm_config_id, :operation, :lead_id, :meeting_id,
                :crm_contact_id, :crm_deal_id, :crm_org_id,
                :request_payload, :response_payload,
                :status, :error_code, :error_message, :duration_ms
            )
            """,
            {
                "client_id": str(client_id),
                "crm_config_id": str(crm_config_id) if crm_config_id else None,
                "operation": operation,
                "lead_id": str(lead_id) if lead_id else None,
                "meeting_id": str(meeting_id) if meeting_id else None,
                "crm_contact_id": crm_contact_id,
                "crm_deal_id": crm_deal_id,
                "crm_org_id": crm_org_id,
                "request_payload": json.dumps(request_payload) if request_payload else None,
                "response_payload": json.dumps(response_payload) if response_payload else None,
                "status": status,
                "error_code": error_code,
                "error_message": error_message,
                "duration_ms": duration_ms,
            },
        )
        await self.db.commit()

    # =========================================================================
    # MAIN PUSH METHOD
    # =========================================================================

    async def push_meeting_booked(
        self,
        client_id: UUID,
        lead: LeadData,
        meeting: MeetingData,
    ) -> CRMPushResult:
        """
        Push a booked meeting to the client's CRM.
        Creates contact + deal in their CRM.
        """
        config = await self.get_config(client_id)

        if not config or not config.is_active:
            return CRMPushResult(skipped=True, reason="No CRM configured")

        start_time = time.time()

        try:
            # Refresh OAuth token if needed (HubSpot)
            if config.crm_type == "hubspot":
                config = await self._refresh_hubspot_token_if_needed(config)

            # Step 1: Find or create contact
            contact_id = await self.find_or_create_contact(config, lead)

            # Step 2: Create deal
            deal_name = f"{lead.organization_name or lead.full_name} - Agency OS"
            deal_id, org_id = await self.create_deal(config, lead, meeting, contact_id, deal_name)

            # Step 3: Log success
            duration_ms = int((time.time() - start_time) * 1000)
            await self.log_push(
                client_id=client_id,
                crm_config_id=config.id,
                operation="create_deal",
                lead_id=lead.id,
                meeting_id=meeting.id,
                crm_contact_id=contact_id,
                crm_deal_id=deal_id,
                crm_org_id=org_id,
                status="success",
                duration_ms=duration_ms,
            )

            # Update last successful push timestamp
            await self.db.execute(
                """
                UPDATE client_crm_configs
                SET last_successful_push_at = NOW(), last_error = NULL
                WHERE id = :id
                """,
                {"id": str(config.id)},
            )
            await self.db.commit()

            return CRMPushResult(
                success=True,
                crm_contact_id=contact_id,
                crm_deal_id=deal_id,
                crm_org_id=org_id,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            logger.error(f"CRM push failed for client {client_id}: {error_msg}")

            await self.log_push(
                client_id=client_id,
                crm_config_id=config.id if config else None,
                operation="create_deal",
                lead_id=lead.id,
                meeting_id=meeting.id,
                status="failed",
                error_message=error_msg,
                duration_ms=duration_ms,
            )

            # Update error state
            if config:
                await self.db.execute(
                    """
                    UPDATE client_crm_configs
                    SET last_error = :error, last_error_at = NOW()
                    WHERE id = :id
                    """,
                    {"id": str(config.id), "error": error_msg},
                )
                await self.db.commit()

            return CRMPushResult(success=False, error=error_msg)

    async def find_or_create_contact(self, config: CRMConfig, lead: LeadData) -> str:
        """Find existing contact or create new one."""
        if config.crm_type == "hubspot":
            return await self._hubspot_find_or_create_contact(config, lead)
        elif config.crm_type == "pipedrive":
            return await self._pipedrive_find_or_create_person(config, lead)
        elif config.crm_type == "close":
            return await self._close_find_or_create_lead(config, lead)
        else:
            raise ValueError(f"Unsupported CRM type: {config.crm_type}")

    async def create_deal(
        self,
        config: CRMConfig,
        lead: LeadData,
        meeting: MeetingData,
        contact_id: str,
        deal_name: str,
    ) -> tuple[str, str | None]:
        """Create deal in CRM. Returns (deal_id, org_id)."""
        if config.crm_type == "hubspot":
            deal_id = await self._hubspot_create_deal(config, lead, meeting, contact_id, deal_name)
            return deal_id, None
        elif config.crm_type == "pipedrive":
            return await self._pipedrive_create_deal(config, lead, meeting, contact_id, deal_name)
        elif config.crm_type == "close":
            deal_id = await self._close_create_opportunity(
                config, lead, meeting, contact_id, deal_name
            )
            return deal_id, None
        else:
            raise ValueError(f"Unsupported CRM type: {config.crm_type}")

    # =========================================================================
    # HUBSPOT IMPLEMENTATION
    # =========================================================================

    def get_hubspot_oauth_url(self, state: str) -> str:
        """Generate HubSpot OAuth authorization URL."""
        params = {
            "client_id": settings.hubspot_client_id,
            "redirect_uri": settings.hubspot_redirect_uri,
            "scope": settings.hubspot_scopes.replace(",", " "),
            "state": state,
        }
        return f"{HUBSPOT_OAUTH}/authorize?{urlencode(params)}"

    async def exchange_hubspot_code(self, code: str) -> dict:
        """Exchange authorization code for tokens."""
        response = await self.http.post(
            f"{HUBSPOT_OAUTH}/v1/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.hubspot_client_id,
                "client_secret": settings.hubspot_client_secret,
                "redirect_uri": settings.hubspot_redirect_uri,
                "code": code,
            },
        )
        response.raise_for_status()
        return response.json()

    async def _refresh_hubspot_token_if_needed(self, config: CRMConfig) -> CRMConfig:
        """Refresh HubSpot OAuth token if expired or expiring soon."""
        if not config.oauth_expires_at:
            return config

        # Refresh if expiring in next 5 minutes
        if config.oauth_expires_at > datetime.utcnow() + timedelta(minutes=5):
            return config

        if not config.oauth_refresh_token:
            raise ValueError("HubSpot refresh token missing")

        logger.info(f"Refreshing HubSpot token for client {config.client_id}")

        response = await self.http.post(
            f"{HUBSPOT_OAUTH}/v1/token",
            data={
                "grant_type": "refresh_token",
                "client_id": settings.hubspot_client_id,
                "client_secret": settings.hubspot_client_secret,
                "refresh_token": config.oauth_refresh_token,
            },
        )
        response.raise_for_status()
        tokens = response.json()

        # Update config with new tokens
        config.oauth_access_token = tokens["access_token"]
        config.oauth_refresh_token = tokens.get("refresh_token", config.oauth_refresh_token)
        config.oauth_expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])

        await self.save_config(config)

        await self.log_push(
            client_id=config.client_id,
            crm_config_id=config.id,
            operation="oauth_token_refresh",
            status="success",
        )

        return config

    async def _hubspot_find_or_create_contact(self, config: CRMConfig, lead: LeadData) -> str:
        """Find or create HubSpot contact."""
        headers = {"Authorization": f"Bearer {config.oauth_access_token}"}

        # Search for existing contact by email
        search_url = f"{HUBSPOT_API}/crm/v3/objects/contacts/search"
        search_body = {
            "filterGroups": [
                {"filters": [{"propertyName": "email", "operator": "EQ", "value": lead.email}]}
            ],
            "limit": 1,
        }

        response = await self.http.post(search_url, json=search_body, headers=headers)
        response.raise_for_status()
        results = response.json().get("results", [])

        if results:
            contact_id = results[0]["id"]
            logger.info(f"Found existing HubSpot contact: {contact_id}")
            return contact_id

        # Create new contact
        create_url = f"{HUBSPOT_API}/crm/v3/objects/contacts"
        create_body = {
            "properties": {
                "email": lead.email,
                "firstname": lead.first_name or "",
                "lastname": lead.last_name or "",
                "phone": lead.phone or "",
                "company": lead.organization_name or "",
                "jobtitle": lead.title or "",
                "website": lead.organization_website or "",
                "hs_lead_status": "NEW",
            }
        }

        # Add LinkedIn if available
        if lead.linkedin_url:
            create_body["properties"]["linkedin_company_page"] = lead.linkedin_url

        response = await self.http.post(create_url, json=create_body, headers=headers)
        response.raise_for_status()
        contact_id = response.json()["id"]

        logger.info(f"Created HubSpot contact: {contact_id}")

        await self.log_push(
            client_id=config.client_id,
            crm_config_id=config.id,
            operation="create_contact",
            crm_contact_id=contact_id,
            status="success",
            request_payload=create_body,
            response_payload=response.json(),
        )

        return contact_id

    async def _hubspot_create_deal(
        self,
        config: CRMConfig,
        lead: LeadData,
        meeting: MeetingData,
        contact_id: str,
        deal_name: str,
    ) -> str:
        """Create HubSpot deal and associate with contact."""
        headers = {"Authorization": f"Bearer {config.oauth_access_token}"}

        # Create deal
        url = f"{HUBSPOT_API}/crm/v3/objects/deals"
        body = {
            "properties": {
                "dealname": deal_name,
                "dealstage": config.stage_id or "appointmentscheduled",
                "hs_lead_source": "Agency OS",
            }
        }

        # Add pipeline if configured
        if config.pipeline_id:
            body["properties"]["pipeline"] = config.pipeline_id

        # Add owner if configured
        if config.owner_id:
            body["properties"]["hubspot_owner_id"] = config.owner_id

        # Add meeting date if available
        if meeting.scheduled_at:
            body["properties"]["meeting_date"] = meeting.scheduled_at.strftime("%Y-%m-%d")

        response = await self.http.post(url, json=body, headers=headers)
        response.raise_for_status()
        deal_id = response.json()["id"]

        # Associate deal with contact
        assoc_url = f"{HUBSPOT_API}/crm/v3/objects/deals/{deal_id}/associations/contacts/{contact_id}/deal_to_contact"
        await self.http.put(assoc_url, headers=headers)

        logger.info(f"Created HubSpot deal: {deal_id}, associated with contact: {contact_id}")
        return deal_id

    async def get_hubspot_pipelines(self, config: CRMConfig) -> list[CRMPipeline]:
        """Get available pipelines from HubSpot."""
        headers = {"Authorization": f"Bearer {config.oauth_access_token}"}
        url = f"{HUBSPOT_API}/crm/v3/pipelines/deals"

        response = await self.http.get(url, headers=headers)
        response.raise_for_status()

        pipelines = []
        for p in response.json().get("results", []):
            stages = [
                CRMStage(
                    id=s["id"],
                    name=s["label"],
                    probability=s.get("metadata", {}).get("probability"),
                )
                for s in p.get("stages", [])
            ]
            pipelines.append(CRMPipeline(id=p["id"], name=p["label"], stages=stages))

        return pipelines

    async def get_hubspot_users(self, config: CRMConfig) -> list[CRMUser]:
        """Get available users/owners from HubSpot."""
        headers = {"Authorization": f"Bearer {config.oauth_access_token}"}
        url = f"{HUBSPOT_API}/crm/v3/owners"

        response = await self.http.get(url, headers=headers)
        response.raise_for_status()

        return [
            CRMUser(
                id=u["id"],
                name=f"{u.get('firstName', '')} {u.get('lastName', '')}".strip(),
                email=u.get("email"),
            )
            for u in response.json().get("results", [])
        ]

    # =========================================================================
    # PIPEDRIVE IMPLEMENTATION
    # =========================================================================

    async def _pipedrive_find_or_create_person(self, config: CRMConfig, lead: LeadData) -> str:
        """Find or create Pipedrive person."""
        # Search for existing person by email
        search_url = f"{PIPEDRIVE_API}/persons/search"
        params = {"api_token": config.api_key, "term": lead.email, "fields": "email", "limit": 1}

        response = await self.http.get(search_url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("data") and data["data"].get("items"):
            person_id = str(data["data"]["items"][0]["item"]["id"])
            logger.info(f"Found existing Pipedrive person: {person_id}")
            return person_id

        # Create new person
        create_url = f"{PIPEDRIVE_API}/persons"
        create_body = {
            "name": lead.full_name
            or f"{lead.first_name or ''} {lead.last_name or ''}".strip()
            or lead.email,
            "email": [{"value": lead.email, "primary": True}],
        }

        if lead.phone:
            create_body["phone"] = [{"value": lead.phone, "primary": True}]

        response = await self.http.post(
            create_url, params={"api_token": config.api_key}, json=create_body
        )
        response.raise_for_status()
        person_id = str(response.json()["data"]["id"])

        logger.info(f"Created Pipedrive person: {person_id}")

        await self.log_push(
            client_id=config.client_id,
            crm_config_id=config.id,
            operation="create_contact",
            crm_contact_id=person_id,
            status="success",
            request_payload=create_body,
            response_payload=response.json(),
        )

        return person_id

    async def _pipedrive_create_deal(
        self,
        config: CRMConfig,
        lead: LeadData,
        meeting: MeetingData,
        person_id: str,
        deal_name: str,
    ) -> tuple[str, str | None]:
        """Create Pipedrive deal. Returns (deal_id, org_id)."""
        org_id = None

        # First, create or find organization
        if lead.organization_name:
            org_id = await self._pipedrive_find_or_create_org(config, lead)

        # Create deal
        url = f"{PIPEDRIVE_API}/deals"
        body: dict[str, Any] = {
            "title": deal_name,
            "person_id": int(person_id),
        }

        if org_id:
            body["org_id"] = int(org_id)

        if config.stage_id:
            body["stage_id"] = int(config.stage_id)

        if config.owner_id:
            body["user_id"] = int(config.owner_id)

        # Add expected close date based on meeting
        if meeting.scheduled_at:
            body["expected_close_date"] = (meeting.scheduled_at + timedelta(days=30)).strftime(
                "%Y-%m-%d"
            )

        response = await self.http.post(url, params={"api_token": config.api_key}, json=body)
        response.raise_for_status()
        deal_id = str(response.json()["data"]["id"])

        logger.info(f"Created Pipedrive deal: {deal_id}")
        return deal_id, org_id

    async def _pipedrive_find_or_create_org(self, config: CRMConfig, lead: LeadData) -> str:
        """Find or create Pipedrive organization."""
        # Search for existing org
        search_url = f"{PIPEDRIVE_API}/organizations/search"
        params = {"api_token": config.api_key, "term": lead.organization_name, "limit": 1}

        response = await self.http.get(search_url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("data") and data["data"].get("items"):
            org_id = str(data["data"]["items"][0]["item"]["id"])
            return org_id

        # Create new org
        create_url = f"{PIPEDRIVE_API}/organizations"
        create_body = {"name": lead.organization_name}

        response = await self.http.post(
            create_url, params={"api_token": config.api_key}, json=create_body
        )
        response.raise_for_status()
        return str(response.json()["data"]["id"])

    async def get_pipedrive_pipelines(self, config: CRMConfig) -> list[CRMPipeline]:
        """Get available pipelines from Pipedrive."""
        url = f"{PIPEDRIVE_API}/pipelines"
        response = await self.http.get(url, params={"api_token": config.api_key})
        response.raise_for_status()

        pipelines = []
        for p in response.json().get("data", []):
            # Get stages for this pipeline
            stages_url = f"{PIPEDRIVE_API}/stages"
            stages_response = await self.http.get(
                stages_url, params={"api_token": config.api_key, "pipeline_id": p["id"]}
            )
            stages_response.raise_for_status()

            stages = [
                CRMStage(id=str(s["id"]), name=s["name"], probability=s.get("probability"))
                for s in stages_response.json().get("data", [])
            ]
            pipelines.append(CRMPipeline(id=str(p["id"]), name=p["name"], stages=stages))

        return pipelines

    async def get_pipedrive_users(self, config: CRMConfig) -> list[CRMUser]:
        """Get available users from Pipedrive."""
        url = f"{PIPEDRIVE_API}/users"
        response = await self.http.get(url, params={"api_token": config.api_key})
        response.raise_for_status()

        return [
            CRMUser(id=str(u["id"]), name=u["name"], email=u.get("email"))
            for u in response.json().get("data", [])
        ]

    # =========================================================================
    # CLOSE IMPLEMENTATION
    # =========================================================================

    def _close_auth(self, config: CRMConfig) -> tuple[str, str]:
        """Get Close basic auth credentials."""
        return (config.api_key or "", "")

    async def _close_find_or_create_lead(self, config: CRMConfig, lead: LeadData) -> str:
        """Find or create Close lead (company + contact)."""
        auth = self._close_auth(config)

        # Search for existing lead by contact email
        search_url = f"{CLOSE_API}/lead"
        params = {"query": f'email:"{lead.email}"', "_limit": 1}

        response = await self.http.get(search_url, params=params, auth=auth)
        response.raise_for_status()
        data = response.json()

        if data.get("data"):
            lead_id = data["data"][0]["id"]
            logger.info(f"Found existing Close lead: {lead_id}")
            return lead_id

        # Create new lead with contact
        create_url = f"{CLOSE_API}/lead"
        create_body: dict[str, Any] = {
            "name": lead.organization_name or lead.full_name or lead.email,
            "contacts": [
                {
                    "name": lead.full_name
                    or f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
                    "emails": [{"email": lead.email, "type": "office"}],
                }
            ],
        }

        if lead.phone:
            create_body["contacts"][0]["phones"] = [{"phone": lead.phone, "type": "office"}]

        if lead.title:
            create_body["contacts"][0]["title"] = lead.title

        if lead.organization_website:
            create_body["url"] = lead.organization_website

        response = await self.http.post(create_url, json=create_body, auth=auth)
        response.raise_for_status()
        lead_id = response.json()["id"]

        logger.info(f"Created Close lead: {lead_id}")

        await self.log_push(
            client_id=config.client_id,
            crm_config_id=config.id,
            operation="create_contact",
            crm_contact_id=lead_id,
            status="success",
            request_payload=create_body,
            response_payload=response.json(),
        )

        return lead_id

    async def _close_create_opportunity(
        self,
        config: CRMConfig,
        lead: LeadData,
        meeting: MeetingData,
        close_lead_id: str,
        deal_name: str,
    ) -> str:
        """Create Close opportunity."""
        auth = self._close_auth(config)

        url = f"{CLOSE_API}/opportunity"
        body: dict[str, Any] = {
            "lead_id": close_lead_id,
            "note": f"Meeting booked via Agency OS. {meeting.notes or ''}".strip(),
        }

        if config.stage_id:
            body["status_id"] = config.stage_id

        if config.owner_id:
            body["user_id"] = config.owner_id

        # Add expected close date
        if meeting.scheduled_at:
            body["date_won"] = None  # Not won yet
            body["confidence"] = 50  # Default confidence

        response = await self.http.post(url, json=body, auth=auth)
        response.raise_for_status()
        opp_id = response.json()["id"]

        logger.info(f"Created Close opportunity: {opp_id}")
        return opp_id

    async def get_close_pipelines(self, config: CRMConfig) -> list[CRMPipeline]:
        """Get available pipelines (statuses) from Close."""
        auth = self._close_auth(config)
        url = f"{CLOSE_API}/status/opportunity"

        response = await self.http.get(url, auth=auth)
        response.raise_for_status()

        # Close uses statuses instead of pipelines
        # Group by pipeline label
        statuses = response.json().get("data", [])

        # Create a single pipeline with all statuses as stages
        stages = [CRMStage(id=s["id"], name=s["label"]) for s in statuses]

        return [CRMPipeline(id="default", name="Opportunities", stages=stages)]

    async def get_close_users(self, config: CRMConfig) -> list[CRMUser]:
        """Get available users from Close."""
        auth = self._close_auth(config)
        url = f"{CLOSE_API}/user"

        response = await self.http.get(url, auth=auth)
        response.raise_for_status()

        return [
            CRMUser(
                id=u["id"],
                name=f"{u.get('first_name', '')} {u.get('last_name', '')}".strip(),
                email=u.get("email"),
            )
            for u in response.json().get("data", [])
        ]

    # =========================================================================
    # TEST CONNECTION
    # =========================================================================

    async def test_connection(self, config: CRMConfig) -> tuple[bool, str | None]:
        """Test CRM connection. Returns (success, error_message)."""
        start_time = time.time()

        try:
            if config.crm_type == "hubspot":
                config = await self._refresh_hubspot_token_if_needed(config)
                await self.get_hubspot_pipelines(config)
            elif config.crm_type == "pipedrive":
                await self.get_pipedrive_pipelines(config)
            elif config.crm_type == "close":
                await self.get_close_pipelines(config)

            duration_ms = int((time.time() - start_time) * 1000)

            await self.log_push(
                client_id=config.client_id,
                crm_config_id=config.id,
                operation="test_connection",
                status="success",
                duration_ms=duration_ms,
            )

            return True, None

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            await self.log_push(
                client_id=config.client_id,
                crm_config_id=config.id,
                operation="test_connection",
                status="failed",
                error_message=error_msg,
                duration_ms=duration_ms,
            )

            return False, error_msg

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    async def get_pipelines(self, config: CRMConfig) -> list[CRMPipeline]:
        """Get pipelines for any CRM type."""
        if config.crm_type == "hubspot":
            config = await self._refresh_hubspot_token_if_needed(config)
            return await self.get_hubspot_pipelines(config)
        elif config.crm_type == "pipedrive":
            return await self.get_pipedrive_pipelines(config)
        elif config.crm_type == "close":
            return await self.get_close_pipelines(config)
        else:
            raise ValueError(f"Unsupported CRM type: {config.crm_type}")

    async def get_users(self, config: CRMConfig) -> list[CRMUser]:
        """Get users for any CRM type."""
        if config.crm_type == "hubspot":
            config = await self._refresh_hubspot_token_if_needed(config)
            return await self.get_hubspot_users(config)
        elif config.crm_type == "pipedrive":
            return await self.get_pipedrive_users(config)
        elif config.crm_type == "close":
            return await self.get_close_users(config)
        else:
            raise ValueError(f"Unsupported CRM type: {config.crm_type}")
