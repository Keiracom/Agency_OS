"""
Skill: J10.6 — Live Activity Feed
Journey: J10 - Admin Dashboard
Checks: 5

Purpose: Verify real-time activity feed displays system events.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "test_admin": {
        "email": "david.stephens@keiracom.com",
        "role": "admin"
    }
}

# =============================================================================
# ACTIVITY EVENT TYPES CONSTANTS
# =============================================================================

ACTIVITY_EVENTS = [
    {"type": "lead_created", "icon": "user-plus", "description": "New lead added to system"},
    {"type": "email_sent", "icon": "mail", "description": "Outreach email sent"},
    {"type": "campaign_started", "icon": "play", "description": "Campaign execution began"},
    {"type": "reply_received", "icon": "message-circle", "description": "Lead replied to outreach"},
    {"type": "client_signup", "icon": "briefcase", "description": "New client registered"},
    {"type": "system_error", "icon": "alert-triangle", "description": "System error occurred"}
]

ACTIVITY_FILTERS = ["all", "leads", "campaigns", "outreach", "system", "clients"]

POLLING_CONFIG = {
    "interval_ms": 30000,  # 30 seconds
    "max_items": 50,
    "realtime_enabled": True
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.6.1",
        "part_a": "Read `frontend/app/admin/activity/page.tsx` — verify activity feed",
        "part_b": "Load activity page, verify events display",
        "key_files": ["frontend/app/admin/activity/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin/activity",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Activity", "Events"]
            },
            "manual_steps": [
                "1. Login as admin user",
                "2. Navigate to {frontend_url}/admin/activity",
                "3. Verify activity feed loads",
                "4. Check recent events are displayed"
            ]
        }
    },
    {
        "id": "J10.6.2",
        "part_a": "Verify activity events show timestamp and user",
        "part_b": "Check each event has proper metadata",
        "key_files": ["frontend/app/admin/activity/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/activity?limit=10",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["id", "type", "timestamp", "user_id", "message"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/activity?limit=10' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J10.6.3",
        "part_a": "Verify activity filtering by type",
        "part_b": "Filter by event type, verify list updates",
        "key_files": ["frontend/app/admin/activity/page.tsx"],
        "live_test": {
            "type": "api_batch",
            "tests": [
                {
                    "name": "Filter by leads",
                    "method": "GET",
                    "url": "{api_url}/api/v1/admin/activity?type=lead_created&limit=5",
                    "expect": {"all_items_have": {"type": "lead_created"}}
                },
                {
                    "name": "Filter by outreach",
                    "method": "GET",
                    "url": "{api_url}/api/v1/admin/activity?type=email_sent&limit=5",
                    "expect": {"all_items_have": {"type": "email_sent"}}
                }
            ],
            "auth": True,
            "curl_command": """curl '{api_url}/api/v1/admin/activity?type=lead_created&limit=5' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/activity page, locate filter dropdown",
                "2. Select 'Leads' filter",
                "3. Verify only lead-related events display",
                "4. Select 'Outreach' filter",
                "5. Verify only email/SMS events display"
            ]
        }
    },
    {
        "id": "J10.6.4",
        "part_a": "Verify activity pagination or infinite scroll",
        "part_b": "Scroll down, verify more events load",
        "key_files": ["frontend/app/admin/activity/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/activity?limit=10&offset=10",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True
            },
            "curl_command": """curl '{api_url}/api/v1/admin/activity?limit=10&offset=10' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/activity page, scroll to bottom of list",
                "2. Verify 'Load more' button or infinite scroll triggers",
                "3. Check additional events load without duplicates",
                "4. Verify smooth scrolling behavior"
            ]
        }
    },
    {
        "id": "J10.6.5",
        "part_a": "Verify real-time updates (polling or websocket)",
        "part_b": "Trigger event, verify it appears without refresh",
        "key_files": ["frontend/app/admin/activity/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open /admin/activity page in one browser tab",
                "2. Open another tab and trigger an action (e.g., create a lead)",
                "3. Return to activity page without refreshing",
                "4. Wait for polling interval (~30 seconds) or verify instant update",
                "5. Verify new event appears at top of feed",
                "6. Check Network tab for polling requests or WebSocket connection"
            ],
            "expect": {
                "new_events_appear": True,
                "no_manual_refresh_needed": True,
                "polling_or_websocket_active": True
            },
            "note": "Real-time may be polling-based (30s interval) or WebSocket"
        }
    }
]

PASS_CRITERIA = [
    "Activity feed renders with events",
    "Events show proper metadata",
    "Filtering works correctly",
    "Pagination or infinite scroll works",
    "Real-time updates function"
]

KEY_FILES = [
    "frontend/app/admin/activity/page.tsx",
    "src/api/routes/admin.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_frontend_url(path: str) -> str:
    """Get full frontend URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append(f"- Activity Page: {LIVE_CONFIG['frontend_url']}/admin/activity")
    lines.append("")
    lines.append("### Activity Event Types")
    for event in ACTIVITY_EVENTS:
        lines.append(f"  - {event['type']}: {event['description']} ({event['icon']})")
    lines.append("")
    lines.append("### Activity Filters")
    lines.append(f"  Available: {', '.join(ACTIVITY_FILTERS)}")
    lines.append("")
    lines.append("### Polling Config")
    lines.append(f"  Interval: {POLLING_CONFIG['interval_ms']}ms")
    lines.append(f"  Max Items: {POLLING_CONFIG['max_items']}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("type"):
            lines.append(f"  Live Test Type: {lt['type']}")
        if lt.get("curl_command"):
            lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
