"""
Skill: J11.1 — SDK Brain Core
Journey: J11 - SDK Foundation
Checks: 6

Purpose: Verify SDK Brain wrapper initializes correctly, loads config, and tracks costs.
"""

CHECKS = [
    {
        "id": "J11.1.1",
        "part_a": "Read `src/agents/sdk_agents/sdk_brain.py` — verify SDKBrain class exists",
        "part_b": "Import and instantiate SDKBrain in Python REPL",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.1.2",
        "part_a": "Verify config loading from `sdk_config.json`",
        "part_b": "Check SDKBrainConfig dataclass populates correctly",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py", "config/sdk_config.json"]
    },
    {
        "id": "J11.1.3",
        "part_a": "Verify Anthropic client initialization with API key",
        "part_b": "Check ANTHROPIC_API_KEY loaded from environment",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.1.4",
        "part_a": "Verify cost tracking per call — input/output tokens recorded",
        "part_b": "Run test call and check SDKBrainResult.cost_aud populated",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.1.5",
        "part_a": "Verify max_turns limit enforced (default 10)",
        "part_b": "Test with agent that would loop forever",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.1.6",
        "part_a": "Verify max_cost_aud limit enforced (stops if exceeded)",
        "part_b": "Set low limit and verify circuit breaker trips",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    }
]

PASS_CRITERIA = [
    "SDKBrain instantiates without errors",
    "Config loaded from JSON file",
    "Anthropic client initialized",
    "Cost tracking returns AUD amounts",
    "Turn limits enforced",
    "Cost limits enforced"
]

KEY_FILES = [
    "src/agents/sdk_agents/sdk_brain.py",
    "config/sdk_config.json"
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
