"""
Skill: J8.4 — Meeting Tracking Fields
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify meeting analytics fields are captured.
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
# MEETING TRACKING CONSTANTS
# =============================================================================

TRACKING_CONSTANTS = {
    "attribution_fields": [
        "touches_before_booking",
        "days_to_booking",
        "converting_activity_id",
        "converting_channel",
        "original_scheduled_at",
    ],
    "channel_types": ["email", "sms", "voice", "linkedin", "direct"],
    "analytics_endpoints": {
        "meeting_stats": "/api/v1/analytics/meetings",
        "booking_trends": "/api/v1/analytics/booking-trends",
    },
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.4.1",
        "part_a": "Verify `touches_before_booking` calculated",
        "part_b": "Check field",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, lead_id, touches_before_booking FROM meetings WHERE touches_before_booking IS NOT NULL LIMIT 5",
            "expect": {
                "columns": ["id", "lead_id", "touches_before_booking"],
                "touches_before_booking_type": "integer"
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/meetings?select=id,lead_id,touches_before_booking&touches_before_booking=not.is.null&limit=5' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.4.2",
        "part_a": "Verify `days_to_booking` calculated",
        "part_b": "Check field",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, lead_id, days_to_booking FROM meetings WHERE days_to_booking IS NOT NULL LIMIT 5",
            "expect": {
                "columns": ["id", "lead_id", "days_to_booking"],
                "days_to_booking_type": "integer"
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/meetings?select=id,lead_id,days_to_booking&days_to_booking=not.is.null&limit=5' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.4.3",
        "part_a": "Verify `converting_activity_id` stored",
        "part_b": "Check attribution",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify converting_activity_id field is populated from last activity before booking",
            "expect": {
                "code_contains": ["converting_activity_id", "activity"]
            }
        }
    },
    {
        "id": "J8.4.4",
        "part_a": "Verify `converting_channel` stored",
        "part_b": "Check attribution",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, lead_id, converting_channel FROM meetings WHERE converting_channel IS NOT NULL LIMIT 5",
            "expect": {
                "columns": ["id", "lead_id", "converting_channel"],
                "converting_channel_values": ["email", "sms", "voice", "linkedin", "direct"]
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/meetings?select=id,lead_id,converting_channel&converting_channel=not.is.null&limit=5' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.4.5",
        "part_a": "Verify `original_scheduled_at` preserved on reschedule",
        "part_b": "Check field",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify reschedule method preserves original_scheduled_at timestamp",
            "expect": {
                "code_contains": ["original_scheduled_at", "reschedule"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Touches calculated correctly",
    "Days to booking accurate",
    "Attribution fields populated",
    "Reschedule tracking works"
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
    lines.append("### Tracking Constants")
    lines.append(f"- Attribution Fields: {', '.join(TRACKING_CONSTANTS['attribution_fields'])}")
    lines.append(f"- Channel Types: {', '.join(TRACKING_CONSTANTS['channel_types'])}")
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
            if lt.get("query"):
                lines.append(f"  Query: {lt['query']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
