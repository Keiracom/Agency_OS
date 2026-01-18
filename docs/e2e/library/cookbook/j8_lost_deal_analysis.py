"""
Skill: J8.13 — Lost Deal Analysis
Journey: J8 - Meeting & Deals
Checks: 3

Purpose: Verify lost deal analytics for CIS learning.
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
# LOST DEAL CONSTANTS
# =============================================================================

LOST_DEAL_CONSTANTS = {
    "lost_reasons": [
        "price",
        "timing",
        "competitor",
        "no_budget",
        "no_decision",
        "lost_contact",
        "other",
    ],
    "analysis_fields": [
        "lost_reason",
        "lost_notes",
        "lost_at",
        "days_in_pipeline",
        "stage_at_loss",
    ],
    "api_endpoints": {
        "lost_analysis": "/api/v1/analytics/lost-deals",
        "loss_patterns": "/api/v1/analytics/loss-patterns",
    },
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.13.1",
        "part_a": "Read `get_lost_analysis` method (lines 700-725)",
        "part_b": "Test query",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/analytics/lost-deals",
            "auth": True,
            "expect": {
                "status": [200, 401, 404],
                "response_contains": ["lost_reason", "count", "deals"]
            },
            "curl_command": "curl -X GET '{api_url}/api/v1/analytics/lost-deals' -H 'Authorization: Bearer {TOKEN}'"
        }
    },
    {
        "id": "J8.13.2",
        "part_a": "Verify lost_reason breakdown",
        "part_b": "Check grouping",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT lost_reason, COUNT(*) as count, SUM(value) as lost_value FROM deals WHERE stage = 'closed_lost' AND lost_reason IS NOT NULL GROUP BY lost_reason ORDER BY count DESC",
            "expect": {
                "columns": ["lost_reason", "count", "lost_value"],
                "lost_reason_values": ["price", "timing", "competitor", "no_budget", "no_decision", "lost_contact", "other"]
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/deals?select=lost_reason,value&stage=eq.closed_lost&lost_reason=not.is.null' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.13.3",
        "part_a": "Verify lost_notes captured",
        "part_b": "Check field",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, lost_reason, lost_notes FROM deals WHERE stage = 'closed_lost' AND lost_notes IS NOT NULL LIMIT 5",
            "expect": {
                "columns": ["id", "lost_reason", "lost_notes"],
                "lost_notes_not_null": True
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/deals?select=id,lost_reason,lost_notes&stage=eq.closed_lost&lost_notes=not.is.null&limit=5' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    }
]

PASS_CRITERIA = [
    "Lost reasons analyzed",
    "Patterns identifiable",
    "CIS can learn from losses"
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
    lines.append("### Lost Deal Constants")
    lines.append(f"- Lost Reasons: {', '.join(LOST_DEAL_CONSTANTS['lost_reasons'])}")
    lines.append(f"- Analysis Fields: {', '.join(LOST_DEAL_CONSTANTS['analysis_fields'])}")
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
