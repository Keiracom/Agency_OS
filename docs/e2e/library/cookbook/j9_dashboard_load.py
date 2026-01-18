"""
Skill: J9.1 — Dashboard Page Load
Journey: J9 - Client Dashboard
Checks: 6

Purpose: Verify dashboard loads correctly for authenticated users with proper
layout, sidebar navigation, and initial data fetching.
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
# DASHBOARD CONSTANTS
# =============================================================================

DASHBOARD_ROUTES = {
    "main": "/dashboard",
    "leads": "/dashboard/leads",
    "campaigns": "/dashboard/campaigns",
    "replies": "/dashboard/replies",
    "reports": "/dashboard/reports",
    "settings": "/dashboard/settings",
}

SIDEBAR_MENU_ITEMS = [
    "Dashboard",
    "Leads",
    "Campaigns",
    "Replies",
    "Reports",
    "Settings",
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.1.1",
        "part_a": "Verify dashboard page renders without errors",
        "part_b": "Navigate to /dashboard as authenticated user, check for React errors",
        "key_files": ["frontend/app/dashboard/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/dashboard",
            "auth": True,
            "expect": {
                "status": 200,
                "no_console_errors": True,
                "body_contains": ["dashboard"]
            },
            "curl_command": """curl '{frontend_url}/dashboard' \\
  -H 'Cookie: sb-access-token={token}'"""
        }
    },
    {
        "id": "J9.1.2",
        "part_a": "Verify dashboard layout renders with sidebar",
        "part_b": "Check that sidebar navigation is visible with all menu items",
        "key_files": ["frontend/app/dashboard/layout.tsx", "frontend/components/layout/sidebar.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard in browser (authenticated)",
                "2. Verify sidebar is visible on left side",
                "3. Check menu items: Dashboard, Leads, Campaigns, Replies, Reports, Settings",
                "4. Verify active menu item is highlighted"
            ],
            "expect": {
                "sidebar_visible": True,
                "menu_items": ["Dashboard", "Leads", "Campaigns", "Replies", "Reports", "Settings"]
            }
        }
    },
    {
        "id": "J9.1.3",
        "part_a": "Verify header renders with user info",
        "part_b": "Check header displays user name, avatar, and credits badge",
        "key_files": ["frontend/components/layout/header.tsx", "frontend/components/layout/credits-badge.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard (authenticated)",
                "2. Check header shows user avatar or initials",
                "3. Verify user name or email is displayed",
                "4. Look for credits badge showing remaining credits"
            ],
            "expect": {
                "header_visible": True,
                "user_info_displayed": True,
                "credits_badge_visible": True
            }
        }
    },
    {
        "id": "J9.1.4",
        "part_a": "Verify loading states display during data fetch",
        "part_b": "Check skeleton loaders appear while API calls are in progress",
        "key_files": ["frontend/components/ui/loading-skeleton.tsx", "frontend/components/ui/skeleton.tsx"],
        "live_test": {
            "type": "code_verify",
            "check": "Dashboard components use Skeleton or loading-skeleton during data fetch",
            "expect": {
                "code_contains": ["Skeleton", "loading", "isLoading"]
            }
        }
    },
    {
        "id": "J9.1.5",
        "part_a": "Verify unauthenticated users are redirected",
        "part_b": "Navigate to /dashboard without auth, verify redirect to /login",
        "key_files": ["frontend/app/dashboard/layout.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/dashboard",
            "auth": False,
            "expect": {
                "status": [302, 307],
                "redirect_to": "/login"
            },
            "curl_command": """curl -I '{frontend_url}/dashboard'"""
        }
    },
    {
        "id": "J9.1.6",
        "part_a": "Verify dashboard widgets render after data loads",
        "part_b": "Check all dashboard widgets (stats, activity, ALS) render with data",
        "key_files": ["frontend/app/dashboard/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard (authenticated)",
                "2. Wait for loading to complete",
                "3. Verify stats cards show numbers (leads, campaigns, etc.)",
                "4. Verify activity feed shows recent events",
                "5. Verify ALS distribution widget shows tier breakdown"
            ],
            "expect": {
                "stats_visible": True,
                "activity_feed_visible": True,
                "als_widget_visible": True
            }
        }
    },
]

PASS_CRITERIA = [
    "Dashboard page loads without console errors",
    "Sidebar navigation displays all menu items",
    "Header shows user info and credits",
    "Loading skeletons appear during data fetch",
    "Unauthenticated users redirect to login",
    "All widgets render with data after loading",
]

KEY_FILES = [
    "frontend/app/dashboard/page.tsx",
    "frontend/app/dashboard/layout.tsx",
    "frontend/components/layout/dashboard-layout.tsx",
    "frontend/components/layout/sidebar.tsx",
    "frontend/components/layout/header.tsx",
    "frontend/components/layout/credits-badge.tsx",
    "frontend/components/ui/loading-skeleton.tsx",
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
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Dashboard Routes")
    for name, route in DASHBOARD_ROUTES.items():
        lines.append(f"  {name}: {route}")
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
