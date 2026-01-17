"""
Skill: J7.8 — Objection Tracking (Phase 24D)
Journey: J7 - Reply Handling
Checks: 5

Purpose: Verify objections are tracked for CIS learning.
"""

CHECKS = [
    {
        "id": "J7.8.1",
        "part_a": "Read `_record_rejection` method (closer.py lines 500-538)",
        "part_b": "N/A",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.8.2",
        "part_a": "Verify rejection_reason field updated",
        "part_b": "Check lead.rejection_reason",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.8.3",
        "part_a": "Verify rejection_at timestamp set",
        "part_b": "Check lead.rejection_at",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.8.4",
        "part_a": "Read `_add_objection_to_history` method (lines 540-566)",
        "part_b": "N/A",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.8.5",
        "part_a": "Verify objections_raised array updated",
        "part_b": "Check lead.objections_raised",
        "key_files": ["src/engines/closer.py"]
    }
]

PASS_CRITERIA = [
    "Rejection reason recorded",
    "Timestamp captured",
    "Objections added to history array",
    "CIS can query rejection patterns"
]

KEY_FILES = [
    "src/engines/closer.py"
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
    lines.append("")
    lines.append("### Rejection Reason Mapping Reference")
    lines.append("```python")
    lines.append("rejection_map = {")
    lines.append('    "timing": "timing_not_now",')
    lines.append('    "budget": "budget_constraints",')
    lines.append('    "authority": "not_decision_maker",')
    lines.append('    "need": "no_need",')
    lines.append('    "competitor": "using_competitor",')
    lines.append('    "trust": "other",')
    lines.append('    "do_not_contact": "do_not_contact",')
    lines.append('    "other": "not_interested_generic",')
    lines.append("}")
    lines.append("```")
    return "\n".join(lines)
