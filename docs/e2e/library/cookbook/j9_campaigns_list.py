"""
Skill: J9.8 — Campaigns List Page
Journey: J9 - Client Dashboard
Checks: 5

Purpose: Verify campaigns list page displays all campaigns for the client with
status indicators, performance metrics, and filtering options.
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
# CAMPAIGN CONSTANTS
# =============================================================================

CAMPAIGN_STATUSES = [
    {"value": "draft", "label": "Draft", "color": "gray"},
    {"value": "active", "label": "Active", "color": "green"},
    {"value": "paused", "label": "Paused", "color": "yellow"},
    {"value": "completed", "label": "Completed", "color": "blue"},
    {"value": "cancelled", "label": "Cancelled", "color": "red"},
]

CAMPAIGN_METRICS = [
    {"name": "emails_sent", "label": "Emails Sent", "type": "count"},
    {"name": "open_rate", "label": "Open Rate", "type": "percentage"},
    {"name": "click_rate", "label": "Click Rate", "type": "percentage"},
    {"name": "reply_rate", "label": "Reply Rate", "type": "percentage"},
    {"name": "bounce_rate", "label": "Bounce Rate", "type": "percentage"},
    {"name": "leads_enrolled", "label": "Leads Enrolled", "type": "count"},
]

CAMPAIGN_TABLE_COLUMNS = [
    "name",
    "status",
    "leads_enrolled",
    "emails_sent",
    "open_rate",
    "reply_rate",
    "created_at",
]

# =============================================================================
# API ENDPOINTS
# =============================================================================

API_ENDPOINTS = [
    {"method": "GET", "path": "/api/v1/campaigns", "purpose": "List campaigns for tenant", "auth": True},
    {"method": "GET", "path": "/api/v1/campaigns?status=active", "purpose": "Filter by status", "auth": True},
    {"method": "GET", "path": "/api/v1/campaigns/{id}", "purpose": "Get campaign details", "auth": True},
    {"method": "POST", "path": "/api/v1/campaigns", "purpose": "Create new campaign", "auth": True},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.8.1",
        "part_a": "Verify campaigns list page renders",
        "part_b": "Navigate to /dashboard/campaigns, check table renders with campaign data",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/dashboard/campaigns",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["campaigns", "Name", "Status"]
            },
            "curl_command": """curl '{frontend_url}/dashboard/campaigns' \\
  -H 'Cookie: sb-access-token={token}'"""
        }
    },
    {
        "id": "J9.8.2",
        "part_a": "Verify campaigns API returns data for tenant",
        "part_b": "GET /api/v1/campaigns returns campaigns scoped to authenticated client",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/campaigns",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_field": "data",
                "data_is_array": True,
                "items_have_fields": ["id", "name", "status", "client_id"]
            },
            "curl_command": """curl '{api_url}/api/v1/campaigns' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.8.3",
        "part_a": "Verify campaign status indicators display",
        "part_b": "Each campaign shows status badge (draft, active, paused, completed)",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx", "frontend/components/ui/badge.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard/campaigns (authenticated)",
                "2. Look at campaign rows in the table",
                "3. Verify each campaign has a status badge",
                "4. Check badge colors match status (green=active, yellow=paused, etc.)",
                "5. Verify badge text matches campaign status"
            ],
            "expect": {
                "status_badges_visible": True,
                "colors_match_status": True,
                "statuses": ["draft", "active", "paused", "completed"]
            }
        }
    },
    {
        "id": "J9.8.4",
        "part_a": "Verify campaign metrics display",
        "part_b": "Table shows emails sent, open rate, reply rate for each campaign",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/campaigns",
            "auth": True,
            "expect": {
                "status": 200,
                "items_have_metrics": ["emails_sent", "open_rate", "reply_rate"]
            },
            "curl_command": """curl '{api_url}/api/v1/campaigns' \\
  -H 'Authorization: Bearer {token}' | jq '.data[0] | {emails_sent, open_rate, reply_rate}'"""
        }
    },
    {
        "id": "J9.8.5",
        "part_a": "Verify new campaign button navigates correctly",
        "part_b": "Click 'New Campaign' button, navigate to /dashboard/campaigns/new",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx", "frontend/app/dashboard/campaigns/new/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard/campaigns (authenticated)",
                "2. Look for 'New Campaign' button (usually top right)",
                "3. Click the button",
                "4. Verify navigation to /dashboard/campaigns/new",
                "5. Verify campaign creation form loads"
            ],
            "expect": {
                "button_visible": True,
                "click_navigates_to": "/dashboard/campaigns/new",
                "form_loads": True
            }
        }
    },
]

PASS_CRITERIA = [
    "Campaigns list page renders with table",
    "API returns campaigns for authenticated tenant",
    "Campaign status badges display correctly",
    "Campaign metrics (sent, open rate, reply rate) display",
    "New campaign navigation works",
]

KEY_FILES = [
    "frontend/app/dashboard/campaigns/page.tsx",
    "frontend/app/dashboard/campaigns/new/page.tsx",
    "frontend/app/dashboard/campaigns/[id]/page.tsx",
    "src/api/routes/campaigns.py",
    "src/models/campaign.py",
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
    lines.append("### Campaign Statuses")
    for status in CAMPAIGN_STATUSES:
        lines.append(f"  - {status['value']}: {status['label']} ({status['color']})")
    lines.append("")
    lines.append("### Campaign Metrics")
    for metric in CAMPAIGN_METRICS:
        lines.append(f"  - {metric['name']}: {metric['label']} ({metric['type']})")
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
