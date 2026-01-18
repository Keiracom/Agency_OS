"""
Skill: J12.5 — 50% Rollout Test
Journey: J12 - SDK Rollout & Monitoring
Checks: 5

Purpose: Scale to 50% of Hot leads using SDK, monitor for issues.
"""

CHECKS = [
    {
        "id": "J12.5.1",
        "part_a": "Review 10% rollout metrics before proceeding",
        "part_b": "Confirm: no errors, costs acceptable, quality good",
        "key_files": ["frontend/app/admin/sdk/metrics/page.tsx"]
    },
    {
        "id": "J12.5.2",
        "part_a": "Set SDK_TRAFFIC_PERCENT=50 in Railway",
        "part_b": "Verify env var updated on prefect-worker service",
        "key_files": ["config/RAILWAY_ENV_VARS.txt"]
    },
    {
        "id": "J12.5.3",
        "part_a": "Monitor for 24 hours",
        "part_b": "Check error rates, cost trends, completion rates",
        "key_files": ["frontend/app/admin/sdk/metrics/page.tsx"]
    },
    {
        "id": "J12.5.4",
        "part_a": "Compare SDK vs non-SDK meeting rates",
        "part_b": "Check if SDK leads booking more meetings (early signal)",
        "key_files": ["src/models/sdk_logs.py"]
    },
    {
        "id": "J12.5.5",
        "part_a": "Verify no budget alerts triggered",
        "part_b": "Check Slack/email for budget warning notifications",
        "key_files": ["src/services/sdk_budget_service.py"]
    }
]

PASS_CRITERIA = [
    "10% rollout successful before 50%",
    "50% traffic split active",
    "No errors during 24h monitoring",
    "Meeting rate trends positive (or neutral)",
    "Budget within limits"
]

KEY_FILES = [
    "src/engines/scout.py",
    "src/services/sdk_budget_service.py",
    "frontend/app/admin/sdk/metrics/page.tsx"
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
