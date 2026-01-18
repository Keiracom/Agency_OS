"""
Skill: J8.8 — Deal Pipeline
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify deal pipeline tracking.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
}

# =============================================================================
# PIPELINE CONSTANTS
# =============================================================================

PIPELINE_CONSTANTS = {
    "stages": ["qualified", "proposal", "negotiation", "closed_won", "closed_lost"],
    "pipeline_metrics": [
        "stage_count",
        "stage_value",
        "weighted_value",
        "average_days_in_stage",
        "conversion_rate",
    ],
    "api_endpoints": {
        "pipeline": "/api/v1/deals/pipeline",
        "stage_history": "/api/v1/deals/{id}/stage-history",
        "forecast": "/api/v1/deals/forecast",
    },
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.8.1",
        "part_a": "Read `get_pipeline` method (lines 529-584)",
        "part_b": "Test pipeline query",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/deals/pipeline",
            "auth": True,
            "expect": {
                "status": [200, 401, 404],
                "response_contains": ["stages", "total_value", "count"]
            },
            "curl_command": "curl -X GET '{api_url}/api/v1/deals/pipeline' -H 'Authorization: Bearer {TOKEN}'"
        }
    },
    {
        "id": "J8.8.2",
        "part_a": "Verify stage counts returned",
        "part_b": "Check counts",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT stage, COUNT(*) as count FROM deals WHERE deleted_at IS NULL GROUP BY stage",
            "expect": {
                "columns": ["stage", "count"],
                "has_rows": True
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/rpc/get_deal_counts_by_stage' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.8.3",
        "part_a": "Verify stage values returned",
        "part_b": "Check totals",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT stage, SUM(value) as total_value FROM deals WHERE deleted_at IS NULL GROUP BY stage",
            "expect": {
                "columns": ["stage", "total_value"],
                "total_value_type": "numeric"
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/deals?select=stage,value' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.8.4",
        "part_a": "Verify weighted_value calculated",
        "part_b": "Check math",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify weighted_value = value * (probability / 100)",
            "expect": {
                "code_contains": ["weighted_value", "probability", "value"]
            }
        }
    },
    {
        "id": "J8.8.5",
        "part_a": "Read `get_stage_history` method",
        "part_b": "Check audit trail",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT deal_id, from_stage, to_stage, changed_at FROM deal_stage_history ORDER BY changed_at DESC LIMIT 10",
            "expect": {
                "columns": ["deal_id", "from_stage", "to_stage", "changed_at"]
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/deal_stage_history?select=deal_id,from_stage,to_stage,changed_at&order=changed_at.desc&limit=10' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    }
]

PASS_CRITERIA = [
    "Pipeline summary accurate",
    "Stage history tracked",
    "Weighted value correct"
]

KEY_FILES = [
    "src/services/deal_service.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_live_url(path: str) -> str:
    """Get full URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_frontend_url(path: str) -> str:
    """Get full frontend URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"

def get_supabase_url(path: str) -> str:
    """Get full Supabase URL for database queries."""
    base = LIVE_CONFIG["supabase_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API URL: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend URL: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase URL: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect URL: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Pipeline Constants")
    lines.append(f"- Stages: {', '.join(PIPELINE_CONSTANTS['stages'])}")
    lines.append(f"- Metrics: {', '.join(PIPELINE_CONSTANTS['pipeline_metrics'])}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
            if lt.get("url"):
                lines.append(f"  URL: {lt['url']}")
            if lt.get("query"):
                lines.append(f"  Query: {lt['query']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
