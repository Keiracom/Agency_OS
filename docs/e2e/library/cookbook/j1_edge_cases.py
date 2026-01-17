"""
Skill: J1.15 — Edge Cases & Error Handling
Journey: J1 - Signup & Onboarding
Checks: 7

Purpose: Test failure scenarios and edge cases.
"""

CHECKS = [
    {
        "id": "J1.15.1",
        "part_a": "Verify session expiry handled",
        "part_b": "Let session expire, verify redirect to login",
        "key_files": []
    },
    {
        "id": "J1.15.2",
        "part_a": "Verify duplicate email rejected",
        "part_b": "Try signup with existing email",
        "key_files": []
    },
    {
        "id": "J1.15.3",
        "part_a": "Verify invalid URL rejected",
        "part_b": "Submit malformed URL",
        "key_files": []
    },
    {
        "id": "J1.15.4",
        "part_a": "Verify extraction timeout handled",
        "part_b": "Submit slow site, check timeout behavior",
        "key_files": []
    },
    {
        "id": "J1.15.5",
        "part_a": "Verify browser refresh preserves job_id",
        "part_b": "Refresh during extraction, verify continues",
        "key_files": []
    },
    {
        "id": "J1.15.6",
        "part_a": "Verify concurrent extractions handled",
        "part_b": "Submit multiple URLs",
        "key_files": []
    },
    {
        "id": "J1.15.7",
        "part_a": "Verify deleted user/client rejected",
        "part_b": "Delete user, try access",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "Session expiry redirects cleanly",
    "Duplicate email shows error",
    "Invalid URLs rejected",
    "Timeouts handled gracefully",
    "Refresh doesn't break flow"
]

KEY_FILES = []

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
