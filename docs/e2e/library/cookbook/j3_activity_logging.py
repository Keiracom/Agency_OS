"""
Skill: J3.6 — Activity Logging
Journey: J3 - Email Outreach
Checks: 5

Purpose: Verify all sends create activity records with complete field population.
"""

CHECKS = [
    {
        "id": "J3.6.1",
        "part_a": "Read `_log_activity` method in email.py — verify implementation",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.6.2",
        "part_a": "Verify all core fields populated (provider_message_id, thread_id, subject, etc.)",
        "part_b": "Check activity record after test send for all fields",
        "key_files": ["src/engines/email.py", "src/models/activity.py"]
    },
    {
        "id": "J3.6.3",
        "part_a": "Verify content_snapshot stored (Phase 16 requirement)",
        "part_b": "Check activity record for content_snapshot JSON structure",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.6.4",
        "part_a": "Verify template_id and ab_test_id stored (Phase 24B requirements)",
        "part_b": "Check activity record for Phase 24B fields",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.6.5",
        "part_a": "Verify full_message_body and links_included extracted and stored",
        "part_b": "Check activity record for message body and parsed links",
        "key_files": ["src/engines/email.py"]
    }
]

PASS_CRITERIA = [
    "Activity created on every send",
    "All Phase 16 fields populated (content_snapshot)",
    "All Phase 24B fields populated (template_id, ab_test_id, ab_variant)",
    "Content snapshot captures for CIS learning",
    "Links extracted and stored in links_included"
]

KEY_FILES = [
    "src/engines/email.py",
    "src/models/activity.py",
    "src/services/activity_service.py"
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
