"""
Skill: J8.1 — Meeting Webhook (Calendly)
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify Calendly webhooks create meetings.
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
# MEETING BOOKING CONSTANTS
# =============================================================================

MEETING_CONSTANTS = {
    "webhook_endpoint": "/api/v1/webhooks/crm/meeting",
    "calendly_events": ["invitee.created", "invitee.canceled"],
    "meeting_types": ["discovery", "demo", "follow_up", "closing", "other"],
    "meeting_statuses": ["scheduled", "confirmed", "completed", "cancelled", "no_show", "rescheduled"],
    "test_calendly_payload": {
        "event": "invitee.created",
        "payload": {
            "event_type": {
                "name": "Discovery Call",
                "duration": 30
            },
            "invitee": {
                "email": "test@example.com",
                "name": "Test Lead"
            },
            "scheduled_event": {
                "start_time": "2024-01-20T10:00:00Z",
                "end_time": "2024-01-20T10:30:00Z",
                "uri": "https://calendly.com/events/test-event-123"
            }
        }
    }
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.1.1",
        "part_a": "Read `webhooks.py` — verify `/webhooks/crm/meeting` endpoint (line 1365)",
        "part_b": "Send test webhook",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/webhooks/crm/meeting",
            "headers": {"Content-Type": "application/json", "X-Calendly-Webhook-Signature": "test"},
            "body": "{test_calendly_payload}",
            "expect": {
                "status": [200, 400, 401],
                "response_contains": ["success", "error", "meeting"]
            },
            "curl_command": "curl -X POST '{api_url}/api/v1/webhooks/crm/meeting' -H 'Content-Type: application/json' -d '{\"event\": \"invitee.created\", \"payload\": {\"invitee\": {\"email\": \"test@example.com\"}}}'"
        }
    },
    {
        "id": "J8.1.2",
        "part_a": "Read `_handle_calendly_webhook` (lines 1493-1559)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify _handle_calendly_webhook function exists and handles invitee.created event",
            "expect": {
                "code_contains": ["_handle_calendly_webhook", "invitee.created", "invitee.canceled"]
            }
        }
    },
    {
        "id": "J8.1.3",
        "part_a": "Verify lead matched by email",
        "part_b": "Check lead lookup",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify lead lookup by invitee email address",
            "expect": {
                "code_contains": ["email", "invitee", "lead"]
            }
        }
    },
    {
        "id": "J8.1.4",
        "part_a": "Verify meeting created via MeetingService",
        "part_b": "Check meeting record",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, lead_id, meeting_type, status FROM meetings ORDER BY created_at DESC LIMIT 5",
            "expect": {
                "has_rows": True,
                "columns": ["id", "lead_id", "meeting_type", "status"]
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/meetings?select=id,lead_id,meeting_type,status&order=created_at.desc&limit=5' -H 'apikey: {SUPABASE_ANON_KEY}' -H 'Authorization: Bearer {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.1.5",
        "part_a": "Verify calendar_event_id stored",
        "part_b": "Check deduplication",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify calendar_event_id field is stored for deduplication",
            "expect": {
                "code_contains": ["calendar_event_id", "uri"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Calendly webhook endpoint exists",
    "Meeting created on invitee.created event",
    "Meeting cancelled on invitee.canceled event",
    "Lead linked correctly"
]

KEY_FILES = [
    "src/api/routes/webhooks.py",
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
    lines.append("### Meeting Constants")
    lines.append(f"- Webhook Endpoint: {MEETING_CONSTANTS['webhook_endpoint']}")
    lines.append(f"- Calendly Events: {', '.join(MEETING_CONSTANTS['calendly_events'])}")
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
