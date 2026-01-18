"""
Skill: J3.9 - Open/Click Tracking
Journey: J3 - Email Outreach
Checks: 4

Purpose: Verify opens and clicks are tracked via webhooks.
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
# TRACKING CONSTANTS
# =============================================================================

TRACKING_EVENTS = {
    "open": {
        "event_type": "open",
        "updates_activity": True,
        "field": "open_count",
    },
    "click": {
        "event_type": "click",
        "updates_activity": True,
        "field": "click_count",
        "tracks_url": True,
    },
}

WEBHOOK_CONFIG = {
    "endpoint": "/api/v1/webhooks/email/salesforge",
    "deduplication_field": "provider_event_id",
    "deduplication_window_hours": 24,
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.9.1",
        "part_a": "Read `src/services/email_events_service.py` - verify open/click event handling",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/services/email_events_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Email events service handles open and click events",
            "expect": {
                "code_contains": ["open", "click", "handle_event", "EmailEvent", "process"]
            }
        }
    },
    {
        "id": "J3.9.2",
        "part_a": "Verify webhook endpoint `/webhooks/email/salesforge` in webhooks.py",
        "part_b": "Test webhook endpoint with sample payload",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/webhooks/email/salesforge",
            "auth": False,
            "body": {
                "event_type": "open",
                "message_id": "test-message-id",
                "email": "test@example.com",
                "timestamp": "2024-01-01T00:00:00Z",
                "provider_event_id": "unique-event-123"
            },
            "expect": {
                "status": [200, 202],
                "body_contains": ["processed", "success"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/webhooks/email/salesforge' \\
  -H 'Content-Type: application/json' \\
  -d '{\"event_type\": \"open\", \"message_id\": \"test\", \"email\": \"test@example.com\"}'"""
        }
    },
    {
        "id": "J3.9.3",
        "part_a": "Verify duplicate event handling via provider_event_id",
        "part_b": "Send same event twice, verify second is ignored",
        "key_files": ["src/services/email_events_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Duplicate events detected and ignored via provider_event_id",
            "expect": {
                "code_contains": ["provider_event_id", "duplicate", "exists", "skip"]
            },
            "manual_steps": [
                "1. Send webhook event with unique provider_event_id",
                "2. Verify event recorded in email_events table",
                "3. Send same event again with same provider_event_id",
                "4. Verify second event is ignored (no duplicate record)",
                "5. Verify activity count not incremented twice"
            ]
        }
    },
    {
        "id": "J3.9.4",
        "part_a": "Verify activity summary updated via database trigger",
        "part_b": "Check activity record open_count/click_count after events",
        "key_files": ["src/services/email_events_service.py", "src/models/activity.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.metadata->>'open_count' as opens,
                       a.metadata->>'click_count' as clicks,
                       COUNT(ee.id) as event_count
                FROM activities a
                LEFT JOIN email_events ee ON ee.activity_id = a.id
                WHERE a.channel = 'email'
                GROUP BY a.id
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_exist": True,
                "counts_match_events": True
            },
            "manual_steps": [
                "1. Find activity with email events",
                "2. Verify open_count in metadata matches open events",
                "3. Verify click_count in metadata matches click events",
                "4. If using trigger, verify trigger exists and fires"
            ]
        }
    }
]

PASS_CRITERIA = [
    "Email events service complete",
    "Webhook endpoints receive events correctly",
    "Duplicates handled gracefully (no double counting)",
    "Activity record updated with event counts"
]

KEY_FILES = [
    "src/services/email_events_service.py",
    "src/api/routes/webhooks.py",
    "src/models/activity.py",
    "src/models/email_event.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API URL: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend URL: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase URL: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect URL: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Tracking Events")
    for event_name, config in TRACKING_EVENTS.items():
        lines.append(f"  {event_name.upper()}:")
        lines.append(f"    Field: {config['field']}")
        lines.append(f"    Updates Activity: {config['updates_activity']}")
    lines.append("")
    lines.append("### Webhook Configuration")
    lines.append(f"  Endpoint: {WEBHOOK_CONFIG['endpoint']}")
    lines.append(f"  Deduplication: {WEBHOOK_CONFIG['deduplication_field']}")
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
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
