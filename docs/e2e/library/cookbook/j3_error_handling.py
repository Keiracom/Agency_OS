"""
Skill: J3.10 — Error Handling
Journey: J3 - Email Outreach
Checks: 4

Purpose: Verify graceful error handling in email sending flow.
"""

CHECKS = [
    {
        "id": "J3.10.1",
        "part_a": "Verify Salesforge/API errors caught and logged in email engine",
        "part_b": "Simulate API failure, check error handling",
        "key_files": ["src/engines/email.py", "src/integrations/salesforge.py"]
    },
    {
        "id": "J3.10.2",
        "part_a": "Verify Sentry capture on failures via sentry_sdk calls",
        "part_b": "Check Sentry dashboard for captured exceptions",
        "key_files": ["src/engines/email.py", "src/integrations/sentry_utils.py"]
    },
    {
        "id": "J3.10.3",
        "part_a": "Verify EngineResult.fail returned on error (not exception raised)",
        "part_b": "Check return structure on failed send",
        "key_files": ["src/engines/email.py", "src/engines/base.py"]
    },
    {
        "id": "J3.10.4",
        "part_a": "Verify retry logic in outreach_flow via @task decorator",
        "part_b": "Check task configuration: retries=2, retry_delay_seconds=10",
        "key_files": ["src/orchestration/flows/outreach_flow.py"]
    }
]

PASS_CRITERIA = [
    "Errors do not crash the flow",
    "Sentry captures exceptions with context",
    "Failed sends logged with reason",
    "Retries attempted (2x with 10s delay)"
]

KEY_FILES = [
    "src/engines/email.py",
    "src/integrations/salesforge.py",
    "src/integrations/sentry_utils.py",
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
