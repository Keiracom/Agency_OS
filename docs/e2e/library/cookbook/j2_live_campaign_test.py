"""
Skill: J2.12 — Campaign Edge Cases
Journey: J2 - Campaign Creation & Management
Checks: 6

Purpose: Test error handling and edge conditions.
"""

CHECKS = [
    {
        "id": "J2.12.1",
        "part_a": "Create campaign without ICP configured",
        "part_b": "Should warn but allow",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.12.2",
        "part_a": "Activate campaign with no leads",
        "part_b": "Should fail validation",
        "key_files": ["src/api/routes/campaigns.py", "src/orchestration/flows/campaign_flow.py"]
    },
    {
        "id": "J2.12.3",
        "part_a": "Activate campaign with no sequences",
        "part_b": "Should fail or warn",
        "key_files": ["src/api/routes/campaigns.py", "src/orchestration/flows/campaign_flow.py"]
    },
    {
        "id": "J2.12.4",
        "part_a": "Duplicate campaign name",
        "part_b": "Check uniqueness constraint",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.12.5",
        "part_a": "Campaign with 0% allocation (all channels)",
        "part_b": "Check validation",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.12.6",
        "part_a": "Pause mid-sequence",
        "part_b": "Verify sequence state preservation",
        "key_files": ["src/api/routes/campaigns.py", "src/orchestration/flows/campaign_flow.py"]
    }
]

PASS_CRITERIA = [
    "Appropriate validation errors returned",
    "No silent failures",
    "State preserved on pause"
]

KEY_FILES = [
    "src/api/routes/campaigns.py",
    "src/orchestration/flows/campaign_flow.py"
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
