"""
Skill: J11.6 — SDK Circuit Breaker
Journey: J11 - SDK Foundation
Checks: 4

Purpose: Verify circuit breaker trips when budget exceeded or errors spike.
"""

CHECKS = [
    {
        "id": "J11.6.1",
        "part_a": "Verify daily budget check before each SDK call",
        "part_b": "Check sdk_budget_service.can_spend() called in sdk_brain.run()",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py", "src/services/sdk_budget_service.py"]
    },
    {
        "id": "J11.6.2",
        "part_a": "Verify circuit trips when daily budget exceeded",
        "part_b": "Set budget to $0.01, make call — verify SDKBudgetExceeded raised",
        "key_files": ["src/services/sdk_budget_service.py"]
    },
    {
        "id": "J11.6.3",
        "part_a": "Verify circuit trips after consecutive failures",
        "part_b": "Simulate 3 failures — check circuit opens and subsequent calls rejected",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.6.4",
        "part_a": "Verify circuit resets after cooldown period",
        "part_b": "Wait for reset interval — check circuit allows calls again",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    }
]

PASS_CRITERIA = [
    "Budget checked before every SDK call",
    "Circuit trips immediately when budget exceeded",
    "Circuit trips after consecutive failures",
    "Circuit resets after cooldown period"
]

KEY_FILES = [
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
