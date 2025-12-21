"""
FILE: tests/fixtures/database_fixtures.py
PURPOSE: Database model fixtures for testing
PHASE: 9 (Integration Testing)
TASK: TST-002
"""

import uuid
from datetime import datetime, timedelta
from typing import Any


# ============================================================================
# Client Fixtures
# ============================================================================

def create_test_client(
    name: str = "Test Agency",
    tier: str = "velocity",
    subscription_status: str = "active",
    credits: int = 5000,
    permission_mode: str = "co_pilot",
) -> dict[str, Any]:
    """Create a test client fixture."""
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "tier": tier,
        "subscription_status": subscription_status,
        "credits_remaining": credits,
        "credits_reset_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "default_permission_mode": permission_mode,
        "stripe_customer_id": f"cus_{uuid.uuid4().hex[:14]}",
        "stripe_subscription_id": f"sub_{uuid.uuid4().hex[:14]}",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "deleted_at": None,
    }


def create_inactive_client() -> dict[str, Any]:
    """Create a client with inactive subscription."""
    client = create_test_client(name="Inactive Agency")
    client["subscription_status"] = "cancelled"
    client["credits_remaining"] = 0
    return client


def create_past_due_client() -> dict[str, Any]:
    """Create a client with past due subscription."""
    client = create_test_client(name="Past Due Agency")
    client["subscription_status"] = "past_due"
    return client


def create_ignition_client() -> dict[str, Any]:
    """Create an Ignition tier client (lowest)."""
    return create_test_client(
        name="Ignition Agency",
        tier="ignition",
        credits=1250,
    )


def create_dominance_client() -> dict[str, Any]:
    """Create a Dominance tier client (highest)."""
    return create_test_client(
        name="Dominance Agency",
        tier="dominance",
        credits=10000,
    )


# ============================================================================
# User Fixtures
# ============================================================================

def create_test_user(
    email: str = "test@example.com",
    full_name: str = "Test User",
) -> dict[str, Any]:
    """Create a test user fixture."""
    return {
        "id": str(uuid.uuid4()),
        "email": email,
        "full_name": full_name,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Membership Fixtures
# ============================================================================

def create_test_membership(
    user_id: str,
    client_id: str,
    role: str = "admin",
    accepted: bool = True,
) -> dict[str, Any]:
    """Create a test membership fixture."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "client_id": client_id,
        "role": role,
        "invited_by": None,
        "accepted_at": datetime.utcnow().isoformat() if accepted else None,
        "created_at": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Campaign Fixtures
# ============================================================================

def create_test_campaign(
    client_id: str,
    name: str = "Test Campaign Q1 2025",
    status: str = "active",
    permission_mode: str = "co_pilot",
    daily_limit: int = 50,
) -> dict[str, Any]:
    """Create a test campaign fixture."""
    return {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "name": name,
        "description": "Tech startups in Australia",
        "status": status,
        "permission_mode": permission_mode,
        "daily_limit": daily_limit,
        "allocation_email": 60,
        "allocation_sms": 20,
        "allocation_linkedin": 20,
        "allocation_voice": 0,
        "allocation_mail": 0,
        "sequence_steps": [
            {"step": 1, "channel": "email", "delay_days": 0, "template_id": "intro_v1"},
            {"step": 2, "channel": "email", "delay_days": 3, "template_id": "followup_v1"},
            {"step": 3, "channel": "linkedin", "delay_days": 5, "template_id": "connection_v1"},
            {"step": 4, "channel": "sms", "delay_days": 7, "template_id": "sms_v1"},
            {"step": 5, "channel": "email", "delay_days": 10, "template_id": "breakup_v1"},
        ],
        "target_settings": {
            "industries": ["Technology", "SaaS", "Fintech"],
            "titles": ["CEO", "CTO", "Founder", "VP Engineering"],
            "company_sizes": ["10-50", "51-200"],
            "locations": ["Sydney", "Melbourne", "Brisbane"],
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "deleted_at": None,
    }


def create_draft_campaign(client_id: str) -> dict[str, Any]:
    """Create a draft campaign."""
    return create_test_campaign(client_id, name="Draft Campaign", status="draft")


def create_paused_campaign(client_id: str) -> dict[str, Any]:
    """Create a paused campaign."""
    return create_test_campaign(client_id, name="Paused Campaign", status="paused")


def create_autopilot_campaign(client_id: str) -> dict[str, Any]:
    """Create an autopilot campaign."""
    return create_test_campaign(
        client_id,
        name="Autopilot Campaign",
        permission_mode="autopilot",
    )


def create_manual_campaign(client_id: str) -> dict[str, Any]:
    """Create a manual campaign."""
    return create_test_campaign(
        client_id,
        name="Manual Campaign",
        permission_mode="manual",
    )


# ============================================================================
# Lead Fixtures
# ============================================================================

def create_test_lead(
    client_id: str,
    campaign_id: str,
    email: str = "lead@techcompany.io",
    als_score: int = 82,
    als_tier: str = "warm",
    status: str = "enriched",
) -> dict[str, Any]:
    """Create a test lead fixture."""
    return {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "campaign_id": campaign_id,
        "email": email,
        "first_name": "Jane",
        "last_name": "Smith",
        "title": "Chief Technology Officer",
        "company_name": "TechCompany",
        "company_domain": "techcompany.io",
        "phone": "+61412345678",
        "linkedin_url": "https://linkedin.com/in/janesmith",
        "status": status,
        "als_score": als_score,
        "als_tier": als_tier,
        "als_data_quality": 90,
        "als_authority": 85,
        "als_company_fit": 80,
        "als_timing": 75,
        "als_risk": 80,
        "enrichment_data": {
            "industry": "Technology",
            "company_size": "51-200",
            "funding": "Series A",
            "location": "Sydney, Australia",
            "technologies": ["AWS", "Python", "React"],
        },
        "sequence_step": 1,
        "last_contacted_at": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "deleted_at": None,
    }


def create_hot_lead(client_id: str, campaign_id: str) -> dict[str, Any]:
    """Create a hot lead (ALS 85+)."""
    lead = create_test_lead(
        client_id,
        campaign_id,
        email="hot.lead@bigcompany.io",
        als_score=92,
        als_tier="hot",
    )
    lead["first_name"] = "Michael"
    lead["last_name"] = "CEO"
    lead["title"] = "Chief Executive Officer"
    lead["als_data_quality"] = 95
    lead["als_authority"] = 98
    lead["als_company_fit"] = 92
    lead["als_timing"] = 88
    lead["als_risk"] = 90
    return lead


def create_warm_lead(client_id: str, campaign_id: str) -> dict[str, Any]:
    """Create a warm lead (ALS 60-84)."""
    return create_test_lead(
        client_id,
        campaign_id,
        email="warm.lead@mediumcompany.io",
        als_score=72,
        als_tier="warm",
    )


def create_cool_lead(client_id: str, campaign_id: str) -> dict[str, Any]:
    """Create a cool lead (ALS 35-59)."""
    lead = create_test_lead(
        client_id,
        campaign_id,
        email="cool.lead@smallcompany.io",
        als_score=48,
        als_tier="cool",
    )
    lead["als_data_quality"] = 60
    lead["als_authority"] = 50
    lead["als_company_fit"] = 45
    lead["als_timing"] = 40
    lead["als_risk"] = 45
    return lead


def create_cold_lead(client_id: str, campaign_id: str) -> dict[str, Any]:
    """Create a cold lead (ALS 20-34)."""
    lead = create_test_lead(
        client_id,
        campaign_id,
        email="cold.lead@tinycompany.io",
        als_score=28,
        als_tier="cold",
    )
    lead["als_data_quality"] = 40
    lead["als_authority"] = 30
    lead["als_company_fit"] = 25
    lead["als_timing"] = 20
    lead["als_risk"] = 25
    return lead


def create_dead_lead(client_id: str, campaign_id: str) -> dict[str, Any]:
    """Create a dead lead (ALS 0-19)."""
    lead = create_test_lead(
        client_id,
        campaign_id,
        email="dead.lead@defunct.io",
        als_score=12,
        als_tier="dead",
    )
    lead["als_data_quality"] = 20
    lead["als_authority"] = 15
    lead["als_company_fit"] = 10
    lead["als_timing"] = 5
    lead["als_risk"] = 10
    return lead


def create_new_lead(client_id: str, campaign_id: str) -> dict[str, Any]:
    """Create a new lead (not enriched)."""
    return create_test_lead(
        client_id,
        campaign_id,
        email="new.lead@unknown.io",
        als_score=0,
        als_tier="dead",
        status="new",
    )


def create_in_sequence_lead(client_id: str, campaign_id: str, step: int = 2) -> dict[str, Any]:
    """Create a lead in sequence."""
    lead = create_test_lead(
        client_id,
        campaign_id,
        email="sequence.lead@company.io",
        status="in_sequence",
    )
    lead["sequence_step"] = step
    lead["last_contacted_at"] = (datetime.utcnow() - timedelta(days=3)).isoformat()
    return lead


def create_converted_lead(client_id: str, campaign_id: str) -> dict[str, Any]:
    """Create a converted lead."""
    lead = create_test_lead(
        client_id,
        campaign_id,
        email="converted.lead@company.io",
        als_score=88,
        als_tier="hot",
        status="converted",
    )
    lead["sequence_step"] = 3
    return lead


def create_unsubscribed_lead(client_id: str, campaign_id: str) -> dict[str, Any]:
    """Create an unsubscribed lead."""
    return create_test_lead(
        client_id,
        campaign_id,
        email="unsubscribed@company.io",
        status="unsubscribed",
    )


# ============================================================================
# Activity Fixtures
# ============================================================================

def create_test_activity(
    lead_id: str,
    channel: str = "email",
    direction: str = "outbound",
    action: str = "sent",
) -> dict[str, Any]:
    """Create a test activity fixture."""
    return {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "channel": channel,
        "direction": direction,
        "action": action,
        "subject": "Quick question about TechCompany" if channel == "email" else None,
        "body": "Hi Jane, I noticed TechCompany is expanding...",
        "provider_message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "metadata": {
            "template_id": "intro_v1",
            "personalization_score": 0.85,
            "sequence_step": 1,
        },
        "created_at": datetime.utcnow().isoformat(),
    }


def create_email_sent_activity(lead_id: str) -> dict[str, Any]:
    """Create an email sent activity."""
    return create_test_activity(lead_id, "email", "outbound", "sent")


def create_email_opened_activity(lead_id: str) -> dict[str, Any]:
    """Create an email opened activity."""
    return create_test_activity(lead_id, "email", "outbound", "opened")


def create_email_reply_activity(lead_id: str) -> dict[str, Any]:
    """Create an inbound email reply activity."""
    activity = create_test_activity(lead_id, "email", "inbound", "received")
    activity["body"] = "Thanks for reaching out! I'd love to learn more."
    activity["metadata"]["intent"] = "interested"
    activity["metadata"]["confidence"] = 0.92
    return activity


def create_sms_sent_activity(lead_id: str) -> dict[str, Any]:
    """Create an SMS sent activity."""
    activity = create_test_activity(lead_id, "sms", "outbound", "sent")
    activity["body"] = "Hi Jane, quick Q about TechCompany. Worth 5 min chat?"
    activity["subject"] = None
    return activity


def create_linkedin_connection_activity(lead_id: str) -> dict[str, Any]:
    """Create a LinkedIn connection request activity."""
    activity = create_test_activity(lead_id, "linkedin", "outbound", "connection_request")
    activity["body"] = "Hi Jane, I'd love to connect and discuss AI trends..."
    activity["subject"] = None
    return activity


def create_voice_call_activity(lead_id: str) -> dict[str, Any]:
    """Create a voice call activity."""
    activity = create_test_activity(lead_id, "voice", "outbound", "call_initiated")
    activity["metadata"]["call_id"] = f"call_{uuid.uuid4().hex[:12]}"
    activity["metadata"]["duration_seconds"] = 180
    activity["metadata"]["outcome"] = "interested"
    return activity


# ============================================================================
# Resource Fixtures
# ============================================================================

def create_email_resource(client_id: str) -> dict[str, Any]:
    """Create an email resource (sending account)."""
    return {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "resource_type": "email",
        "name": "Primary Email Account",
        "identifier": "outreach@agency.com",
        "daily_limit": 50,
        "current_usage": 0,
        "is_active": True,
        "metadata": {
            "domain": "agency.com",
            "warmup_complete": True,
        },
        "created_at": datetime.utcnow().isoformat(),
    }


def create_phone_resource(client_id: str) -> dict[str, Any]:
    """Create a phone resource (Twilio number)."""
    return {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "resource_type": "phone",
        "name": "Primary SMS Number",
        "identifier": "+61499999999",
        "daily_limit": 100,
        "current_usage": 0,
        "is_active": True,
        "metadata": {
            "provider": "twilio",
            "capabilities": ["sms", "voice"],
        },
        "created_at": datetime.utcnow().isoformat(),
    }


def create_linkedin_resource(client_id: str) -> dict[str, Any]:
    """Create a LinkedIn resource (HeyReach seat)."""
    return {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "resource_type": "linkedin",
        "name": "LinkedIn Seat 1",
        "identifier": "seat_001",
        "daily_limit": 17,
        "current_usage": 0,
        "is_active": True,
        "metadata": {
            "provider": "heyreach",
            "profile_url": "https://linkedin.com/in/agencyprofile",
        },
        "created_at": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Batch Creation Helpers
# ============================================================================

def create_lead_batch(
    client_id: str,
    campaign_id: str,
    count: int = 10,
    tier_distribution: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Create a batch of leads with tier distribution."""
    if tier_distribution is None:
        tier_distribution = {"hot": 2, "warm": 4, "cool": 3, "cold": 1}

    leads = []
    lead_num = 0

    for tier, tier_count in tier_distribution.items():
        for i in range(tier_count):
            lead_num += 1
            if tier == "hot":
                lead = create_hot_lead(client_id, campaign_id)
            elif tier == "warm":
                lead = create_warm_lead(client_id, campaign_id)
            elif tier == "cool":
                lead = create_cool_lead(client_id, campaign_id)
            else:
                lead = create_cold_lead(client_id, campaign_id)

            lead["email"] = f"lead{lead_num}@company{lead_num}.io"
            leads.append(lead)

    return leads[:count]


# ============================================================================
# Verification Checklist
# ============================================================================
# [x] Contract comment at top
# [x] Client fixtures (active, inactive, past_due, all tiers)
# [x] User and membership fixtures
# [x] Campaign fixtures (active, draft, paused, all permission modes)
# [x] Lead fixtures (all ALS tiers: hot, warm, cool, cold, dead)
# [x] Lead status fixtures (new, enriched, in_sequence, converted, unsubscribed)
# [x] Activity fixtures (all channels and directions)
# [x] Resource fixtures (email, phone, linkedin)
# [x] Batch creation helpers
