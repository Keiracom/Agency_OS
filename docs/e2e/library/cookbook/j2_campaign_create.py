"""
Skill: J2.1 — Campaign List Page
Journey: J2 - Campaign Creation & Management
Checks: 5

Purpose: Verify campaign list displays real data from API.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "test_user": {
        "email": "david.stephens@keiracom.com"
    }
}

# =============================================================================
# CAMPAIGN STATUSES
# =============================================================================

CAMPAIGN_STATUSES = ["draft", "active", "paused", "completed"]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2.1.1",
        "part_a": "Read `frontend/app/dashboard/campaigns/page.tsx` — verify `useCampaigns` hook",
        "part_b": "Load `/dashboard/campaigns`, check network tab",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/dashboard/campaigns",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Campaigns", "Create", "Status"]
            },
            "manual_steps": [
                "1. Login and navigate to /dashboard/campaigns",
                "2. Open DevTools > Network tab",
                "3. Look for GET /api/v1/campaigns call",
                "4. Verify response contains campaign array"
            ]
        }
    },
    {
        "id": "J2.1.2",
        "part_a": "Verify API endpoint `GET /api/v1/campaigns` exists in `campaigns.py`",
        "part_b": "Confirm campaigns list renders",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/campaigns",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["id", "name", "status", "created_at"]
            },
            "curl_command": """curl '{api_url}/api/v1/campaigns' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J2.1.3",
        "part_a": "Check status filter implementation (active/paused/draft/completed)",
        "part_b": "Click each filter, verify response",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx"],
        "live_test": {
            "type": "api_batch",
            "tests": [
                {
                    "name": "Filter by draft",
                    "method": "GET",
                    "url": "{api_url}/api/v1/campaigns?status=draft",
                    "expect": {"all_items_have": {"status": "draft"}}
                },
                {
                    "name": "Filter by active",
                    "method": "GET",
                    "url": "{api_url}/api/v1/campaigns?status=active",
                    "expect": {"all_items_have": {"status": "active"}}
                },
                {
                    "name": "Filter by paused",
                    "method": "GET",
                    "url": "{api_url}/api/v1/campaigns?status=paused",
                    "expect": {"all_items_have": {"status": "paused"}}
                }
            ],
            "auth": True,
            "curl_command": """curl '{api_url}/api/v1/campaigns?status=draft' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J2.1.4",
        "part_a": "Check search functionality wiring",
        "part_b": "Search for campaign name",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/campaigns?search={search_term}",
            "auth": True,
            "test_values": {
                "search_term": "test"
            },
            "expect": {
                "status": 200,
                "body_is_array": True
            },
            "manual_steps": [
                "1. Go to /dashboard/campaigns",
                "2. Type a campaign name in search box",
                "3. Verify list filters to matching campaigns",
                "4. Verify empty search shows all campaigns"
            ]
        }
    },
    {
        "id": "J2.1.5",
        "part_a": "Verify channel allocation bar displays correctly",
        "part_b": "Check bar colors match allocations",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Navigate to /dashboard/campaigns",
                "2. Find a campaign with leads assigned to multiple channels",
                "3. Inspect the channel allocation bar component",
                "4. Verify bar segments match: email (blue), SMS (green), voice (orange), LinkedIn (purple)",
                "5. Hover over segments to verify tooltips show counts"
            ],
            "expect": {
                "bar_renders": True,
                "colors_match_channels": True,
                "tooltips_show_counts": True
            },
            "note": "Channel allocation bar may not be visible if no leads assigned"
        }
    }
]

PASS_CRITERIA = [
    "Campaign list loads from API (not mock data)",
    "Status filters work correctly",
    "Search filters work correctly",
    "Channel allocation bar displays accurately"
]

KEY_FILES = [
    "frontend/app/dashboard/campaigns/page.tsx",
    "src/api/routes/campaigns.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Campaigns Page: {LIVE_CONFIG['frontend_url']}/dashboard/campaigns")
    lines.append("")
    lines.append("### Campaign Statuses")
    lines.append(f"  {', '.join(CAMPAIGN_STATUSES)}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("manual_steps"):
            lines.append("  Manual Steps:")
            for step in lt["manual_steps"][:3]:
                lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
