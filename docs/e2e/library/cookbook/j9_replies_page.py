"""
Skill: J9.11 — Replies Page
Journey: J9 - Client Dashboard
Checks: 5

Purpose: Verify replies page displays all email replies with sentiment analysis,
allows reply management, and shows conversation threads.
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
# REPLIES CONSTANTS
# =============================================================================

SENTIMENT_TYPES = [
    {"value": "positive", "label": "Positive", "color": "green", "description": "Interested, wants to talk"},
    {"value": "neutral", "label": "Neutral", "color": "yellow", "description": "Needs more info"},
    {"value": "negative", "label": "Negative", "color": "red", "description": "Not interested, unsubscribe"},
    {"value": "ooo", "label": "Out of Office", "color": "gray", "description": "Auto-reply, OOO"},
]

REPLY_STATUSES = [
    {"value": "unread", "label": "Unread"},
    {"value": "read", "label": "Read"},
    {"value": "actioned", "label": "Actioned"},
    {"value": "archived", "label": "Archived"},
]

REPLY_ACTIONS = [
    "mark_as_read",
    "mark_as_actioned",
    "archive",
    "forward_to_sales",
    "schedule_meeting",
]

REPLY_TABLE_COLUMNS = [
    "lead_name",
    "subject",
    "sentiment",
    "status",
    "received_at",
    "preview",
]

# =============================================================================
# API ENDPOINTS
# =============================================================================

API_ENDPOINTS = [
    {"method": "GET", "path": "/api/v1/replies", "purpose": "List replies for tenant", "auth": True},
    {"method": "GET", "path": "/api/v1/replies?sentiment=positive", "purpose": "Filter by sentiment", "auth": True},
    {"method": "GET", "path": "/api/v1/replies/{id}", "purpose": "Get reply details with thread", "auth": True},
    {"method": "PATCH", "path": "/api/v1/replies/{id}", "purpose": "Update reply status", "auth": True},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.11.1",
        "part_a": "Verify replies page renders",
        "part_b": "Navigate to /dashboard/replies, check page renders with reply list",
        "key_files": ["frontend/app/dashboard/replies/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/dashboard/replies",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["replies", "Sentiment", "Status"]
            },
            "curl_command": """curl '{frontend_url}/dashboard/replies' \\
  -H 'Cookie: sb-access-token={token}'"""
        }
    },
    {
        "id": "J9.11.2",
        "part_a": "Verify replies API returns data for tenant",
        "part_b": "GET /api/v1/replies returns replies scoped to authenticated client",
        "key_files": ["src/api/routes/replies.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/replies",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_field": "data",
                "replies_have_fields": ["id", "lead_id", "sentiment", "status", "received_at"]
            },
            "curl_command": """curl '{api_url}/api/v1/replies' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.11.3",
        "part_a": "Verify sentiment indicators display",
        "part_b": "Each reply shows sentiment badge (positive, neutral, negative)",
        "key_files": ["frontend/app/dashboard/replies/page.tsx", "frontend/components/ui/badge.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard/replies (authenticated)",
                "2. Look at reply rows in the list",
                "3. Verify each reply has a sentiment badge",
                "4. Check badge colors: green=positive, yellow=neutral, red=negative, gray=ooo",
                "5. Verify badge accurately reflects AI-detected sentiment"
            ],
            "expect": {
                "sentiment_badges_visible": True,
                "colors_match_sentiment": True,
                "sentiments": ["positive", "neutral", "negative", "ooo"]
            }
        }
    },
    {
        "id": "J9.11.4",
        "part_a": "Verify reply filtering works",
        "part_b": "Filter by sentiment or status, verify filtered results",
        "key_files": ["frontend/app/dashboard/replies/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/replies?sentiment=positive",
            "auth": True,
            "expect": {
                "status": 200,
                "all_replies_have_sentiment": "positive"
            },
            "curl_command": """curl '{api_url}/api/v1/replies?sentiment=positive' \\
  -H 'Authorization: Bearer {token}' | jq '.data[] | select(.sentiment != "positive")'"""
        }
    },
    {
        "id": "J9.11.5",
        "part_a": "Verify conversation thread displays",
        "part_b": "Click reply, view full email thread with original outbound email",
        "key_files": ["frontend/app/dashboard/replies/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/replies/{reply_id}",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["id", "body", "thread"],
                "thread_has_original_email": True
            },
            "curl_command": """curl '{api_url}/api/v1/replies/{reply_id}' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
]

PASS_CRITERIA = [
    "Replies page renders without errors",
    "Replies API returns data for tenant",
    "Sentiment indicators display correctly",
    "Reply filtering works by sentiment/status",
    "Conversation thread displays full context",
]

KEY_FILES = [
    "frontend/app/dashboard/replies/page.tsx",
    "src/api/routes/replies.py",
    "src/models/reply.py",
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
    lines.append("### Sentiment Types")
    for sentiment in SENTIMENT_TYPES:
        lines.append(f"  - {sentiment['value']}: {sentiment['label']} ({sentiment['color']}) - {sentiment['description']}")
    lines.append("")
    lines.append("### Reply Statuses")
    for status in REPLY_STATUSES:
        lines.append(f"  - {status['value']}: {status['label']}")
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
