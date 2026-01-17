"""
Skill: J7.13 — Error Handling
Journey: J7 - Reply Handling
Checks: 5

Purpose: Verify graceful error handling for reply processing.
"""

CHECKS = [
    {
        "id": "J7.13.1",
        "part_a": "Verify try/catch in closer.py `process_reply` (lines 139-249)",
        "part_b": "Test invalid lead",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.13.2",
        "part_a": "Verify EngineResult.fail returned on error",
        "part_b": "Check return structure",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.13.3",
        "part_a": "Verify webhook returns 200 even on processing error",
        "part_b": "Check webhook response",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.13.4",
        "part_a": "Verify retries on flow tasks (3x)",
        "part_b": "Check task decorator",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"]
    },
    {
        "id": "J7.13.5",
        "part_a": "Verify unknown lead doesn't crash webhook",
        "part_b": "Test unknown sender",
        "key_files": ["src/api/routes/webhooks.py"]
    }
]

PASS_CRITERIA = [
    "Errors don't crash webhook",
    "Retries attempted",
    "Unknown senders logged but don't crash",
    "EngineResult.fail returned on error"
]

KEY_FILES = [
    "src/engines/closer.py",
    "src/api/routes/webhooks.py",
    "src/orchestration/flows/reply_recovery_flow.py"
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
    lines.append("### Retry Configuration Reference")
    lines.append("```python")
    lines.append('@task(name="process_missed_reply", retries=3, retry_delay_seconds=10)')
    lines.append("```")
    return "\n".join(lines)
