"""
Skill: J11.5 — SDK Rate Limiting
Journey: J11 - SDK Foundation
Checks: 4

Purpose: Verify SDK respects rate limits for API calls and concurrent requests.
"""

CHECKS = [
    {
        "id": "J11.5.1",
        "part_a": "Verify per-agent timeout settings from config",
        "part_b": "Check enrichment=120s, email=60s, voice_kb=180s, objection=60s",
        "key_files": ["config/sdk_config.json"]
    },
    {
        "id": "J11.5.2",
        "part_a": "Verify max concurrent SDK calls limited",
        "part_b": "Test semaphore/queue prevents more than N simultaneous calls",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.5.3",
        "part_a": "Verify tool-level rate limits (Serper, Apify)",
        "part_b": "Check web_search respects Serper rate limits",
        "key_files": ["src/agents/sdk_agents/sdk_tools.py"]
    },
    {
        "id": "J11.5.4",
        "part_a": "Verify timeout handling returns graceful error",
        "part_b": "Simulate timeout — check SDKBrainResult.error populated",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    }
]

PASS_CRITERIA = [
    "Per-agent timeouts enforced",
    "Concurrent call limit prevents overload",
    "Tool-level rate limits respected",
    "Timeouts handled gracefully with error message"
]

KEY_FILES = [
    "src/agents/sdk_agents/sdk_brain.py",
    "src/agents/sdk_agents/sdk_tools.py",
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
