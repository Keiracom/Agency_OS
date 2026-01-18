"""
Skill: J9.14 — Real-Time Updates
Journey: J9 - Client Dashboard
Checks: 4

Purpose: Verify dashboard receives real-time updates for new leads, email events,
and activity changes without requiring page refresh.
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
# REALTIME CONSTANTS
# =============================================================================

REALTIME_CHANNELS = [
    {"name": "leads", "events": ["INSERT", "UPDATE", "DELETE"]},
    {"name": "emails", "events": ["INSERT", "UPDATE"]},
    {"name": "replies", "events": ["INSERT"]},
    {"name": "activity_events", "events": ["INSERT"]},
]

REALTIME_UPDATE_TYPES = [
    {"type": "lead_created", "description": "New lead added", "widget": "activity_feed"},
    {"type": "lead_score_updated", "description": "Lead score changed", "widget": "als_distribution"},
    {"type": "email_sent", "description": "Email sent to lead", "widget": "stats, activity_feed"},
    {"type": "email_opened", "description": "Lead opened email", "widget": "stats, activity_feed"},
    {"type": "email_clicked", "description": "Lead clicked link", "widget": "activity_feed"},
    {"type": "reply_received", "description": "New reply from lead", "widget": "stats, activity_feed"},
    {"type": "meeting_booked", "description": "Meeting scheduled", "widget": "meetings, activity_feed"},
]

POLLING_FALLBACK = {
    "enabled": True,
    "interval_ms": 30000,
    "description": "Fallback polling if WebSocket fails",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.14.1",
        "part_a": "Verify real-time connection establishes",
        "part_b": "Check WebSocket or polling connection establishes on dashboard load",
        "key_files": ["frontend/app/dashboard/page.tsx"],
        "live_test": {
            "type": "code_verify",
            "check": "Dashboard establishes Supabase realtime subscription or polling mechanism",
            "expect": {
                "code_contains": ["supabase.channel", "subscribe", "useEffect", "setInterval"]
            }
        }
    },
    {
        "id": "J9.14.2",
        "part_a": "Verify new lead appears in real-time",
        "part_b": "Create new lead via API, verify it appears in dashboard without refresh",
        "key_files": ["frontend/app/dashboard/page.tsx", "frontend/components/dashboard/ActivityTicker.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard in browser (authenticated)",
                "2. Keep dashboard open and visible",
                "3. In another tab or via curl, create a new lead via API:",
                "   POST {api_url}/api/v1/leads",
                "4. Watch the dashboard without refreshing",
                "5. Verify new lead appears in activity feed within 30 seconds",
                "6. Verify stats widget updates to reflect new lead count"
            ],
            "expect": {
                "lead_appears_without_refresh": True,
                "stats_update_automatically": True,
                "update_time": "< 30 seconds"
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/leads' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"first_name": "Test", "last_name": "Lead", "email": "test@example.com"}'"""
        }
    },
    {
        "id": "J9.14.3",
        "part_a": "Verify email event updates in real-time",
        "part_b": "Trigger email open event, verify activity feed updates without refresh",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard in browser (authenticated)",
                "2. Note the current activity feed items",
                "3. Trigger an email open event (via webhook or test endpoint)",
                "4. Watch the activity feed without refreshing",
                "5. Verify 'Email opened by [lead]' event appears",
                "6. Check timestamp is current"
            ],
            "expect": {
                "email_event_appears": True,
                "no_refresh_needed": True,
                "timestamp_current": True
            }
        }
    },
    {
        "id": "J9.14.4",
        "part_a": "Verify stats update in real-time",
        "part_b": "Change lead status, verify stats widget updates without refresh",
        "key_files": ["frontend/app/dashboard/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard in browser (authenticated)",
                "2. Note the current stats values (total leads, etc.)",
                "3. In another tab, update a lead's ALS score via API",
                "4. Watch the ALS distribution widget without refreshing",
                "5. Verify tier counts update to reflect score change",
                "6. Verify total stats remain consistent"
            ],
            "expect": {
                "stats_update_automatically": True,
                "als_distribution_updates": True,
                "no_refresh_needed": True
            },
            "curl_command": """curl -X PATCH '{api_url}/api/v1/leads/{lead_id}' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"als_score": 90}'"""
        }
    },
]

PASS_CRITERIA = [
    "Real-time connection establishes successfully",
    "New leads appear without page refresh",
    "Email events update activity feed in real-time",
    "Stats widgets update without refresh",
]

KEY_FILES = [
    "frontend/app/dashboard/page.tsx",
    "frontend/components/dashboard/ActivityTicker.tsx",
    "src/api/routes/customers.py",
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_live_url(path: str) -> str:
    """Get full URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"


def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"


def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Realtime Channels")
    for channel in REALTIME_CHANNELS:
        lines.append(f"  - {channel['name']}: {', '.join(channel['events'])}")
    lines.append("")
    lines.append("### Realtime Update Types")
    for update in REALTIME_UPDATE_TYPES:
        lines.append(f"  - {update['type']}: {update['description']} -> {update['widget']}")
    lines.append("")
    lines.append("### Polling Fallback")
    lines.append(f"  Enabled: {POLLING_FALLBACK['enabled']}")
    lines.append(f"  Interval: {POLLING_FALLBACK['interval_ms']}ms")
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
            if lt.get("steps"):
                lines.append("  Steps:")
                for step in lt["steps"]:
                    lines.append(f"    {step}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    lines.append("")
    lines.append("### Key Files")
    for f in KEY_FILES:
        lines.append(f"- {f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_instructions())
