"""
Skill: J10.15 — Admin Settings
Journey: J10 - Admin Dashboard
Checks: 4

Purpose: Verify admin settings page and user management.
"""

CHECKS = [
    {
        "id": "J10.15.1",
        "part_a": "Read `frontend/app/admin/settings/page.tsx` — verify layout",
        "part_b": "Load settings page, verify sections render",
        "key_files": ["frontend/app/admin/settings/page.tsx"]
    },
    {
        "id": "J10.15.2",
        "part_a": "Read `frontend/app/admin/settings/users/page.tsx` — verify user list",
        "part_b": "Load users page, verify admin users display",
        "key_files": ["frontend/app/admin/settings/users/page.tsx"]
    },
    {
        "id": "J10.15.3",
        "part_a": "Verify global settings management",
        "part_b": "Check global config options are editable",
        "key_files": ["frontend/app/admin/settings/page.tsx", "src/api/routes/admin.py"]
    },
    {
        "id": "J10.15.4",
        "part_a": "Verify admin user role management",
        "part_b": "Check admin can promote/demote user roles",
        "key_files": ["frontend/app/admin/settings/users/page.tsx", "src/api/routes/admin.py"]
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

# Settings Categories Reference
SETTINGS_CATEGORIES = [
    {"category": "General", "settings": ["Agency name", "Timezone", "Default language"]},
    {"category": "Outreach", "settings": ["Daily email limit", "Daily LinkedIn limit", "Retry attempts"]},
    {"category": "Scoring", "settings": ["Hot threshold", "Cold threshold", "Decay rate"]},
    {"category": "Notifications", "settings": ["Alert email", "Slack webhook", "Critical alerts only"]},
    {"category": "Integrations", "settings": ["API keys", "Webhook URLs", "OAuth connections"]}
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
