"""
Skill: J2.11 — Campaign Metrics
Journey: J2 - Campaign Creation & Management
Checks: 5

Purpose: Verify campaign metrics are calculated correctly.
"""

CHECKS = [
    {
        "id": "J2.11.1",
        "part_a": "Verify `total_leads` count in campaign response",
        "part_b": "Check API response",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.11.2",
        "part_a": "Verify `leads_contacted` count",
        "part_b": "Check activity-based count",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.11.3",
        "part_a": "Verify `leads_replied` count",
        "part_b": "Check reply detection",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.11.4",
        "part_a": "Verify `reply_rate` calculation (replied/contacted)",
        "part_b": "Verify percentage",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.11.5",
        "part_a": "Verify metrics update in real-time",
        "part_b": "Make activity, check update",
        "key_files": ["src/api/routes/campaigns.py"]
    }
]

PASS_CRITERIA = [
    "All metrics calculated from activities table",
    "Metrics reflect real data",
    "Reply rate percentage accurate"
]

KEY_FILES = [
    "src/api/routes/campaigns.py"
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
