"""
Skill: J8.14 — End-to-End Meeting-to-Deal Test
Journey: J8 - Meeting & Deals
Checks: 9

Purpose: Verify full meeting-to-deal flow works.
"""

CHECKS = [
    {
        "id": "J8.14.1",
        "part_a": "N/A",
        "part_b": "Send Calendly webhook for new booking",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J8.14.2",
        "part_a": "N/A",
        "part_b": "Verify meeting created",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.14.3",
        "part_a": "N/A",
        "part_b": "Verify lead status updated to meeting_booked",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.14.4",
        "part_a": "N/A",
        "part_b": "Record meeting outcome as 'good'",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.14.5",
        "part_a": "N/A",
        "part_b": "Verify deal auto-created",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.14.6",
        "part_a": "N/A",
        "part_b": "Progress deal through stages",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.14.7",
        "part_a": "N/A",
        "part_b": "Close deal as won",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.14.8",
        "part_a": "N/A",
        "part_b": "Verify revenue attribution calculated",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.14.9",
        "part_a": "N/A",
        "part_b": "Verify CRM push (if configured)",
        "key_files": ["src/services/crm_push_service.py"]
    }
]

PASS_CRITERIA = [
    "Full flow completes without errors",
    "Meeting created correctly",
    "Deal created from meeting",
    "Attribution calculated",
    "Lead marked as converted"
]

KEY_FILES = [
    "src/api/routes/webhooks.py",
    "src/services/meeting_service.py",
    "src/services/deal_service.py",
    "src/services/crm_push_service.py"
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
