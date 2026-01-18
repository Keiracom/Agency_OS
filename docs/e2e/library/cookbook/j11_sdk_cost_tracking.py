"""
Skill: J11.4 — SDK Cost Tracking
Journey: J11 - SDK Foundation
Checks: 5

Purpose: Verify per-call cost calculation and daily budget enforcement.
"""

CHECKS = [
    {
        "id": "J11.4.1",
        "part_a": "Verify pricing config loaded from `sdk_config.json`",
        "part_b": "Check pricing_aud section has Sonnet, Haiku, Opus rates",
        "key_files": ["config/sdk_config.json", "src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.4.2",
        "part_a": "Verify cost calculation formula",
        "part_b": "Test: (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.4.3",
        "part_a": "Verify cached input discount applied (90% off)",
        "part_b": "Check cached_input_per_mtok used when cache_context=True",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.4.4",
        "part_a": "Verify daily budget tracking per tier",
        "part_b": "Check Ignition=$50, Velocity=$100, Dominance=$200 limits",
        "key_files": ["config/sdk_config.json", "src/services/sdk_budget_service.py"]
    },
    {
        "id": "J11.4.5",
        "part_a": "Verify cost logged to database after each call",
        "part_b": "Check ai_costs table updated with sdk_brain entries",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py", "src/models/costs.py"]
    }
]

PASS_CRITERIA = [
    "Pricing rates loaded from config",
    "Cost calculated correctly in AUD",
    "Cache discount applied when appropriate",
    "Daily budget tracked per client tier",
    "Costs logged to database"
]

KEY_FILES = [
    "src/agents/sdk_agents/sdk_brain.py",
    "config/sdk_config.json",
    "src/services/sdk_budget_service.py",
    "src/models/costs.py"
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
