"""
Skill: J2B.1 — Apollo Search Integration
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify Apollo search integration for lead discovery and initial data population.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "warning": "Apollo API calls consume credits - get CEO approval first"
}

# =============================================================================
# APOLLO SEARCH PARAMETERS
# =============================================================================

APOLLO_SEARCH_PARAMS = {
    "required_filters": ["job_titles", "company_sizes", "industries"],
    "optional_filters": ["locations", "technologies", "keywords"],
    "max_results_per_page": 100,
    "rate_limits": {"requests_per_minute": 100, "requests_per_day": 10000}
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2B.1.1",
        "part_a": "Read `src/integrations/apollo.py` — verify search endpoint configuration",
        "part_b": "Test Apollo search API connection",
        "key_files": ["src/integrations/apollo.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Apollo integration has search_people method",
            "expect": {
                "code_contains": ["search_people", "APOLLO_API_KEY", "api.apollo.io"]
            }
        }
    },
    {
        "id": "J2B.1.2",
        "part_a": "Verify `search_people` method accepts ICP filters (title, industry, company_size)",
        "part_b": "Execute search with test ICP criteria",
        "key_files": ["src/integrations/apollo.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/leads/search",
            "auth": True,
            "body": {
                "job_titles": ["CTO", "VP Engineering"],
                "company_sizes": ["50-200"],
                "industries": ["Technology"],
                "limit": 5
            },
            "expect": {
                "status": 200,
                "body_has_field": "leads"
            },
            "warning": "Consumes Apollo credits - CEO approval required",
            "curl_command": """curl -X POST '{api_url}/api/v1/leads/search' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"job_titles": ["CTO"], "company_sizes": ["50-200"], "limit": 5}'"""
        }
    },
    {
        "id": "J2B.1.3",
        "part_a": "Verify pagination handling for large result sets",
        "part_b": "Test pagination with maxResults > 100",
        "key_files": ["src/integrations/apollo.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Apollo integration handles pagination",
            "expect": {
                "code_contains": ["page", "pagination", "total_pages", "next_page"]
            }
        }
    },
    {
        "id": "J2B.1.4",
        "part_a": "Verify rate limiting compliance (Apollo API limits)",
        "part_b": "Check rate limit headers in response",
        "key_files": ["src/integrations/apollo.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Rate limiting implemented",
            "expect": {
                "code_contains": ["rate_limit", "sleep", "retry", "429"]
            }
        }
    },
    {
        "id": "J2B.1.5",
        "part_a": "Verify search results mapped to lead_pool schema",
        "part_b": "Confirm field mapping (name, email, company, title, linkedin_url)",
        "key_files": ["src/integrations/apollo.py", "src/models/lead.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, first_name, last_name, email, company_name, title, linkedin_url
                FROM lead_pool
                WHERE source = 'apollo'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["first_name", "last_name", "email", "company_name", "title"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Apollo API credentials configured and working",
    "Search returns valid lead data with required fields",
    "Pagination handles large result sets correctly",
    "Rate limits respected to avoid API throttling",
    "Results properly mapped to internal lead schema"
]

KEY_FILES = [
    "src/integrations/apollo.py",
    "src/models/lead.py",
    "config/RAILWAY_ENV_VARS.txt"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### Apollo Search Parameters")
    for param, value in APOLLO_SEARCH_PARAMS.items():
        lines.append(f"  {param}: {value}")
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
