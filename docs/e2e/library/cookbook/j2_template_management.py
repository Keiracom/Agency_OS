"""
Skill: J2.8 — Deep Research (Hot Leads)
Journey: J2 - Campaign Creation & Management
Checks: 5

Purpose: Verify deep research triggers for hot leads.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "note": "Deep research uses Apify credits - get approval before testing"
}

# =============================================================================
# DEEP RESEARCH COMPONENTS
# =============================================================================

RESEARCH_COMPONENTS = [
    {"component": "LinkedIn Profile Scrape", "source": "Apify", "data": "Recent posts, activity, connections"},
    {"component": "Company Scrape", "source": "Apify", "data": "Company updates, news, employees"},
    {"component": "Icebreaker Generation", "source": "Claude AI", "data": "Personalized opening lines"},
    {"component": "Pain Point Analysis", "source": "Claude AI", "data": "Likely challenges based on role/industry"},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2.8.1",
        "part_a": "Verify deep research trigger at ALS >= 85",
        "part_b": "Check trigger condition",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Deep research triggers at hot threshold (85+)",
            "expect": {
                "code_contains": ["85", "hot", "research", "trigger"]
            },
            "db_verify": """
                SELECT id, email, als_score, research_completed_at
                FROM leads
                WHERE als_score >= 85 AND research_completed_at IS NOT NULL
                LIMIT 5;
            """
        }
    },
    {
        "id": "J2.8.2",
        "part_a": "Read `/api/v1/leads/{id}/research` endpoint",
        "part_b": "Test endpoint",
        "key_files": ["src/api/routes/leads.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/leads/{lead_id}/research",
            "auth": True,
            "expect": {
                "status": [200, 202],
                "body_has_field": "research_id"
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/leads/{lead_id}/research' \\
  -H 'Authorization: Bearer {token}'""",
            "warning": "This endpoint consumes Apify credits - confirm before running"
        }
    },
    {
        "id": "J2.8.3",
        "part_a": "Verify LinkedIn scraping for person/company",
        "part_b": "Check Apify integration",
        "key_files": ["src/integrations/apify.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Apify integration has LinkedIn scraping methods",
            "expect": {
                "code_contains": ["linkedin", "scrape", "profile", "company"]
            },
            "manual_verify": [
                "1. Read src/integrations/apify.py",
                "2. Find scrape_linkedin_profile method",
                "3. Find scrape_linkedin_company method",
                "4. Verify they return structured data"
            ]
        }
    },
    {
        "id": "J2.8.4",
        "part_a": "Verify icebreaker generation",
        "part_b": "Check AI call for icebreakers",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Content engine generates icebreakers",
            "expect": {
                "code_contains": ["icebreaker", "generate", "personalize"]
            },
            "db_verify": """
                SELECT la.id, la.icebreakers
                FROM lead_assignments la
                WHERE la.icebreakers IS NOT NULL
                LIMIT 5;
            """
        }
    },
    {
        "id": "J2.8.5",
        "part_a": "Verify research data stored in lead_assignments",
        "part_b": "Check research_data field",
        "key_files": ["src/services/lead_allocator_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id, la.pool_lead_id,
                       la.research_data,
                       la.icebreakers,
                       la.research_completed_at
                FROM lead_assignments la
                WHERE la.research_data IS NOT NULL
                ORDER BY la.research_completed_at DESC
                LIMIT 5;
            """,
            "expect": {
                "research_data_not_null": True,
                "research_data_has_fields": ["linkedin_profile", "company_info", "recent_activity"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Deep research triggers automatically at 85+ score",
    "LinkedIn profile scraped via Apify",
    "Icebreakers generated via AI",
    "Research data stored for content personalization"
]

KEY_FILES = [
    "src/engines/scorer.py",
    "src/api/routes/leads.py",
    "src/integrations/apify.py",
    "src/engines/content.py",
    "src/services/lead_allocator_service.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append(f"- Note: {LIVE_CONFIG['note']}")
    lines.append("")
    lines.append("### Research Components")
    for comp in RESEARCH_COMPONENTS:
        lines.append(f"  {comp['component']}: {comp['source']} → {comp['data']}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("warning"):
            lines.append(f"  ⚠️ Warning: {lt['warning']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
