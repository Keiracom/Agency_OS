"""
Skill: J3.2 — Salesforge Integration
Journey: J3 - Email Outreach
Checks: 6

Purpose: Verify Salesforge is the primary email sender with full API integration.
"""

CHECKS = [
    {
        "id": "J3.2.1",
        "part_a": "Read `src/integrations/salesforge.py` — verify complete implementation (402 lines)",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/integrations/salesforge.py"]
    },
    {
        "id": "J3.2.2",
        "part_a": "Verify `SALESFORGE_API_KEY` env var exists in settings",
        "part_b": "Check Railway vars for SALESFORGE_API_KEY",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J3.2.3",
        "part_a": "Verify API key format validation in SalesforgeClient",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/integrations/salesforge.py"]
    },
    {
        "id": "J3.2.4",
        "part_a": "Verify `send_email` method complete with all required parameters",
        "part_b": "Call Salesforge API with test data (TEST_MODE)",
        "key_files": ["src/integrations/salesforge.py"]
    },
    {
        "id": "J3.2.5",
        "part_a": "Verify batch sending support via `send_batch` method",
        "part_b": "Test batch method with 2-3 test emails",
        "key_files": ["src/integrations/salesforge.py"]
    },
    {
        "id": "J3.2.6",
        "part_a": "Verify tags sent with emails (campaign_id, lead_id, client_id)",
        "part_b": "Check Salesforge dashboard for tagged emails",
        "key_files": ["src/integrations/salesforge.py", "src/engines/email.py"]
    }
]

PASS_CRITERIA = [
    "Salesforge integration is complete (402 lines verified)",
    "API key configured in Railway",
    "Emails send successfully via Salesforge",
    "Tags attached for tracking",
    "Warmforge mailbox compatibility preserved",
    "Rate limit 50/day/domain respected"
]

KEY_FILES = [
    "src/integrations/salesforge.py",
    "src/config/settings.py",
    "src/engines/email.py"
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
