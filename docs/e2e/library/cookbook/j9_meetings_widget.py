"""
Skill: J9.5 — Meetings Widget
Journey: J9 - Client Dashboard
Checks: 4

Purpose: Verify meetings widget displays upcoming meetings, integrates with
calendar data, and shows correct meeting counts and details.
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
# MEETING CONSTANTS
# =============================================================================

MEETING_STATUSES = ["scheduled", "completed", "cancelled", "no_show"]

MEETING_TYPES = [
    "discovery_call",
    "demo",
    "follow_up",
    "closing_call",
    "onboarding",
]

MEETING_FIELDS = [
    "id",
    "lead_id",
    "scheduled_at",
    "duration_minutes",
    "meeting_type",
    "status",
    "notes",
    "calendar_event_id",
]

DATE_RANGE_FILTERS = {
    "today": "Today's meetings",
    "this_week": "This week's meetings",
    "this_month": "This month's meetings",
    "upcoming": "All upcoming meetings",
}

# =============================================================================
# API ENDPOINTS
# =============================================================================

API_ENDPOINTS = [
    {"method": "GET", "path": "/api/v1/meetings", "purpose": "List meetings for tenant", "auth": True},
    {"method": "GET", "path": "/api/v1/meetings/upcoming", "purpose": "Get upcoming meetings", "auth": True},
    {"method": "GET", "path": "/api/v1/meetings/{id}", "purpose": "Get meeting details", "auth": True},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.5.1",
        "part_a": "Verify meetings widget renders on dashboard",
        "part_b": "Check MeetingsWidget component is visible with meeting list",
        "key_files": ["frontend/components/dashboard/meetings-widget.tsx", "frontend/app/dashboard/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard (authenticated)",
                "2. Look for meetings widget on the dashboard",
                "3. Verify widget shows upcoming meetings or 'No meetings' message",
                "4. Check widget has proper styling and layout"
            ],
            "expect": {
                "widget_visible": True,
                "meetings_or_empty_state_shown": True
            }
        }
    },
    {
        "id": "J9.5.2",
        "part_a": "Verify meetings API returns scheduled meetings",
        "part_b": "GET /api/v1/meetings returns array of upcoming meetings for tenant",
        "key_files": ["src/api/routes/meetings.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/meetings",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["id", "lead_id", "scheduled_at", "meeting_type"]
            },
            "curl_command": """curl '{api_url}/api/v1/meetings' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.5.3",
        "part_a": "Verify meeting details display correctly",
        "part_b": "Each meeting shows date, time, lead name, and meeting type",
        "key_files": ["frontend/components/dashboard/meetings-widget.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard (authenticated)",
                "2. Look at meetings widget with scheduled meetings",
                "3. Verify each meeting shows date (e.g., 'Jan 20, 2026')",
                "4. Verify each meeting shows time (e.g., '10:00 AM')",
                "5. Verify lead name is displayed",
                "6. Verify meeting type badge (e.g., 'Discovery Call', 'Demo')"
            ],
            "expect": {
                "date_displayed": True,
                "time_displayed": True,
                "lead_name_displayed": True,
                "meeting_type_badge": True
            }
        }
    },
    {
        "id": "J9.5.4",
        "part_a": "Verify meetings count badge shows correct number",
        "part_b": "Badge shows count of meetings scheduled this week/month",
        "key_files": ["frontend/components/dashboard/meetings-widget.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/meetings/upcoming",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_field": "count"
            },
            "curl_command": """curl '{api_url}/api/v1/meetings/upcoming' \\
  -H 'Authorization: Bearer {token}' | jq '.count'"""
        }
    },
]

PASS_CRITERIA = [
    "Meetings widget renders without errors",
    "Meetings API returns data for authenticated tenant",
    "Meeting details (date, time, lead, type) display correctly",
    "Meetings count badge reflects actual count",
]

KEY_FILES = [
    "frontend/components/dashboard/meetings-widget.tsx",
    "frontend/app/dashboard/page.tsx",
    "src/api/routes/meetings.py",
    "src/models/meeting.py",
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
    lines.append("### Meeting Types")
    for mtype in MEETING_TYPES:
        lines.append(f"  - {mtype}")
    lines.append("")
    lines.append("### API Endpoints")
    for ep in API_ENDPOINTS:
        lines.append(f"  {ep['method']} {ep['path']} - {ep['purpose']}")
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
