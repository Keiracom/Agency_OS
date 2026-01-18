"""
Skill: J12.2 — Traffic Splitting
Journey: J12 - SDK Rollout & Monitoring
Checks: 4

Purpose: Verify feature flag controls what percentage of leads use SDK.
"""

CHECKS = [
    {
        "id": "J12.2.1",
        "part_a": "Verify SDK_TRAFFIC_PERCENT environment variable",
        "part_b": "Check config supports 0, 10, 50, 100 values",
        "key_files": ["config/sdk_config.json"]
    },
    {
        "id": "J12.2.2",
        "part_a": "Verify traffic split logic in scout engine",
        "part_b": "Check random selection based on SDK_TRAFFIC_PERCENT",
        "key_files": ["src/engines/scout.py"]
    },
    {
        "id": "J12.2.3",
        "part_a": "Verify consistent assignment per lead",
        "part_b": "Same lead always gets same path (SDK or not) using lead_id hash",
        "key_files": ["src/engines/scout.py"]
    },
    {
        "id": "J12.2.4",
        "part_a": "Verify traffic split logged for analysis",
        "part_b": "Check lead_assignments.sdk_enabled flag populated",
        "key_files": ["src/models/lead.py"]
    }
]

PASS_CRITERIA = [
    "Traffic percent configurable via env var",
    "Random selection respects percentage",
    "Same lead gets consistent assignment",
    "Assignment logged for A/B analysis"
]

KEY_FILES = [
    "config/sdk_config.json",
    "src/engines/scout.py",
    "src/models/lead.py"
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
