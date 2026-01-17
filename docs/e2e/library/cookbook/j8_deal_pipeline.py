"""
Skill: J8.8 — Deal Pipeline
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify deal pipeline tracking.
"""

CHECKS = [
    {
        "id": "J8.8.1",
        "part_a": "Read `get_pipeline` method (lines 529-584)",
        "part_b": "Test pipeline query",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.8.2",
        "part_a": "Verify stage counts returned",
        "part_b": "Check counts",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.8.3",
        "part_a": "Verify stage values returned",
        "part_b": "Check totals",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.8.4",
        "part_a": "Verify weighted_value calculated",
        "part_b": "Check math",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.8.5",
        "part_a": "Read `get_stage_history` method",
        "part_b": "Check audit trail",
        "key_files": ["src/services/deal_service.py"]
    }
]

PASS_CRITERIA = [
    "Pipeline summary accurate",
    "Stage history tracked",
    "Weighted value correct"
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
