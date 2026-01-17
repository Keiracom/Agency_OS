"""
Skill: J3.12 — Live Email Test
Journey: J3 - Email Outreach
Checks: 6

Purpose: Verify emails land in inbox (not spam) with correct formatting.
"""

CHECKS = [
    {
        "id": "J3.12.1",
        "part_a": "Verify sender domain has SPF/DKIM/DMARC records configured",
        "part_b": "Check DNS records for sender domain",
        "key_files": []
    },
    {
        "id": "J3.12.2",
        "part_a": "Verify from_email is valid and matches sender domain",
        "part_b": "Check sender configuration in Salesforge",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.12.3",
        "part_a": "N/A (live test only)",
        "part_b": "Send real email via TEST_MODE to david.stephens@keiracom.com",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.12.4",
        "part_a": "N/A (live test only)",
        "part_b": "Check inbox (not spam folder) for delivered email",
        "key_files": []
    },
    {
        "id": "J3.12.5",
        "part_a": "N/A (live test only)",
        "part_b": "Verify content, personalization, and HTML formatting correct",
        "key_files": []
    },
    {
        "id": "J3.12.6",
        "part_a": "N/A (live test only)",
        "part_b": "Verify threading works in inbox view (send follow-up)",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "Email lands in inbox (not spam)",
    "Subject displays correctly",
    "Body renders properly (HTML)",
    "Personalization fields replaced",
    "Threading displays correctly for follow-ups",
    "SPF/DKIM/DMARC pass checks"
]

KEY_FILES = [
    "src/engines/email.py",
    "src/integrations/salesforge.py",
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
