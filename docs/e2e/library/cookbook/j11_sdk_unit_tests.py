"""
Skill: J11.9 — SDK Unit Tests
Journey: J11 - SDK Foundation
Checks: 6

Purpose: Verify each SDK agent has unit tests with mocked dependencies.
"""

CHECKS = [
    {
        "id": "J11.9.1",
        "part_a": "Verify test file exists: `tests/agents/sdk_agents/test_sdk_brain.py`",
        "part_b": "Run `pytest tests/agents/sdk_agents/test_sdk_brain.py -v`",
        "key_files": ["tests/agents/sdk_agents/test_sdk_brain.py"]
    },
    {
        "id": "J11.9.2",
        "part_a": "Verify test file exists: `tests/agents/sdk_agents/test_sdk_tools.py`",
        "part_b": "Run `pytest tests/agents/sdk_agents/test_sdk_tools.py -v`",
        "key_files": ["tests/agents/sdk_agents/test_sdk_tools.py"]
    },
    {
        "id": "J11.9.3",
        "part_a": "Verify enrichment agent tests with mocked web_search",
        "part_b": "Check tests mock Serper API and verify agent logic",
        "key_files": ["tests/agents/sdk_agents/test_enrichment_agent.py"]
    },
    {
        "id": "J11.9.4",
        "part_a": "Verify email agent tests with mocked enrichment data",
        "part_b": "Check tests provide sample enrichment and verify email output",
        "key_files": ["tests/agents/sdk_agents/test_email_agent.py"]
    },
    {
        "id": "J11.9.5",
        "part_a": "Verify voice KB agent tests",
        "part_b": "Check tests verify pronunciation, openers, objection handlers output",
        "key_files": ["tests/agents/sdk_agents/test_voice_kb_agent.py"]
    },
    {
        "id": "J11.9.6",
        "part_a": "Verify all SDK unit tests pass",
        "part_b": "Run `pytest tests/agents/sdk_agents/ -v` — all green",
        "key_files": ["tests/agents/sdk_agents/"]
    }
]

PASS_CRITERIA = [
    "Test files exist for all SDK components",
    "Tests use mocked external dependencies",
    "Enrichment agent tests cover tool use",
    "Email agent tests cover personalization",
    "Voice KB agent tests cover all output fields",
    "All unit tests pass"
]

KEY_FILES = [
    "tests/agents/sdk_agents/test_sdk_brain.py",
    "tests/agents/sdk_agents/test_sdk_tools.py",
    "tests/agents/sdk_agents/test_enrichment_agent.py",
    "tests/agents/sdk_agents/test_email_agent.py",
    "tests/agents/sdk_agents/test_voice_kb_agent.py"
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
