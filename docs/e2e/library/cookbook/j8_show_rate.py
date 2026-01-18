"""
Skill: J8.6 — Show Rate Tracking
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify show/no-show tracking for CIS learning.
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
# SHOW RATE CONSTANTS
# =============================================================================

SHOW_RATE_CONSTANTS = {
    "confirmation_sources": ["calendar_integration", "manual", "webhook", "api"],
    "no_show_reasons": [
        "forgot",
        "conflict",
        "no_response",
        "technical_issues",
        "changed_mind",
        "unknown",
    ],
    "show_rate_fields": [
        "showed_up",
        "showed_up_confirmed_by",
        "showed_up_at",
        "no_show_reason",
    ],
    "analytics_endpoint": "/api/v1/analytics/show-rate",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.6.1",
        "part_a": "Read `record_show` method (lines 316-362)",
        "part_b": "Test show recording",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify record_show method with showed_up boolean parameter",
            "expect": {
                "code_contains": ["def record_show", "showed_up", "bool"]
            }
        }
    },
    {
        "id": "J8.6.2",
        "part_a": "Verify `showed_up` field",
        "part_b": "Check boolean",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, showed_up, status FROM meetings WHERE showed_up IS NOT NULL LIMIT 10",
            "expect": {
                "columns": ["id", "showed_up", "status"],
                "showed_up_type": "boolean"
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/meetings?select=id,showed_up,status&showed_up=not.is.null&limit=10' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.6.3",
        "part_a": "Verify `showed_up_confirmed_by` field",
        "part_b": "Check source",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, showed_up, showed_up_confirmed_by FROM meetings WHERE showed_up_confirmed_by IS NOT NULL LIMIT 5",
            "expect": {
                "columns": ["id", "showed_up", "showed_up_confirmed_by"],
                "showed_up_confirmed_by_values": ["calendar_integration", "manual", "webhook", "api"]
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/meetings?select=id,showed_up,showed_up_confirmed_by&showed_up_confirmed_by=not.is.null&limit=5' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.6.4",
        "part_a": "Verify `no_show_reason` field",
        "part_b": "Check reason",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, showed_up, no_show_reason FROM meetings WHERE showed_up = false AND no_show_reason IS NOT NULL LIMIT 5",
            "expect": {
                "columns": ["id", "showed_up", "no_show_reason"],
                "showed_up": False
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/meetings?select=id,showed_up,no_show_reason&showed_up=eq.false&no_show_reason=not.is.null&limit=5' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.6.5",
        "part_a": "Read `get_show_rate_analysis` method",
        "part_b": "Check analytics",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/analytics/show-rate",
            "auth": True,
            "expect": {
                "status": [200, 401, 404],
                "response_contains": ["show_rate", "total", "showed", "no_show"]
            },
            "curl_command": "curl -X GET '{api_url}/api/v1/analytics/show-rate' -H 'Authorization: Bearer {TOKEN}'"
        }
    }
]

PASS_CRITERIA = [
    "Show/no-show recorded",
    "Confirmation method tracked",
    "Show rate analytics available"
]

KEY_FILES = [
    "src/services/meeting_service.py"
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
    lines.append("### Show Rate Constants")
    lines.append(f"- Confirmation Sources: {', '.join(SHOW_RATE_CONSTANTS['confirmation_sources'])}")
    lines.append(f"- No-Show Reasons: {', '.join(SHOW_RATE_CONSTANTS['no_show_reasons'])}")
    lines.append(f"- Analytics Endpoint: {SHOW_RATE_CONSTANTS['analytics_endpoint']}")
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
