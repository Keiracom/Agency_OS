"""
Skill: J10.5 — Alerts Section
Journey: J10 - Admin Dashboard
Checks: 4

Purpose: Verify critical alerts display and notification system.
"""

CHECKS = [
    {
        "id": "J10.5.1",
        "part_a": "Read admin page alerts component — verify alert types",
        "part_b": "Load dashboard, verify alerts section renders",
        "key_files": ["frontend/app/admin/page.tsx"]
    },
    {
        "id": "J10.5.2",
        "part_a": "Verify critical alerts display with priority",
        "part_b": "Create test alert, verify it appears in list",
        "key_files": ["frontend/app/admin/page.tsx", "src/api/routes/admin.py"]
    },
    {
        "id": "J10.5.3",
        "part_a": "Verify alert dismissal functionality",
        "part_b": "Dismiss an alert, verify it is removed",
        "key_files": ["frontend/app/admin/page.tsx"]
    },
    {
        "id": "J10.5.4",
        "part_a": "Verify alert actions (view details, take action)",
        "part_b": "Click alert action, verify navigation or modal",
        "key_files": ["frontend/app/admin/page.tsx"]
    }
]

PASS_CRITERIA = [
    "Alerts section renders correctly",
    "Critical alerts show with proper priority",
    "Alert dismissal works",
    "Alert actions navigate correctly"
]

KEY_FILES = [
    "frontend/app/admin/page.tsx",
    "src/api/routes/admin.py"
]

# Alert Types Reference
ALERT_TYPES = [
    {"type": "critical", "color": "red", "priority": 1, "examples": ["System down", "API key expired"]},
    {"type": "warning", "color": "yellow", "priority": 2, "examples": ["Rate limit approaching", "Budget threshold"]},
    {"type": "info", "color": "blue", "priority": 3, "examples": ["New client signup", "Campaign completed"]}
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
