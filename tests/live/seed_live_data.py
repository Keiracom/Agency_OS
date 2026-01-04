"""
FILE: tests/live/seed_live_data.py
PURPOSE: Seed test data for live UX testing
PHASE: 15 (Live UX Testing)
TASK: LUX-002

This script creates real test data in the production database:
1. Creates a test client with subscription
2. Creates a test user with membership
3. Runs ICP extraction on a real website
4. Generates a campaign with AI

IMPORTANT: This creates REAL data. Use cleanup functions when done.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Optional

from tests.live.config import get_config, require_valid_config


async def create_test_client(supabase_client) -> dict:
    """Create a test client in the database."""
    config = get_config()

    client_data = {
        "id": str(uuid4()),
        "name": config.test_client_name,
        "tier": config.test_client_tier,
        "subscription_status": "active",
        "credits_remaining": 10000,
        "credits_reset_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "default_permission_mode": "co_pilot",
        "website_url": config.test_client_website,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    result = supabase_client.table("clients").insert(client_data).execute()

    if result.data:
        print(f"✅ Created test client: {client_data['name']} ({client_data['id']})")
        return result.data[0]
    else:
        raise Exception(f"Failed to create client: {result}")


async def create_test_user(supabase_client, client_id: str) -> dict:
    """Create a test user and membership."""
    config = get_config()

    # Note: In production, users are created via Supabase Auth
    # For testing, we create directly in the users table
    user_id = str(uuid4())

    user_data = {
        "id": user_id,
        "email": config.test_user_email,
        "full_name": config.test_user_name,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    # Create user
    result = supabase_client.table("users").insert(user_data).execute()
    if not result.data:
        print(f"⚠️ User may already exist: {config.test_user_email}")

    # Create membership
    membership_data = {
        "id": str(uuid4()),
        "user_id": user_id,
        "client_id": client_id,
        "role": "owner",
        "accepted_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }

    result = supabase_client.table("memberships").insert(membership_data).execute()

    if result.data:
        print(f"✅ Created test user: {config.test_user_email} with owner role")
        return {"user_id": user_id, "membership": result.data[0]}
    else:
        raise Exception(f"Failed to create membership: {result}")


async def create_test_lead(supabase_client, client_id: str, campaign_id: str) -> dict:
    """Create YOU as a test lead in the system."""
    config = get_config()

    lead_data = {
        "id": str(uuid4()),
        "client_id": client_id,
        "campaign_id": campaign_id,
        "email": config.test_lead_email,
        "phone": config.test_lead_phone or None,
        "first_name": config.test_lead_first_name,
        "last_name": config.test_lead_last_name,
        "company": config.test_lead_company,
        "title": config.test_lead_title,
        "domain": config.test_lead_email.split("@")[1] if "@" in config.test_lead_email else None,
        "status": "new",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    result = supabase_client.table("leads").insert(lead_data).execute()

    if result.data:
        print(f"✅ Created test lead: {config.test_lead_email} ({lead_data['id']})")
        return result.data[0]
    else:
        raise Exception(f"Failed to create lead: {result}")


async def create_test_campaign(supabase_client, client_id: str) -> dict:
    """Create a test campaign."""
    campaign_data = {
        "id": str(uuid4()),
        "client_id": client_id,
        "name": "Live UX Test Campaign",
        "description": "Campaign for live UX testing - verifying email/SMS delivery",
        "status": "active",
        "permission_mode": "autopilot",
        "daily_limit": 10,
        "allocation_email": 70,
        "allocation_sms": 20,
        "allocation_linkedin": 10,
        "allocation_voice": 0,
        "allocation_mail": 0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    result = supabase_client.table("campaigns").insert(campaign_data).execute()

    if result.data:
        print(f"✅ Created test campaign: {campaign_data['name']} ({campaign_data['id']})")
        return result.data[0]
    else:
        raise Exception(f"Failed to create campaign: {result}")


async def run_icp_extraction(client_id: str, website_url: str) -> dict:
    """Run real ICP extraction via the API."""
    import httpx

    config = get_config()

    if config.dry_run:
        print("⏭️ Dry run - skipping ICP extraction")
        return {"status": "skipped", "reason": "dry_run"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{config.api_base_url}/api/v1/onboarding/analyze",
            json={
                "client_id": client_id,
                "website_url": website_url,
            },
            timeout=120.0,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ ICP extraction started: job_id={result.get('job_id')}")
            return result
        else:
            print(f"❌ ICP extraction failed: {response.status_code} - {response.text}")
            return {"status": "failed", "error": response.text}


async def generate_campaign_content(client_id: str, campaign_id: str) -> dict:
    """Generate campaign content via AI."""
    import httpx

    config = get_config()

    if config.dry_run:
        print("⏭️ Dry run - skipping campaign generation")
        return {"status": "skipped", "reason": "dry_run"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{config.api_base_url}/api/v1/campaigns/generate",
            json={
                "client_id": client_id,
                "campaign_name": "Live Test Campaign",
            },
            timeout=120.0,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Campaign content generated")
            return result
        else:
            print(f"❌ Campaign generation failed: {response.status_code}")
            return {"status": "failed", "error": response.text}


async def seed_all_data() -> dict:
    """Seed all test data for live UX testing."""
    from supabase import create_client

    config = require_valid_config()
    config.print_status()

    print("\n🚀 Starting data seeding...\n")

    # Create Supabase client
    supabase = create_client(config.supabase_url, config.supabase_key)

    results = {
        "client": None,
        "user": None,
        "campaign": None,
        "lead": None,
        "icp": None,
    }

    try:
        # 1. Create test client
        results["client"] = await create_test_client(supabase)
        client_id = results["client"]["id"]

        # 2. Create test user with membership
        results["user"] = await create_test_user(supabase, client_id)

        # 3. Create test campaign
        results["campaign"] = await create_test_campaign(supabase, client_id)
        campaign_id = results["campaign"]["id"]

        # 4. Create test lead (YOU)
        results["lead"] = await create_test_lead(supabase, client_id, campaign_id)

        # 5. Run ICP extraction (optional, takes time)
        if config.test_client_website:
            results["icp"] = await run_icp_extraction(client_id, config.test_client_website)

        print("\n" + "=" * 60)
        print("✅ DATA SEEDING COMPLETE")
        print("=" * 60)
        print(f"\nClient ID: {client_id}")
        print(f"Campaign ID: {campaign_id}")
        print(f"Lead ID: {results['lead']['id']}")
        print(f"\nDashboard URL: {config.frontend_url}/dashboard")
        print(f"Lead Detail: {config.frontend_url}/dashboard/leads/{results['lead']['id']}")
        print("=" * 60 + "\n")

        return results

    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        raise


async def cleanup_test_data(client_id: str) -> None:
    """Clean up test data (soft delete)."""
    from supabase import create_client

    config = get_config()
    supabase = create_client(config.supabase_url, config.supabase_key)

    now = datetime.utcnow().isoformat()

    # Soft delete in reverse order
    print(f"\n🧹 Cleaning up test data for client {client_id}...")

    # Delete activities
    supabase.table("activities").update(
        {"deleted_at": now}
    ).eq("client_id", client_id).execute()
    print("  - Activities soft deleted")

    # Delete leads
    supabase.table("leads").update(
        {"deleted_at": now}
    ).eq("client_id", client_id).execute()
    print("  - Leads soft deleted")

    # Delete campaigns
    supabase.table("campaigns").update(
        {"deleted_at": now}
    ).eq("client_id", client_id).execute()
    print("  - Campaigns soft deleted")

    # Delete client
    supabase.table("clients").update(
        {"deleted_at": now}
    ).eq("id", client_id).execute()
    print("  - Client soft deleted")

    print("✅ Cleanup complete\n")


def main():
    """Main entry point for data seeding."""
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        if len(sys.argv) < 3:
            print("Usage: python seed_live_data.py cleanup <client_id>")
            sys.exit(1)
        client_id = sys.argv[2]
        asyncio.run(cleanup_test_data(client_id))
    else:
        asyncio.run(seed_all_data())


if __name__ == "__main__":
    main()


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Creates test client with subscription
# [x] Creates test user with membership
# [x] Creates test campaign
# [x] Creates test lead (YOU)
# [x] Optional ICP extraction
# [x] Cleanup function for soft delete
# [x] Dry run support
# [x] Prints useful URLs at end
