"""
Skill: J8.7 — DealService Implementation
Journey: J8 - Meeting & Deals
Checks: 6

Purpose: Verify DealService is complete.
"""

CHECKS = [
    {
        "id": "J8.7.1",
        "part_a": "Read `src/services/deal_service.py` (867 lines)",
        "part_b": "N/A",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.7.2",
        "part_a": "Verify `create` method",
        "part_b": "Test deal creation",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.7.3",
        "part_a": "Verify `update_stage` method",
        "part_b": "Test stage changes",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.7.4",
        "part_a": "Verify `close_won` method",
        "part_b": "Test winning deal",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.7.5",
        "part_a": "Verify `close_lost` method",
        "part_b": "Test losing deal",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.7.6",
        "part_a": "Verify `update_value` method",
        "part_b": "Test value updates",
        "key_files": ["src/services/deal_service.py"]
    }
]

PASS_CRITERIA = [
    "All CRUD methods implemented",
    "Stage validation works",
    "Probability auto-assigned per stage",
    "Lost reason validation works"
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
