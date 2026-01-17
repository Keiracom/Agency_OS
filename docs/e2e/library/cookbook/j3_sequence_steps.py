"""
Skill: J3.11 — Sequence Steps
Journey: J3 - Email Outreach
Checks: 5

Purpose: Verify email sequence steps execute correctly with proper threading.
"""

CHECKS = [
    {
        "id": "J3.11.1",
        "part_a": "Read `src/orchestration/flows/outreach_flow.py` — verify sequence step handling",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/orchestration/flows/outreach_flow.py"]
    },
    {
        "id": "J3.11.2",
        "part_a": "Verify sequence_step incremented correctly on each send",
        "part_b": "Send sequence of emails, check step numbers",
        "key_files": ["src/orchestration/flows/outreach_flow.py", "src/engines/email.py"]
    },
    {
        "id": "J3.11.3",
        "part_a": "Verify is_followup flag set correctly for steps > 1",
        "part_b": "Check email headers for threading on step 2+",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.11.4",
        "part_a": "Verify thread_id maintained across sequence steps",
        "part_b": "Check activity records for consistent thread_id",
        "key_files": ["src/engines/email.py", "src/models/activity.py"]
    },
    {
        "id": "J3.11.5",
        "part_a": "Verify sequence respects wait times between steps",
        "part_b": "Check Prefect flow scheduling for step delays",
        "key_files": ["src/orchestration/flows/outreach_flow.py"]
    }
]

PASS_CRITERIA = [
    "Sequence steps increment correctly (1, 2, 3...)",
    "is_followup flag triggers threading for step 2+",
    "Thread ID maintained across all sequence steps",
    "Wait times between steps respected",
    "Emails appear threaded in recipient inbox"
]

KEY_FILES = [
    "src/orchestration/flows/outreach_flow.py",
    "src/engines/email.py",
    "src/models/activity.py",
    "src/models/sequence.py"
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
