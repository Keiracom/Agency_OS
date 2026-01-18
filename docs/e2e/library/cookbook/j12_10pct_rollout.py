"""
Skill: J12.4 — 10% Rollout Test
Journey: J12 - SDK Rollout & Monitoring
Checks: 5

Purpose: Verify 10% of Hot leads use SDK successfully.
"""

CHECKS = [
    {
        "id": "J12.4.1",
        "part_a": "Set SDK_TRAFFIC_PERCENT=10 in Railway",
        "part_b": "Verify env var updated on prefect-worker service",
        "key_files": ["config/RAILWAY_ENV_VARS.txt"]
    },
    {
        "id": "J12.4.2",
        "part_a": "Process 100 Hot leads through system",
        "part_b": "Verify ~10 leads used SDK path",
        "key_files": ["src/engines/scout.py"]
    },
    {
        "id": "J12.4.3",
        "part_a": "Verify SDK leads have enriched data",
        "part_b": "Check sdk_enabled=true leads have pain_points populated",
        "key_files": ["src/models/lead.py"]
    },
    {
        "id": "J12.4.4",
        "part_a": "Verify no errors in SDK processing",
        "part_b": "Check Sentry for SDK-related errors — should be zero",
        "key_files": ["src/integrations/sentry_utils.py"]
    },
    {
        "id": "J12.4.5",
        "part_a": "Verify costs within budget",
        "part_b": "Check daily SDK spend < tier limit",
        "key_files": ["src/services/sdk_budget_service.py"]
    }
]

PASS_CRITERIA = [
    "10% traffic split active",
    "~10% of Hot leads use SDK",
    "SDK leads properly enriched",
    "No errors during 10% rollout",
    "Costs within expected range"
]

KEY_FILES = [
    "src/engines/scout.py",
    "src/services/sdk_budget_service.py"
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
