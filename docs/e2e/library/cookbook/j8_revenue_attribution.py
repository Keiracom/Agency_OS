"""
Skill: J8.10 — Revenue Attribution
Journey: J8 - Meeting & Deals
Checks: 4

Purpose: Verify revenue attributed to channels and activities.
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
# ATTRIBUTION CONSTANTS
# =============================================================================

ATTRIBUTION_CONSTANTS = {
    "attribution_models": ["first_touch", "last_touch", "linear", "weighted"],
    "channels": ["email", "sms", "voice", "linkedin", "direct"],
    "attribution_fields": [
        "first_touch_channel",
        "last_touch_channel",
        "converting_channel",
        "attributed_revenue",
    ],
    "api_endpoints": {
        "attribution": "/api/v1/analytics/attribution",
        "channel_breakdown": "/api/v1/analytics/channel-breakdown",
        "funnel": "/api/v1/analytics/funnel",
    },
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.10.1",
        "part_a": "Read `calculate_attribution` method (lines 610-630)",
        "part_b": "N/A",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify calculate_attribution method with model parameter",
            "expect": {
                "code_contains": ["calculate_attribution", "first_touch", "last_touch"]
            }
        }
    },
    {
        "id": "J8.10.2",
        "part_a": "Verify first_touch model",
        "part_b": "Test attribution",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/analytics/attribution?model=first_touch",
            "auth": True,
            "expect": {
                "status": [200, 401, 404],
                "response_contains": ["channel", "revenue", "deals"]
            },
            "curl_command": "curl -X GET '{api_url}/api/v1/analytics/attribution?model=first_touch' -H 'Authorization: Bearer {TOKEN}'"
        }
    },
    {
        "id": "J8.10.3",
        "part_a": "Read `get_channel_attribution` method",
        "part_b": "Test channel breakdown",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT converting_channel, COUNT(*) as deals, SUM(value) as revenue FROM deals WHERE stage = 'closed_won' AND converting_channel IS NOT NULL GROUP BY converting_channel",
            "expect": {
                "columns": ["converting_channel", "deals", "revenue"]
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/deals?select=converting_channel,value&stage=eq.closed_won&converting_channel=not.is.null' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.10.4",
        "part_a": "Read `get_funnel_analytics` method",
        "part_b": "Test funnel",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/analytics/funnel",
            "auth": True,
            "expect": {
                "status": [200, 401, 404],
                "response_contains": ["stages", "conversion", "drop_off"]
            },
            "curl_command": "curl -X GET '{api_url}/api/v1/analytics/funnel' -H 'Authorization: Bearer {TOKEN}'"
        }
    }
]

PASS_CRITERIA = [
    "Attribution calculated on close_won",
    "Multiple models supported",
    "Channel breakdown available",
    "Funnel analytics work"
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
    lines.append("### Attribution Constants")
    lines.append(f"- Attribution Models: {', '.join(ATTRIBUTION_CONSTANTS['attribution_models'])}")
    lines.append(f"- Channels: {', '.join(ATTRIBUTION_CONSTANTS['channels'])}")
    lines.append(f"- Attribution Fields: {', '.join(ATTRIBUTION_CONSTANTS['attribution_fields'])}")
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
