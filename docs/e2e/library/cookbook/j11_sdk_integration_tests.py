"""
Skill: J11.10 — SDK Integration Tests
Journey: J11 - SDK Foundation
Checks: 5

Purpose: Verify SDK works with real Anthropic API (with cost caps).
"""

CHECKS = [
    {
        "id": "J11.10.1",
        "part_a": "Verify integration test config sets low budget cap",
        "part_b": "Check test config limits to $1 AUD max per test run",
        "key_files": ["tests/integration/sdk/conftest.py"]
    },
    {
        "id": "J11.10.2",
        "part_a": "Test SDKBrain.run() with real API call",
        "part_b": "Simple prompt → verify response and cost tracking",
        "key_files": ["tests/integration/sdk/test_sdk_brain_integration.py"]
    },
    {
        "id": "J11.10.3",
        "part_a": "Test web_search tool with real Serper call",
        "part_b": "Search query → verify results returned from Serper API",
        "key_files": ["tests/integration/sdk/test_sdk_tools_integration.py"]
    },
    {
        "id": "J11.10.4",
        "part_a": "Test enrichment agent end-to-end with real APIs",
        "part_b": "Provide lead data → verify enrichment output populated",
        "key_files": ["tests/integration/sdk/test_enrichment_integration.py"]
    },
    {
        "id": "J11.10.5",
        "part_a": "Verify integration tests skip in CI without API keys",
        "part_b": "Check pytest.mark.skipif for missing ANTHROPIC_API_KEY",
        "key_files": ["tests/integration/sdk/conftest.py"]
    }
]

PASS_CRITERIA = [
    "Integration tests have budget caps",
    "Real Anthropic API calls work",
    "Real Serper API calls work",
    "Full enrichment flow works end-to-end",
    "Tests skip gracefully without API keys"
]

KEY_FILES = [
    "tests/integration/sdk/conftest.py",
    "tests/integration/sdk/test_sdk_brain_integration.py",
    "tests/integration/sdk/test_sdk_tools_integration.py",
    "tests/integration/sdk/test_enrichment_integration.py"
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
