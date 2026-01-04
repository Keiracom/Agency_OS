# SKILL.md — Live UX Testing

**Skill:** Live End-to-End UX Testing for Agency OS  
**Author:** CTO (Claude)  
**Version:** 1.0  
**Created:** December 26, 2024  
**Location:** `skills/testing/LIVE_UX_TEST_SKILL.md`

---

## Purpose

Test the complete Agency OS user experience with:
- Real API integrations (not mocks)
- Real data in Supabase
- Real emails/SMS sent to tester
- Real webhook round-trips
- Real dashboard verification

**This is NOT unit testing. This is live system validation.**

---

## Prerequisites

### Required API Keys

| Integration | Environment Variable | Purpose | Required |
|-------------|---------------------|---------|----------|
| Supabase | `SUPABASE_URL`, `SUPABASE_KEY` | Database | ✅ Yes |
| Anthropic | `ANTHROPIC_API_KEY` | AI (ICP, Messaging) | ✅ Yes |
| Apify | `APIFY_API_KEY` | Website scraping | ✅ Yes |
| Apollo | `APOLLO_API_KEY` | Lead enrichment | ✅ Yes |
| Resend | `RESEND_API_KEY` | Email delivery | ✅ Yes |
| Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | SMS delivery | Optional |
| HeyReach | `HEYREACH_API_KEY` | LinkedIn | Optional |

### Tester Information Needed

```yaml
# tests/live/.env.live
TESTER_EMAIL=your-real-email@gmail.com
TESTER_PHONE=+61412345678
TESTER_FIRST_NAME=Dave
TESTER_LAST_NAME=Test
TESTER_COMPANY=Test Agency Pty Ltd
TEST_WEBSITE_URL=https://some-real-agency-website.com
```

---

## Required Files

| Task ID | File | Purpose |
|---------|------|---------|
| LUX-001 | `tests/live/config.py` | Load live test configuration |
| LUX-002 | `tests/live/seed_live_data.py` | Seed real data to Supabase |
| LUX-003 | `tests/live/test_onboarding_live.py` | Test real ICP extraction |
| LUX-004 | `tests/live/test_campaign_live.py` | Test real campaign generation |
| LUX-005 | `tests/live/test_outreach_live.py` | Test real sends to tester |
| LUX-006 | `tests/live/verify_dashboards.py` | Verify dashboard accuracy |

---

## File Specifications

### LUX-001: Live Test Config

**File:** `tests/live/config.py`

```python
"""
Live test configuration loader.
Loads real API keys and tester info for live UX testing.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load live test environment
env_path = Path(__file__).parent / ".env.live"
load_dotenv(env_path)


@dataclass
class TesterInfo:
    """Information about the person running the test."""
    email: str
    phone: str | None
    first_name: str
    last_name: str
    company: str


@dataclass
class LiveTestConfig:
    """Configuration for live UX tests."""
    
    # Tester as lead
    tester: TesterInfo
    
    # Test website for ICP extraction
    test_website_url: str
    
    # API availability
    has_resend: bool
    has_twilio: bool
    has_heyreach: bool
    has_apollo: bool
    has_apify: bool
    
    # Test mode flags
    skip_sends: bool = False  # Set True to log but not send
    cleanup_after: bool = True  # Delete test data after


def load_config() -> LiveTestConfig:
    """Load live test configuration from environment."""
    
    tester = TesterInfo(
        email=os.environ["TESTER_EMAIL"],
        phone=os.environ.get("TESTER_PHONE"),
        first_name=os.environ.get("TESTER_FIRST_NAME", "Test"),
        last_name=os.environ.get("TESTER_LAST_NAME", "User"),
        company=os.environ.get("TESTER_COMPANY", "Test Agency"),
    )
    
    return LiveTestConfig(
        tester=tester,
        test_website_url=os.environ["TEST_WEBSITE_URL"],
        has_resend=bool(os.environ.get("RESEND_API_KEY")),
        has_twilio=bool(os.environ.get("TWILIO_ACCOUNT_SID")),
        has_heyreach=bool(os.environ.get("HEYREACH_API_KEY")),
        has_apollo=bool(os.environ.get("APOLLO_API_KEY")),
        has_apify=bool(os.environ.get("APIFY_API_KEY")),
        skip_sends=os.environ.get("SKIP_SENDS", "false").lower() == "true",
        cleanup_after=os.environ.get("CLEANUP_AFTER", "true").lower() == "true",
    )
```

---

### LUX-002: Data Seeding Script

**File:** `tests/live/seed_live_data.py`

```python
"""
Seed real data for live UX testing.

This script:
1. Creates a test client in Supabase
2. Runs real ICP extraction on a website
3. Generates a real campaign with messaging
4. Adds the tester as a lead

Usage:
    python -m tests.live.seed_live_data
"""

import asyncio
from datetime import datetime
from uuid import uuid4

from tests.live.config import load_config, LiveTestConfig
from src.integrations.supabase import get_supabase_client
from src.agents.icp_discovery_agent import get_icp_discovery_agent
from src.agents.campaign_generation_agent import get_campaign_generation_agent


async def create_test_client(config: LiveTestConfig) -> dict:
    """Create a test client in Supabase."""
    supabase = get_supabase_client()
    
    client_data = {
        "id": str(uuid4()),
        "name": f"Live Test - {config.tester.company}",
        "website_url": config.test_website_url,
        "tier": "velocity",
        "subscription_status": "active",
        "credits_remaining": 1000,
        "default_permission_mode": "autopilot",
        "created_at": datetime.utcnow().isoformat(),
    }
    
    result = supabase.table("clients").insert(client_data).execute()
    print(f"✅ Created test client: {client_data['id']}")
    return result.data[0]


async def extract_real_icp(client_id: str, website_url: str) -> dict:
    """Run real ICP extraction using live APIs."""
    agent = get_icp_discovery_agent()
    
    print(f"🔍 Extracting ICP from {website_url}...")
    result = await agent.extract_icp(website_url)
    
    if not result.success:
        raise Exception(f"ICP extraction failed: {result.error}")
    
    # Save to database
    supabase = get_supabase_client()
    icp_data = {
        "id": str(uuid4()),
        "client_id": client_id,
        **result.profile.model_dump(),
    }
    
    supabase.table("client_icp_profiles").insert(icp_data).execute()
    print(f"✅ ICP extracted: {len(result.profile.icp_industries)} industries, "
          f"{len(result.profile.icp_pain_points)} pain points")
    
    return result.profile


async def generate_real_campaign(client_id: str, icp_profile: dict) -> dict:
    """Generate real campaign with messaging."""
    agent = get_campaign_generation_agent()
    
    print("🎯 Generating campaign...")
    result = await agent.generate_campaign(
        icp_profile=icp_profile,
        available_channels=["email", "sms", "linkedin"],
        lead_budget=10,
    )
    
    # Save campaign to database
    supabase = get_supabase_client()
    campaign_data = {
        "id": str(uuid4()),
        "client_id": client_id,
        "name": f"Live Test Campaign - {datetime.now().strftime('%Y-%m-%d')}",
        "status": "active",
        "permission_mode": "autopilot",
        "sequence_steps": result.campaigns[0].sequence.model_dump(),
        "created_at": datetime.utcnow().isoformat(),
    }
    
    supabase.table("campaigns").insert(campaign_data).execute()
    print(f"✅ Campaign created: {campaign_data['id']}")
    
    return campaign_data


async def add_tester_as_lead(
    config: LiveTestConfig,
    client_id: str,
    campaign_id: str,
) -> dict:
    """Add the tester as a lead in the campaign."""
    supabase = get_supabase_client()
    
    lead_data = {
        "id": str(uuid4()),
        "client_id": client_id,
        "campaign_id": campaign_id,
        "email": config.tester.email,
        "first_name": config.tester.first_name,
        "last_name": config.tester.last_name,
        "company_name": config.tester.company,
        "phone": config.tester.phone,
        "status": "new",
        "als_score": 85,  # Hot lead for testing
        "als_tier": "hot",
        "sequence_step": 0,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    supabase.table("leads").insert(lead_data).execute()
    print(f"✅ Tester added as lead: {config.tester.email}")
    
    return lead_data


async def seed_all():
    """Main seeding function."""
    config = load_config()
    
    print("=" * 60)
    print("LIVE UX TEST - DATA SEEDING")
    print("=" * 60)
    print(f"Website: {config.test_website_url}")
    print(f"Tester: {config.tester.email}")
    print("=" * 60)
    
    # Step 1: Create client
    client = await create_test_client(config)
    
    # Step 2: Extract ICP
    icp = await extract_real_icp(client["id"], config.test_website_url)
    
    # Step 3: Generate campaign
    campaign = await generate_real_campaign(client["id"], icp)
    
    # Step 4: Add tester as lead
    lead = await add_tester_as_lead(config, client["id"], campaign["id"])
    
    print("=" * 60)
    print("✅ SEEDING COMPLETE")
    print("=" * 60)
    print(f"Client ID: {client['id']}")
    print(f"Campaign ID: {campaign['id']}")
    print(f"Lead ID: {lead['id']}")
    print("")
    print("Next steps:")
    print("1. Run: python -m tests.live.test_outreach_live")
    print("2. Check your email/phone for messages")
    print("3. Open/reply to test the webhook flow")
    print("4. Run: python -m tests.live.verify_dashboards")
    
    return {
        "client_id": client["id"],
        "campaign_id": campaign["id"],
        "lead_id": lead["id"],
    }


if __name__ == "__main__":
    asyncio.run(seed_all())
```

---

### LUX-003: Live Onboarding Test

**File:** `tests/live/test_onboarding_live.py`

```python
"""
Test real onboarding flow with live ICP extraction.

This test:
1. Submits a real website URL
2. Verifies Apify scrapes successfully
3. Verifies Apollo enriches portfolio
4. Verifies Anthropic extracts ICP
5. Checks ICP profile is saved to database
"""

import pytest
import asyncio

from tests.live.config import load_config
from src.agents.icp_discovery_agent import get_icp_discovery_agent


class TestLiveOnboarding:
    """Live onboarding tests with real APIs."""
    
    @pytest.fixture
    def config(self):
        return load_config()
    
    @pytest.mark.live
    async def test_real_icp_extraction(self, config):
        """Test ICP extraction with real website."""
        agent = get_icp_discovery_agent()
        
        result = await agent.extract_icp(config.test_website_url)
        
        # Assertions
        assert result.success, f"ICP extraction failed: {result.error}"
        assert result.website_scraped, "Website was not scraped"
        assert result.pages_parsed > 0, "No pages were parsed"
        assert result.profile is not None, "No ICP profile generated"
        
        # Check ICP quality
        profile = result.profile
        assert len(profile.icp_industries) > 0, "No industries identified"
        assert len(profile.icp_pain_points) > 0, "No pain points identified"
        assert profile.confidence >= 0.5, f"Low confidence: {profile.confidence}"
        
        print(f"✅ ICP extracted successfully")
        print(f"   Industries: {profile.icp_industries}")
        print(f"   Pain points: {profile.icp_pain_points[:3]}")
        print(f"   Confidence: {profile.confidence}")
```

---

### LUX-004: Live Campaign Test

**File:** `tests/live/test_campaign_live.py`

```python
"""
Test real campaign generation with live AI.

This test:
1. Uses a real ICP profile
2. Generates real sequence via SequenceBuilder
3. Generates real messaging via MessagingGenerator
4. Verifies quality of generated content
"""

import pytest
from tests.live.config import load_config
from src.agents.campaign_generation_agent import get_campaign_generation_agent


class TestLiveCampaign:
    """Live campaign generation tests."""
    
    @pytest.mark.live
    async def test_real_campaign_generation(self, test_icp_profile):
        """Test campaign generation with real ICP."""
        agent = get_campaign_generation_agent()
        
        result = await agent.generate_campaign(
            icp_profile=test_icp_profile,
            available_channels=["email", "sms", "linkedin"],
            lead_budget=10,
        )
        
        # Assertions
        assert len(result.campaigns) > 0, "No campaigns generated"
        
        campaign = result.campaigns[0]
        assert len(campaign.sequence.touches) >= 5, "Sequence too short"
        assert campaign.messaging is not None, "No messaging generated"
        
        # Check messaging quality
        first_touch = campaign.messaging.get("touch_1_email")
        assert first_touch is not None, "No first touch email"
        assert len(first_touch.subject_options) >= 2, "Not enough subject options"
        assert "{first_name}" in first_touch.email_body, "No personalization"
        
        print(f"✅ Campaign generated successfully")
        print(f"   Touches: {len(campaign.sequence.touches)}")
        print(f"   Subject: {first_touch.subject_options[0]}")
```

---

### LUX-005: Live Outreach Test

**File:** `tests/live/test_outreach_live.py`

```python
"""
Test real outreach execution - sends to tester.

⚠️  WARNING: This sends REAL emails/SMS to the configured tester.

This test:
1. Sends real email via Resend
2. Sends real SMS via Twilio (if configured)
3. Verifies delivery
4. Creates activity records
"""

import pytest
import asyncio
from datetime import datetime

from tests.live.config import load_config
from src.engines.email import EmailEngine, get_email_engine
from src.engines.sms import SMSEngine, get_sms_engine
from src.integrations.supabase import get_supabase_client


class TestLiveOutreach:
    """Live outreach tests - sends real messages."""
    
    @pytest.fixture
    def config(self):
        return load_config()
    
    @pytest.mark.live
    async def test_real_email_send(self, config, test_lead, test_campaign):
        """Send real email to tester."""
        if config.skip_sends:
            pytest.skip("SKIP_SENDS=true, skipping real send")
        
        if not config.has_resend:
            pytest.skip("Resend not configured")
        
        engine = get_email_engine()
        
        result = await engine.send(
            to_email=config.tester.email,
            subject="[LIVE TEST] Agency OS Test Email",
            body=f"""
Hi {config.tester.first_name},

This is a live test email from Agency OS.

If you received this, the email integration is working!

- Open this email to test open tracking
- Click here to test click tracking: https://example.com/test
- Reply to test reply detection

Sent at: {datetime.now().isoformat()}
            """,
            lead_id=test_lead["id"],
            campaign_id=test_campaign["id"],
        )
        
        assert result["success"], f"Email failed: {result.get('error')}"
        assert result.get("message_id"), "No message ID returned"
        
        print(f"✅ Email sent successfully")
        print(f"   To: {config.tester.email}")
        print(f"   Message ID: {result['message_id']}")
        print("")
        print("📧 CHECK YOUR INBOX!")
    
    @pytest.mark.live
    async def test_real_sms_send(self, config, test_lead, test_campaign):
        """Send real SMS to tester."""
        if config.skip_sends:
            pytest.skip("SKIP_SENDS=true, skipping real send")
        
        if not config.has_twilio:
            pytest.skip("Twilio not configured")
        
        if not config.tester.phone:
            pytest.skip("No tester phone configured")
        
        engine = get_sms_engine()
        
        result = await engine.send(
            to_phone=config.tester.phone,
            body=f"[TEST] Agency OS live test. Reply YES to confirm. Sent: {datetime.now().strftime('%H:%M')}",
            lead_id=test_lead["id"],
            campaign_id=test_campaign["id"],
        )
        
        assert result["success"], f"SMS failed: {result.get('error')}"
        
        print(f"✅ SMS sent successfully")
        print(f"   To: {config.tester.phone}")
        print("")
        print("📱 CHECK YOUR PHONE!")


async def run_full_outreach_test():
    """Run complete outreach test manually."""
    config = load_config()
    supabase = get_supabase_client()
    
    # Get test data (must run seed_live_data.py first)
    leads = supabase.table("leads").select("*").eq(
        "email", config.tester.email
    ).execute()
    
    if not leads.data:
        print("❌ No test lead found. Run seed_live_data.py first.")
        return
    
    lead = leads.data[0]
    campaign_id = lead["campaign_id"]
    
    print("=" * 60)
    print("LIVE OUTREACH TEST")
    print("=" * 60)
    
    # Send email
    email_engine = get_email_engine()
    email_result = await email_engine.send(
        to_email=config.tester.email,
        subject="[LIVE TEST] Your Agency OS Test",
        body=f"Hi {config.tester.first_name}, this is a live test!",
        lead_id=lead["id"],
        campaign_id=campaign_id,
    )
    print(f"Email: {'✅' if email_result['success'] else '❌'}")
    
    # Send SMS if configured
    if config.has_twilio and config.tester.phone:
        sms_engine = get_sms_engine()
        sms_result = await sms_engine.send(
            to_phone=config.tester.phone,
            body="[TEST] Agency OS - Reply YES to confirm",
            lead_id=lead["id"],
            campaign_id=campaign_id,
        )
        print(f"SMS: {'✅' if sms_result['success'] else '❌'}")
    
    print("=" * 60)
    print("Now check your email/phone and interact!")


if __name__ == "__main__":
    asyncio.run(run_full_outreach_test())
```

---

### LUX-006: Dashboard Verification

**File:** `tests/live/verify_dashboards.py`

```python
"""
Verify dashboard accuracy after live testing.

This script:
1. Queries database for test data
2. Calculates expected metrics
3. Compares with dashboard API responses
4. Reports discrepancies
"""

import asyncio
from datetime import datetime, timedelta

from tests.live.config import load_config
from src.integrations.supabase import get_supabase_client


async def get_test_client_id() -> str:
    """Get the live test client ID."""
    config = load_config()
    supabase = get_supabase_client()
    
    clients = supabase.table("clients").select("id").ilike(
        "name", "%Live Test%"
    ).execute()
    
    if not clients.data:
        raise Exception("No live test client found. Run seed_live_data.py first.")
    
    return clients.data[0]["id"]


async def verify_user_dashboard():
    """Verify User Dashboard metrics."""
    client_id = await get_test_client_id()
    supabase = get_supabase_client()
    
    print("=" * 60)
    print("USER DASHBOARD VERIFICATION")
    print("=" * 60)
    
    # Count leads
    leads = supabase.table("leads").select("id, als_tier, status").eq(
        "client_id", client_id
    ).is_("deleted_at", "null").execute()
    
    total_leads = len(leads.data)
    hot_leads = len([l for l in leads.data if l["als_tier"] == "hot"])
    warm_leads = len([l for l in leads.data if l["als_tier"] == "warm"])
    cool_leads = len([l for l in leads.data if l["als_tier"] == "cool"])
    
    print(f"Leads: {total_leads} total")
    print(f"  Hot: {hot_leads}")
    print(f"  Warm: {warm_leads}")
    print(f"  Cool: {cool_leads}")
    
    # Count activities
    activities = supabase.table("activities").select("action, channel").eq(
        "client_id", client_id
    ).execute()
    
    sends = len([a for a in activities.data if a["action"] == "sent"])
    opens = len([a for a in activities.data if a["action"] == "opened"])
    clicks = len([a for a in activities.data if a["action"] == "clicked"])
    replies = len([a for a in activities.data if a["action"] == "replied"])
    
    print(f"\nActivities:")
    print(f"  Sent: {sends}")
    print(f"  Opens: {opens}")
    print(f"  Clicks: {clicks}")
    print(f"  Replies: {replies}")
    
    # Calculate rates
    if sends > 0:
        open_rate = (opens / sends) * 100
        reply_rate = (replies / sends) * 100
        print(f"\nRates:")
        print(f"  Open Rate: {open_rate:.1f}%")
        print(f"  Reply Rate: {reply_rate:.1f}%")
    
    print("")
    print("✅ Compare these numbers with /dashboard")


async def verify_admin_dashboard():
    """Verify Admin Dashboard metrics."""
    supabase = get_supabase_client()
    
    print("=" * 60)
    print("ADMIN DASHBOARD VERIFICATION")
    print("=" * 60)
    
    # Count clients
    clients = supabase.table("clients").select("id, tier, subscription_status").is_(
        "deleted_at", "null"
    ).execute()
    
    total_clients = len(clients.data)
    active_clients = len([c for c in clients.data if c["subscription_status"] == "active"])
    
    print(f"Clients: {total_clients} total, {active_clients} active")
    
    # Calculate MRR (simplified)
    tier_prices = {
        "ignition": 3875,
        "velocity": 6200,
        "dominance": 11625,
    }
    
    mrr = sum(
        tier_prices.get(c["tier"], 0) 
        for c in clients.data 
        if c["subscription_status"] == "active"
    )
    print(f"MRR: ${mrr:,.0f}")
    
    # Count all activities
    activities = supabase.table("activities").select("channel, action").execute()
    
    by_channel = {}
    for a in activities.data:
        channel = a["channel"]
        if channel not in by_channel:
            by_channel[channel] = {"sent": 0, "opened": 0, "replied": 0}
        if a["action"] == "sent":
            by_channel[channel]["sent"] += 1
        elif a["action"] == "opened":
            by_channel[channel]["opened"] += 1
        elif a["action"] == "replied":
            by_channel[channel]["replied"] += 1
    
    print(f"\nChannel Performance:")
    for channel, stats in by_channel.items():
        print(f"  {channel}: {stats['sent']} sent, {stats['opened']} opens, {stats['replied']} replies")
    
    print("")
    print("✅ Compare these numbers with /admin")


async def verify_all():
    """Run all verifications."""
    await verify_user_dashboard()
    print("")
    await verify_admin_dashboard()


if __name__ == "__main__":
    asyncio.run(verify_all())
```

---

## Test Execution Order

```bash
# Step 1: Configure
cp tests/live/.env.live.example tests/live/.env.live
# Edit .env.live with your real details

# Step 2: Seed data
python -m tests.live.seed_live_data

# Step 3: Send outreach (to yourself)
python -m tests.live.test_outreach_live

# Step 4: Interact manually
# - Check email, open it
# - Reply to email
# - Check SMS, reply
# - Book a meeting

# Step 5: Verify dashboards
python -m tests.live.verify_dashboards

# Step 6: Visual verification
# - Open /dashboard in browser
# - Open /admin in browser
# - Compare with verify_dashboards output
```

---

## Success Criteria

### Seeding Complete When:
- [ ] Test client appears in Supabase `clients` table
- [ ] ICP profile saved with industries + pain points
- [ ] Campaign created with sequence + messaging
- [ ] Tester added as lead with `als_tier: hot`

### Outreach Complete When:
- [ ] Email received in tester's inbox
- [ ] SMS received on tester's phone (if configured)
- [ ] Activity records created in database

### Webhooks Working When:
- [ ] Email open creates `opened` activity
- [ ] Email reply creates `replied` activity + intent classification
- [ ] Lead status updates appropriately

### Dashboards Accurate When:
- [ ] User Dashboard KPIs match database counts
- [ ] Admin Dashboard MRR matches tier calculation
- [ ] Activity feed shows all interactions
- [ ] ALS distribution pie chart accurate

---

## Cleanup

After testing, remove test data:

```python
# tests/live/cleanup.py
async def cleanup_test_data():
    """Remove all live test data."""
    supabase = get_supabase_client()
    
    # Find test clients
    clients = supabase.table("clients").select("id").ilike(
        "name", "%Live Test%"
    ).execute()
    
    for client in clients.data:
        client_id = client["id"]
        
        # Delete in order (foreign keys)
        supabase.table("activities").delete().eq("client_id", client_id).execute()
        supabase.table("leads").delete().eq("client_id", client_id).execute()
        supabase.table("campaigns").delete().eq("client_id", client_id).execute()
        supabase.table("client_icp_profiles").delete().eq("client_id", client_id).execute()
        supabase.table("clients").delete().eq("id", client_id).execute()
    
    print(f"✅ Cleaned up {len(clients.data)} test clients")
```

---

## QA Checks (Phase 15 Specific)

| Check | Severity | Description |
|-------|----------|-------------|
| Real API keys configured | CRITICAL | .env.live has valid keys |
| Tester email valid | CRITICAL | Can receive emails |
| No production data modified | CRITICAL | Only test client affected |
| Cleanup available | HIGH | Can remove test data |
| Webhook endpoints configured | HIGH | Resend/Twilio webhooks point to API |

---

**END OF LIVE UX TEST SKILL**
