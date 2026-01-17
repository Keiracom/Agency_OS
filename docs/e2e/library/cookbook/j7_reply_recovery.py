"""
Skill: J7.11 — Reply Recovery Flow (Safety Net)
Journey: J7 - Reply Handling
Checks: 7

Purpose: Verify 6-hourly polling catches missed webhook replies.
"""

CHECKS = [
    {
        "id": "J7.11.1",
        "part_a": "Read `src/orchestration/flows/reply_recovery_flow.py` (548 lines)",
        "part_b": "N/A",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"]
    },
    {
        "id": "J7.11.2",
        "part_a": "Verify `poll_email_replies_task` polls Postmark",
        "part_b": "Check logs",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"]
    },
    {
        "id": "J7.11.3",
        "part_a": "Verify `poll_sms_replies_task` polls Twilio",
        "part_b": "Check logs",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"]
    },
    {
        "id": "J7.11.4",
        "part_a": "Verify `poll_linkedin_replies_task` polls HeyReach",
        "part_b": "Check logs",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"]
    },
    {
        "id": "J7.11.5",
        "part_a": "Verify deduplication check (lines 255-287)",
        "part_b": "Simulate duplicate",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"]
    },
    {
        "id": "J7.11.6",
        "part_a": "Verify `process_missed_reply_task` calls Closer",
        "part_b": "Check processing",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py", "src/engines/closer.py"]
    },
    {
        "id": "J7.11.7",
        "part_a": "Trigger flow manually in Prefect",
        "part_b": "Check recovery runs",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"]
    }
]

PASS_CRITERIA = [
    "Polls all 3 channels",
    "Deduplication prevents double processing",
    "Missed replies processed correctly",
    "Flow runs on 6-hour schedule (PAUSED by default)"
]

KEY_FILES = [
    "src/orchestration/flows/reply_recovery_flow.py",
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
    lines.append("### Flow Tasks Reference")
    lines.append("- poll_email_replies_task (Postmark)")
    lines.append("- poll_sms_replies_task (Twilio)")
    lines.append("- poll_linkedin_replies_task (HeyReach)")
    lines.append("- find_lead_by_contact_task")
    lines.append("- check_if_reply_processed_task")
    lines.append("- process_missed_reply_task")
    return "\n".join(lines)
