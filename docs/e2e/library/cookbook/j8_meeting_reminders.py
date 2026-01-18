"""
Skill: J8.5 — Meeting Reminder System
Journey: J8 - Meeting & Deals
Checks: 4

Purpose: Verify meeting reminders work.
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
# REMINDER CONSTANTS
# =============================================================================

REMINDER_CONSTANTS = {
    "default_reminder_hours": 24,
    "reminder_channels": ["email", "sms"],
    "reminder_statuses": ["pending", "sent", "failed"],
    "prefect_flow": "send_meeting_reminders",
    "reminder_fields": [
        "reminder_sent",
        "reminder_sent_at",
        "reminder_channel",
    ],
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.5.1",
        "part_a": "Read `list_needing_reminder` method",
        "part_b": "N/A",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify list_needing_reminder method queries meetings within reminder window",
            "expect": {
                "code_contains": ["list_needing_reminder", "reminder_sent", "scheduled_at"]
            }
        }
    },
    {
        "id": "J8.5.2",
        "part_a": "Verify 24-hour reminder window",
        "part_b": "Check query",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, scheduled_at, reminder_sent FROM meetings WHERE scheduled_at > NOW() AND scheduled_at < NOW() + INTERVAL '24 hours' AND (reminder_sent = false OR reminder_sent IS NULL) LIMIT 10",
            "expect": {
                "columns": ["id", "scheduled_at", "reminder_sent"],
                "reminder_sent": False
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/meetings?select=id,scheduled_at,reminder_sent&scheduled_at=gt.now()&reminder_sent=is.false&limit=10' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.5.3",
        "part_a": "Verify `reminder_sent` flag updated",
        "part_b": "Check field",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify send_reminder method sets reminder_sent = True",
            "expect": {
                "code_contains": ["reminder_sent", "True", "send_reminder"]
            }
        }
    },
    {
        "id": "J8.5.4",
        "part_a": "Verify `reminder_sent_at` timestamp",
        "part_b": "Check field",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, reminder_sent, reminder_sent_at FROM meetings WHERE reminder_sent = true AND reminder_sent_at IS NOT NULL LIMIT 5",
            "expect": {
                "columns": ["id", "reminder_sent", "reminder_sent_at"],
                "reminder_sent": True,
                "reminder_sent_at_not_null": True
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/meetings?select=id,reminder_sent,reminder_sent_at&reminder_sent=eq.true&reminder_sent_at=not.is.null&limit=5' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    }
]

PASS_CRITERIA = [
    "Reminder query returns correct meetings",
    "Reminder sent tracking works",
    "24-hour window configurable"
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

def get_prefect_url(path: str) -> str:
    """Get full Prefect URL."""
    base = LIVE_CONFIG["prefect_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API URL: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend URL: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase URL: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect URL: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Reminder Constants")
    lines.append(f"- Default Reminder Hours: {REMINDER_CONSTANTS['default_reminder_hours']}")
    lines.append(f"- Reminder Channels: {', '.join(REMINDER_CONSTANTS['reminder_channels'])}")
    lines.append(f"- Prefect Flow: {REMINDER_CONSTANTS['prefect_flow']}")
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
