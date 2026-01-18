"""
Skill: J2B.4 — LinkedIn Data Enrichment
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify Apify scrapes LinkedIn person and company profiles with posts.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "warning": "Apify LinkedIn scraping consumes credits - CEO approval required"
}

# =============================================================================
# APIFY ACTOR CONFIG
# =============================================================================

APIFY_ACTORS = {
    "linkedin_profile": {
        "actor_id": "apify/linkedin-profile-scraper",
        "fields": ["headline", "about", "connections", "experience", "education"],
        "cost_per_run": "$0.01-0.05"
    },
    "linkedin_posts": {
        "actor_id": "apify/linkedin-posts-scraper",
        "fields": ["text", "likes", "comments", "shares", "date"],
        "cost_per_run": "$0.01-0.05"
    },
    "linkedin_company": {
        "actor_id": "apify/linkedin-company-scraper",
        "fields": ["description", "specialties", "followers", "employees", "posts"],
        "cost_per_run": "$0.01-0.05"
    }
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2B.4.1",
        "part_a": "Read `src/integrations/apify.py` — verify LinkedIn person actor configuration",
        "part_b": "Check actor ID for LinkedIn profile scraper",
        "key_files": ["src/integrations/apify.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Apify integration has LinkedIn profile scraper configured",
            "expect": {
                "code_contains": ["linkedin", "profile", "scraper", "apify"]
            }
        }
    },
    {
        "id": "J2B.4.2",
        "part_a": "Verify person profile fields captured: headline, about, connections",
        "part_b": "Test scrape returns expected data structure",
        "key_files": ["src/integrations/apify.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id,
                       la.linkedin_person_data->>'headline' as headline,
                       la.linkedin_person_data->>'about' as about,
                       la.linkedin_person_data->>'connections' as connections
                FROM lead_assignments la
                WHERE la.linkedin_person_data IS NOT NULL
                ORDER BY la.linkedin_person_scraped_at DESC
                LIMIT 5;
            """,
            "expect": {
                "headline_exists": True,
                "about_exists": True
            }
        }
    },
    {
        "id": "J2B.4.3",
        "part_a": "Verify person posts scraped with engagement metrics (likes, comments)",
        "part_b": "Check posts array in scrape result",
        "key_files": ["src/integrations/apify.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id,
                       jsonb_array_length(la.linkedin_person_data->'posts') as post_count,
                       la.linkedin_person_data->'posts'->0->>'likes' as first_post_likes
                FROM lead_assignments la
                WHERE la.linkedin_person_data->'posts' IS NOT NULL
                ORDER BY la.linkedin_person_scraped_at DESC
                LIMIT 5;
            """,
            "expect": {
                "posts_array_exists": True
            }
        }
    },
    {
        "id": "J2B.4.4",
        "part_a": "Verify LinkedIn company actor configuration",
        "part_b": "Check actor ID for company profile scraper",
        "key_files": ["src/integrations/apify.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Apify integration has LinkedIn company scraper configured",
            "expect": {
                "code_contains": ["linkedin", "company", "scraper"]
            }
        }
    },
    {
        "id": "J2B.4.5",
        "part_a": "Verify company fields captured: description, specialties, followers, posts",
        "part_b": "Test company scrape returns all required fields",
        "key_files": ["src/integrations/apify.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id,
                       la.linkedin_company_data->>'description' as description,
                       la.linkedin_company_data->>'followers' as followers,
                       la.linkedin_company_data->>'specialties' as specialties
                FROM lead_assignments la
                WHERE la.linkedin_company_data IS NOT NULL
                ORDER BY la.linkedin_company_scraped_at DESC
                LIMIT 5;
            """,
            "expect": {
                "description_exists": True,
                "followers_exists": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Apify LinkedIn person actor runs successfully",
    "Person profile data captured (headline, about, connections)",
    "Person posts scraped with dates and engagement metrics",
    "Apify LinkedIn company actor runs successfully",
    "Company profile and posts captured with followers count"
]

KEY_FILES = [
    "src/integrations/apify.py",
    "src/engines/scout.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### Apify Actors")
    for actor, config in APIFY_ACTORS.items():
        lines.append(f"  {actor}: {config['actor_id']} ({config['cost_per_run']})")
        lines.append(f"    Fields: {', '.join(config['fields'])}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
