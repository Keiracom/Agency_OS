"""
Skill: J12.9 — Cost Anomaly Detection
Journey: J12 - SDK Rollout & Monitoring
Checks: 4

Purpose: Verify system detects and handles unusual cost spikes.
"""

CHECKS = [
    {
        "id": "J12.9.1",
        "part_a": "Verify per-call cost limit enforced",
        "part_b": "Check max_cost_per_call_aud=$5 in config",
        "key_files": ["config/sdk_config.json"]
    },
    {
        "id": "J12.9.2",
        "part_a": "Verify anomaly detection for high-cost calls",
        "part_b": "If single call > $2, log warning and flag for review",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J12.9.3",
        "part_a": "Verify runaway agent detection",
        "part_b": "If agent uses > 15 turns, terminate and log error",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J12.9.4",
        "part_a": "Verify daily cost trend analysis",
        "part_b": "Alert if today's cost > 150% of 7-day average",
        "key_files": ["src/services/sdk_budget_service.py"]
    }
]

PASS_CRITERIA = [
    "Per-call cost limit enforced",
    "High-cost calls flagged",
    "Runaway agents terminated",
    "Daily trend anomalies detected"
]

KEY_FILES = [
    "config/sdk_config.json",
    "src/agents/sdk_agents/sdk_brain.py",
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
