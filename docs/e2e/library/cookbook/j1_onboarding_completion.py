"""
Skill: J1.13 — Onboarding Completion
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify onboarding completes and user lands on dashboard.
"""

CHECKS = [
    {
        "id": "J1.13.1",
        "part_a": "Verify `icp_confirmed_at` being set marks onboarding complete",
        "part_b": "Query database",
        "key_files": []
    },
    {
        "id": "J1.13.2",
        "part_a": "Verify `get_onboarding_status()` returns `needs_onboarding=false` after confirm",
        "part_b": "Call RPC",
        "key_files": []
    },
    {
        "id": "J1.13.3",
        "part_a": "Verify dashboard loads without redirect loop",
        "part_b": "Access /dashboard after confirm",
        "key_files": []
    },
    {
        "id": "J1.13.4",
        "part_a": "Verify ICP data displayed on dashboard",
        "part_b": "Check dashboard shows ICP",
        "key_files": ["frontend/app/dashboard/page.tsx"]
    },
    {
        "id": "J1.13.5",
        "part_a": "Verify activity logged for onboarding completion",
        "part_b": "Query activities table",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "Onboarding status reflects complete",
    "Dashboard accessible",
    "No redirect loops",
    "ICP visible on dashboard"
]

KEY_FILES = [
    "frontend/app/dashboard/page.tsx"
]

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
