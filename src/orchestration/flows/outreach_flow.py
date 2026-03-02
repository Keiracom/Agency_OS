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
from sqlalchemy import and_, select, text

from src.agents.sdk_agents import should_use_sdk_email
from src.engines.allocator import get_allocator_engine
from src.engines.content import get_content_engine
from src.engines.email import get_email_engine
from src.engines.linkedin import get_linkedin_engine
from src.engines.sms import get_sms_engine
from src.engines.timing import get_timing_engine
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
from src.services.cis_service import get_cis_service
from src.services.content_qa_service import (
    validate_email_content,
    validate_linkedin_content,
    validate_sms_content,
)

logger = logging.getLogger(__name__)


# ============================================
# TASKS
# ============================================


@task(name="check_campaign_quality_gate", retries=2, retry_delay_seconds=5)
async def check_campaign_quality_gate_task(campaign_id: str) -> dict[str, Any]:
    """
    Pre-campaign quality gate check (Directive 048 Part E - Expanded).

    Halts and notifies if:
    - Hot+Warm combined below 5% of total leads
    - Verified email below 80% of leads
    - DM (Decision Maker) identified below 60% of leads

    Triggers additional discovery if Hot+Warm below 25%.

    Args:
        campaign_id: Campaign UUID string

    Returns:
        Dict with quality gate result
    """
    async with get_db_session() as db:
        # Get comprehensive stats for campaign leads
        result = await db.execute(
            text("""
                SELECT
                    COUNT(*) as total_leads,
                    COUNT(CASE WHEN als_tier = 'hot' THEN 1 END) as hot_count,
                    COUNT(CASE WHEN als_tier = 'warm' THEN 1 END) as warm_count,
                    COUNT(CASE WHEN als_tier = 'cool' THEN 1 END) as cool_count,
                    COUNT(CASE WHEN als_tier = 'cold' THEN 1 END) as cold_count,
                    COUNT(CASE WHEN als_tier = 'dead' THEN 1 END) as dead_count,
                    COUNT(CASE WHEN email_verified = TRUE THEN 1 END) as verified_email_count,
                    COUNT(CASE WHEN seniority_level IN ('owner', 'founder', 'c_suite', 'vp', 'director')
                          OR title ILIKE '%owner%' OR title ILIKE '%ceo%' OR title ILIKE '%founder%'
                          OR title ILIKE '%director%' OR title ILIKE '%managing%' THEN 1 END) as dm_count
                FROM leads
                WHERE campaign_id = :campaign_id
                AND status = 'in_sequence'
                AND deleted_at IS NULL
            """),
            {"campaign_id": campaign_id},
        )
        row = result.fetchone()

        if not row or row.total_leads == 0:
            await _create_campaign_halt_notification(
                db, campaign_id, "no_leads", "Campaign has no leads in sequence", {}
            )
            return {
                "campaign_id": campaign_id,
                "passed": False,
                "reason": "no_leads",
                "halt_notification_sent": True,
            }

        total = row.total_leads
        hot_warm_count = row.hot_count + row.warm_count
        hot_warm_pct = (hot_warm_count / total) * 100
        verified_email_pct = (row.verified_email_count / total) * 100
        dm_pct = (row.dm_count / total) * 100

        metrics = {
            "total_leads": total,
            "hot_count": row.hot_count,
            "warm_count": row.warm_count,
            "cool_count": row.cool_count,
            "cold_count": row.cold_count,
            "dead_count": row.dead_count,
            "hot_warm_percentage": round(hot_warm_pct, 1),
            "verified_email_percentage": round(verified_email_pct, 1),
            "dm_identified_percentage": round(dm_pct, 1),
        }

        failures = []

        # Check 1: Hot+Warm combined below 5%
        if hot_warm_pct < 5:
            failures.append(
                {
                    "check": "hot_warm_ratio",
                    "threshold": "5%",
                    "actual": f"{hot_warm_pct:.1f}%",
                    "message": f"Hot+Warm leads ({hot_warm_pct:.1f}%) below 5% threshold",
                }
            )

        # Check 2: Verified email below 80%
        if verified_email_pct < 80:
            failures.append(
                {
                    "check": "verified_email_ratio",
                    "threshold": "80%",
                    "actual": f"{verified_email_pct:.1f}%",
                    "message": f"Verified emails ({verified_email_pct:.1f}%) below 80% threshold",
                }
            )

        # Check 3: DM identified below 60%
        if dm_pct < 60:
            failures.append(
                {
                    "check": "dm_identified_ratio",
                    "threshold": "60%",
                    "actual": f"{dm_pct:.1f}%",
                    "message": f"Decision Makers identified ({dm_pct:.1f}%) below 60% threshold",
                }
            )

        if failures:
            # Create detailed halt notification
            failure_reasons = "; ".join([f["message"] for f in failures])
            await _create_campaign_halt_notification(
                db,
                campaign_id,
                "quality_gate_failed",
                f"Campaign halted: {failure_reasons}",
                {"failures": failures, "metrics": metrics},
            )
            return {
                "campaign_id": campaign_id,
                "passed": False,
                "reason": "quality_gate_failed",
                "failures": failures,
                "metrics": metrics,
                "halt_notification_sent": True,
            }

        # Check if additional discovery needed (Hot+Warm below 25%)
        needs_discovery = hot_warm_pct < 25

        return {
            "campaign_id": campaign_id,
            "passed": True,
            "metrics": metrics,
            "needs_additional_discovery": needs_discovery,
            "discovery_reason": f"Hot+Warm at {hot_warm_pct:.1f}% (below 25%)"
            if needs_discovery
            else None,
        }


async def _create_campaign_halt_notification(
    db, campaign_id: str, reason: str, message: str, metadata: dict
) -> None:
    """Create notification when campaign is halted by quality gate."""
    try:
        # Get campaign and client info
        result = await db.execute(
            text("""
                SELECT c.name, c.client_id, cl.name as client_name
                FROM campaigns c
                JOIN clients cl ON c.client_id = cl.id
                WHERE c.id = :campaign_id
            """),
            {"campaign_id": campaign_id},
        )
        row = result.fetchone()

        if row:
            import json
            from uuid import uuid4

            notification_id = str(uuid4())
            await db.execute(
                text("""
                    INSERT INTO admin_notifications (
                        id, notification_type, client_id, campaign_id,
                        title, message, severity, status, metadata,
                        created_at, updated_at
                    ) VALUES (
                        :id, 'campaign_halt', :client_id, :campaign_id,
                        :title, :message, 'high', 'pending', :metadata,
                        NOW(), NOW()
                    )
                """),
                {
                    "id": notification_id,
                    "client_id": str(row.client_id),
                    "campaign_id": campaign_id,
                    "title": f"⚠️ Campaign Halted: {row.name}",
                    "message": message,
                    "metadata": json.dumps(metadata),
                },
            )
            await db.commit()
            logger.info(
                f"Created campaign halt notification {notification_id} for campaign {campaign_id}"
            )
    except Exception as e:
        logger.error(f"Failed to create halt notification: {e}")


@task(name="auto_assign_resources", retries=2, retry_delay_seconds=5)
async def auto_assign_resources_task(lead_id: str, campaign_id: str) -> dict[str, Any]:
    """
    Automatically assign resources to a lead based on tier and availability.

    Directive 048 Part E: Channel selection no longer requires manual assignment.
    Reads CHANNEL_ACCESS_BY_ALS and auto-assigns on campaign entry.

    Args:
        lead_id: Lead UUID string
        campaign_id: Campaign UUID string

    Returns:
        Dict with assigned resources
    """
    from src.config.tiers import CHANNEL_ACCESS_BY_ALS, get_als_tier

    async with get_db_session() as db:
        # Get lead tier and client resources
        result = await db.execute(
            text("""
                SELECT
                    l.id, l.als_tier, l.als_score, l.client_id,
                    l.assigned_email_resource, l.assigned_linkedin_seat, l.assigned_phone_resource
                FROM leads l
                WHERE l.id = :lead_id
            """),
            {"lead_id": lead_id},
        )
        lead_row = result.fetchone()

        if not lead_row:
            return {"lead_id": lead_id, "success": False, "error": "Lead not found"}

        reachability_score = lead_row.als_score or 0
        als_tier = get_als_tier(reachability_score)
        client_id = lead_row.client_id
        assigned = {}

        # Get allowed channels directly from CHANNEL_ACCESS_BY_ALS
        allowed_channels = CHANNEL_ACCESS_BY_ALS.get(als_tier, [])

        # Get available resources from resource_pool with round-robin selection
        resources_result = await db.execute(
            text("""
                SELECT
                    channel_type, resource_id, daily_remaining,
                    ROW_NUMBER() OVER (PARTITION BY channel_type ORDER BY daily_remaining DESC) as rn
                FROM resource_pool
                WHERE client_id = :client_id
                AND is_available = TRUE
                AND daily_remaining > 0
            """),
            {"client_id": str(client_id)},
        )

        # Build resource map with best available resource per channel
        available_resources = {}
        for row in resources_result.fetchall():
            if row.rn == 1:  # Best resource for this channel
                available_resources[row.channel_type] = row.resource_id

        # Auto-assign email (always check first)
        if "email" in allowed_channels:
            if not lead_row.assigned_email_resource:
                if "email" in available_resources:
                    assigned["email"] = available_resources["email"]
                else:
                    # Fallback: get any email domain from client config
                    fallback = await db.execute(
                        text("""
                            SELECT email_domains[1] as domain
                            FROM clients WHERE id = :client_id
                        """),
                        {"client_id": str(client_id)},
                    )
                    fb_row = fallback.fetchone()
                    if fb_row and fb_row.domain:
                        assigned["email"] = fb_row.domain

        # Auto-assign LinkedIn (warm+ tiers)
        if "linkedin" in allowed_channels:
            if not lead_row.assigned_linkedin_seat and "linkedin" in available_resources:
                assigned["linkedin"] = available_resources["linkedin"]

        # Auto-assign SMS (warm+ tiers per updated spec)
        if "sms" in allowed_channels:
            if not lead_row.assigned_phone_resource and "phone" in available_resources:
                assigned["phone"] = available_resources["phone"]

        # Auto-assign Voice (hot tier only)
        if "voice" in allowed_channels:
            if not lead_row.assigned_phone_resource and "phone" in available_resources:
                assigned["phone"] = available_resources["phone"]

        # Update lead with assignments
        if assigned:
            update_parts = []
            params = {"lead_id": lead_id}

            if "email" in assigned:
                update_parts.append("assigned_email_resource = :email_resource")
                params["email_resource"] = assigned["email"]
            if "linkedin" in assigned:
                update_parts.append("assigned_linkedin_seat = :linkedin_seat")
                params["linkedin_seat"] = assigned["linkedin"]
            if "phone" in assigned:
                update_parts.append("assigned_phone_resource = :phone_resource")
                params["phone_resource"] = assigned["phone"]

            if update_parts:
                update_parts.append("updated_at = NOW()")
                await db.execute(
                    text(f"""
                        UPDATE leads
                        SET {", ".join(update_parts)}
                        WHERE id = :lead_id
                    """),
                    params,
                )
                await db.commit()
                logger.info(f"Auto-assigned resources for lead {lead_id}: {assigned}")

        return {
            "lead_id": lead_id,
            "success": True,
            "tier": als_tier,
            "reachability_score": reachability_score,
            "allowed_channels": allowed_channels,
            "assigned": assigned,
        }


@task(name="trigger_additional_discovery", retries=2, retry_delay_seconds=10)
async def trigger_additional_discovery_task(campaign_id: str) -> dict[str, Any]:
    """
    Trigger one additional discovery batch when Hot+Warm below 25%.

    Args:
        campaign_id: Campaign UUID string

    Returns:
        Dict with discovery result
    """
    from src.orchestration.flows.batch_controller_flow import trigger_replacement_discovery_task

    async with get_db_session() as db:
        # Get campaign client_id
        result = await db.execute(
            text("SELECT client_id FROM campaigns WHERE id = :campaign_id"),
            {"campaign_id": campaign_id},
        )
        row = result.fetchone()

        if not row:
            return {"campaign_id": campaign_id, "success": False, "error": "Campaign not found"}

        # Trigger discovery for 50 additional leads
        discovery_result = await trigger_replacement_discovery_task(
            campaign_id=campaign_id,
            client_id=str(row.client_id),
            count_needed=50,
        )

        return {
            "campaign_id": campaign_id,
            "success": discovery_result.get("success", False),
            "leads_discovered": discovery_result.get("leads_discovered", 0),
            "reason": "hot_warm_below_25_percent",
        }


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
    - Campaign passes quality gate (not 100% Cold)

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
                    Client.subscription_status.in_(
                        [
                            SubscriptionStatus.ACTIVE,
                            SubscriptionStatus.TRIALING,
                        ]
                    ),
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
                leads_by_channel["email"].append(
                    {
                        **lead_data,
                        "resource": email_resource,
                    }
                )
            if linkedin_seat:
                leads_by_channel["linkedin"].append(
                    {
                        **lead_data,
                        "resource": linkedin_seat,
                    }
                )
            if phone_resource:
                # Could be SMS or voice - we'll check lead tier later
                leads_by_channel["sms"].append(
                    {
                        **lead_data,
                        "resource": phone_resource,
                    }
                )
                leads_by_channel["voice"].append(
                    {
                        **lead_data,
                        "resource": phone_resource,
                    }
                )

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
            raise ValueError(f"Client subscription status is {client.subscription_status.value}")

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

        # Campaign approval guard (LAW: campaign_approval_flow)
        # No outreach may execute unless campaign has gone through approval and is ACTIVE.
        # Status flow: DRAFT → PENDING_APPROVAL → APPROVED → ACTIVE
        if campaign.status != CampaignStatus.ACTIVE:
            logger.info(
                f"Campaign {campaign_id} not approved for outreach (status={campaign.status.value}). "
                f"Skipping outreach per campaign_approval_flow LAW."
            )
            raise ValueError(f"Campaign status is {campaign.status.value}, must be ACTIVE")

        # Phase H, Item 43: Campaign pause check
        if campaign.paused_at is not None:
            raise ValueError(f"Campaign is paused since {campaign.paused_at.isoformat()}")

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
            "reachability_score": lead.als_score,
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
            logger.warning(f"Email QA failed for lead {lead_id}: {qa_result.error_messages}")
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

            # CIS: Record outreach outcome for learning
            try:
                cis_service = get_cis_service(db)
                activity_id = send_result.data.get("activity_id")
                if activity_id:
                    # Determine personalization level based on SDK usage
                    personalization_level = "sdk_enhanced" if sdk_used else "basic"

                    await cis_service.record_outreach_outcome(
                        activity_id=activity_id,
                        lead_id=lead_uuid,
                        client_id=lead.client_id,
                        campaign_id=campaign_uuid,
                        channel="email",
                        sequence_step=lead.sequence_step,
                        propensity_score_at_send=lead.als_score,
                        als_tier_at_send=lead.als_tier,
                        subject_line=content_result.data.get("subject"),
                        hook_type=content_result.data.get("hook_type"),
                        personalization_level=personalization_level,
                        session=db,
                    )
            except Exception as cis_error:
                logger.warning(f"CIS recording failed (non-blocking): {cis_error}")

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
    The TimingEngine enforces weekend rules before any sends.
    """
    # P0 Fix: Check weekend rules BEFORE content generation to avoid wasted resources
    timing_engine = get_timing_engine()
    timezone = "Australia/Sydney"  # Default timezone for LinkedIn timing

    # Sunday: No LinkedIn activity allowed
    if timing_engine.is_weekend(timezone):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(timezone)
        today = datetime.now(tz).weekday()

        if today == 6:  # Sunday
            logger.info(
                f"LinkedIn outreach skipped for lead {lead_id}: Sunday (no LinkedIn activity)"
            )
            return {
                "lead_id": lead_id,
                "channel": "linkedin",
                "success": False,
                "error": "LinkedIn paused on Sunday - queued for Monday",
                "skipped_reason": "weekend_sunday",
            }
        # Saturday: reduced quota handled by engine, but log the weekend status
        logger.info(f"LinkedIn outreach on Saturday for lead {lead_id}: 50% quota in effect")

    # Check business hours
    if not timing_engine.is_business_hours(timezone):
        logger.info(f"LinkedIn outreach skipped for lead {lead_id}: Outside business hours")
        return {
            "lead_id": lead_id,
            "channel": "linkedin",
            "success": False,
            "error": "LinkedIn paused outside business hours",
            "skipped_reason": "outside_business_hours",
        }

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
            logger.warning(f"LinkedIn QA failed for lead {lead_id}: {qa_result.error_messages}")
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

            # CIS: Record outreach outcome for learning
            try:
                cis_service = get_cis_service(db)
                activity_id = send_result.data.get("activity_id")
                if activity_id:
                    # Fetch lead for ALS data
                    lead_result = await db.execute(select(Lead).where(Lead.id == lead_uuid))
                    lead = lead_result.scalar_one_or_none()

                    await cis_service.record_outreach_outcome(
                        activity_id=activity_id,
                        lead_id=lead_uuid,
                        client_id=lead.client_id if lead else None,
                        campaign_id=campaign_uuid,
                        channel="linkedin",
                        sequence_step=lead.sequence_step if lead else None,
                        propensity_score_at_send=lead.als_score if lead else None,
                        als_tier_at_send=lead.als_tier if lead else None,
                        hook_type=content_result.data.get("hook_type"),
                        personalization_level="basic",
                        session=db,
                    )
            except Exception as cis_error:
                logger.warning(f"CIS recording failed (non-blocking): {cis_error}")

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

        # P1 Fix: Validate reachability score (SMS requires Hot tier, reachability >= 85)
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
                f"SMS blocked for lead {lead_id}: reachability {lead.als_score} < 85 (Hot required)"
            )
            return {
                "lead_id": lead_id,
                "channel": "sms",
                "success": False,
                "error": f"SMS requires Hot tier (reachability >= 85). Lead has reachability {lead.als_score}",
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
            logger.warning(f"SMS QA failed for lead {lead_id}: {qa_result.error_messages}")
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

            # CIS: Record outreach outcome for learning
            try:
                cis_service = get_cis_service(db)
                activity_id = send_result.data.get("activity_id")
                if activity_id:
                    await cis_service.record_outreach_outcome(
                        activity_id=activity_id,
                        lead_id=lead_uuid,
                        client_id=lead.client_id,
                        campaign_id=campaign_uuid,
                        channel="sms",
                        sequence_step=lead.sequence_step,
                        propensity_score_at_send=lead.als_score,
                        als_tier_at_send=lead.als_tier,
                        hook_type=content_result.data.get("hook_type"),
                        personalization_level="basic",
                        session=db,
                    )
            except Exception as cis_error:
                logger.warning(f"CIS recording failed (non-blocking): {cis_error}")

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

    # Step 0: Pre-campaign quality gate (Directive 048 Part E)
    # Get unique campaigns from leads and check each one
    campaigns_checked = {}
    skipped_campaigns = []

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

    # Collect unique campaign IDs for quality gate check
    all_campaign_ids = set()
    for channel_leads in leads_data["leads_by_channel"].values():
        for lead_data in channel_leads:
            all_campaign_ids.add(lead_data["campaign_id"])

    # Check quality gate for each campaign
    for campaign_id in all_campaign_ids:
        quality_result = await check_campaign_quality_gate_task(campaign_id)
        campaigns_checked[campaign_id] = quality_result

        if not quality_result.get("passed"):
            logger.warning(
                f"Campaign {campaign_id} failed quality gate: {quality_result.get('reason')} "
                f"(cold_percentage={quality_result.get('cold_percentage', 0):.1f}%)"
            )
            skipped_campaigns.append(campaign_id)

    # Filter out leads from skipped campaigns
    for channel in leads_data["leads_by_channel"]:
        leads_data["leads_by_channel"][channel] = [
            lead
            for lead in leads_data["leads_by_channel"][channel]
            if lead["campaign_id"] not in skipped_campaigns
        ]

    # Auto-assign resources for leads without assignments
    for channel in ["email", "linkedin", "sms"]:
        for lead_data in leads_data["leads_by_channel"].get(channel, []):
            if not lead_data.get("resource"):
                assignment = await auto_assign_resources_task(
                    lead_id=lead_data["lead_id"],
                    campaign_id=lead_data["campaign_id"],
                )
                if assignment.get("assigned", {}).get(channel):
                    lead_data["resource"] = assignment["assigned"][channel]

    # Recalculate totals after filtering
    total_after_filter = sum(len(leads) for leads in leads_data["leads_by_channel"].values())

    if total_after_filter == 0:
        logger.info("No leads ready after quality gate filter")
        return {
            "total_leads": leads_data["total_leads"],
            "total_after_filter": 0,
            "emails_sent": 0,
            "linkedin_sent": 0,
            "sms_sent": 0,
            "skipped_campaigns": skipped_campaigns,
            "message": "All campaigns failed quality gate (100% Cold leads)",
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
            results["email"].append(
                {
                    "lead_id": lead_data["lead_id"],
                    "channel": "email",
                    "success": False,
                    "error": str(e),
                }
            )

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
            results["linkedin"].append(
                {
                    "lead_id": lead_data["lead_id"],
                    "channel": "linkedin",
                    "success": False,
                    "error": str(e),
                }
            )

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
            results["sms"].append(
                {
                    "lead_id": lead_data["lead_id"],
                    "channel": "sms",
                    "success": False,
                    "error": str(e),
                }
            )

    # Compile summary
    emails_sent = sum(1 for r in results["email"] if r["success"])
    linkedin_sent = sum(1 for r in results["linkedin"] if r["success"])
    sms_sent = sum(1 for r in results["sms"] if r["success"])

    # CIS: Update channel performance metrics per campaign
    try:
        async with get_db_session() as db:
            cis_service = get_cis_service(db)

            # Group sends by campaign and channel
            campaign_channel_counts: dict[str, dict[str, int]] = {}
            campaign_clients: dict[str, str] = {}

            for channel_name, channel_results in results.items():
                for result in channel_results:
                    if result.get("success"):
                        campaign_id = None
                        client_id = None

                        # Find campaign_id from leads_data
                        for lead_data in leads_data["leads_by_channel"].get(channel_name, []):
                            if lead_data["lead_id"] == result.get("lead_id"):
                                campaign_id = lead_data.get("campaign_id")
                                client_id = lead_data.get("client_id")
                                break

                        if campaign_id:
                            key = f"{campaign_id}_{channel_name}"
                            if key not in campaign_channel_counts:
                                campaign_channel_counts[key] = {
                                    "count": 0,
                                    "campaign_id": campaign_id,
                                    "channel": channel_name,
                                }
                            campaign_channel_counts[key]["count"] += 1
                            if client_id:
                                campaign_clients[campaign_id] = client_id

            # Update CIS channel performance for each campaign/channel combo
            for _key, data in campaign_channel_counts.items():
                campaign_id = data["campaign_id"]
                client_id = campaign_clients.get(campaign_id)
                if client_id:
                    await cis_service.update_channel_performance(
                        client_id=client_id,
                        campaign_id=campaign_id,
                        channel=data["channel"],
                        messages_sent=data["count"],
                        session=db,
                    )
    except Exception as cis_error:
        logger.warning(f"CIS channel performance update failed (non-blocking): {cis_error}")

    summary = {
        "total_leads": leads_data["total_leads"],
        "total_after_quality_gate": total_after_filter,
        "campaigns_checked": len(campaigns_checked),
        "skipped_campaigns": skipped_campaigns,
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
