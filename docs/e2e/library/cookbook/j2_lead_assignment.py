"""
Skill: J2.5 — Lead Pool Population
Journey: J2 - Campaign Creation & Management
Checks: 6

Purpose: Verify Apollo search populates the platform-wide lead pool.

Pool Population Waterfall:
- Tier 1: Apollo People Search
- Tier 2: Clay Enrichment (if Apollo fails)
- Tier 3: Direct Scraping (if both fail)
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "note": "Pool population requires Apollo API credits - get approval before testing"
}

# =============================================================================
# WATERFALL TIERS
# =============================================================================

WATERFALL_TIERS = [
    {"tier": 1, "method": "Apollo People Search", "cost": "1 credit/person"},
    {"tier": 2, "method": "Clay Enrichment", "cost": "1-5 credits/person"},
    {"tier": 3, "method": "Direct Scraping", "cost": "Apify credits"},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2.5.1",
        "part_a": "Read `src/orchestration/flows/pool_population_flow.py`",
        "part_b": "Identify flow tasks",
        "key_files": ["src/orchestration/flows/pool_population_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Flow file exists with proper task structure",
            "expect": {
                "code_contains": ["@flow", "@task", "apollo", "pool"]
            }
        }
    },
    {
        "id": "J2.5.2",
        "part_a": "Read `src/integrations/apollo.py` — verify `search_people_for_pool`",
        "part_b": "Check Apollo API calls",
        "key_files": ["src/integrations/apollo.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Apollo integration has search_people method",
            "expect": {
                "code_contains": ["search_people", "APOLLO_API_KEY", "api.apollo.io"]
            },
            "warning": "Live API test requires Apollo credits - confirm before running"
        }
    },
    {
        "id": "J2.5.3",
        "part_a": "Verify 3-tier waterfall: Apollo → Clay → Direct Scraping",
        "part_b": "Check tier fallback logic",
        "key_files": ["src/orchestration/flows/pool_population_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Waterfall logic with tier fallbacks exists",
            "expect": {
                "code_contains": ["tier", "fallback", "apollo", "clay"]
            },
            "manual_verify": [
                "1. Read pool_population_flow.py",
                "2. Find tier 1 (Apollo) call",
                "3. Find tier 2 (Clay) fallback",
                "4. Find tier 3 (scraping) fallback",
                "5. Verify fallback triggers on failure"
            ]
        }
    },
    {
        "id": "J2.5.4",
        "part_a": "Read `src/services/lead_pool_service.py` — verify `create_or_update`",
        "part_b": "Check dedup by email",
        "key_files": ["src/services/lead_pool_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT COUNT(*) as total, COUNT(DISTINCT email) as unique_emails
                FROM lead_pool
                LIMIT 1;
            """,
            "expect": {
                "total_equals_unique": True
            },
            "note": "Total should equal unique_emails (no duplicates)"
        }
    },
    {
        "id": "J2.5.5",
        "part_a": "Verify `lead_pool` table receives enriched data",
        "part_b": "Query table after flow",
        "key_files": ["src/services/lead_pool_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, email, first_name, last_name, title, company_name,
                       linkedin_url, email_status, pool_status, als_score
                FROM lead_pool
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_have_fields": ["email", "first_name", "company_name", "email_status"]
            }
        }
    },
    {
        "id": "J2.5.6",
        "part_a": "Verify email_status captured from Apollo (CRITICAL for bounce prevention)",
        "part_b": "Check email_status field",
        "key_files": ["src/integrations/apollo.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT email_status, COUNT(*) as count
                FROM lead_pool
                WHERE email_status IS NOT NULL
                GROUP BY email_status;
            """,
            "expect": {
                "rows_exist": True,
                "status_values": ["verified", "guessed", "invalid", "catch-all"]
            },
            "note": "email_status is critical - 'invalid' emails should NOT be contacted"
        }
    }
]

PASS_CRITERIA = [
    "Pool population flow runs via Prefect",
    "Apollo integration returns enriched leads",
    "Leads stored in `lead_pool` with 50+ fields",
    "Email deduplication works (same email = update)",
    "email_status field captured for bounce prevention"
]

KEY_FILES = [
    "src/orchestration/flows/pool_population_flow.py",
    "src/integrations/apollo.py",
    "src/services/lead_pool_service.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append(f"- Note: {LIVE_CONFIG['note']}")
    lines.append("")
    lines.append("### Waterfall Tiers")
    for tier in WATERFALL_TIERS:
        lines.append(f"  Tier {tier['tier']}: {tier['method']} ({tier['cost']})")
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
