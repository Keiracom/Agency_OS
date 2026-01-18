"""
Skill: J9.3 — Activity Feed
Journey: J9 - Client Dashboard
Checks: 6

Purpose: Verify activity feed widget displays recent actions including lead
updates, email sends, replies, and campaign events with correct timestamps.
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
# ACTIVITY EVENT TYPES
# =============================================================================

ACTIVITY_EVENT_TYPES = {
    "lead_created": {
        "description": "New lead added to system",
        "icon": "user-plus",
        "color": "green",
    },
    "lead_score_updated": {
        "description": "Lead ALS score changed",
        "icon": "trending-up",
        "color": "blue",
    },
    "lead_status_changed": {
        "description": "Lead status changed (e.g., to qualified)",
        "icon": "refresh",
        "color": "yellow",
    },
    "email_sent": {
        "description": "Email sent to lead",
        "icon": "mail",
        "color": "blue",
    },
    "email_opened": {
        "description": "Lead opened email",
        "icon": "eye",
        "color": "green",
    },
    "email_clicked": {
        "description": "Lead clicked link in email",
        "icon": "mouse-pointer",
        "color": "green",
    },
    "reply_received": {
        "description": "Lead replied to email",
        "icon": "message-circle",
        "color": "purple",
    },
    "meeting_booked": {
        "description": "Meeting scheduled with lead",
        "icon": "calendar",
        "color": "green",
    },
}

TIMESTAMP_FORMATS = {
    "relative": "2 hours ago",
    "absolute": "Jan 18, 2026 10:30 AM",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.3.1",
        "part_a": "Verify activity feed component renders",
        "part_b": "Check ActivityTicker or LiveActivityFeed component is visible on dashboard",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx", "frontend/components/admin/LiveActivityFeed.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard (authenticated)",
                "2. Look for activity feed widget on the dashboard",
                "3. Verify component is visible and displays events",
                "4. Check for ActivityTicker or LiveActivityFeed component"
            ],
            "expect": {
                "activity_feed_visible": True,
                "events_displayed": True
            }
        }
    },
    {
        "id": "J9.3.2",
        "part_a": "Verify activity feed shows lead events",
        "part_b": "Check feed displays lead creation, score updates, status changes",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx"],
        "live_test": {
            "type": "db_query",
            "description": "Query recent lead events and compare to feed",
            "query": """SELECT event_type, lead_id, created_at
                       FROM activity_events
                       WHERE client_id = '{client_id}'
                       AND event_type IN ('lead_created', 'lead_score_updated', 'lead_status_changed')
                       ORDER BY created_at DESC
                       LIMIT 10""",
            "expect": {
                "events_match_feed": True,
                "event_types": ["lead_created", "lead_score_updated", "lead_status_changed"]
            }
        }
    },
    {
        "id": "J9.3.3",
        "part_a": "Verify activity feed shows email events",
        "part_b": "Check feed displays email sent, opened, clicked events",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard (authenticated)",
                "2. Look at activity feed for email events",
                "3. Check for 'Email sent to [name]' events",
                "4. Check for 'Email opened by [name]' events",
                "5. Check for 'Link clicked by [name]' events"
            ],
            "expect": {
                "email_sent_events": True,
                "email_opened_events": True,
                "email_clicked_events": True
            }
        }
    },
    {
        "id": "J9.3.4",
        "part_a": "Verify activity feed shows reply events",
        "part_b": "Check feed displays new reply notifications with sentiment indicator",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard (authenticated)",
                "2. Look for reply events in activity feed",
                "3. Check reply shows lead name and subject",
                "4. Verify sentiment indicator (positive/neutral/negative) is visible",
                "5. Check color coding matches sentiment"
            ],
            "expect": {
                "reply_events_visible": True,
                "sentiment_indicator_shown": True,
                "color_coding_correct": True
            }
        }
    },
    {
        "id": "J9.3.5",
        "part_a": "Verify timestamps are formatted correctly",
        "part_b": "Check timestamps show relative time (e.g., '2 hours ago') or formatted date",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx"],
        "live_test": {
            "type": "code_verify",
            "check": "Activity feed uses formatDistanceToNow or similar for relative timestamps",
            "expect": {
                "code_contains": ["formatDistanceToNow", "timeAgo", "moment", "dayjs"]
            }
        }
    },
    {
        "id": "J9.3.6",
        "part_a": "Verify activity feed is scoped to client",
        "part_b": "Feed should only show activities for the authenticated client's tenant",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx", "src/api/routes/customers.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/customers/activity",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_field": "events",
                "events_scoped_to_tenant": True
            },
            "curl_command": """curl '{api_url}/api/v1/customers/activity' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
]

PASS_CRITERIA = [
    "Activity feed component renders without errors",
    "Lead events appear in feed (create, update, score change)",
    "Email events appear in feed (sent, opened, clicked)",
    "Reply events appear with sentiment indicators",
    "Timestamps formatted as relative time or readable date",
    "Activities scoped to authenticated client only",
]

KEY_FILES = [
    "frontend/components/dashboard/ActivityTicker.tsx",
    "frontend/components/admin/LiveActivityFeed.tsx",
    "frontend/app/dashboard/page.tsx",
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
    lines.append("### Activity Event Types")
    for event_type, details in ACTIVITY_EVENT_TYPES.items():
        lines.append(f"  {event_type}: {details['description']} (color: {details['color']})")
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
