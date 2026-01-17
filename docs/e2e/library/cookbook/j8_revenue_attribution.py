"""
Skill: J8.10 — Revenue Attribution
Journey: J8 - Meeting & Deals
Checks: 4

Purpose: Verify revenue attributed to channels and activities.
"""

CHECKS = [
    {
        "id": "J8.10.1",
        "part_a": "Read `calculate_attribution` method (lines 610-630)",
        "part_b": "N/A",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.10.2",
        "part_a": "Verify first_touch model",
        "part_b": "Test attribution",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.10.3",
        "part_a": "Read `get_channel_attribution` method",
        "part_b": "Test channel breakdown",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.10.4",
        "part_a": "Read `get_funnel_analytics` method",
        "part_b": "Test funnel",
        "key_files": ["src/services/deal_service.py"]
    }
]

PASS_CRITERIA = [
    "Attribution calculated on close_won",
    "Multiple models supported",
    "Channel breakdown available",
    "Funnel analytics work"
]

KEY_FILES = [
    "src/services/deal_service.py"
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
