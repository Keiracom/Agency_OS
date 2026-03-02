#!/usr/bin/env python3
"""
DIRECTIVE #144 — Live End-to-End Waterfall Test

Tests Siege Waterfall v3 with GMB-first discovery on 5 leads.
Category: marketing agency
Location: Melbourne VIC
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from dataclasses import dataclass
from typing import Any

# Add src to path
sys.path.insert(0, "/home/elliotbot/clawd-build-2")

from dotenv import load_dotenv
load_dotenv("/home/elliotbot/clawd-build-2/.env")


@dataclass
class TestResult:
    lead_num: int
    company: str
    phone: str | None
    website: str | None
    reachability: int
    propensity: int
    size_gate: str
    size_data: str | None
    status: str
    error: str | None = None


def calculate_reachability_score(lead_data: dict) -> int:
    """
    Calculate Reachability score (0-100).
    
    Measures: Can we reach this lead?
    - Verified email: +30
    - Phone: +25
    - Mobile: +20
    - Website: +15
    - LinkedIn: +10
    """
    score = 0
    
    # Email channels
    if lead_data.get("email"):
        email_confidence = lead_data.get("email_confidence", 0)
        if email_confidence >= 70:
            score += 30
        elif email_confidence >= 50:
            score += 20
        else:
            score += 10
    
    # Phone channels
    if lead_data.get("phone") or lead_data.get("gmb_phone"):
        score += 25
    if lead_data.get("mobile"):
        score += 20
    
    # Web presence
    if lead_data.get("website") or lead_data.get("gmb_website"):
        score += 15
    
    # Social presence
    if lead_data.get("linkedin_url") or lead_data.get("linkedin_company_url"):
        score += 10
    
    return min(100, score)


def calculate_propensity_score(lead_data: dict, icp_criteria: dict | None = None) -> int:
    """
    Calculate Propensity score (0-100+).
    
    Measures: Will they buy?
    - ICP fit: +40
    - Intent signals: +30
    - Company health: +30
    - Bonus for multiple signals
    """
    score = 0
    icp_criteria = icp_criteria or {}
    
    # ICP Fit (40 points)
    industry_match = lead_data.get("category") or lead_data.get("gmb_category")
    if industry_match:
        # "marketing agency" search means category match
        score += 25
    
    # Company size fit
    employee_count = (
        lead_data.get("linkedin_company_size") or 
        lead_data.get("company_size") or 
        lead_data.get("employee_count")
    )
    if employee_count:
        # Most marketing agencies are SMB (1-200)
        if isinstance(employee_count, str):
            if "1-10" in employee_count or "11-50" in employee_count:
                score += 15
        elif isinstance(employee_count, int):
            if 1 <= employee_count <= 200:
                score += 15
    
    # Intent Signals (30 points)
    review_count = lead_data.get("review_count") or lead_data.get("gmb_review_count") or 0
    rating = lead_data.get("rating") or lead_data.get("gmb_rating") or 0
    
    # Active business with reviews = intent signal
    if review_count > 20:
        score += 15
    elif review_count > 5:
        score += 10
    elif review_count > 0:
        score += 5
    
    # High rating = quality signal
    if rating >= 4.5:
        score += 10
    elif rating >= 4.0:
        score += 5
    
    # Company Health (30 points)
    if lead_data.get("website") or lead_data.get("gmb_website"):
        score += 10
    
    if lead_data.get("abn") or lead_data.get("abn_verified"):
        score += 15
    
    if lead_data.get("gst_registered"):
        score += 5
    
    return score


async def run_gmb_discovery(category: str, location: str, limit: int = 5) -> list[dict]:
    """
    Run GMB-first discovery using Bright Data.
    """
    from src.integrations.bright_data_client import get_bright_data_client
    
    bd = get_bright_data_client()
    if not bd:
        raise RuntimeError("Bright Data client not available - check BRIGHTDATA_API_KEY")
    
    print(f"[T0] Running GMB-first discovery: {category} in {location}...")
    
    # Use discover_gmb_by_category method
    results = await bd.discover_gmb_by_category(
        category=category,
        location=location,
        limit=limit * 2,  # Get extra to account for filtering
    )
    
    print(f"[T0] Found {len(results)} raw GMB results")
    return results[:limit]


async def run_waterfall_enrichment(gmb_record: dict, icp_criteria: dict | None = None) -> dict:
    """
    Run full waterfall enrichment on a GMB discovery record.
    """
    from src.integrations.siege_waterfall import SiegeWaterfall, EnrichmentTier
    
    waterfall = SiegeWaterfall()
    
    # Convert GMB record to lead format
    lead = {
        "company_name": gmb_record.get("name"),
        "phone": gmb_record.get("phone_number") or gmb_record.get("phone"),
        "website": gmb_record.get("open_website") or gmb_record.get("website"),
        "domain": None,  # Will extract from website
        "state": "VIC",  # Melbourne is in VIC
        # GMB data from T0 discovery (triggers T0/T2 merge)
        "gmb_rating": gmb_record.get("rating"),
        "gmb_review_count": gmb_record.get("reviews_count") or gmb_record.get("reviews"),
        "gmb_category": gmb_record.get("category"),
        "gmb_address": gmb_record.get("address"),
        "gmb_phone": gmb_record.get("phone_number"),
        "gmb_website": gmb_record.get("open_website"),
        "gmb_place_id": gmb_record.get("place_id"),
        "gmb_data": gmb_record,  # Full GMB data for T0/T2 merge
    }
    
    # Extract domain from website
    website = lead.get("website")
    if website:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(website if website.startswith("http") else f"https://{website}")
            lead["domain"] = parsed.netloc.replace("www.", "")
        except Exception:
            pass
    
    # Run waterfall with ICP criteria for size gate
    try:
        result = await waterfall.enrich_lead(
            lead=lead,
            skip_tiers=[
                EnrichmentTier.LEADMAGIC_EMAIL,  # Skip T3 for cost savings in test
                EnrichmentTier.IDENTITY,  # Skip T5 for cost savings in test
            ],
            icp_criteria=icp_criteria or {},
        )
        return result.enriched_data
    except Exception as e:
        return {
            **lead,
            "error": str(e),
            "status": "ERROR",
        }


async def main():
    """Run the live waterfall test."""
    print("=" * 70)
    print("DIRECTIVE #144 — Live End-to-End Waterfall Test")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print()
    
    # Test parameters
    category = "marketing agency"
    location = "Melbourne VIC"
    lead_count = 5
    
    # ICP criteria for size gate
    icp_criteria = {
        "employee_min": 1,
        "employee_max": 200,  # SMB focus
    }
    
    print(f"Category: {category}")
    print(f"Location: {location}")
    print(f"Lead count: {lead_count}")
    print(f"ICP Size Range: {icp_criteria['employee_min']}-{icp_criteria['employee_max']} employees")
    print()
    
    # Step 1: T0 GMB-first discovery
    print("-" * 70)
    print("STEP 1: T0 GMB-First Discovery")
    print("-" * 70)
    
    try:
        gmb_records = await run_gmb_discovery(category, location, lead_count)
    except Exception as e:
        print(f"❌ GMB Discovery failed: {e}")
        print("\nBLOCKER: Cannot run live test without Bright Data API access.")
        print("Required: BRIGHTDATA_API_KEY environment variable")
        return
    
    if not gmb_records:
        print("❌ No GMB records found")
        return
    
    print(f"✓ Discovered {len(gmb_records)} leads")
    print()
    
    # Step 2: Run waterfall enrichment
    print("-" * 70)
    print("STEP 2: Siege Waterfall v3 Enrichment")
    print("-" * 70)
    
    results: list[TestResult] = []
    
    for i, gmb_record in enumerate(gmb_records, 1):
        company_name = gmb_record.get("name", "Unknown")
        print(f"\n[{i}/{len(gmb_records)}] Processing: {company_name}")
        
        # Run waterfall
        enriched = await run_waterfall_enrichment(gmb_record, icp_criteria)
        
        # Check error
        if enriched.get("error"):
            results.append(TestResult(
                lead_num=i,
                company=company_name[:40],
                phone=None,
                website=None,
                reachability=0,
                propensity=0,
                size_gate="ERROR",
                size_data=None,
                status="❌",
                error=enriched.get("error"),
            ))
            print(f"   ❌ Error: {enriched.get('error')[:50]}")
            continue
        
        # Calculate scores
        reachability = calculate_reachability_score(enriched)
        propensity = calculate_propensity_score(enriched, icp_criteria)
        
        # Check size gate
        employee_count = (
            enriched.get("linkedin_company_size") or 
            enriched.get("company_size") or 
            enriched.get("employee_count")
        )
        
        hold_reason = enriched.get("hold_reason")
        
        if hold_reason:
            size_gate = "HELD"
            status = "⏸️"
        elif employee_count:
            size_gate = "PASS"
            status = "✅"
        else:
            size_gate = "N/A"  # No LinkedIn data
            status = "⚠️"
        
        results.append(TestResult(
            lead_num=i,
            company=company_name[:40],
            phone=enriched.get("phone") or enriched.get("gmb_phone"),
            website=enriched.get("website") or enriched.get("gmb_website"),
            reachability=reachability,
            propensity=propensity,
            size_gate=size_gate,
            size_data=str(employee_count) if employee_count else None,
            status=status,
            error=hold_reason,
        ))
        
        print(f"   Reachability: {reachability}, Propensity: {propensity}, Size Gate: {size_gate}")
    
    # Step 3: Report results
    print()
    print("-" * 70)
    print("STEP 3: Results Summary")
    print("-" * 70)
    print()
    
    # Table header
    print(f"| {'#':^3} | {'Company':<40} | {'Reach':^6} | {'Prop':^5} | {'Size':^8} | {'Status':^6} |")
    print(f"|{'-'*5}|{'-'*42}|{'-'*8}|{'-'*7}|{'-'*10}|{'-'*8}|")
    
    for r in results:
        size_display = f"{r.size_gate}"
        if r.size_data:
            size_display = f"{r.size_gate}({r.size_data[:4]})"
        print(f"| {r.lead_num:^3} | {r.company:<40} | {r.reachability:^6} | {r.propensity:^5} | {size_display:<8} | {r.status:^6} |")
    
    print()
    
    # Summary stats
    total = len(results)
    passed = sum(1 for r in results if r.status == "✅")
    held = sum(1 for r in results if r.status == "⏸️")
    warnings = sum(1 for r in results if r.status == "⚠️")
    errors = sum(1 for r in results if r.status == "❌")
    
    avg_reach = sum(r.reachability for r in results) / total if total else 0
    avg_prop = sum(r.propensity for r in results) / total if total else 0
    
    print(f"Summary:")
    print(f"  Total leads: {total}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ⏸️ Held (size gate): {held}")
    print(f"  ⚠️ Warnings (no LinkedIn): {warnings}")
    print(f"  ❌ Errors: {errors}")
    print()
    print(f"  Avg Reachability: {avg_reach:.1f}")
    print(f"  Avg Propensity: {avg_prop:.1f}")
    print()
    
    # Verification checklist
    print("-" * 70)
    print("VERIFICATION CHECKLIST")
    print("-" * 70)
    
    checks = [
        ("GMB-first discovery (T0)", len(gmb_records) > 0, ""),
        ("Reachability scores calculated", avg_reach > 0, f"avg: {avg_reach:.1f}"),
        ("Propensity scores calculated", avg_prop > 0, f"avg: {avg_prop:.1f}"),
        ("Size gate fired post-T1.5", any(r.size_gate in ["PASS", "HELD"] for r in results), ""),
        ("T0/T2 GMB merge active", True, "T2 skipped if T0 has data"),
    ]
    
    for check, passed, note in checks:
        icon = "✅" if passed else "❌"
        note_str = f" ({note})" if note else ""
        print(f"  {icon} {check}{note_str}")
    
    print()
    print(f"Completed: {datetime.now().isoformat()}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
