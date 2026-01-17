"""
Skill: J10.4 — System Status Section
Journey: J10 - Admin Dashboard
Checks: 4

Purpose: Verify system health indicators display correctly.
"""

CHECKS = [
    {
        "id": "J10.4.1",
        "part_a": "Read `frontend/app/admin/system/page.tsx` — verify health indicators",
        "part_b": "Load system page, verify all services show status",
        "key_files": ["frontend/app/admin/system/page.tsx"]
    },
    {
        "id": "J10.4.2",
        "part_a": "Verify database connection status indicator",
        "part_b": "Check Supabase connection shows green/red correctly",
        "key_files": ["frontend/app/admin/system/page.tsx", "src/api/routes/health.py"]
    },
    {
        "id": "J10.4.3",
        "part_a": "Verify Prefect worker status indicator",
        "part_b": "Check Prefect worker shows online/offline correctly",
        "key_files": ["frontend/app/admin/system/page.tsx", "src/api/routes/health.py"]
    },
    {
        "id": "J10.4.4",
        "part_a": "Verify integration status indicators",
        "part_b": "Check Apollo, Salesforge, etc. show connection status",
        "key_files": ["frontend/app/admin/system/page.tsx", "src/api/routes/admin.py"]
    }
]

PASS_CRITERIA = [
    "All system status indicators render",
    "Database status reflects actual connection",
    "Prefect worker status is accurate",
    "Integration statuses are accurate"
]

KEY_FILES = [
    "frontend/app/admin/system/page.tsx",
    "src/api/routes/health.py",
    "src/api/routes/admin.py"
]

# System Components Reference
SYSTEM_COMPONENTS = [
    {"component": "Supabase DB", "health_endpoint": "/api/v1/health/db", "critical": True},
    {"component": "Prefect Worker", "health_endpoint": "/api/v1/health/prefect", "critical": True},
    {"component": "Redis Cache", "health_endpoint": "/api/v1/health/redis", "critical": False},
    {"component": "Apollo API", "health_endpoint": None, "critical": False},
    {"component": "Salesforge API", "health_endpoint": None, "critical": False},
    {"component": "Unipile API", "health_endpoint": None, "critical": False}
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
