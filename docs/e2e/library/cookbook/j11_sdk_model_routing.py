"""
Skill: J11.8 — SDK Model Routing
Journey: J11 - SDK Foundation
Checks: 4

Purpose: Verify correct model selection (Haiku for simple, Sonnet for complex tasks).
"""

CHECKS = [
    {
        "id": "J11.8.1",
        "part_a": "Verify model_routing config loaded",
        "part_b": "Check Haiku assigned to: classification, sentiment, template_selection",
        "key_files": ["config/sdk_config.json"]
    },
    {
        "id": "J11.8.2",
        "part_a": "Verify Sonnet assigned to complex tasks",
        "part_b": "Check: deep_research, email_writing, voice_kb, objection_handling",
        "key_files": ["config/sdk_config.json"]
    },
    {
        "id": "J11.8.3",
        "part_a": "Verify SDKSimpleClient uses Haiku for classification",
        "part_b": "Call classify_intent() — check model in API request is Haiku",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.8.4",
        "part_a": "Verify SDKBrain uses Sonnet for enrichment",
        "part_b": "Call enrichment agent — check model in API request is Sonnet",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py", "src/agents/sdk_agents/enrichment_agent.py"]
    }
]

PASS_CRITERIA = [
    "Model routing config defines task→model mapping",
    "Simple tasks use Haiku ($1.24/$6.20 per MTok)",
    "Complex tasks use Sonnet ($4.65/$23.25 per MTok)",
    "Correct model used in actual API calls"
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
