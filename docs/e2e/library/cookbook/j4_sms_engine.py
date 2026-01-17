"""
Skill: J4.4 — SMS Engine Implementation
Journey: J4 - SMS Outreach
Checks: 7

Purpose: Verify SMS engine is fully implemented.
"""

CHECKS = [
    {
        "id": "J4.4.1",
        "part_a": "Read `src/engines/sms.py` — verify `send` method",
        "part_b": "N/A",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.4.2",
        "part_a": "Verify no TODO/FIXME/pass in sms.py",
        "part_b": "Run `grep -n \"TODO\\|FIXME\\|pass\" src/engines/sms.py`",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.4.3",
        "part_a": "Verify `send_batch` method for bulk sends",
        "part_b": "N/A",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.4.4",
        "part_a": "Verify `check_dncr` method exposed",
        "part_b": "N/A",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.4.5",
        "part_a": "Verify OutreachEngine base class extended",
        "part_b": "Check class definition",
        "key_files": ["src/engines/sms.py", "src/engines/outreach_base.py"]
    },
    {
        "id": "J4.4.6",
        "part_a": "Verify DNCR check happens before send",
        "part_b": "Trace code path",
        "key_files": ["src/engines/sms.py", "src/integrations/twilio.py"]
    },
    {
        "id": "J4.4.7",
        "part_a": "Verify DNCRError raised when blocked",
        "part_b": "Check exception handling",
        "key_files": ["src/engines/sms.py"]
    }
]

PASS_CRITERIA = [
    "No incomplete implementations (TODO/FIXME/pass)",
    "All methods have implementations",
    "Validation for required fields",
    "Extends OutreachEngine correctly",
    "DNCR check before send",
    "DNCRError handled properly"
]

KEY_FILES = [
    "src/engines/sms.py",
    "src/engines/outreach_base.py",
    "src/integrations/twilio.py",
    "src/integrations/dncr.py"
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
