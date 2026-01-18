"""
Skill: J10.15 — Admin Settings
Journey: J10 - Admin Dashboard
Checks: 4

Purpose: Verify admin settings page and user management.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "client_id": "81dbaee6-4e71-48ad-be40-fa915fae66e0",
    "user_id": "a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2",
    "test_email": "david.stephens@keiracom.com",
    "test_phone": "+61457543392",
    "test_admin": {
        "email": "david.stephens@keiracom.com",
        "role": "admin"
    }
}

# =============================================================================
# ADMIN SETTINGS CONSTANTS
# =============================================================================

SETTINGS_CATEGORIES = [
    {"category": "General", "settings": ["Agency name", "Timezone", "Default language"]},
    {"category": "Outreach", "settings": ["Daily email limit", "Daily LinkedIn limit", "Retry attempts"]},
    {"category": "Scoring", "settings": ["Hot threshold", "Cold threshold", "Decay rate"]},
    {"category": "Notifications", "settings": ["Alert email", "Slack webhook", "Critical alerts only"]},
    {"category": "Integrations", "settings": ["API keys", "Webhook URLs", "OAuth connections"]}
]

USER_ROLES = {
    "super_admin": {"description": "Full system access", "can_manage_admins": True},
    "admin": {"description": "Admin dashboard access", "can_manage_admins": False},
    "user": {"description": "Standard user access", "can_manage_admins": False},
    "client": {"description": "Client portal access only", "can_manage_admins": False}
}

GLOBAL_SETTINGS = {
    "als_thresholds": {"hot": 85, "warm": 60, "cool": 35, "cold": 20},
    "outreach_limits": {"email_daily": 500, "linkedin_daily": 100, "sms_daily": 200},
    "retry_config": {"max_retries": 3, "retry_delay_hours": 24}
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.15.1",
        "part_a": "Read `frontend/app/admin/settings/page.tsx` — verify layout",
        "part_b": "Load settings page, verify sections render",
        "key_files": ["frontend/app/admin/settings/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin/settings",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Settings", "General", "Users"]
            },
            "manual_steps": [
                "1. Login as admin user",
                "2. Navigate to {frontend_url}/admin/settings",
                "3. Verify settings page loads",
                "4. Check category tabs/sections: General, Outreach, Scoring, etc."
            ]
        }
    },
    {
        "id": "J10.15.2",
        "part_a": "Read `frontend/app/admin/settings/users/page.tsx` — verify user list",
        "part_b": "Load users page, verify admin users display",
        "key_files": ["frontend/app/admin/settings/users/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/settings/users",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["id", "email", "role", "created_at"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/settings/users' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/settings page, click 'Users' tab/section",
                "2. Verify user list displays",
                "3. Check each user shows: email, role, status",
                "4. Verify current user is highlighted or marked"
            ]
        }
    },
    {
        "id": "J10.15.3",
        "part_a": "Verify global settings management",
        "part_b": "Check global config options are editable",
        "key_files": ["frontend/app/admin/settings/page.tsx", "src/api/routes/admin.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/settings/global",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["als_thresholds", "outreach_limits"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/settings/global' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/settings page, locate 'Scoring' section",
                "2. Verify ALS thresholds are displayed and editable",
                "3. Change Hot threshold from 85 to 86",
                "4. Click Save",
                "5. Refresh page and verify change persisted",
                "6. Revert change back to 85"
            ],
            "update_test": {
                "method": "PATCH",
                "url": "{api_url}/api/v1/admin/settings/global",
                "body": {"als_thresholds": {"hot": 85}},
                "expect": {"status": 200}
            },
            "warning": "Modifying global settings affects all clients - test carefully"
        }
    },
    {
        "id": "J10.15.4",
        "part_a": "Verify admin user role management",
        "part_b": "Check admin can promote/demote user roles",
        "key_files": ["frontend/app/admin/settings/users/page.tsx", "src/api/routes/admin.py"],
        "live_test": {
            "type": "api",
            "method": "PATCH",
            "url": "{api_url}/api/v1/admin/settings/users/{user_id}/role",
            "auth": True,
            "body": {
                "role": "admin"
            },
            "expect": {
                "status": 200,
                "body_has_field": "role"
            },
            "curl_command": """curl -X PATCH '{api_url}/api/v1/admin/settings/users/{user_id}/role' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"role": "admin"}'""",
            "manual_steps": [
                "1. On /admin/settings/users page, find a test user",
                "2. Click 'Edit Role' or role dropdown",
                "3. Change role from 'user' to 'admin'",
                "4. Verify confirmation modal appears",
                "5. Confirm change",
                "6. Verify user role updated in list",
                "7. Revert role back to original"
            ],
            "warning": "Only super_admin can promote users to admin role",
            "note": "Do not demote yourself or the only admin"
        }
    }
]

PASS_CRITERIA = [
    "Settings page loads correctly",
    "User list displays correctly",
    "Global settings are editable",
    "Role management functions"
]

KEY_FILES = [
    "frontend/app/admin/settings/page.tsx",
    "frontend/app/admin/settings/users/page.tsx",
    "src/api/routes/admin.py"
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
    lines.append(f"- Settings Page: {LIVE_CONFIG['frontend_url']}/admin/settings")
    lines.append("")
    lines.append("### Settings Categories")
    for cat in SETTINGS_CATEGORIES:
        lines.append(f"  - {cat['category']}: {', '.join(cat['settings'][:2])}...")
    lines.append("")
    lines.append("### User Roles")
    for role, info in USER_ROLES.items():
        admin_note = " (can manage admins)" if info["can_manage_admins"] else ""
        lines.append(f"  - {role}: {info['description']}{admin_note}")
    lines.append("")
    lines.append("### Global Settings Reference")
    lines.append(f"  ALS Thresholds: Hot={GLOBAL_SETTINGS['als_thresholds']['hot']}, " +
                f"Warm={GLOBAL_SETTINGS['als_thresholds']['warm']}, " +
                f"Cool={GLOBAL_SETTINGS['als_thresholds']['cool']}")
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
        if lt.get("curl_command"):
            lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        if lt.get("warning"):
            lines.append(f"  Warning: {lt['warning']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
