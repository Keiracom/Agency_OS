"""
Skill: J2B.2 — Apollo Enrichment
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify Apollo enrichment adds detailed person and company data to leads.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "warning": "Apollo enrichment consumes credits - CEO approval required"
}

# =============================================================================
# ENRICHMENT FIELDS
# =============================================================================

ENRICHMENT_FIELDS = {
    "person": ["email", "phone", "linkedin_url", "title", "employment_history", "education"],
    "organization": ["industry", "employee_count", "revenue", "technologies", "keywords"],
    "credit_cost": {"person": 1, "organization": 1}
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2B.2.1",
        "part_a": "Read `src/integrations/apollo.py` — verify `enrich_person` method exists",
        "part_b": "Test enrichment with known email address",
        "key_files": ["src/integrations/apollo.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Apollo integration has enrich_person method",
            "expect": {
                "code_contains": ["enrich_person", "person/enrich", "email"]
            }
        }
    },
    {
        "id": "J2B.2.2",
        "part_a": "Verify person enrichment captures: email, phone, linkedin_url, employment history",
        "part_b": "Check enriched data structure contains all fields",
        "key_files": ["src/integrations/apollo.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/leads/{lead_id}/enrich",
            "auth": True,
            "expect": {
                "status": [200, 202],
                "body_has_fields": ["email", "phone", "linkedin_url"]
            },
            "warning": "Consumes Apollo credits",
            "curl_command": """curl -X POST '{api_url}/api/v1/leads/{lead_id}/enrich' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J2B.2.3",
        "part_a": "Read `enrich_organization` method for company data",
        "part_b": "Test organization enrichment returns industry, employee_count, revenue",
        "key_files": ["src/integrations/apollo.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Apollo integration has enrich_organization method",
            "expect": {
                "code_contains": ["enrich_organization", "organization/enrich", "domain"]
            }
        }
    },
    {
        "id": "J2B.2.4",
        "part_a": "Verify credit usage tracking for enrichment calls",
        "part_b": "Check credit balance before/after enrichment",
        "key_files": ["src/integrations/apollo.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT operation, credits_used, cost_aud, created_at
                FROM external_api_costs
                WHERE provider = 'apollo'
                ORDER BY created_at DESC
                LIMIT 10;
            """,
            "expect": {
                "rows_exist": True,
                "credits_tracked": True
            }
        }
    },
    {
        "id": "J2B.2.5",
        "part_a": "Verify enrichment data stored in lead_pool table",
        "part_b": "Query database for enriched lead record",
        "key_files": ["src/integrations/apollo.py", "src/models/lead.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, email, phone, linkedin_url, company_name,
                       enrichment_data, enriched_at
                FROM lead_pool
                WHERE enriched_at IS NOT NULL
                ORDER BY enriched_at DESC
                LIMIT 5;
            """,
            "expect": {
                "enrichment_data_not_null": True,
                "enriched_at_populated": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Person enrichment returns complete profile data",
    "Company enrichment returns industry and size metrics",
    "Credit usage tracked for cost monitoring",
    "Enriched data persisted to database",
    "Missing data handled gracefully (no crashes on partial data)"
]

KEY_FILES = [
    "src/integrations/apollo.py",
    "src/models/lead.py",
    "src/engines/scout.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### Enrichment Fields")
    for category, fields in ENRICHMENT_FIELDS.items():
        lines.append(f"  {category}: {fields}")
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
