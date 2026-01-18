"""
Skill: J11.2 — SDK Tools
Journey: J11 - SDK Foundation
Checks: 5

Purpose: Verify SDK tools (web_search, web_fetch, linkedin_posts) work correctly.
"""

CHECKS = [
    {
        "id": "J11.2.1",
        "part_a": "Read `src/agents/sdk_agents/sdk_tools.py` — verify tool definitions",
        "part_b": "Check WEB_SEARCH_TOOL, WEB_FETCH_TOOL, LINKEDIN_POSTS_TOOL schemas",
        "key_files": ["src/agents/sdk_agents/sdk_tools.py"]
    },
    {
        "id": "J11.2.2",
        "part_a": "Test web_search function with Serper API",
        "part_b": "Run `await web_search('Anthropic funding')` — verify results returned",
        "key_files": ["src/agents/sdk_agents/sdk_tools.py"]
    },
    {
        "id": "J11.2.3",
        "part_a": "Test web_fetch function with real URL",
        "part_b": "Run `await web_fetch('https://anthropic.com')` — verify HTML parsed to text",
        "key_files": ["src/agents/sdk_agents/sdk_tools.py"]
    },
    {
        "id": "J11.2.4",
        "part_a": "Test linkedin_posts function with Apify",
        "part_b": "Run with test LinkedIn URL — verify posts returned (or graceful error)",
        "key_files": ["src/agents/sdk_agents/sdk_tools.py"]
    },
    {
        "id": "J11.2.5",
        "part_a": "Verify TOOL_REGISTRY maps names to functions",
        "part_b": "Check `execute_tool('web_search', query='test')` routes correctly",
        "key_files": ["src/agents/sdk_agents/sdk_tools.py"]
    }
]

PASS_CRITERIA = [
    "Tool definitions match Claude's expected schema",
    "web_search returns formatted results from Serper",
    "web_fetch parses HTML to readable text",
    "linkedin_posts handles Apify integration",
    "TOOL_REGISTRY routes tool calls correctly"
]

KEY_FILES = [
    "src/agents/sdk_agents/sdk_tools.py"
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
