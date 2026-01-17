"""
Skill: J3.3 — Email Engine Implementation
Journey: J3 - Email Outreach
Checks: 7

Purpose: Verify email engine is fully implemented with all required methods.
"""

CHECKS = [
    {
        "id": "J3.3.1",
        "part_a": "Read `src/engines/email.py` — verify `send` method implementation",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.3.2",
        "part_a": "Verify no TODO/FIXME/pass in email.py via grep",
        "part_b": "Run `grep -n \"TODO\\|FIXME\\|pass\" src/engines/email.py`",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.3.3",
        "part_a": "Verify `send_batch` method for bulk sends",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.3.4",
        "part_a": "Verify subject and from_email validation logic",
        "part_b": "Test with missing required fields, verify error",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.3.5",
        "part_a": "Verify OutreachEngine base class is extended correctly",
        "part_b": "Check class definition and inheritance",
        "key_files": ["src/engines/email.py", "src/engines/base.py"]
    },
    {
        "id": "J3.3.6",
        "part_a": "Verify `_get_thread_info` method for email threading (Rule 18)",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.3.7",
        "part_a": "Verify In-Reply-To and References headers set for follow-ups",
        "part_b": "Send follow-up email, check headers in received email",
        "key_files": ["src/engines/email.py"]
    }
]

PASS_CRITERIA = [
    "No incomplete implementations (no TODO/FIXME/pass)",
    "All methods have implementations",
    "Validation for required fields works",
    "Extends OutreachEngine correctly",
    "Email threading implemented with In-Reply-To + References",
    "Single send and batch send both work",
    "TEST_MODE redirect integrated"
]

KEY_FILES = [
    "src/engines/email.py",
    "src/engines/base.py",
    "src/orchestration/flows/outreach_flow.py"
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
