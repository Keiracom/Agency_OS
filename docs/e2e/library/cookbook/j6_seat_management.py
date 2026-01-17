"""
Skill: J6.11 — Seat Management
Journey: J6 - LinkedIn Outreach
Checks: 3

Purpose: Verify seat status and quota tracking.
"""

CHECKS = [
    {
        "id": "J6.11.1",
        "part_a": "Verify `get_seat_status` method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.11.2",
        "part_a": "Verify `check_seat_limit` in HeyReach",
        "part_b": "N/A",
        "key_files": ["src/integrations/heyreach.py"]
    },
    {
        "id": "J6.11.3",
        "part_a": "Verify remaining quota returned",
        "part_b": "Check response",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "Seat status retrievable",
    "Remaining quota accurate"
]

KEY_FILES = [
    "src/engines/linkedin.py",
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
