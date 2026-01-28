"""
FILE: src/orchestration/flows/crm_sync_flow.py
PURPOSE: Scheduled polling flow for two-way CRM sync (safety net)
PHASE: Item 20 (Two-way CRM Sync)
TASK: CRM-SYNC-001
DEPENDENCIES:
  - src/services/deal_service.py
  - src/services/meeting_service.py
  - src/models/database.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 14: Soft delete checks

This flow polls external CRMs for deal/opportunity updates that may have been
missed by webhooks. It runs as a safety net to ensure complete data capture
for blind conversions.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from prefect import flow, task
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.supabase import get_db_session

logger = logging.getLogger(__name__)


# ============================================================================
# TASK: Get Clients with CRM Integrations
# ============================================================================


@task(name="get_crm_enabled_clients")
async def get_crm_enabled_clients(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Get all clients with CRM integrations configured.

    Returns:
        List of client records with CRM credentials
    """
    query = text("""
        SELECT
            c.id,
            c.company_name,
            c.tier,
            c.crm_type,
            c.crm_api_key,
            c.hubspot_access_token,
            c.pipedrive_api_token,
            c.close_api_key
        FROM clients c
        WHERE c.deleted_at IS NULL
        AND (
            c.crm_type IS NOT NULL
            OR c.hubspot_access_token IS NOT NULL
            OR c.pipedrive_api_token IS NOT NULL
            OR c.close_api_key IS NOT NULL
        )
    """)

    result = await db.execute(query)
    rows = result.fetchall()

    clients = []
    for row in rows:
        # Determine which CRM(s) are configured
        crms = []
        if row.hubspot_access_token:
            crms.append({"type": "hubspot", "token": row.hubspot_access_token})
        if row.pipedrive_api_token:
            crms.append({"type": "pipedrive", "token": row.pipedrive_api_token})
        if row.close_api_key:
            crms.append({"type": "close", "token": row.close_api_key})

        if crms:
            clients.append(
                {
                    "id": row.id,
                    "company_name": row.company_name,
                    "tier": row.tier,
                    "crm_configs": crms,
                }
            )

    logger.info(f"Found {len(clients)} clients with CRM integrations")
    return clients


# ============================================================================
# TASK: Poll HubSpot for Recent Deals
# ============================================================================


@task(name="poll_hubspot_deals", retries=2, retry_delay_seconds=60)
async def poll_hubspot_deals(
    db: AsyncSession,
    client_id: UUID,
    access_token: str,
    since_hours: int = 24,
) -> dict[str, Any]:
    """
    Poll HubSpot for recently updated deals.

    Args:
        db: Database session
        client_id: Client UUID
        access_token: HubSpot access token
        since_hours: Hours to look back

    Returns:
        Sync result summary
    """
    import httpx

    synced = 0
    errors = 0
    blind_meetings = 0

    try:
        # Calculate timestamp for filtering
        since_timestamp = int((datetime.utcnow() - timedelta(hours=since_hours)).timestamp() * 1000)

        # HubSpot deals API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.hubapi.com/crm/v3/objects/deals",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "limit": 100,
                    "properties": "dealname,amount,dealstage,closedate,hs_lastmodifieddate",
                    "filterGroups[0][filters][0][propertyName]": "hs_lastmodifieddate",
                    "filterGroups[0][filters][0][operator]": "GTE",
                    "filterGroups[0][filters][0][value]": str(since_timestamp),
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"HubSpot API error: {response.status_code} - {response.text}")
                return {"synced": 0, "errors": 1, "blind_meetings": 0, "error": response.text}

            data = response.json()
            deals = data.get("results", [])

            logger.info(f"HubSpot returned {len(deals)} deals for client {client_id}")

            # Process each deal
            from src.services.deal_service import DealService
            from src.services.meeting_service import MeetingService

            deal_service = DealService(db)
            meeting_service = MeetingService(db)

            for deal in deals:
                try:
                    external_id = deal.get("id")
                    properties = deal.get("properties", {})

                    # Check if we already have this deal
                    existing = await deal_service.get_by_external_id("hubspot", external_id)

                    # Parse deal data
                    deal_data = {
                        "external_id": external_id,
                        "name": properties.get("dealname", ""),
                        "value": properties.get("amount"),
                        "stage": properties.get("dealstage", "").lower(),
                        "close_date": properties.get("closedate"),
                    }

                    # Sync deal
                    synced_deal = await deal_service.sync_from_external(
                        client_id=client_id,
                        external_crm="hubspot",
                        external_deal_id=external_id,
                        data=deal_data,
                    )

                    synced += 1

                    # Create blind meeting if new deal without meeting
                    if not existing and not synced_deal.get("meeting_id"):
                        try:
                            await meeting_service.create_blind_meeting(
                                client_id=client_id,
                                lead_id=synced_deal.get("lead_id"),
                                deal_id=synced_deal["id"],
                                source="hubspot_poll",
                                notes="Blind meeting captured from HubSpot sync (polling)",
                                external_deal_id=external_id,
                            )
                            blind_meetings += 1
                        except Exception as e:
                            logger.warning(f"Failed to create blind meeting: {e}")

                except Exception as e:
                    logger.error(f"Error syncing HubSpot deal {deal.get('id')}: {e}")
                    errors += 1

    except Exception as e:
        logger.error(f"HubSpot polling error for client {client_id}: {e}")
        errors += 1

    return {
        "synced": synced,
        "errors": errors,
        "blind_meetings": blind_meetings,
        "crm": "hubspot",
    }


# ============================================================================
# TASK: Poll Pipedrive for Recent Deals
# ============================================================================


@task(name="poll_pipedrive_deals", retries=2, retry_delay_seconds=60)
async def poll_pipedrive_deals(
    db: AsyncSession,
    client_id: UUID,
    api_token: str,
    since_hours: int = 24,
) -> dict[str, Any]:
    """
    Poll Pipedrive for recently updated deals.

    Args:
        db: Database session
        client_id: Client UUID
        api_token: Pipedrive API token
        since_hours: Hours to look back

    Returns:
        Sync result summary
    """
    import httpx

    synced = 0
    errors = 0
    blind_meetings = 0

    try:
        # Calculate timestamp for filtering
        (datetime.utcnow() - timedelta(hours=since_hours)).isoformat()

        # Pipedrive deals API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.pipedrive.com/v1/deals",
                params={
                    "api_token": api_token,
                    "limit": 100,
                    "sort": "update_time DESC",
                    "start": 0,
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"Pipedrive API error: {response.status_code} - {response.text}")
                return {"synced": 0, "errors": 1, "blind_meetings": 0, "error": response.text}

            data = response.json()
            deals = data.get("data", []) or []

            # Filter by update time (client-side since API might not support it)
            since_dt = datetime.utcnow() - timedelta(hours=since_hours)
            recent_deals = []
            for deal in deals:
                update_time = deal.get("update_time")
                if update_time:
                    deal_dt = datetime.fromisoformat(
                        update_time.replace("Z", "+00:00").split("+")[0]
                    )
                    if deal_dt >= since_dt:
                        recent_deals.append(deal)

            logger.info(
                f"Pipedrive returned {len(recent_deals)} recent deals for client {client_id}"
            )

            # Process each deal
            from src.services.deal_service import DealService
            from src.services.meeting_service import MeetingService

            deal_service = DealService(db)
            meeting_service = MeetingService(db)

            for deal in recent_deals:
                try:
                    external_id = str(deal.get("id"))

                    # Check if we already have this deal
                    existing = await deal_service.get_by_external_id("pipedrive", external_id)

                    # Parse deal data
                    deal_data = {
                        "external_id": external_id,
                        "name": deal.get("title", ""),
                        "value": deal.get("value"),
                        "stage": str(deal.get("stage_id", "")),
                        "close_date": deal.get("expected_close_date"),
                    }

                    # Sync deal
                    synced_deal = await deal_service.sync_from_external(
                        client_id=client_id,
                        external_crm="pipedrive",
                        external_deal_id=external_id,
                        data=deal_data,
                    )

                    synced += 1

                    # Create blind meeting if new deal without meeting
                    if not existing and not synced_deal.get("meeting_id"):
                        try:
                            await meeting_service.create_blind_meeting(
                                client_id=client_id,
                                lead_id=synced_deal.get("lead_id"),
                                deal_id=synced_deal["id"],
                                source="pipedrive_poll",
                                notes="Blind meeting captured from Pipedrive sync (polling)",
                                external_deal_id=external_id,
                            )
                            blind_meetings += 1
                        except Exception as e:
                            logger.warning(f"Failed to create blind meeting: {e}")

                except Exception as e:
                    logger.error(f"Error syncing Pipedrive deal {deal.get('id')}: {e}")
                    errors += 1

    except Exception as e:
        logger.error(f"Pipedrive polling error for client {client_id}: {e}")
        errors += 1

    return {
        "synced": synced,
        "errors": errors,
        "blind_meetings": blind_meetings,
        "crm": "pipedrive",
    }


# ============================================================================
# TASK: Poll Close for Recent Opportunities
# ============================================================================


@task(name="poll_close_opportunities", retries=2, retry_delay_seconds=60)
async def poll_close_opportunities(
    db: AsyncSession,
    client_id: UUID,
    api_key: str,
    since_hours: int = 24,
) -> dict[str, Any]:
    """
    Poll Close CRM for recently updated opportunities.

    Args:
        db: Database session
        client_id: Client UUID
        api_key: Close API key
        since_hours: Hours to look back

    Returns:
        Sync result summary
    """
    import base64

    import httpx

    synced = 0
    errors = 0
    blind_meetings = 0

    try:
        # Close uses Basic auth with API key
        auth_header = base64.b64encode(f"{api_key}:".encode()).decode()

        # Close opportunities API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.close.com/api/v1/opportunity/",
                headers={"Authorization": f"Basic {auth_header}"},
                params={
                    "_limit": 100,
                    "_order_by": "-date_updated",
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"Close API error: {response.status_code} - {response.text}")
                return {"synced": 0, "errors": 1, "blind_meetings": 0, "error": response.text}

            data = response.json()
            opportunities = data.get("data", []) or []

            # Filter by update time
            since_dt = datetime.utcnow() - timedelta(hours=since_hours)
            recent_opps = []
            for opp in opportunities:
                update_time = opp.get("date_updated")
                if update_time:
                    opp_dt = datetime.fromisoformat(
                        update_time.replace("Z", "+00:00").split("+")[0]
                    )
                    if opp_dt >= since_dt:
                        recent_opps.append(opp)

            logger.info(
                f"Close returned {len(recent_opps)} recent opportunities for client {client_id}"
            )

            # Process each opportunity
            from src.services.deal_service import DealService
            from src.services.meeting_service import MeetingService

            deal_service = DealService(db)
            meeting_service = MeetingService(db)

            for opp in recent_opps:
                try:
                    external_id = opp.get("id")

                    # Check if we already have this deal
                    existing = await deal_service.get_by_external_id("close", external_id)

                    # Map Close status to our stages
                    status_type = opp.get("status_type", "active")
                    stage_map = {
                        "active": "qualification",
                        "won": "closed_won",
                        "lost": "closed_lost",
                    }
                    stage = stage_map.get(status_type.lower(), "qualification")

                    # Parse opportunity data
                    deal_data = {
                        "external_id": external_id,
                        "name": opp.get("note") or opp.get("lead_name", "Close Opportunity"),
                        "value": opp.get("value"),
                        "stage": stage,
                        "close_date": opp.get("date_won") or opp.get("expected_close_date"),
                    }

                    # Sync deal
                    synced_deal = await deal_service.sync_from_external(
                        client_id=client_id,
                        external_crm="close",
                        external_deal_id=external_id,
                        data=deal_data,
                    )

                    synced += 1

                    # Create blind meeting if new deal without meeting
                    if not existing and not synced_deal.get("meeting_id"):
                        try:
                            await meeting_service.create_blind_meeting(
                                client_id=client_id,
                                lead_id=synced_deal.get("lead_id"),
                                deal_id=synced_deal["id"],
                                source="close_poll",
                                notes="Blind meeting captured from Close sync (polling)",
                                external_deal_id=external_id,
                            )
                            blind_meetings += 1
                        except Exception as e:
                            logger.warning(f"Failed to create blind meeting: {e}")

                except Exception as e:
                    logger.error(f"Error syncing Close opportunity {opp.get('id')}: {e}")
                    errors += 1

    except Exception as e:
        logger.error(f"Close polling error for client {client_id}: {e}")
        errors += 1

    return {
        "synced": synced,
        "errors": errors,
        "blind_meetings": blind_meetings,
        "crm": "close",
    }


# ============================================================================
# TASK: Log Sync Results
# ============================================================================


@task(name="log_crm_sync_results")
async def log_crm_sync_results(
    db: AsyncSession,
    client_id: UUID,
    results: list[dict[str, Any]],
) -> None:
    """
    Log CRM sync results to the database.

    Args:
        db: Database session
        client_id: Client UUID
        results: List of sync results from each CRM
    """
    for result in results:
        try:
            query = text("""
                INSERT INTO crm_sync_log (
                    client_id, crm_source, sync_type, event_type,
                    sync_status, sync_notes, processed_at
                ) VALUES (
                    :client_id, :crm_source, 'poll', 'sync_batch',
                    :status, :notes, NOW()
                )
            """)

            status = "success" if result.get("errors", 0) == 0 else "partial"
            if result.get("synced", 0) == 0 and result.get("errors", 0) > 0:
                status = "failed"

            notes = (
                f"Synced: {result.get('synced', 0)}, "
                f"Errors: {result.get('errors', 0)}, "
                f"Blind meetings: {result.get('blind_meetings', 0)}"
            )

            await db.execute(
                query,
                {
                    "client_id": client_id,
                    "crm_source": result.get("crm", "unknown"),
                    "status": status,
                    "notes": notes,
                },
            )

            await db.commit()

        except Exception as e:
            logger.error(f"Failed to log sync results: {e}")


# ============================================================================
# MAIN FLOW: CRM Sync
# ============================================================================


@flow(name="crm-sync-flow", log_prints=True)
async def crm_sync_flow(
    since_hours: int = 24,
    client_id: str | None = None,
) -> dict[str, Any]:
    """
    Main CRM sync flow - polls external CRMs for deal/opportunity updates.

    This flow is a safety net for missed webhooks, ensuring complete data
    capture for blind conversions (meetings/deals created directly in CRM).

    Args:
        since_hours: Hours to look back for updates (default 24)
        client_id: Optional specific client to sync (default: all clients)

    Returns:
        Summary of sync results
    """
    print(f"Starting CRM sync flow (since_hours={since_hours})")

    total_synced = 0
    total_errors = 0
    total_blind_meetings = 0
    clients_processed = 0

    async with get_db_session() as db:
        # Get clients with CRM integrations
        clients = await get_crm_enabled_clients(db)

        if client_id:
            clients = [c for c in clients if str(c["id"]) == client_id]

        for client in clients:
            client_uuid = client["id"]
            client_results = []

            print(f"Syncing CRMs for client: {client['company_name']}")

            for crm_config in client["crm_configs"]:
                crm_type = crm_config["type"]
                token = crm_config["token"]

                try:
                    if crm_type == "hubspot":
                        result = await poll_hubspot_deals(
                            db=db,
                            client_id=client_uuid,
                            access_token=token,
                            since_hours=since_hours,
                        )
                    elif crm_type == "pipedrive":
                        result = await poll_pipedrive_deals(
                            db=db,
                            client_id=client_uuid,
                            api_token=token,
                            since_hours=since_hours,
                        )
                    elif crm_type == "close":
                        result = await poll_close_opportunities(
                            db=db,
                            client_id=client_uuid,
                            api_key=token,
                            since_hours=since_hours,
                        )
                    else:
                        logger.warning(f"Unknown CRM type: {crm_type}")
                        continue

                    client_results.append(result)
                    total_synced += result.get("synced", 0)
                    total_errors += result.get("errors", 0)
                    total_blind_meetings += result.get("blind_meetings", 0)

                except Exception as e:
                    logger.error(f"Error polling {crm_type} for client {client_uuid}: {e}")
                    client_results.append(
                        {
                            "crm": crm_type,
                            "synced": 0,
                            "errors": 1,
                            "blind_meetings": 0,
                            "error": str(e),
                        }
                    )

            # Log results for this client
            await log_crm_sync_results(db, client_uuid, client_results)
            clients_processed += 1

    summary = {
        "clients_processed": clients_processed,
        "total_synced": total_synced,
        "total_errors": total_errors,
        "total_blind_meetings": total_blind_meetings,
        "since_hours": since_hours,
    }

    print(f"CRM sync complete: {summary}")
    return summary


# ============================================================================
# VERIFICATION CHECKLIST
# ============================================================================
# [x] Contract comment at top
# [x] Flow with Prefect decorators
# [x] Tasks for each CRM: HubSpot, Pipedrive, Close
# [x] Get clients with CRM integrations
# [x] Poll external CRM APIs
# [x] Sync deals via DealService.sync_from_external()
# [x] Create blind meetings for new deals without meetings
# [x] Log sync results to crm_sync_log table
# [x] Retry logic for API failures
# [x] Session passed as argument (Rule 11)
# [x] Error handling with graceful degradation
# [x] Summary statistics returned
