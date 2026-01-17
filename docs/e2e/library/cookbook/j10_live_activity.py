"""
Skill: J10.6 — Live Activity Feed
Journey: J10 - Admin Dashboard
Checks: 5

Purpose: Verify real-time activity feed displays system events.
"""

CHECKS = [
    {
        "id": "J10.6.1",
        "part_a": "Read `frontend/app/admin/activity/page.tsx` — verify activity feed",
        "part_b": "Load activity page, verify events display",
        "key_files": ["frontend/app/admin/activity/page.tsx"]
    },
    {
        "id": "J10.6.2",
        "part_a": "Verify activity events show timestamp and user",
        "part_b": "Check each event has proper metadata",
        "key_files": ["frontend/app/admin/activity/page.tsx"]
    },
    {
        "id": "J10.6.3",
        "part_a": "Verify activity filtering by type",
        "part_b": "Filter by event type, verify list updates",
        "key_files": ["frontend/app/admin/activity/page.tsx"]
    },
    {
        "id": "J10.6.4",
        "part_a": "Verify activity pagination or infinite scroll",
        "part_b": "Scroll down, verify more events load",
        "key_files": ["frontend/app/admin/activity/page.tsx"]
    },
    {
        "id": "J10.6.5",
        "part_a": "Verify real-time updates (polling or websocket)",
        "part_b": "Trigger event, verify it appears without refresh",
        "key_files": ["frontend/app/admin/activity/page.tsx"]
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

# Activity Event Types Reference
ACTIVITY_EVENTS = [
    {"type": "lead_created", "icon": "user-plus", "description": "New lead added to system"},
    {"type": "email_sent", "icon": "mail", "description": "Outreach email sent"},
    {"type": "campaign_started", "icon": "play", "description": "Campaign execution began"},
    {"type": "reply_received", "icon": "message-circle", "description": "Lead replied to outreach"},
    {"type": "client_signup", "icon": "briefcase", "description": "New client registered"},
    {"type": "system_error", "icon": "alert-triangle", "description": "System error occurred"}
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
