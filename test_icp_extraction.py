"""
Test script for ICP extraction with dilate.com.au.
Run with: python test_icp_extraction.py
"""

import asyncio
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_icp_extraction():
    """Test ICP extraction with dilate.com.au."""
    from src.agents.icp_discovery_agent import get_icp_discovery_agent

    print("=" * 60)
    print("Testing ICP Extraction with dilate.com.au")
    print("=" * 60)

    agent = get_icp_discovery_agent()

    print("\nStarting extraction...")
    result = await agent.extract_icp("https://www.dilate.com.au")

    print("\n" + "=" * 60)
    print("EXTRACTION RESULT")
    print("=" * 60)

    print(f"\nSuccess: {result.success}")
    print(f"Error: {result.error}")
    print(f"Website Scraped: {result.website_scraped}")
    print(f"Pages Parsed: {result.pages_parsed}")
    print(f"Services Found: {result.services_found}")
    print(f"Portfolio Companies Found: {result.portfolio_companies_found}")
    print(f"Industries Classified: {result.industries_classified}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"Total Tokens: {result.total_tokens}")
    print(f"Total Cost (AUD): ${result.total_cost_aud:.4f}")

    if result.profile:
        profile = result.profile
        print("\n" + "-" * 60)
        print("ICP PROFILE")
        print("-" * 60)

        print(f"\nCompany Name: {profile.company_name}")
        print(f"Website URL: {profile.website_url}")
        print(f"Confidence: {profile.confidence:.2%}")

        print(f"\nServices Offered ({len(profile.services_offered)}):")
        for svc in profile.services_offered[:10]:
            print(f"  - {svc}")

        print(f"\nPortfolio Companies ({len(profile.portfolio_companies)}):")
        for company in profile.portfolio_companies[:15]:
            print(f"  - {company}")

        print(f"\nNotable Brands ({len(profile.notable_brands)}):")
        for brand in profile.notable_brands[:10]:
            print(f"  - {brand}")

        print(f"\nICP Industries ({len(profile.icp_industries)}):")
        for industry in profile.icp_industries:
            print(f"  - {industry}")

        print(f"\nICP Company Sizes ({len(profile.icp_company_sizes)}):")
        for size in profile.icp_company_sizes:
            print(f"  - {size}")

        print(f"\nICP Locations ({len(profile.icp_locations)}):")
        for loc in profile.icp_locations:
            print(f"  - {loc}")

        print(f"\nSocial Links ({len(profile.social_links)}):")
        for platform, url in profile.social_links.items():
            print(f"  - {platform}: {url}")

        if profile.social_profiles:
            sp = profile.social_profiles
            print(f"\nSocial Profiles:")
            print(f"  Total Followers: {sp.total_social_followers:,}")
            print(f"  Platforms Found: {sp.platforms_found}")

            if sp.linkedin:
                print(f"\n  LinkedIn:")
                print(f"    Name: {sp.linkedin.name}")
                print(f"    Followers: {sp.linkedin.followers:,}" if sp.linkedin.followers else "    Followers: N/A")
                print(f"    Employees: {sp.linkedin.employee_range}")
                print(f"    Industry: {sp.linkedin.industry}")

            if sp.instagram:
                print(f"\n  Instagram:")
                print(f"    Username: {sp.instagram.username}")
                print(f"    Followers: {sp.instagram.followers:,}" if sp.instagram.followers else "    Followers: N/A")
                print(f"    Posts: {sp.instagram.posts_count}")

            if sp.facebook:
                print(f"\n  Facebook:")
                print(f"    Name: {sp.facebook.name}")
                print(f"    Followers: {sp.facebook.followers:,}" if sp.facebook.followers else "    Followers: N/A")
                print(f"    Rating: {sp.facebook.rating}")

            if sp.google_business:
                print(f"\n  Google Business:")
                print(f"    Name: {sp.google_business.name}")
                print(f"    Rating: {sp.google_business.rating}")
                print(f"    Reviews: {sp.google_business.review_count}")
                print(f"    Address: {sp.google_business.address}")

        print(f"\nPattern Description:")
        print(f"  {profile.pattern_description}")

        # Save full profile to JSON
        output_file = "test_icp_result.json"
        with open(output_file, "w") as f:
            json.dump(profile.model_dump(), f, indent=2, default=str)
        print(f"\n\nFull profile saved to: {output_file}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    # Success criteria check
    print("\n" + "-" * 60)
    print("SUCCESS CRITERIA CHECK")
    print("-" * 60)

    if result.profile:
        checks = {
            "Portfolio companies extracted": len(result.profile.portfolio_companies) > 0,
            "Social links populated": len(result.profile.social_links) > 0,
            "ICP industries populated": len(result.profile.icp_industries) > 0,
            "ICP company sizes populated": len(result.profile.icp_company_sizes) > 0,
            "Confidence > 70%": result.profile.confidence > 0.70,
        }

        for check, passed in checks.items():
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {check}")

        all_passed = all(checks.values())
        print(f"\nOverall: {'ALL CHECKS PASSED' if all_passed else 'SOME CHECKS FAILED'}")


if __name__ == "__main__":
    asyncio.run(test_icp_extraction())
