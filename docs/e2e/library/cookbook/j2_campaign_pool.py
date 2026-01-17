"""
Skill: J2.4 — Campaign Activation Flow
Journey: J2 - Campaign Creation & Management
Checks: 5

Purpose: Verify campaign activation triggers Prefect flow.
"""

CHECKS = [
    {
        "id": "J2.4.1",
        "part_a": "Read `src/api/routes/campaigns.py` — find activate endpoint",
        "part_b": "Locate POST `/campaigns/{id}/activate`",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.4.2",
        "part_a": "Verify activation triggers `campaign_flow` in Prefect",
        "part_b": "Check Prefect deployment exists",
        "key_files": ["src/orchestration/flows/campaign_flow.py"]
    },
    {
        "id": "J2.4.3",
        "part_a": "Read `src/orchestration/flows/campaign_flow.py` — verify JIT validation",
        "part_b": "Check validation steps",
        "key_files": ["src/orchestration/flows/campaign_flow.py"]
    },
    {
        "id": "J2.4.4",
        "part_a": "Verify campaign status updates to 'active'",
        "part_b": "Check DB after activation",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.4.5",
        "part_a": "Verify webhook triggers flow OR API triggers flow",
        "part_b": "Test both trigger methods",
        "key_files": ["src/api/routes/campaigns.py", "src/orchestration/flows/campaign_flow.py"]
    }
]

PASS_CRITERIA = [
    "Activation triggers Prefect flow",
    "JIT validation runs (fails if missing requirements)",
    "Campaign status changes to 'active'",
    "Activity logged"
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
