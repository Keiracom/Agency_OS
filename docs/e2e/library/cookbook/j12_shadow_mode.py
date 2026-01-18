"""
Skill: J12.1 — Shadow Mode Infrastructure
Journey: J12 - SDK Rollout & Monitoring
Checks: 5

Purpose: Verify SDK can run in shadow mode (logs output, doesn't affect production).
"""

CHECKS = [
    {
        "id": "J12.1.1",
        "part_a": "Verify SDK_SHADOW_MODE environment variable exists",
        "part_b": "Check Railway env vars include SDK_SHADOW_MODE=true option",
        "key_files": ["config/sdk_config.json"]
    },
    {
        "id": "J12.1.2",
        "part_a": "Verify shadow mode runs SDK but discards output",
        "part_b": "Enable shadow mode → SDK runs → original (non-SDK) output used",
        "key_files": ["src/engines/scout.py", "src/engines/closer.py"]
    },
    {
        "id": "J12.1.3",
        "part_a": "Verify shadow mode logs SDK output for comparison",
        "part_b": "Check sdk_shadow_logs table populated with SDK results",
        "key_files": ["src/models/sdk_logs.py"]
    },
    {
        "id": "J12.1.4",
        "part_a": "Verify shadow mode tracks SDK costs separately",
        "part_b": "Check ai_costs table has shadow_mode=true flag",
        "key_files": ["src/models/costs.py"]
    },
    {
        "id": "J12.1.5",
        "part_a": "Verify shadow mode can be toggled without deployment",
        "part_b": "Change env var → behavior changes without code deploy",
        "key_files": ["config/sdk_config.json"]
    }
]

PASS_CRITERIA = [
    "Shadow mode flag exists in config",
    "SDK runs but output not used in production",
    "SDK output logged for analysis",
    "Costs tracked with shadow flag",
    "Toggle without deployment"
]

KEY_FILES = [
    "config/sdk_config.json",
    "src/engines/scout.py",
    "src/engines/closer.py",
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
