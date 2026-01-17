"""
Skill: J4.7 — Activity Logging
Journey: J4 - SMS Outreach
Checks: 5

Purpose: Verify all sends create activity records with Phase 16/24B fields.
"""

CHECKS = [
    {
        "id": "J4.7.1",
        "part_a": "Read `_log_activity` method in sms.py",
        "part_b": "N/A",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.7.2",
        "part_a": "Verify all fields populated (provider_message_id, sequence_step, content_preview)",
        "part_b": "Check activity schema",
        "key_files": ["src/engines/sms.py", "src/models/activity.py"]
    },
    {
        "id": "J4.7.3",
        "part_a": "Verify content_snapshot stored (Phase 16)",
        "part_b": "Check snapshot structure",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.7.4",
        "part_a": "Verify template_id, ab_test_id, ab_variant stored (Phase 24B)",
        "part_b": "Check fields",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.7.5",
        "part_a": "Verify full_message_body and links_included extracted",
        "part_b": "Check parsed links",
        "key_files": ["src/engines/sms.py"]
    }
]

PASS_CRITERIA = [
    "Activity created on every send",
    "DNCR rejections logged as `rejected_dncr` action",
    "All Phase 16 fields populated (content_snapshot)",
    "All Phase 24B fields populated (template_id, ab_test_id, ab_variant)",
    "Links extracted and stored"
]

KEY_FILES = [
    "src/engines/sms.py",
    "src/models/activity.py"
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
