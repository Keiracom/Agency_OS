"""
Skill: J12.8 — Alert Configuration
Journey: J12 - SDK Rollout & Monitoring
Checks: 4

Purpose: Verify alerts fire when SDK costs exceed thresholds.
"""

CHECKS = [
    {
        "id": "J12.8.1",
        "part_a": "Verify alert thresholds in config",
        "part_b": "Check: warning=$150, critical=$250 daily cost",
        "key_files": ["config/sdk_config.json"]
    },
    {
        "id": "J12.8.2",
        "part_a": "Verify Slack webhook configured for alerts",
        "part_b": "Check SLACK_WEBHOOK_URL in Railway env vars",
        "key_files": ["config/RAILWAY_ENV_VARS.txt"]
    },
    {
        "id": "J12.8.3",
        "part_a": "Test warning alert fires correctly",
        "part_b": "Simulate $150 daily spend — verify Slack notification sent",
        "key_files": ["src/services/sdk_budget_service.py"]
    },
    {
        "id": "J12.8.4",
        "part_a": "Test critical alert fires and pauses SDK",
        "part_b": "Simulate $250 daily spend — verify SDK paused + alert sent",
        "key_files": ["src/services/sdk_budget_service.py"]
    }
]

PASS_CRITERIA = [
    "Alert thresholds configured",
    "Slack webhook working",
    "Warning alert fires at $150",
    "Critical alert fires and pauses SDK at $250"
]

KEY_FILES = [
    "config/sdk_config.json",
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
