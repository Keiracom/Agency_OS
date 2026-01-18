"""
Skill: J2B.8 — Enrichment Analytics
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify enrichment API endpoints and analytics tracking for monitoring.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "warning": "Enrichment API calls may consume external credits"
}

# =============================================================================
# COST TRACKING
# =============================================================================

COST_TRACKING = {
    "claude_analysis": {"table": "ai_costs", "operation": "lead_analysis"},
    "apify_scraping": {"table": "external_api_costs", "provider": "apify"},
    "apollo_enrichment": {"table": "external_api_costs", "provider": "apollo"}
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2B.8.1",
        "part_a": "Read `src/api/routes/leads.py` — verify `/api/v1/leads/{id}/research` endpoint",
        "part_b": "Test endpoint triggers enrichment flow",
        "key_files": ["src/api/routes/leads.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/leads/{lead_id}/research",
            "auth": True,
            "expect": {
                "status": [200, 202],
                "body_has_field": "enrichment_id"
            },
            "warning": "Consumes Apify/Claude credits - CEO approval required",
            "curl_command": """curl -X POST '{api_url}/api/v1/leads/{lead_id}/research' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J2B.8.2",
        "part_a": "Verify response includes enrichment status and estimated completion time",
        "part_b": "Check API response structure",
        "key_files": ["src/api/routes/leads.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/leads/{lead_id}/enrichment-status",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["status", "started_at"]
            },
            "curl_command": """curl -X GET '{api_url}/api/v1/leads/{lead_id}/enrichment-status' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J2B.8.3",
        "part_a": "Verify batch enrichment endpoint exists for bulk operations",
        "part_b": "Test batch endpoint with multiple assignment IDs",
        "key_files": ["src/api/routes/leads.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Batch enrichment endpoint exists",
            "expect": {
                "code_contains": ["batch", "enrich", "assignment_ids"]
            }
        }
    },
    {
        "id": "J2B.8.4",
        "part_a": "Verify AI cost tracking: tokens_used, cost_aud logged for Claude analysis",
        "part_b": "Check ai_costs table after enrichment",
        "key_files": ["src/agents/skills/research_skills.py", "src/models/ai_cost.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, client_id, operation, model,
                       input_tokens, output_tokens, cost_aud, created_at
                FROM ai_costs
                WHERE operation LIKE '%research%' OR operation LIKE '%analysis%'
                ORDER BY created_at DESC
                LIMIT 10;
            """,
            "expect": {
                "tokens_tracked": True,
                "cost_calculated": True
            }
        }
    },
    {
        "id": "J2B.8.5",
        "part_a": "Verify Apify cost tracking for LinkedIn scrapes",
        "part_b": "Check external API costs logged",
        "key_files": ["src/integrations/apify.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, provider, operation, cost_aud, metadata, created_at
                FROM external_api_costs
                WHERE provider = 'apify'
                ORDER BY created_at DESC
                LIMIT 10;
            """,
            "expect": {
                "provider": "apify",
                "cost_logged": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Manual enrichment can be triggered via API endpoint",
    "Enrichment status returned in API response",
    "Batch enrichment supported for efficiency",
    "AI costs (Claude tokens) tracked and logged",
    "External API costs (Apify) tracked for budgeting"
]

KEY_FILES = [
    "src/api/routes/leads.py",
    "src/agents/skills/research_skills.py",
    "src/integrations/apify.py",
    "src/models/ai_cost.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### Cost Tracking")
    for service, config in COST_TRACKING.items():
        lines.append(f"  {service}: {config}")
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
