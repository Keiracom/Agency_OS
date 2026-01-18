"""
Skill: J9.12 — Settings Page
Journey: J9 - Client Dashboard
Checks: 3

Purpose: Verify settings page allows client to configure account preferences,
notification settings, and integration connections.
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
# SETTINGS CONSTANTS
# =============================================================================

SETTINGS_SECTIONS = [
    {"name": "profile", "label": "Profile", "path": "/dashboard/settings"},
    {"name": "icp", "label": "ICP Settings", "path": "/dashboard/settings/icp"},
    {"name": "linkedin", "label": "LinkedIn", "path": "/dashboard/settings/linkedin"},
    {"name": "notifications", "label": "Notifications", "path": "/dashboard/settings/notifications"},
    {"name": "integrations", "label": "Integrations", "path": "/dashboard/settings/integrations"},
    {"name": "billing", "label": "Billing", "path": "/dashboard/settings/billing"},
]

ICP_SETTINGS_FIELDS = [
    "target_industries",
    "target_company_sizes",
    "target_job_titles",
    "target_locations",
    "exclusion_criteria",
    "custom_signals",
]

LINKEDIN_SETTINGS = [
    "account_connected",
    "daily_connection_limit",
    "daily_message_limit",
    "sync_enabled",
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.12.1",
        "part_a": "Verify settings page renders",
        "part_b": "Navigate to /dashboard/settings, check page renders with settings options",
        "key_files": ["frontend/app/dashboard/settings/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/dashboard/settings",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["settings", "Profile", "ICP"]
            },
            "curl_command": """curl '{frontend_url}/dashboard/settings' \\
  -H 'Cookie: sb-access-token={token}'"""
        }
    },
    {
        "id": "J9.12.2",
        "part_a": "Verify ICP settings link works",
        "part_b": "Click ICP settings link, navigate to /dashboard/settings/icp",
        "key_files": ["frontend/app/dashboard/settings/page.tsx", "frontend/app/dashboard/settings/icp/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard/settings (authenticated)",
                "2. Look for 'ICP Settings' link/card",
                "3. Click on 'ICP Settings'",
                "4. Verify navigation to /dashboard/settings/icp",
                "5. Verify ICP settings form loads with current values"
            ],
            "expect": {
                "link_visible": True,
                "click_navigates_to": "/dashboard/settings/icp",
                "icp_form_loads": True
            }
        }
    },
    {
        "id": "J9.12.3",
        "part_a": "Verify LinkedIn settings link works",
        "part_b": "Click LinkedIn settings link, navigate to /dashboard/settings/linkedin",
        "key_files": ["frontend/app/dashboard/settings/page.tsx", "frontend/app/dashboard/settings/linkedin/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard/settings (authenticated)",
                "2. Look for 'LinkedIn' link/card",
                "3. Click on 'LinkedIn'",
                "4. Verify navigation to /dashboard/settings/linkedin",
                "5. Verify LinkedIn connection status displays"
            ],
            "expect": {
                "link_visible": True,
                "click_navigates_to": "/dashboard/settings/linkedin",
                "linkedin_settings_load": True
            }
        }
    },
]

PASS_CRITERIA = [
    "Settings page renders without errors",
    "ICP settings navigation works",
    "LinkedIn settings navigation works",
]

KEY_FILES = [
    "frontend/app/dashboard/settings/page.tsx",
    "frontend/app/dashboard/settings/icp/page.tsx",
    "frontend/app/dashboard/settings/linkedin/page.tsx",
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
    lines.append("### Settings Sections")
    for section in SETTINGS_SECTIONS:
        lines.append(f"  - {section['name']}: {section['label']} ({section['path']})")
    lines.append("")
    lines.append("### ICP Settings Fields")
    for field in ICP_SETTINGS_FIELDS:
        lines.append(f"  - {field}")
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
