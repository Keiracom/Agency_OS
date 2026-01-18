"""
Skill: J10.2 — Command Center Page
Journey: J10 - Admin Dashboard
Checks: 6

Purpose: Verify the main admin command center dashboard page functionality.
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
# ADMIN DASHBOARD CONSTANTS
# =============================================================================

DASHBOARD_SECTIONS = [
    {"section": "KPIs", "purpose": "Key performance indicators at a glance", "required": True},
    {"section": "System Status", "purpose": "Health of all system components", "required": True},
    {"section": "Alerts", "purpose": "Critical issues requiring attention", "required": True},
    {"section": "Live Activity", "purpose": "Real-time event stream", "required": False},
    {"section": "Quick Actions", "purpose": "Common admin actions", "required": False}
]

NAV_LINKS = [
    {"label": "Dashboard", "path": "/admin", "icon": "home"},
    {"label": "Clients", "path": "/admin/clients", "icon": "users"},
    {"label": "Revenue", "path": "/admin/revenue", "icon": "dollar-sign"},
    {"label": "AI Costs", "path": "/admin/costs/ai", "icon": "cpu"},
    {"label": "System", "path": "/admin/system", "icon": "server"},
    {"label": "Compliance", "path": "/admin/compliance", "icon": "shield"},
    {"label": "Settings", "path": "/admin/settings", "icon": "settings"}
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.2.1",
        "part_a": "Read `frontend/app/admin/page.tsx` — verify dashboard layout",
        "part_b": "Load /admin page, verify all sections render",
        "key_files": ["frontend/app/admin/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Dashboard", "KPI", "Status", "Alerts"]
            },
            "manual_steps": [
                "1. Login as admin user",
                "2. Navigate to {frontend_url}/admin",
                "3. Verify page loads without console errors",
                "4. Check all dashboard sections render"
            ]
        }
    },
    {
        "id": "J10.2.2",
        "part_a": "Verify KPI cards section exists",
        "part_b": "Check KPI section displays key metrics",
        "key_files": ["frontend/app/admin/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. On /admin page, locate KPI cards section",
                "2. Verify cards for: Active Leads, Campaigns, Revenue, AI Costs, Clients",
                "3. Check each card displays a numeric value",
                "4. Verify trend indicators (up/down arrows) are visible"
            ],
            "expect": {
                "kpi_cards_count": ">=5",
                "shows_numeric_values": True,
                "shows_trend_indicators": True
            }
        }
    },
    {
        "id": "J10.2.3",
        "part_a": "Verify system status section exists",
        "part_b": "Check system health indicators render",
        "key_files": ["frontend/app/admin/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/health/ready",
            "auth": False,
            "expect": {
                "status": 200,
                "body_has_field": "status"
            },
            "curl_command": """curl '{api_url}/api/v1/health/ready'"""
        }
    },
    {
        "id": "J10.2.4",
        "part_a": "Verify alerts section exists",
        "part_b": "Check critical alerts display correctly",
        "key_files": ["frontend/app/admin/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. On /admin page, locate Alerts section",
                "2. Verify alerts are sorted by priority (critical first)",
                "3. Check each alert shows: type, message, timestamp",
                "4. Verify dismiss button is functional"
            ],
            "expect": {
                "alerts_section_exists": True,
                "sorted_by_priority": True
            }
        }
    },
    {
        "id": "J10.2.5",
        "part_a": "Verify live activity feed section exists",
        "part_b": "Check real-time activity displays",
        "key_files": ["frontend/app/admin/page.tsx", "frontend/app/admin/activity/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/activity?limit=10",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True
            },
            "curl_command": """curl '{api_url}/api/v1/admin/activity?limit=10' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J10.2.6",
        "part_a": "Verify navigation sidebar links work",
        "part_b": "Click each nav link, verify navigation to correct page",
        "key_files": ["frontend/app/admin/layout.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. On /admin page, locate sidebar navigation",
                "2. Click 'Clients' link, verify navigation to /admin/clients",
                "3. Click 'Revenue' link, verify navigation to /admin/revenue",
                "4. Click 'AI Costs' link, verify navigation to /admin/costs/ai",
                "5. Click 'System' link, verify navigation to /admin/system",
                "6. Click 'Settings' link, verify navigation to /admin/settings"
            ],
            "expect": {
                "all_links_work": True,
                "correct_page_loads": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Admin dashboard loads without errors",
    "All dashboard sections render",
    "KPI cards show current data",
    "System status indicators work",
    "Navigation sidebar functions correctly",
    "Page is responsive across breakpoints"
]

KEY_FILES = [
    "frontend/app/admin/page.tsx",
    "frontend/app/admin/layout.tsx",
    "frontend/app/admin/activity/page.tsx"
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
    lines.append(f"- Admin Page: {LIVE_CONFIG['frontend_url']}/admin")
    lines.append("")
    lines.append("### Dashboard Sections")
    for section in DASHBOARD_SECTIONS:
        req = "Required" if section["required"] else "Optional"
        lines.append(f"  - {section['section']}: {section['purpose']} ({req})")
    lines.append("")
    lines.append("### Navigation Links")
    for link in NAV_LINKS[:4]:
        lines.append(f"  - {link['label']}: {link['path']}")
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
        if lt.get("manual_steps"):
            lines.append("  Manual Steps:")
            for step in lt["manual_steps"][:3]:
                lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
