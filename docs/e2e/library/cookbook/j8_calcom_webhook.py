"""
Skill: J8.2 — Meeting Webhook (Cal.com)
Journey: J8 - Meeting & Deals
Checks: 2

Purpose: Verify Cal.com webhooks create meetings.
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
# CAL.COM CONSTANTS
# =============================================================================

CALCOM_CONSTANTS = {
    "webhook_endpoint": "/api/v1/webhooks/crm/meeting",
    "calcom_events": ["BOOKING_CREATED", "BOOKING_CANCELLED", "BOOKING_RESCHEDULED"],
    "test_calcom_payload": {
        "triggerEvent": "BOOKING_CREATED",
        "payload": {
            "type": "Discovery Call",
            "attendees": [
                {"email": "test@example.com", "name": "Test Lead"}
            ],
            "startTime": "2024-01-20T10:00:00Z",
            "endTime": "2024-01-20T10:30:00Z",
            "uid": "cal-event-123"
        }
    }
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.2.1",
        "part_a": "Read `_handle_calcom_webhook` (lines 1562-1566)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify _handle_calcom_webhook function exists in webhooks.py",
            "expect": {
                "code_contains": ["_handle_calcom_webhook", "calcom", "Cal.com"]
            }
        }
    },
    {
        "id": "J8.2.2",
        "part_a": "VERIFY: Cal.com handler NOT fully implemented",
        "part_b": "Check response",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/webhooks/crm/meeting",
            "headers": {"Content-Type": "application/json", "X-Cal-Signature": "test"},
            "body": "{test_calcom_payload}",
            "expect": {
                "status": [200, 400, 501],
                "response_contains": ["ignored", "not implemented", "success"]
            },
            "curl_command": "curl -X POST '{api_url}/api/v1/webhooks/crm/meeting' -H 'Content-Type: application/json' -H 'X-Cal-Signature: test' -d '{\"triggerEvent\": \"BOOKING_CREATED\", \"payload\": {\"attendees\": [{\"email\": \"test@example.com\"}]}}'"
        }
    }
]

PASS_CRITERIA = [
    "Cal.com handler is NOT implemented — returns 'ignored'",
    "CEO Decision: Implement Cal.com or use Calendly only?"
]

KEY_FILES = [
    "src/api/routes/webhooks.py"
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
    lines.append("### Cal.com Constants")
    lines.append(f"- Webhook Endpoint: {CALCOM_CONSTANTS['webhook_endpoint']}")
    lines.append(f"- Cal.com Events: {', '.join(CALCOM_CONSTANTS['calcom_events'])}")
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
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
