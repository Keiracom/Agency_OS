"""
Skill: J12.10 — Rollback Procedure
Journey: J12 - SDK Rollout & Monitoring
Checks: 5

Purpose: Verify one-click rollback disables SDK and reverts to standard flow.
"""

CHECKS = [
    {
        "id": "J12.10.1",
        "part_a": "Verify rollback button exists in admin",
        "part_b": "Check /admin/sdk/settings has 'Disable SDK' button",
        "key_files": ["frontend/app/admin/sdk/settings/page.tsx"]
    },
    {
        "id": "J12.10.2",
        "part_a": "Verify rollback sets SDK_TRAFFIC_PERCENT=0",
        "part_b": "Click disable → verify env var updated via API",
        "key_files": ["src/api/routes/admin.py"]
    },
    {
        "id": "J12.10.3",
        "part_a": "Verify in-flight SDK calls complete gracefully",
        "part_b": "Existing calls finish, new calls use standard path",
        "key_files": ["src/engines/scout.py"]
    },
    {
        "id": "J12.10.4",
        "part_a": "Verify rollback logged with reason",
        "part_b": "Check sdk_rollback_log table populated",
        "key_files": ["src/models/sdk_logs.py"]
    },
    {
        "id": "J12.10.5",
        "part_a": "Verify alert sent on rollback",
        "part_b": "Check Slack notification: 'SDK rolled back by [user]'",
        "key_files": ["src/services/sdk_budget_service.py"]
    }
]

PASS_CRITERIA = [
    "Admin rollback button exists",
    "Rollback sets traffic to 0%",
    "In-flight calls complete gracefully",
    "Rollback logged with audit trail",
    "Team notified via Slack"
]

KEY_FILES = [
    "frontend/app/admin/sdk/settings/page.tsx",
    "src/api/routes/admin.py",
    "src/engines/scout.py",
    "src/models/sdk_logs.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
