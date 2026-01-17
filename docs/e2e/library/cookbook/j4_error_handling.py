"""
Skill: J4.10 — Error Handling
Journey: J4 - SMS Outreach
Checks: 4

Purpose: Verify graceful error handling for SMS operations.
"""

CHECKS = [
    {
        "id": "J4.10.1",
        "part_a": "Verify Twilio errors caught (TwilioRestException)",
        "part_b": "Check exception handling in twilio.py",
        "key_files": ["src/integrations/twilio.py"]
    },
    {
        "id": "J4.10.2",
        "part_a": "Verify DNCR errors caught (DNCRError)",
        "part_b": "Check exception handling in sms.py",
        "key_files": ["src/engines/sms.py", "src/integrations/dncr.py"]
    },
    {
        "id": "J4.10.3",
        "part_a": "Verify EngineResult.fail returned on error",
        "part_b": "Check return structure",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.10.4",
        "part_a": "Verify retry logic in outreach_flow",
        "part_b": "Check @task decorator for retries=2, retry_delay_seconds=10",
        "key_files": ["src/orchestration/flows/outreach_flow.py"]
    }
]

PASS_CRITERIA = [
    "Errors don't crash the flow",
    "DNCR rejections handled gracefully",
    "Failed sends logged with reason",
    "Retries attempted (2x with 10s delay)"
]

KEY_FILES = [
    "src/integrations/twilio.py",
    "src/integrations/dncr.py",
    "src/engines/sms.py",
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
