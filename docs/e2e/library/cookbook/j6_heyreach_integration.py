"""
Skill: J6.2 — HeyReach Integration
Journey: J6 - LinkedIn Outreach
Checks: 6

Purpose: Verify HeyReach client is properly configured.
"""

CHECKS = [
    {
        "id": "J6.2.1",
        "part_a": "Read `src/integrations/heyreach.py` — verify complete implementation",
        "part_b": "N/A",
        "key_files": ["src/integrations/heyreach.py"]
    },
    {
        "id": "J6.2.2",
        "part_a": "Verify `HEYREACH_API_KEY` env var in Railway",
        "part_b": "Check Railway vars",
        "key_files": []
    },
    {
        "id": "J6.2.3",
        "part_a": "Verify `send_connection_request` method",
        "part_b": "Test API call",
        "key_files": ["src/integrations/heyreach.py"]
    },
    {
        "id": "J6.2.4",
        "part_a": "Verify `send_message` method",
        "part_b": "Test API call",
        "key_files": ["src/integrations/heyreach.py"]
    },
    {
        "id": "J6.2.5",
        "part_a": "Verify `get_seats` method",
        "part_b": "Test API call",
        "key_files": ["src/integrations/heyreach.py"]
    },
    {
        "id": "J6.2.6",
        "part_a": "Verify `get_new_replies` method",
        "part_b": "Test API call",
        "key_files": ["src/integrations/heyreach.py"]
    }
]

PASS_CRITERIA = [
    "HeyReach integration is complete (482 lines verified)",
    "API key configured",
    "All methods functional"
]

KEY_FILES = [
    "src/integrations/heyreach.py"
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
