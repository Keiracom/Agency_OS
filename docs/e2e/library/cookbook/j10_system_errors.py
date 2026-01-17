"""
Skill: J10.11 — System Errors Page
Journey: J10 - Admin Dashboard
Checks: 4

Purpose: Verify system error logging and display functionality.
"""

CHECKS = [
    {
        "id": "J10.11.1",
        "part_a": "Read `frontend/app/admin/system/errors/page.tsx` — verify error list",
        "part_b": "Load errors page, verify error log renders",
        "key_files": ["frontend/app/admin/system/errors/page.tsx"]
    },
    {
        "id": "J10.11.2",
        "part_a": "Verify error details display",
        "part_b": "Click error row, verify stack trace and context display",
        "key_files": ["frontend/app/admin/system/errors/page.tsx"]
    },
    {
        "id": "J10.11.3",
        "part_a": "Verify error filtering by severity",
        "part_b": "Filter by critical/warning/info, verify list updates",
        "key_files": ["frontend/app/admin/system/errors/page.tsx"]
    },
    {
        "id": "J10.11.4",
        "part_a": "Verify Sentry integration link",
        "part_b": "Check 'View in Sentry' link works for each error",
        "key_files": ["frontend/app/admin/system/errors/page.tsx"]
    }
]

PASS_CRITERIA = [
    "Error log page loads correctly",
    "Error details display properly",
    "Severity filtering works",
    "Sentry integration is functional"
]

KEY_FILES = [
    "frontend/app/admin/system/errors/page.tsx",
    "src/api/routes/admin.py",
    "src/integrations/sentry_utils.py"
]

# Error Severity Reference
ERROR_SEVERITIES = [
    {"level": "critical", "color": "red", "examples": ["Database connection lost", "API key invalid"]},
    {"level": "error", "color": "orange", "examples": ["Email send failed", "Enrichment failed"]},
    {"level": "warning", "color": "yellow", "examples": ["Rate limit approaching", "Slow response"]},
    {"level": "info", "color": "blue", "examples": ["Scheduled job completed", "Config changed"]}
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
