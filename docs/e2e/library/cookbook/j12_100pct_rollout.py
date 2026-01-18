"""
Skill: J12.6 — 100% Rollout Verification
Journey: J12 - SDK Rollout & Monitoring
Checks: 5

Purpose: Full rollout - all Hot leads use SDK.
"""

CHECKS = [
    {
        "id": "J12.6.1",
        "part_a": "Review 50% rollout metrics before proceeding",
        "part_b": "Confirm: stable for 48+ hours, meeting rates good, costs OK",
        "key_files": ["frontend/app/admin/sdk/metrics/page.tsx"]
    },
    {
        "id": "J12.6.2",
        "part_a": "Set SDK_TRAFFIC_PERCENT=100 in Railway",
        "part_b": "Verify env var updated on prefect-worker service",
        "key_files": ["config/RAILWAY_ENV_VARS.txt"]
    },
    {
        "id": "J12.6.3",
        "part_a": "Verify all Hot leads (ALS >= 85) use SDK",
        "part_b": "Check 100% of Hot leads have sdk_enabled=true",
        "key_files": ["src/engines/scout.py"]
    },
    {
        "id": "J12.6.4",
        "part_a": "Monitor daily costs by tier",
        "part_b": "Verify: Ignition < $50, Velocity < $100, Dominance < $200",
        "key_files": ["src/services/sdk_budget_service.py"]
    },
    {
        "id": "J12.6.5",
        "part_a": "Document rollout completion",
        "part_b": "Update PROGRESS.md with SDK rollout complete date",
        "key_files": ["PROGRESS.md"]
    }
]

PASS_CRITERIA = [
    "50% rollout stable before 100%",
    "100% traffic enabled",
    "All Hot leads using SDK",
    "Daily costs within tier limits",
    "Rollout documented"
]

KEY_FILES = [
    "src/engines/scout.py",
    "src/services/sdk_budget_service.py",
    "PROGRESS.md"
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
