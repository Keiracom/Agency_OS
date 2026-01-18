"""
Skill: J8.3 — MeetingService Implementation
Journey: J8 - Meeting & Deals
Checks: 8

Purpose: Verify MeetingService is complete.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "client_id": "81dbaee6-4e71-48ad-be40-fa915fae66e0",
    "user_id": "a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2",
    "test_email": "david.stephens@keiracom.com",
    "test_phone": "+61457543392",
}

# =============================================================================
# MEETING SERVICE CONSTANTS
# =============================================================================

MEETING_SERVICE_CONSTANTS = {
    "meeting_types": ["discovery", "demo", "follow_up", "closing", "other"],
    "meeting_statuses": ["scheduled", "confirmed", "completed", "cancelled", "no_show", "rescheduled"],
    "meeting_outcomes": ["good", "neutral", "bad", "no_show"],
    "api_endpoints": {
        "create": "/api/v1/meetings",
        "get": "/api/v1/meetings/{id}",
        "update": "/api/v1/meetings/{id}",
        "list": "/api/v1/meetings",
    },
    "required_fields": ["lead_id", "scheduled_at", "meeting_type", "agency_id"],
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.3.1",
        "part_a": "Read `src/services/meeting_service.py` (839 lines)",
        "part_b": "N/A",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify MeetingService class exists with all required methods",
            "expect": {
                "code_contains": ["class MeetingService", "def create", "def confirm", "def cancel"]
            }
        }
    },
    {
        "id": "J8.3.2",
        "part_a": "Verify `create` method with all fields",
        "part_b": "Test meeting creation",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/meetings",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "scheduled_at": "2024-01-25T10:00:00Z",
                "meeting_type": "discovery",
                "duration_minutes": 30
            },
            "expect": {
                "status": [200, 201, 401, 422],
                "response_contains": ["id", "meeting"]
            },
            "curl_command": "curl -X POST '{api_url}/api/v1/meetings' -H 'Content-Type: application/json' -H 'Authorization: Bearer {TOKEN}' -d '{\"lead_id\": \"...\", \"scheduled_at\": \"2024-01-25T10:00:00Z\", \"meeting_type\": \"discovery\"}'"
        }
    },
    {
        "id": "J8.3.3",
        "part_a": "Verify `confirm` method",
        "part_b": "Test confirmation",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify confirm method updates meeting status to confirmed",
            "expect": {
                "code_contains": ["def confirm", "confirmed", "status"]
            }
        }
    },
    {
        "id": "J8.3.4",
        "part_a": "Verify `send_reminder` method",
        "part_b": "Test reminder marking",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify send_reminder method sets reminder_sent flag",
            "expect": {
                "code_contains": ["def send_reminder", "reminder_sent", "reminder_sent_at"]
            }
        }
    },
    {
        "id": "J8.3.5",
        "part_a": "Verify `record_show` method",
        "part_b": "Test show/no-show",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify record_show method captures showed_up boolean and no_show_reason",
            "expect": {
                "code_contains": ["def record_show", "showed_up", "no_show_reason"]
            }
        }
    },
    {
        "id": "J8.3.6",
        "part_a": "Verify `record_outcome` method",
        "part_b": "Test outcome recording",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify record_outcome method sets outcome and optionally creates deal",
            "expect": {
                "code_contains": ["def record_outcome", "outcome", "create_deal"]
            }
        }
    },
    {
        "id": "J8.3.7",
        "part_a": "Verify `reschedule` method",
        "part_b": "Test reschedule",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify reschedule method preserves original_scheduled_at and updates new time",
            "expect": {
                "code_contains": ["def reschedule", "original_scheduled_at", "rescheduled"]
            }
        }
    },
    {
        "id": "J8.3.8",
        "part_a": "Verify `cancel` method",
        "part_b": "Test cancellation",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify cancel method sets status to cancelled with reason",
            "expect": {
                "code_contains": ["def cancel", "cancelled", "cancel_reason"]
            }
        }
    }
]

PASS_CRITERIA = [
    "All CRUD methods implemented",
    "Meeting types validated",
    "Outcomes validated",
    "Lead updated with meeting info"
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
    lines.append("### Meeting Service Constants")
    lines.append(f"- Meeting Types: {', '.join(MEETING_SERVICE_CONSTANTS['meeting_types'])}")
    lines.append(f"- Meeting Statuses: {', '.join(MEETING_SERVICE_CONSTANTS['meeting_statuses'])}")
    lines.append(f"- Meeting Outcomes: {', '.join(MEETING_SERVICE_CONSTANTS['meeting_outcomes'])}")
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
