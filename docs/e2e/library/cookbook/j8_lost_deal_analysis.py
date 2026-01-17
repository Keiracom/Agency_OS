"""
Skill: J8.13 — Lost Deal Analysis
Journey: J8 - Meeting & Deals
Checks: 3

Purpose: Verify lost deal analytics for CIS learning.
"""

CHECKS = [
    {
        "id": "J8.13.1",
        "part_a": "Read `get_lost_analysis` method (lines 700-725)",
        "part_b": "Test query",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.13.2",
        "part_a": "Verify lost_reason breakdown",
        "part_b": "Check grouping",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.13.3",
        "part_a": "Verify lost_notes captured",
        "part_b": "Check field",
        "key_files": ["src/services/deal_service.py"]
    }
]

PASS_CRITERIA = [
    "Lost reasons analyzed",
    "Patterns identifiable",
    "CIS can learn from losses"
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
