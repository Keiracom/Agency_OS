#!/usr/bin/env python3
"""
DIRECTIVE #048 — 10-Lead Live Test: Full Waterfall v2.2
CEO: Dave
Date: 2026-02-18

Target: 10 Australian digital/marketing agencies
Geography: Sydney, Melbourne, Brisbane metro
Size: SME (1-50 employees)

Waterfall Architecture v2.2:
T1 → ABN lookup
T1.25 → ABR registered name normalisation
T1.5 → BD LinkedIn Company
T2 → BD GMB (async, poll until complete)
T2.5 → BD GMB Reviews (hot leads ALS ≥75 only)
T3 → Hunter.io email
T-DM0 → DataForSEO SERP → extract LinkedIn profile URLs
T-DM1 → BD LinkedIn Profile scrape per DM
T-DM2 → BD LinkedIn Posts 90d (ALS ≥70)
T-DM3 → BD X Posts 90d (ALS ≥70, skip gracefully if no handle found)

Success Metrics:
- ICP pass rate: 100%
- Tier completion rate per tier
- GMB match confidence avg ≥80%
- Email found rate ≥80%
- DM identified rate ≥70%
- Cost per lead vs $0.065 target
"""

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.expanduser("~/.config/agency-os/.env"))

import httpx

from src.integrations.abn_client import get_abn_client

# Import project modules
from src.integrations.bright_data_client import BrightDataClient
from src.services.icp_filter_service import ICPFilterService

# Constants
DIRECTIVE_TAG = "directive_048_live_test"
CITIES = ["Sydney", "Melbourne", "Brisbane"]
SEARCH_QUERIES = [
    "marketing agency",
    "digital marketing agency",
    "SEO agency",
    "social media agency",
    "advertising agency",
]

# Dataset IDs
GMB_DATASET_ID = "gd_m8ebnr0q2qlklc02fz"  # Google Maps Business Information
LINKEDIN_COMPANY_DATASET_ID = "gd_l1vikfnt1wgvvqz95w"
LINKEDIN_PEOPLE_DATASET_ID = "gd_l1viktl72bvl7bjuj0"

# Cost tracking (AUD)
COSTS = {
    "t1_abn": 0.00,
    "t1_25_normalize": 0.00,
    "t1_5_linkedin_company": 0.0015,
    "t2_gmb": 0.001,
    "t2_5_reviews": 0.0005,
    "t3_hunter_email": 0.012,
    "t_dm0_serp": 0.0015,
    "t_dm1_linkedin_profile": 0.0015,
    "t_dm2_linkedin_posts": 0.001,
    "t_dm3_x_posts": 0.001,
}


@dataclass
class TierResult:
    tier: str
    success: bool
    data: dict = field(default_factory=dict)
    cost_aud: float = 0.0
    duration_ms: int = 0
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None


@dataclass
class LeadResult:
    lead_number: int
    company_name: str
    city: str
    icp_qualified: bool
    icp_reason: str | None = None
    tier_results: list[TierResult] = field(default_factory=list)
    final_data: dict = field(default_factory=dict)
    total_cost_aud: float = 0.0
    email_found: bool = False
    dm_found: bool = False
    dm_name: str | None = None
    dm_title: str | None = None
    dm_linkedin_url: str | None = None
    posts_found: list[dict] = field(default_factory=list)
    personalisation_hooks: list[str] = field(default_factory=list)


class Directive048Test:
    """Full waterfall v2.2 test runner."""

    def __init__(self):
        self.bd_api_key = os.getenv("BRIGHTDATA_API_KEY")
        self.dataforseo_login = os.getenv("DATAFORSEO_LOGIN")
        self.dataforseo_password = os.getenv("DATAFORSEO_PASSWORD")

        self.bd_client = BrightDataClient(api_key=self.bd_api_key)
        self.abn_client = get_abn_client()
        self.icp_filter = ICPFilterService()

        self.results: list[LeadResult] = []
        self.start_time: float = 0
        self.total_cost: float = 0

    async def discover_gmb_leads(self, limit: int = 10) -> list[dict]:
        """
        T2: Discover fresh leads from Google Maps via Bright Data.
        Uses the GMB dataset with discover_by=location.
        """
        print("\n" + "="*60)
        print("PHASE 1: GMB Discovery")
        print("="*60)

        leads = []
        leads_per_city = (limit // len(CITIES)) + 1

        headers = {
            "Authorization": f"Bearer {self.bd_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            for city in CITIES:
                if len(leads) >= limit:
                    break

                query = f"marketing agency {city}"
                print(f"\n🔍 Searching: {query}")

                # Trigger GMB dataset collection
                try:
                    trigger_resp = await client.post(
                        "https://api.brightdata.com/datasets/v3/trigger",
                        params={
                            "dataset_id": GMB_DATASET_ID,
                            "type": "discover_new",
                            "discover_by": "location",
                            "notify": "false",
                            "include_errors": "true",
                        },
                        headers=headers,
                        json=[{
                            "country": "AU",
                            "keyword": query,
                            "lat": "",
                        }],
                    )
                    trigger_resp.raise_for_status()
                    snapshot_id = trigger_resp.json().get("snapshot_id")
                    print(f"   Snapshot ID: {snapshot_id}")

                except Exception as e:
                    print(f"   ❌ Trigger failed: {e}")
                    continue

                # Poll for completion
                ready = False
                for attempt in range(36):  # 3 minutes max
                    await asyncio.sleep(5)
                    try:
                        status_resp = await client.get(
                            f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
                            headers=headers,
                        )
                        status = status_resp.json().get("status")
                        if status == "ready":
                            ready = True
                            print(f"   ✅ Ready after {(attempt+1)*5}s")
                            break
                        elif status == "failed":
                            print("   ❌ Collection failed")
                            break
                    except Exception as e:
                        print(f"   ⚠️  Poll error: {e}")

                if not ready:
                    print("   ❌ Timeout waiting for results")
                    continue

                # Fetch results
                try:
                    data_resp = await client.get(
                        f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                        params={"format": "json"},
                        headers=headers,
                    )
                    results = data_resp.json()

                    # Filter and collect leads
                    for biz in results[:leads_per_city]:
                        if "error" in biz:
                            continue

                        lead = {
                            "company_name": biz.get("name"),
                            "phone": biz.get("phone_number"),
                            "website": biz.get("open_website"),
                            "address": biz.get("address"),
                            "city": city,
                            "state": "NSW" if city == "Sydney" else ("VIC" if city == "Melbourne" else "QLD"),
                            "gmb_category": biz.get("category"),
                            "gmb_all_categories": biz.get("all_categories", []),
                            "gmb_rating": biz.get("rating"),
                            "gmb_review_count": biz.get("reviews_count", 0),
                            "gmb_place_id": biz.get("place_id"),
                            "gmb_url": biz.get("url"),
                        }

                        if lead["company_name"] and len(leads) < limit:
                            leads.append(lead)
                            print(f"   📌 {lead['company_name']}")

                except Exception as e:
                    print(f"   ❌ Fetch failed: {e}")
                    continue

        print(f"\n📊 Total leads discovered: {len(leads)}")
        return leads[:limit]

    async def run_icp_filter(self, lead: dict) -> tuple[bool, str]:
        """Run ICP filter on lead."""
        qualified, details = self.icp_filter.is_icp_qualified({
            "company_name": lead.get("company_name"),
            "company_industry": lead.get("industry"),
            "categories": lead.get("gmb_all_categories"),
            "gmb_category": lead.get("gmb_category"),
        })
        return qualified, details.get("reason", "Unknown")

    async def tier1_abn(self, lead: dict) -> TierResult:
        """T1: ABN Lookup."""
        start = time.time()
        try:
            results = await self.abn_client.search_by_name(
                lead["company_name"],
                state=lead.get("state"),
            )

            if results:
                best = results[0]
                return TierResult(
                    tier="T1_ABN",
                    success=True,
                    data={
                        "abn": best.get("abn"),
                        "business_name": best.get("business_name"),
                        "trading_name": best.get("trading_name"),
                        "entity_type": best.get("entity_type"),
                        "gst_registered": best.get("gst_registered"),
                        "state": best.get("state"),
                        "postcode": best.get("postcode"),
                    },
                    cost_aud=COSTS["t1_abn"],
                    duration_ms=int((time.time() - start) * 1000),
                )
            else:
                return TierResult(
                    tier="T1_ABN",
                    success=False,
                    error="No ABN match found",
                    duration_ms=int((time.time() - start) * 1000),
                )
        except Exception as e:
            return TierResult(
                tier="T1_ABN",
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def tier1_25_normalize(self, lead: dict, abn_data: dict) -> TierResult:
        """T1.25: ABR Registered Name Normalization."""
        # This extracts trading names and business names from ABN data
        return TierResult(
            tier="T1.25_NORMALIZE",
            success=True,
            data={
                "normalized_name": abn_data.get("trading_name") or abn_data.get("business_name") or lead["company_name"],
                "legal_name": abn_data.get("business_name"),
                "trading_names": [abn_data.get("trading_name")] if abn_data.get("trading_name") else [],
            },
            cost_aud=COSTS["t1_25_normalize"],
        )

    async def tier1_5_linkedin_company(self, lead: dict) -> TierResult:
        """T1.5: Bright Data LinkedIn Company scrape."""
        start = time.time()

        # First we need to find the LinkedIn company URL via SERP
        domain = None
        website = lead.get("website")
        if website:
            from urllib.parse import urlparse
            domain = urlparse(website).netloc.replace("www.", "")

        if not domain:
            return TierResult(
                tier="T1.5_LINKEDIN_CO",
                success=False,
                skipped=True,
                skip_reason="No website/domain available",
            )

        try:
            # Use Bright Data LinkedIn Company scraper
            result = await self.bd_client.scrape_linkedin_company(
                f"https://www.linkedin.com/company/{domain}"
            )

            if result:
                return TierResult(
                    tier="T1.5_LINKEDIN_CO",
                    success=True,
                    data={
                        "linkedin_company_name": result.get("name"),
                        "linkedin_industry": result.get("industry"),
                        "linkedin_employee_count": result.get("employee_count"),
                        "linkedin_description": result.get("description"),
                        "linkedin_company_url": result.get("url"),
                    },
                    cost_aud=COSTS["t1_5_linkedin_company"],
                    duration_ms=int((time.time() - start) * 1000),
                )
            else:
                return TierResult(
                    tier="T1.5_LINKEDIN_CO",
                    success=False,
                    error="LinkedIn company not found",
                    cost_aud=COSTS["t1_5_linkedin_company"],
                    duration_ms=int((time.time() - start) * 1000),
                )
        except Exception as e:
            return TierResult(
                tier="T1.5_LINKEDIN_CO",
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def tier3_hunter_email(self, lead: dict, dm_name: str | None = None) -> TierResult:
        """T3: Hunter.io email discovery."""
        start = time.time()

        domain = None
        website = lead.get("website")
        if website:
            from urllib.parse import urlparse
            domain = urlparse(website).netloc.replace("www.", "")

        if not domain:
            return TierResult(
                tier="T3_HUNTER",
                success=False,
                skipped=True,
                skip_reason="No domain available",
            )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Domain search to find decision-makers
                resp = await client.get(
                    "https://api.hunter.io/v2/domain-search",
                    params={
                        "domain": domain,
                        "api_key": self.hunter_api_key,
                        "limit": 5,
                    },
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})

                emails = data.get("emails", [])
                if emails:
                    # Find best contact (CEO, MD, Founder, Owner priority)
                    priority_titles = ["ceo", "chief executive", "managing director", "founder", "owner", "director"]
                    best_email = None

                    for email in emails:
                        title = (email.get("position") or "").lower()
                        if any(pt in title for pt in priority_titles):
                            best_email = email
                            break

                    if not best_email and emails:
                        best_email = emails[0]

                    if best_email:
                        return TierResult(
                            tier="T3_HUNTER",
                            success=True,
                            data={
                                "email": best_email.get("value"),
                                "email_type": best_email.get("type"),
                                "email_confidence": best_email.get("confidence"),
                                "dm_first_name": best_email.get("first_name"),
                                "dm_last_name": best_email.get("last_name"),
                                "dm_position": best_email.get("position"),
                                "dm_linkedin": best_email.get("linkedin"),
                                "all_emails_found": len(emails),
                            },
                            cost_aud=COSTS["t3_hunter_email"],
                            duration_ms=int((time.time() - start) * 1000),
                        )

                return TierResult(
                    tier="T3_HUNTER",
                    success=False,
                    error="No emails found for domain",
                    cost_aud=COSTS["t3_hunter_email"],
                    duration_ms=int((time.time() - start) * 1000),
                )

        except Exception as e:
            return TierResult(
                tier="T3_HUNTER",
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def tier_dm0_serp(self, lead: dict, dm_name: str | None = None) -> TierResult:
        """T-DM0: DataForSEO SERP to find DM LinkedIn profile URLs."""
        start = time.time()

        company_name = lead.get("company_name")

        try:
            import base64
            auth = base64.b64encode(
                f"{self.dataforseo_login}:{self.dataforseo_password}".encode()
            ).decode()

            async with httpx.AsyncClient(timeout=60.0) as client:
                # Search for LinkedIn profiles at this company
                search_query = f'site:linkedin.com/in "{company_name}" CEO OR "Managing Director" OR "Founder" OR "Owner"'

                resp = await client.post(
                    "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
                    headers={
                        "Authorization": f"Basic {auth}",
                        "Content-Type": "application/json",
                    },
                    json=[{
                        "keyword": search_query,
                        "location_code": 2036,  # Australia
                        "language_code": "en",
                        "device": "desktop",
                        "depth": 10,
                    }],
                )
                resp.raise_for_status()
                data = resp.json()

                results = data.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
                linkedin_profiles = []

                for item in results:
                    url = item.get("url", "")
                    if "linkedin.com/in/" in url:
                        linkedin_profiles.append({
                            "url": url,
                            "title": item.get("title"),
                            "description": item.get("description"),
                        })

                if linkedin_profiles:
                    return TierResult(
                        tier="T-DM0_SERP",
                        success=True,
                        data={
                            "dm_linkedin_urls": [p["url"] for p in linkedin_profiles[:3]],
                            "dm_serp_results": linkedin_profiles[:3],
                        },
                        cost_aud=COSTS["t_dm0_serp"],
                        duration_ms=int((time.time() - start) * 1000),
                    )
                else:
                    return TierResult(
                        tier="T-DM0_SERP",
                        success=False,
                        error="No LinkedIn profiles found in SERP",
                        cost_aud=COSTS["t_dm0_serp"],
                        duration_ms=int((time.time() - start) * 1000),
                    )

        except Exception as e:
            return TierResult(
                tier="T-DM0_SERP",
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def tier_dm1_linkedin_profile(self, linkedin_url: str) -> TierResult:
        """T-DM1: Bright Data LinkedIn Profile scrape."""
        start = time.time()

        try:
            result = await self.bd_client.scrape_linkedin_profile(linkedin_url)

            if result:
                return TierResult(
                    tier="T-DM1_PROFILE",
                    success=True,
                    data={
                        "dm_full_name": result.get("full_name"),
                        "dm_headline": result.get("headline"),
                        "dm_current_company": result.get("current_company"),
                        "dm_location": result.get("location"),
                        "dm_summary": result.get("summary"),
                        "dm_experience": result.get("experience", [])[:3],
                    },
                    cost_aud=COSTS["t_dm1_linkedin_profile"],
                    duration_ms=int((time.time() - start) * 1000),
                )
            else:
                return TierResult(
                    tier="T-DM1_PROFILE",
                    success=False,
                    error="Profile scrape returned no data",
                    cost_aud=COSTS["t_dm1_linkedin_profile"],
                    duration_ms=int((time.time() - start) * 1000),
                )
        except Exception as e:
            return TierResult(
                tier="T-DM1_PROFILE",
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def process_lead(self, lead_number: int, lead: dict) -> LeadResult:
        """Process a single lead through the full waterfall."""
        print(f"\n{'='*60}")
        print(f"LEAD {lead_number}: {lead['company_name']}")
        print(f"City: {lead['city']} | Category: {lead.get('gmb_category')}")
        print("="*60)

        result = LeadResult(
            lead_number=lead_number,
            company_name=lead["company_name"],
            city=lead["city"],
            icp_qualified=False,
            final_data=dict(lead),
        )

        # ICP Check
        print("\n🔍 Running ICP filter...")
        icp_pass, icp_reason = await self.run_icp_filter(lead)
        result.icp_qualified = icp_pass
        result.icp_reason = icp_reason

        if not icp_pass:
            print(f"   ❌ ICP FAILED: {icp_reason}")
            print("\n   ⚠️  HALT: Non-ICP lead detected!")
            return result

        print(f"   ✅ ICP PASSED: {icp_reason}")

        # T1: ABN Lookup
        print("\n📋 T1: ABN Lookup...")
        t1_result = await self.tier1_abn(lead)
        result.tier_results.append(t1_result)
        result.total_cost_aud += t1_result.cost_aud

        if t1_result.success:
            result.final_data.update(t1_result.data)
            print(f"   ✅ ABN: {t1_result.data.get('abn')} | {t1_result.data.get('business_name')}")

            # T1.25: Normalize
            print("\n📋 T1.25: Name Normalization...")
            t1_25_result = await self.tier1_25_normalize(lead, t1_result.data)
            result.tier_results.append(t1_25_result)
            result.final_data.update(t1_25_result.data)
            print(f"   ✅ Normalized: {t1_25_result.data.get('normalized_name')}")
        else:
            print(f"   ⚠️  No ABN match: {t1_result.error}")

        # T1.5: LinkedIn Company
        print("\n🏢 T1.5: LinkedIn Company...")
        t1_5_result = await self.tier1_5_linkedin_company(lead)
        result.tier_results.append(t1_5_result)
        result.total_cost_aud += t1_5_result.cost_aud

        if t1_5_result.success:
            result.final_data.update(t1_5_result.data)
            print(f"   ✅ Industry: {t1_5_result.data.get('linkedin_industry')} | Employees: {t1_5_result.data.get('linkedin_employee_count')}")
        else:
            print(f"   ⚠️  {t1_5_result.error or t1_5_result.skip_reason}")

        # T3: Hunter Email
        print("\n📧 T3: Hunter.io Email Discovery...")
        t3_result = await self.tier3_hunter_email(lead)
        result.tier_results.append(t3_result)
        result.total_cost_aud += t3_result.cost_aud

        if t3_result.success:
            result.final_data.update(t3_result.data)
            result.email_found = True
            result.dm_name = f"{t3_result.data.get('dm_first_name', '')} {t3_result.data.get('dm_last_name', '')}".strip()
            result.dm_title = t3_result.data.get("dm_position")
            result.dm_linkedin_url = t3_result.data.get("dm_linkedin")
            print(f"   ✅ Email: {t3_result.data.get('email')}")
            print(f"      DM: {result.dm_name} ({result.dm_title})")
        else:
            print(f"   ⚠️  {t3_result.error or t3_result.skip_reason}")

        # T-DM0: SERP for LinkedIn DM profiles
        print("\n🔎 T-DM0: DataForSEO SERP (LinkedIn DM Discovery)...")
        t_dm0_result = await self.tier_dm0_serp(lead)
        result.tier_results.append(t_dm0_result)
        result.total_cost_aud += t_dm0_result.cost_aud

        dm_linkedin_url = None
        if t_dm0_result.success:
            urls = t_dm0_result.data.get("dm_linkedin_urls", [])
            if urls:
                dm_linkedin_url = urls[0]
                result.dm_linkedin_url = result.dm_linkedin_url or dm_linkedin_url
                result.dm_found = True
                print(f"   ✅ Found {len(urls)} LinkedIn profiles")
                for i, serp_r in enumerate(t_dm0_result.data.get("dm_serp_results", [])[:2]):
                    print(f"      {i+1}. {serp_r.get('title', 'Unknown')}")
        else:
            print(f"   ⚠️  {t_dm0_result.error}")

        # T-DM1: LinkedIn Profile Scrape
        if dm_linkedin_url:
            print("\n👤 T-DM1: LinkedIn Profile Scrape...")
            t_dm1_result = await self.tier_dm1_linkedin_profile(dm_linkedin_url)
            result.tier_results.append(t_dm1_result)
            result.total_cost_aud += t_dm1_result.cost_aud

            if t_dm1_result.success:
                result.final_data.update(t_dm1_result.data)
                result.dm_found = True
                result.dm_name = result.dm_name or t_dm1_result.data.get("dm_full_name")
                print(f"   ✅ {t_dm1_result.data.get('dm_full_name')}")
                print(f"      {t_dm1_result.data.get('dm_headline', '')[:60]}...")
            else:
                print(f"   ⚠️  {t_dm1_result.error}")

        # Summary
        print("\n📊 Lead Summary:")
        print(f"   Company: {result.company_name}")
        print(f"   Email: {result.final_data.get('email', 'Not found')}")
        print(f"   DM: {result.dm_name or 'Not found'} | Title: {result.dm_title or 'Unknown'}")
        print(f"   Cost: ${result.total_cost_aud:.4f} AUD")

        return result

    async def run(self):
        """Execute the full directive test."""
        self.start_time = time.time()

        print("\n" + "="*60)
        print("DIRECTIVE #048 — 10-Lead Live Test: Full Waterfall v2.2")
        print("="*60)
        print(f"Started: {datetime.now(UTC).isoformat()}")
        print("Target: 10 Australian digital/marketing agencies")
        print("Geo: Sydney, Melbourne, Brisbane")

        # Phase 1: GMB Discovery
        leads = await self.discover_gmb_leads(limit=10)

        if not leads:
            print("\n❌ HALT: No leads discovered from GMB")
            return

        # Phase 2: Process each lead
        print("\n" + "="*60)
        print("PHASE 2: Waterfall Processing")
        print("="*60)

        for i, lead in enumerate(leads, 1):
            result = await self.process_lead(i, lead)
            self.results.append(result)
            self.total_cost += result.total_cost_aud

            # Brief pause between leads
            await asyncio.sleep(1)

        # Phase 3: Generate Report
        self.generate_report()

    def generate_report(self):
        """Generate final test report."""
        wall_time = time.time() - self.start_time

        print("\n" + "="*60)
        print("DIRECTIVE #048 — FINAL REPORT")
        print("="*60)

        # Tier Hit/Miss Table
        print("\n📊 Tier Hit/Miss Table:")
        print("-" * 80)
        print(f"{'Lead':<5} {'Company':<25} {'T1':<4} {'T1.5':<5} {'T3':<4} {'DM0':<5} {'DM1':<5} {'Cost':<8}")
        print("-" * 80)

        tier_success = {"T1_ABN": 0, "T1.5_LINKEDIN_CO": 0, "T3_HUNTER": 0, "T-DM0_SERP": 0, "T-DM1_PROFILE": 0}
        icp_pass_count = 0
        email_found = 0
        dm_found = 0

        for r in self.results:
            if r.icp_qualified:
                icp_pass_count += 1
            if r.email_found:
                email_found += 1
            if r.dm_found:
                dm_found += 1

            t1 = "✓" if any(t.tier == "T1_ABN" and t.success for t in r.tier_results) else "✗"
            t15 = "✓" if any(t.tier == "T1.5_LINKEDIN_CO" and t.success for t in r.tier_results) else "✗"
            t3 = "✓" if any(t.tier == "T3_HUNTER" and t.success for t in r.tier_results) else "✗"
            dm0 = "✓" if any(t.tier == "T-DM0_SERP" and t.success for t in r.tier_results) else "✗"
            dm1 = "✓" if any(t.tier == "T-DM1_PROFILE" and t.success for t in r.tier_results) else "✗"

            if t1 == "✓":
                tier_success["T1_ABN"] += 1
            if t15 == "✓":
                tier_success["T1.5_LINKEDIN_CO"] += 1
            if t3 == "✓":
                tier_success["T3_HUNTER"] += 1
            if dm0 == "✓":
                tier_success["T-DM0_SERP"] += 1
            if dm1 == "✓":
                tier_success["T-DM1_PROFILE"] += 1

            print(f"{r.lead_number:<5} {r.company_name[:24]:<25} {t1:<4} {t15:<5} {t3:<4} {dm0:<5} {dm1:<5} ${r.total_cost_aud:.4f}")

        print("-" * 80)

        # Success Metrics
        total = len(self.results)
        print("\n📈 Success Metrics:")
        print(f"   ICP Pass Rate: {icp_pass_count}/{total} ({100*icp_pass_count/total:.0f}%) — Target: 100%")
        print(f"   Email Found Rate: {email_found}/{total} ({100*email_found/total:.0f}%) — Target: ≥80%")
        print(f"   DM Identified Rate: {dm_found}/{total} ({100*dm_found/total:.0f}%) — Target: ≥70%")

        print("\n📉 Tier Completion Rates:")
        for tier, count in tier_success.items():
            print(f"   {tier}: {count}/{total} ({100*count/total:.0f}%)")

        # Cost Analysis
        print("\n💰 Cost Analysis:")
        print(f"   Total Cost: ${self.total_cost:.4f} AUD")
        print(f"   Cost per Lead: ${self.total_cost/total:.4f} AUD")
        print("   Target: $0.065/lead")
        variance = ((self.total_cost/total) - 0.065) / 0.065 * 100
        print(f"   Variance: {variance:+.1f}%")

        # Speed
        print("\n⏱️  Speed:")
        print(f"   Total Wall-Clock Time: {wall_time:.1f}s ({wall_time/60:.1f}m)")
        print(f"   Avg per Lead: {wall_time/total:.1f}s")

        # Per-Lead Summary
        print("\n📋 Per-Lead Summary:")
        print("-" * 100)
        for r in self.results:
            print(f"\n   Lead {r.lead_number}: {r.company_name}")
            print(f"   Email: {r.final_data.get('email', 'Not found')}")
            print(f"   DM: {r.dm_name or 'Not found'} | Title: {r.dm_title or 'Unknown'}")
            if r.posts_found:
                print(f"   Post Sample: \"{r.posts_found[0].get('text', '')[:100]}...\"")
            print(f"   Personalisation Hooks: {', '.join(r.personalisation_hooks) if r.personalisation_hooks else 'None'}")

        # Final Assessment
        print("\n" + "="*60)
        print("🎯 FINAL ASSESSMENT")
        print("="*60)

        pipeline_ready = (
            icp_pass_count == total and
            email_found / total >= 0.8 and
            dm_found / total >= 0.7
        )

        if pipeline_ready:
            print("✅ Pipeline is READY for live outreach")
        else:
            print("❌ Pipeline NOT READY — see metrics above")
            if icp_pass_count < total:
                print("   ⚠️  ICP filter passed non-agency leads")
            if email_found / total < 0.8:
                print("   ⚠️  Email found rate below 80% threshold")
            if dm_found / total < 0.7:
                print("   ⚠️  DM identification rate below 70% threshold")


async def main():
    test = Directive048Test()
    await test.run()


if __name__ == "__main__":
    asyncio.run(main())
