"""
Live UX Testing Skill for Agency OS

Test the complete Agency OS user experience with:
- Real API integrations (not mocks)
- Real data in Supabase
- Real emails/SMS sent to tester
- Real webhook round-trips
- Real dashboard verification

This is NOT unit testing. This is live system validation.

Version: 1.0
Author: CTO (Claude)
Created: December 26, 2024
Location: skills/testing/LIVE_UX_TEST_SKILL.md
"""

from typing import Dict, List
from dataclasses import dataclass


def get_instructions() -> str:
    """Return the key instructions for live UX testing."""
    return """
LIVE UX TESTING INSTRUCTIONS
============================

PURPOSE:
Test the complete Agency OS user experience with real APIs, real data,
and real sends. This is NOT unit testing - this is live system validation.

PREREQUISITES:
--------------
1. Required API keys configured:
   - SUPABASE_URL, SUPABASE_KEY (Database)
   - ANTHROPIC_API_KEY (AI for ICP, Messaging)
   - APIFY_API_KEY (Website scraping)
   - APOLLO_API_KEY (Lead enrichment)
   - RESEND_API_KEY (Email delivery)
   - Optional: TWILIO_*, HEYREACH_API_KEY

2. Tester information in tests/live/.env.live:
   - TESTER_EMAIL=your-real-email@gmail.com
   - TESTER_PHONE=+61412345678
   - TESTER_FIRST_NAME, TESTER_LAST_NAME
   - TEST_WEBSITE_URL=https://some-real-agency-website.com

TEST EXECUTION ORDER:
---------------------
1. Configure: cp tests/live/.env.live.example tests/live/.env.live
2. Seed data: python -m tests.live.seed_live_data
3. Send outreach: python -m tests.live.test_outreach_live
4. Interact manually:
   - Check email, open it
   - Reply to email
   - Check SMS, reply
   - Book a meeting
5. Verify dashboards: python -m tests.live.verify_dashboards
6. Visual verification: Open /dashboard and /admin in browser

SUCCESS CRITERIA:
-----------------
Seeding Complete When:
- [ ] Test client appears in Supabase clients table
- [ ] ICP profile saved with industries + pain points
- [ ] Campaign created with sequence + messaging
- [ ] Tester added as lead with als_tier: hot

Outreach Complete When:
- [ ] Email received in tester's inbox
- [ ] SMS received on tester's phone (if configured)
- [ ] Activity records created in database

Webhooks Working When:
- [ ] Email open creates 'opened' activity
- [ ] Email reply creates 'replied' activity + intent classification
- [ ] Lead status updates appropriately

Dashboards Accurate When:
- [ ] User Dashboard KPIs match database counts
- [ ] Admin Dashboard MRR matches tier calculation
- [ ] Activity feed shows all interactions
- [ ] ALS distribution pie chart accurate

CLEANUP:
--------
After testing, run cleanup to remove test data:
python -m tests.live.cleanup
"""


def get_code_templates() -> Dict[str, str]:
    """Return code templates for live UX testing."""
    return {
        "config": CONFIG_TEMPLATE,
        "seed_data": SEED_DATA_TEMPLATE,
        "test_outreach": TEST_OUTREACH_TEMPLATE,
        "verify_dashboards": VERIFY_DASHBOARDS_TEMPLATE,
        "cleanup": CLEANUP_TEMPLATE,
    }


def get_required_files() -> List[Dict[str, str]]:
    """Return list of required files for live UX testing."""
    return [
        {"id": "LUX-001", "file": "tests/live/config.py", "purpose": "Load live test configuration"},
        {"id": "LUX-002", "file": "tests/live/seed_live_data.py", "purpose": "Seed real data to Supabase"},
        {"id": "LUX-003", "file": "tests/live/test_onboarding_live.py", "purpose": "Test real ICP extraction"},
        {"id": "LUX-004", "file": "tests/live/test_campaign_live.py", "purpose": "Test real campaign generation"},
        {"id": "LUX-005", "file": "tests/live/test_outreach_live.py", "purpose": "Test real sends to tester"},
        {"id": "LUX-006", "file": "tests/live/verify_dashboards.py", "purpose": "Verify dashboard accuracy"},
    ]


def get_required_api_keys() -> List[Dict[str, str]]:
    """Return list of required API keys."""
    return [
        {"integration": "Supabase", "env_vars": ["SUPABASE_URL", "SUPABASE_KEY"], "required": True},
        {"integration": "Anthropic", "env_vars": ["ANTHROPIC_API_KEY"], "required": True},
        {"integration": "Apify", "env_vars": ["APIFY_API_KEY"], "required": True},
        {"integration": "Apollo", "env_vars": ["APOLLO_API_KEY"], "required": True},
        {"integration": "Resend", "env_vars": ["RESEND_API_KEY"], "required": True},
        {"integration": "Twilio", "env_vars": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"], "required": False},
        {"integration": "HeyReach", "env_vars": ["HEYREACH_API_KEY"], "required": False},
    ]


def get_tester_config_fields() -> List[Dict[str, str]]:
    """Return tester configuration fields."""
    return [
        {"field": "TESTER_EMAIL", "example": "your-real-email@gmail.com", "required": True},
        {"field": "TESTER_PHONE", "example": "+61412345678", "required": False},
        {"field": "TESTER_FIRST_NAME", "example": "Dave", "required": False},
        {"field": "TESTER_LAST_NAME", "example": "Test", "required": False},
        {"field": "TESTER_COMPANY", "example": "Test Agency Pty Ltd", "required": False},
        {"field": "TEST_WEBSITE_URL", "example": "https://some-real-agency-website.com", "required": True},
    ]


def get_qa_checks() -> List[Dict[str, str]]:
    """Return QA checks specific to live UX testing."""
    return [
        {"check": "Real API keys configured", "severity": "CRITICAL"},
        {"check": "Tester email valid", "severity": "CRITICAL"},
        {"check": "No production data modified", "severity": "CRITICAL"},
        {"check": "Cleanup available", "severity": "HIGH"},
        {"check": "Webhook endpoints configured", "severity": "HIGH"},
    ]


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
    tester: TesterInfo
    test_website_url: str
    has_resend: bool
    has_twilio: bool
    has_heyreach: bool
    has_apollo: bool
    has_apify: bool
    skip_sends: bool = False
    cleanup_after: bool = True


# =============================================================================
# CODE TEMPLATES
# =============================================================================

CONFIG_TEMPLATE = '''
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
    tester: TesterInfo
    test_website_url: str
    has_resend: bool
    has_twilio: bool
    has_heyreach: bool
    has_apollo: bool
    has_apify: bool
    skip_sends: bool = False
    cleanup_after: bool = True


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
'''

SEED_DATA_TEMPLATE = '''
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

from tests.live.config import load_config


async def create_test_client(config):
    """Create a test client in Supabase."""
    # Implementation details...
    pass


async def extract_real_icp(client_id: str, website_url: str):
    """Run real ICP extraction using live APIs."""
    # Implementation details...
    pass


async def generate_real_campaign(client_id: str, icp_profile):
    """Generate real campaign with messaging."""
    # Implementation details...
    pass


async def add_tester_as_lead(config, client_id: str, campaign_id: str):
    """Add the tester as a lead in the campaign."""
    # Implementation details...
    pass


async def seed_all():
    """Main seeding function."""
    config = load_config()

    print("=" * 60)
    print("LIVE UX TEST - DATA SEEDING")
    print("=" * 60)

    client = await create_test_client(config)
    icp = await extract_real_icp(client["id"], config.test_website_url)
    campaign = await generate_real_campaign(client["id"], icp)
    lead = await add_tester_as_lead(config, client["id"], campaign["id"])

    print("SEEDING COMPLETE")
    print(f"Client ID: {client['id']}")
    print(f"Campaign ID: {campaign['id']}")
    print(f"Lead ID: {lead['id']}")


if __name__ == "__main__":
    asyncio.run(seed_all())
'''

TEST_OUTREACH_TEMPLATE = '''
"""
Test real outreach execution - sends to tester.

WARNING: This sends REAL emails/SMS to the configured tester.

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


class TestLiveOutreach:
    """Live outreach tests - sends real messages."""

    @pytest.mark.live
    async def test_real_email_send(self, config, test_lead, test_campaign):
        """Send real email to tester."""
        if config.skip_sends:
            pytest.skip("SKIP_SENDS=true, skipping real send")

        # Send email via engine
        # Verify success
        # Check your inbox!
        pass

    @pytest.mark.live
    async def test_real_sms_send(self, config, test_lead, test_campaign):
        """Send real SMS to tester."""
        if not config.has_twilio:
            pytest.skip("Twilio not configured")

        # Send SMS via engine
        # Verify success
        # Check your phone!
        pass
'''

VERIFY_DASHBOARDS_TEMPLATE = '''
"""
Verify dashboard accuracy after live testing.

This script:
1. Queries database for test data
2. Calculates expected metrics
3. Compares with dashboard API responses
4. Reports discrepancies
"""

import asyncio


async def verify_user_dashboard():
    """Verify User Dashboard metrics."""
    print("USER DASHBOARD VERIFICATION")
    # Count leads, activities
    # Calculate rates
    # Compare with /dashboard
    pass


async def verify_admin_dashboard():
    """Verify Admin Dashboard metrics."""
    print("ADMIN DASHBOARD VERIFICATION")
    # Count clients, MRR
    # Calculate channel performance
    # Compare with /admin
    pass


async def verify_all():
    """Run all verifications."""
    await verify_user_dashboard()
    await verify_admin_dashboard()


if __name__ == "__main__":
    asyncio.run(verify_all())
'''

CLEANUP_TEMPLATE = '''
"""
Remove all live test data after testing.
"""

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

    print(f"Cleaned up {len(clients.data)} test clients")
'''


if __name__ == "__main__":
    print(get_instructions())
