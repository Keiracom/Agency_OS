"""
Skill: J6.12 — Error Handling
Journey: J6 - LinkedIn Outreach
Checks: 4

Purpose: Verify graceful error handling.
"""

CHECKS = [
    {
        "id": "J6.12.1",
        "part_a": "Verify HeyReach errors caught",
        "part_b": "Check exception handling",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.12.2",
        "part_a": "Verify EngineResult.fail returned on error",
        "part_b": "Check return",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.12.3",
        "part_a": "Verify retry logic in HeyReach client (tenacity)",
        "part_b": "Check decorator",
        "key_files": ["src/integrations/heyreach.py"]
    },
    {
        "id": "J6.12.4",
        "part_a": "Verify missing seat_id handled",
        "part_b": "Test without seat_id",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "Errors don't crash the flow",
    "Retries attempted (3x)",
    "Required fields validated"
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
