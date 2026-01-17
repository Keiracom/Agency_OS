"""
Skill: J2.10 — Campaign Sequences
Journey: J2 - Campaign Creation & Management
Checks: 5

Purpose: Verify sequence step creation and management.
"""

CHECKS = [
    {
        "id": "J2.10.1",
        "part_a": "Read POST `/campaigns/{id}/sequences` endpoint",
        "part_b": "Check sequence creation",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.10.2",
        "part_a": "Verify sequence_steps table schema",
        "part_b": "Check step_number, channel, delay_days",
        "key_files": ["src/models/outreach.py"]
    },
    {
        "id": "J2.10.3",
        "part_a": "Verify step templates linked to sequences",
        "part_b": "Check template_id relationship",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.10.4",
        "part_a": "Verify sequence ordering (step_number)",
        "part_b": "Create multi-step sequence",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.10.5",
        "part_a": "Verify channel-specific sequence validation",
        "part_b": "Check channel requirements",
        "key_files": ["src/api/routes/campaigns.py"]
    }
]

PASS_CRITERIA = [
    "Sequences can be created for campaigns",
    "Multiple steps with delays supported",
    "Templates can be attached to steps",
    "Channel validation applied"
]

KEY_FILES = [
    "src/api/routes/campaigns.py",
    "src/models/outreach.py"
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
