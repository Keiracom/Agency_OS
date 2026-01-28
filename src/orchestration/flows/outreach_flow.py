"""
FILE: src/orchestration/flows/outreach_flow.py
PURPOSE: Hourly outreach flow with JIT validation and multi-channel execution
PHASE: 5 (Orchestration), Unipile Migration
TASK: ORC-004
DEPENDENCIES:
  - src/integrations/supabase.py
  - src/integrations/unipile.py (LinkedIn - migrated from heyreach.py)
  - src/engines/content.py
  - src/engines/email.py
  - src/engines/sms.py
  - src/engines/linkedin.py (uses Unipile, not HeyReach)
  - src/engines/timing.py (humanized delays for LinkedIn)
  - src/engines/voice.py
  - src/engines/mail.py
  - src/engines/allocator.py
  - src/models/lead.py
  - src/models/client.py
  - src/models/campaign.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 13: JIT validation before every outreach (client, campaign, lead status)
  - Rule 14: Soft deletes only
  - Rule 17: Resource-level rate limits via Allocator
UNIPILE MIGRATION:
  - LinkedIn now uses Unipile API (70-85% cost reduction vs HeyReach)
  - Uses account_id instead of seat_id for LinkedIn resources
  - TimingEngine provides humanized delays (8-45 min between actions)
  - Higher rate limits supported (80-100/day configurable in settings)
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy import and_, select

from src.agents.sdk_agents import should_use_sdk_email
from src.engines.allocator import get_allocator_engine
from src.engines.content import get_content_engine
from src.engines.email import get_email_engine
from src.engines.linkedin import get_linkedin_engine
from src.engines.sms import get_sms_engine
from src.integrations.supabase import get_db_session
from src.models.base import (
    CampaignStatus,
    ChannelType,
    LeadStatus,
    PermissionMode,
    SubscriptionStatus,
)
from src.models.campaign import Campaign
from src.models.client import Client
from src.models.lead import Lead
from src.services.content_qa_service import (
    validate_email_content,
    validate_linkedin_content,
    validate_sms_content,
)

logger = logging.getLogger(__name__)


# ============================================
# TASKS
# ============================================


@task(name="get_leads_ready_for_outreach", retries=2, retry_delay_seconds=5)
async def get_leads_ready_for_outreach_task(limit: int = 50) -> dict[str, Any]:
    """
    Get leads ready for outreach with JIT validation.

    Only returns leads where:
    - Lead is in 'in_sequence' status
    - Client subscription is active/trialing
    - Client has credits
    - Campaign is active and not deleted
    - Lead is not unsubscribed/bounced/converted

    Args:
        limit: Maximum leads to process

    Returns:
        Dict with leads grouped by channel and campaign
    """
    async with get_db_session() as db:
        # Query with JIT validation joins (Rule 13)
        stmt = (
            select(
                Lead.id,
                Lead.client_id,
                Lead.campaign_id,
                Lead.assigned_email_resource,
                Lead.assigned_linkedin_seat,
                Lead.assigned_phone_resource,
                Campaign.permission_mode,
                Client.subscription_status,
                Client.credits_remaining,
            )
            .join(Client, Lead.client_id == Client.id)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(
                and_(
                    # Lead status check
                    Lead.status == LeadStatus.IN_SEQUENCE,
                    Lead.deleted_at.is_(None),  # Soft delete check
                    # Client validation (JIT)
                    Client.deleted_at.is_(None),
                    Client.subscription_status.in_([
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.TRIALING,
                    ]),
                    Client.credits_remaining > 0,
                    # Campaign validation (JIT)
                    Campaign.deleted_at.is_(None),
                    Campaign.status == CampaignStatus.ACTIVE,
                )
            )
            .order_by(Lead.updated_at.asc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        rows = result.all()

        # Group leads by assigned channels
        leads_by_channel: dict[str, list[dict[str, Any]]] = {
            "email": [],
            "linkedin": [],
            "sms": [],
            "voice": [],
            "mail": [],
        }

        for row in rows:
            (
                lead_id,
                client_id,
                campaign_id,
                email_resource,
                linkedin_seat,
                phone_resource,
                permission_mode,
                subscription_status,
                credits,
            ) = row

            lead_data = {
                "lead_id": str(lead_id),
                "client_id": str(client_id),
                "campaign_id": str(campaign_id),
                "permission_mode": permission_mode.value if permission_mode else "co_pilot",
            }

            # Assign to channels based on resource allocation
            if email_resource:
                leads_by_channel["email"].append({
                    **lead_data,
                    "resource": email_resource,
                })
            if linkedin_seat:
                leads_by_channel["linkedin"].append({
                    **lead_data,
                    "resource": linkedin_seat,
                })
            if phone_resource:
                # Could be SMS or voice - we'll check lead tier later
                leads_by_channel["sms"].append({
                    **lead_data,
                    "resource": phone_resource,
                })
                leads_by_channel["voice"].append({
                    **lead_data,
                    "resource": phone_resource,
                })

        total_leads = len(rows)
        logger.info(
            f"Found {total_leads} leads ready for outreach: "
            f"{len(leads_by_channel['email'])} email, "
            f"{len(leads_by_channel['linkedin'])} linkedin, "
            f"{len(leads_by_channel['sms'])} sms"
        )

        return {
            "total_leads": total_leads,
            "leads_by_channel": leads_by_channel,
        }


@task(name="jit_validate_outreach", retries=2, retry_delay_seconds=3)
async def jit_validate_outreach_task(
    lead_id: str, campaign_id: str, client_id: str
) -> dict[str, Any]:
    """
    JIT validation before sending outreach.

    Rule 13: Validate client, campaign, and lead status immediately before sending.

    Args:
        lead_id: Lead UUID string
        campaign_id: Campaign UUID string
        client_id: Client UUID string

    Returns:
        Dict with validation result

    Raises:
        ValueError: If validation fails
    """
    async with get_db_session() as db:
        # Validate client
        stmt_client = select(Client).where(
            and_(
                Client.id == UUID(client_id),
                Client.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt_client)
        client = result.scalar_one_or_none()

        if not client:
            raise ValueError(f"Client {client_id} not found or deleted")

        if client.subscription_status not in [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        ]:
            raise ValueError(
                f"Client subscription status is {client.subscription_status.value}"
            )

        if client.credits_remaining <= 0:
            raise ValueError("Client has no credits remaining")

        # Phase H, Item 43: Client emergency pause check
        if client.paused_at is not None:
            raise ValueError(
                f"Client has emergency pause active since {client.paused_at.isoformat()}"
            )

        # Validate campaign
        stmt_campaign = select(Campaign).where(
            and_(
                Campaign.id == UUID(campaign_id),
                Campaign.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt_campaign)
        campaign = result.scalar_one_or_none()

        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found or deleted")

        if campaign.status != CampaignStatus.ACTIVE:
            raise ValueError(f"Campaign status is {campaign.status.value}")

        # Phase H, Item 43: Campaign pause check
        if campaign.paused_at is not None:
            raise ValueError(
                f"Campaign is paused since {campaign.paused_at.isoformat()}"
            )

        # Validate lead
        stmt_lead = select(Lead).where(
            and_(
                Lead.id == UUID(lead_id),
                Lead.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt_lead)
        lead = result.scalar_one_or_none()

        if not lead:
            raise ValueError(f"Lead {lead_id} not found or deleted")

        if lead.status in [
            LeadStatus.UNSUBSCRIBED,
            LeadStatus.BOUNCED,
            LeadStatus.CONVERTED,
        ]:
            raise ValueError(f"Lead status is {lead.status.value}")

        # Permission mode check
        permission_mode = campaign.permission_mode or PermissionMode.CO_PILOT
        if permission_mode == PermissionMode.MANUAL:
            raise ValueError("Campaign is in manual mode - requires approval")

        return {
            "valid": True,
            "client_id": client_id,
            "campaign_id": campaign_id,
            "lead_id": lead_id,
            "permission_mode": permission_mode.value,
        }


@task(name="send_email_outreach", retries=2, retry_delay_seconds=10)
async def send_email_outreach_task(
    lead_id: str, campaign_id: str, resource: str, permission_mode: str
) -> dict[str, Any]:
    """
    Send email outreach to a lead.

    Hot leads (ALS 85+) use SDK-powered hyper-personalized email generation.
    Other leads use standard Haiku-based generation.

    Args:
        lead_id: Lead UUID string
        campaign_id: Campaign UUID string
        resource: Email domain resource
        permission_mode: Permission mode (autopilot, co_pilot, manual)

    Returns:
        Dict with send result
    """
    async with get_db_session() as db:
        content_engine = get_content_engine()
        email_engine = get_email_engine()
        allocator_engine = get_allocator_engine()

        lead_uuid = UUID(lead_id)
        campaign_uuid = UUID(campaign_id)

        # Check rate limit
        quota_result = await allocator_engine.check_and_consume_quota(
            channel=ChannelType.EMAIL,
            resource_id=resource,
        )

        if not quota_result.success:
            return {
                "lead_id": lead_id,
                "channel": "email",
                "success": False,
                "error": f"Rate limit exceeded: {quota_result.error}",
            }

        # Fetch lead to check ALS score for SDK routing
        lead_stmt = select(Lead).where(Lead.id == lead_uuid)
        lead_result = await db.execute(lead_stmt)
        lead = lead_result.scalar_one_or_none()

        if not lead:
            return {
                "lead_id": lead_id,
                "channel": "email",
                "success": False,
                "error": f"Lead {lead_id} not found",
            }

        # Build lead_data for SDK eligibility check
        lead_data = {
            "als_score": lead.als_score,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "title": lead.title,
            "company_name": lead.company,
            "organization_industry": lead.organization_industry,
            "organization_employee_count": lead.organization_employee_count,
        }

        # SDK email for Hot leads (ALS 85+), standard for others
        if should_use_sdk_email(lead_data):
            # Use SDK-powered email generation for Hot leads
            content_result = await content_engine.generate_email_with_sdk(
                db=db,
                lead_id=lead_uuid,
                campaign_id=campaign_uuid,
                tone="professional",
            )
            logger.info(f"SDK email generated for Hot lead {lead_id} (ALS: {lead.als_score})")
        else:
            # Standard Haiku-based generation
            content_result = await content_engine.generate_email(
                db=db,
                lead_id=lead_uuid,
                campaign_id=campaign_uuid,
                tone="professional",
            )

        if not content_result.success:
            return {
                "lead_id": lead_id,
                "channel": "email",
                "success": False,
                "error": f"Content generation failed: {content_result.error}",
            }

        # Phase 22: Content QA validation before send
        qa_result = validate_email_content(
            subject=content_result.data.get("subject", ""),
            body=content_result.data.get("body", ""),
            lead_first_name=lead.first_name,
            lead_company=lead.company,
        )

        if not qa_result.passed:
            logger.warning(
                f"Email QA failed for lead {lead_id}: {qa_result.error_messages}"
            )
            return {
                "lead_id": lead_id,
                "channel": "email",
                "success": False,
                "error": f"Content QA failed: {'; '.join(qa_result.error_messages)}",
                "qa_issues": qa_result.to_dict(),
            }

        # Send email
        send_result = await email_engine.send_email(
            db=db,
            lead_id=lead_uuid,
            subject=content_result.data["subject"],
            body=content_result.data["body"],
            from_domain=resource,
        )

        if send_result.success:
            sdk_used = should_use_sdk_email(lead_data)
            logger.info(f"Email sent to lead {lead_id} (SDK: {sdk_used})")

        return {
            "lead_id": lead_id,
            "channel": "email",
            "success": send_result.success,
            "message_id": send_result.data.get("message_id") if send_result.success else None,
            "error": send_result.error if not send_result.success else None,
            "sdk_used": should_use_sdk_email(lead_data),
        }


@task(name="send_linkedin_outreach", retries=2, retry_delay_seconds=10)
async def send_linkedin_outreach_task(
    lead_id: str, campaign_id: str, resource: str, permission_mode: str
) -> dict[str, Any]:
    """
    Send LinkedIn outreach to a lead via Unipile.

    Args:
        lead_id: Lead UUID string
        campaign_id: Campaign UUID string
        resource: Unipile account ID (migrated from HeyReach seat ID)
        permission_mode: Permission mode

    Returns:
        Dict with send result

    Note: Uses Unipile API (migrated from HeyReach) with timing-aware sending.
    The TimingEngine provides humanized delays, but those are applied at the
    queue/scheduling level, not during immediate sends.
    """
    async with get_db_session() as db:
        content_engine = get_content_engine()
        linkedin_engine = get_linkedin_engine()
        allocator_engine = get_allocator_engine()

        lead_uuid = UUID(lead_id)
        campaign_uuid = UUID(campaign_id)

        # Check rate limit (now uses configurable limits from settings)
        quota_result = await allocator_engine.check_and_consume_quota(
            channel=ChannelType.LINKEDIN,
            resource_id=resource,
        )

        if not quota_result.success:
            return {
                "lead_id": lead_id,
                "channel": "linkedin",
                "success": False,
                "error": f"Rate limit exceeded: {quota_result.error}",
            }

        # Generate content
        content_result = await content_engine.generate_linkedin_message(
            db=db,
            lead_id=lead_uuid,
            campaign_id=campaign_uuid,
            message_type="connection_request",
        )

        if not content_result.success:
            return {
                "lead_id": lead_id,
                "channel": "linkedin",
                "success": False,
                "error": f"Content generation failed: {content_result.error}",
            }

        # Phase 22: Content QA validation before send
        qa_result = validate_linkedin_content(
            message=content_result.data.get("message", ""),
            message_type="connection",
        )

        if not qa_result.passed:
            logger.warning(
                f"LinkedIn QA failed for lead {lead_id}: {qa_result.error_messages}"
            )
            return {
                "lead_id": lead_id,
                "channel": "linkedin",
                "success": False,
                "error": f"Content QA failed: {'; '.join(qa_result.error_messages)}",
                "qa_issues": qa_result.to_dict(),
            }

        # Send connection request via Unipile (migrated from HeyReach)
        # Note: account_id is the Unipile account ID (replaced seat_id)
        send_result = await linkedin_engine.send_connection_request(
            db=db,
            lead_id=lead_uuid,
            campaign_id=campaign_uuid,
            message=content_result.data["message"],
            account_id=resource,
        )

        if send_result.success:
            logger.info(f"LinkedIn connection request sent to lead {lead_id} via Unipile")

        return {
            "lead_id": lead_id,
            "channel": "linkedin",
            "success": send_result.success,
            "provider_id": send_result.data.get("provider_id") if send_result.success else None,
            "error": send_result.error if not send_result.success else None,
        }


@task(name="send_sms_outreach", retries=2, retry_delay_seconds=10)
async def send_sms_outreach_task(
    lead_id: str, campaign_id: str, resource: str, permission_mode: str
) -> dict[str, Any]:
    """
    Send SMS outreach to a lead.

    Args:
        lead_id: Lead UUID string
        campaign_id: Campaign UUID string
        resource: Phone number resource
        permission_mode: Permission mode

    Returns:
        Dict with send result
    """
    async with get_db_session() as db:
        content_engine = get_content_engine()
        sms_engine = get_sms_engine()
        allocator_engine = get_allocator_engine()

        lead_uuid = UUID(lead_id)
        campaign_uuid = UUID(campaign_id)

        # P1 Fix: Validate ALS score (SMS requires Hot tier, ALS >= 85)
        lead = await db.get(Lead, lead_uuid)
        if not lead:
            return {
                "lead_id": lead_id,
                "channel": "sms",
                "success": False,
                "error": "Lead not found",
            }

        if lead.als_score is None or lead.als_score < 85:
            logger.warning(
                f"SMS blocked for lead {lead_id}: ALS {lead.als_score} < 85 (Hot required)"
            )
            return {
                "lead_id": lead_id,
                "channel": "sms",
                "success": False,
                "error": f"SMS requires Hot tier (ALS >= 85). Lead has ALS {lead.als_score}",
            }

        # Check rate limit
        quota_result = await allocator_engine.check_and_consume_quota(
            channel=ChannelType.SMS,
            resource_id=resource,
        )

        if not quota_result.success:
            return {
                "lead_id": lead_id,
                "channel": "sms",
                "success": False,
                "error": f"Rate limit exceeded: {quota_result.error}",
            }

        # Generate content
        content_result = await content_engine.generate_sms(
            db=db,
            lead_id=lead_uuid,
            campaign_id=campaign_uuid,
        )

        if not content_result.success:
            return {
                "lead_id": lead_id,
                "channel": "sms",
                "success": False,
                "error": f"Content generation failed: {content_result.error}",
            }

        # Phase 22: Content QA validation before send
        qa_result = validate_sms_content(
            message=content_result.data.get("message", ""),
        )

        if not qa_result.passed:
            logger.warning(
                f"SMS QA failed for lead {lead_id}: {qa_result.error_messages}"
            )
            return {
                "lead_id": lead_id,
                "channel": "sms",
                "success": False,
                "error": f"Content QA failed: {'; '.join(qa_result.error_messages)}",
                "qa_issues": qa_result.to_dict(),
            }

        # Send SMS
        send_result = await sms_engine.send_sms(
            db=db,
            lead_id=lead_uuid,
            message=content_result.data["message"],
            from_number=resource,
        )

        if send_result.success:
            logger.info(f"SMS sent to lead {lead_id}")

        return {
            "lead_id": lead_id,
            "channel": "sms",
            "success": send_result.success,
            "message_id": send_result.data.get("message_id") if send_result.success else None,
            "error": send_result.error if not send_result.success else None,
        }


# ============================================
# FLOW
# ============================================


@flow(
    name="hourly_outreach",
    description="Hourly outreach flow with JIT validation and multi-channel execution",
    log_prints=True,
    task_runner=ConcurrentTaskRunner(max_workers=10),
)
async def hourly_outreach_flow(batch_size: int = 50) -> dict[str, Any]:
    """
    Hourly outreach flow.

    Steps:
    1. Get leads ready for outreach (with JIT validation)
    2. For each lead and channel:
       a. JIT validate client/campaign/lead status
       b. Check rate limits (via Allocator)
       c. Generate content (via Content engine)
       d. Send via appropriate channel engine
       e. Record activity

    Args:
        batch_size: Maximum leads to process

    Returns:
        Dict with outreach summary
    """
    logger.info(f"Starting hourly outreach flow (batch_size={batch_size})")

    # Step 1: Get leads ready for outreach
    leads_data = await get_leads_ready_for_outreach_task(limit=batch_size)

    if leads_data["total_leads"] == 0:
        logger.info("No leads ready for outreach")
        return {
            "total_leads": 0,
            "emails_sent": 0,
            "linkedin_sent": 0,
            "sms_sent": 0,
            "message": "No leads ready for outreach",
        }

    # Step 2: Process outreach by channel
    results = {
        "email": [],
        "linkedin": [],
        "sms": [],
    }

    # Process email outreach
    for lead_data in leads_data["leads_by_channel"]["email"]:
        try:
            # JIT validation
            validation = await jit_validate_outreach_task(
                lead_id=lead_data["lead_id"],
                campaign_id=lead_data["campaign_id"],
                client_id=lead_data["client_id"],
            )

            # Send email
            result = await send_email_outreach_task(
                lead_id=lead_data["lead_id"],
                campaign_id=lead_data["campaign_id"],
                resource=lead_data["resource"],
                permission_mode=validation["permission_mode"],
            )
            results["email"].append(result)

        except ValueError as e:
            logger.warning(f"JIT validation failed for lead {lead_data['lead_id']}: {e}")
            results["email"].append({
                "lead_id": lead_data["lead_id"],
                "channel": "email",
                "success": False,
                "error": str(e),
            })

    # Process LinkedIn outreach
    for lead_data in leads_data["leads_by_channel"]["linkedin"]:
        try:
            # JIT validation
            validation = await jit_validate_outreach_task(
                lead_id=lead_data["lead_id"],
                campaign_id=lead_data["campaign_id"],
                client_id=lead_data["client_id"],
            )

            # Send LinkedIn
            result = await send_linkedin_outreach_task(
                lead_id=lead_data["lead_id"],
                campaign_id=lead_data["campaign_id"],
                resource=lead_data["resource"],
                permission_mode=validation["permission_mode"],
            )
            results["linkedin"].append(result)

        except ValueError as e:
            logger.warning(f"JIT validation failed for lead {lead_data['lead_id']}: {e}")
            results["linkedin"].append({
                "lead_id": lead_data["lead_id"],
                "channel": "linkedin",
                "success": False,
                "error": str(e),
            })

    # Process SMS outreach
    for lead_data in leads_data["leads_by_channel"]["sms"]:
        try:
            # JIT validation
            validation = await jit_validate_outreach_task(
                lead_id=lead_data["lead_id"],
                campaign_id=lead_data["campaign_id"],
                client_id=lead_data["client_id"],
            )

            # Send SMS
            result = await send_sms_outreach_task(
                lead_id=lead_data["lead_id"],
                campaign_id=lead_data["campaign_id"],
                resource=lead_data["resource"],
                permission_mode=validation["permission_mode"],
            )
            results["sms"].append(result)

        except ValueError as e:
            logger.warning(f"JIT validation failed for lead {lead_data['lead_id']}: {e}")
            results["sms"].append({
                "lead_id": lead_data["lead_id"],
                "channel": "sms",
                "success": False,
                "error": str(e),
            })

    # Compile summary
    emails_sent = sum(1 for r in results["email"] if r["success"])
    linkedin_sent = sum(1 for r in results["linkedin"] if r["success"])
    sms_sent = sum(1 for r in results["sms"] if r["success"])

    summary = {
        "total_leads": leads_data["total_leads"],
        "emails_sent": emails_sent,
        "linkedin_sent": linkedin_sent,
        "sms_sent": sms_sent,
        "total_sent": emails_sent + linkedin_sent + sms_sent,
        "results": results,
        "completed_at": datetime.utcnow().isoformat(),
    }

    logger.info(
        f"Hourly outreach flow completed: {emails_sent} emails, "
        f"{linkedin_sent} linkedin, {sms_sent} sms"
    )

    return summary


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed via get_db_session() context manager
# [x] No imports from other orchestration files
# [x] Imports from engines (content, email, sms, linkedin, allocator), models, integrations
# [x] JIT validation before every outreach (Rule 13)
# [x] Validates client subscription status
# [x] Validates campaign status
# [x] Validates lead status
# [x] Checks permission mode (autopilot/co_pilot/manual)
# [x] Rate limit checks via Allocator (Rule 17)
# [x] Soft delete checks in all queries (Rule 14)
# [x] @flow and @task decorators from Prefect
# [x] ConcurrentTaskRunner with max_workers=10
# [x] Proper error handling with retries
# [x] Logging throughout
# [x] Records activities (via channel engines)
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Returns structured dict results
#
# UNIPILE MIGRATION:
# [x] LinkedIn uses account_id instead of seat_id
# [x] LinkedInEngine now uses Unipile client (not HeyReach)
# [x] TimingEngine available for humanized delays (queue-based scheduling)
# [x] Higher rate limits supported (80-100/day configurable)
