"""
Skill: J6.3 — LinkedIn Engine Implementation
Journey: J6 - LinkedIn Outreach
Checks: 7

Purpose: Verify LinkedIn engine is fully implemented.
"""

CHECKS = [
    {
        "id": "J6.3.1",
        "part_a": "Read `src/engines/linkedin.py` — verify `send` method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.3.2",
        "part_a": "Verify no TODO/FIXME/pass in linkedin.py",
        "part_b": "Run grep",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.3.3",
        "part_a": "Verify `send_connection_request` convenience method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.3.4",
        "part_a": "Verify `send_message` convenience method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.3.5",
        "part_a": "Verify `send_batch` method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.3.6",
        "part_a": "Verify `get_seat_status` method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.3.7",
        "part_a": "Verify OutreachEngine base class extended",
        "part_b": "Check class definition",
        "key_files": ["src/engines/linkedin.py"]
    }
]

PASS_CRITERIA = [
    "No incomplete implementations",
    "All methods functional",
    "Extends OutreachEngine correctly"
]

KEY_FILES = [
    "src/engines/linkedin.py"
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
