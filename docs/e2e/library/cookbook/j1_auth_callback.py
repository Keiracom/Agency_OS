"""
Skill: J1.4 — Auth Callback
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify callback exchanges code and checks onboarding status.
"""

CHECKS = [
    {
        "id": "J1.4.1",
        "part_a": "Read `frontend/app/auth/callback/route.ts` — verify `exchangeCodeForSession`",
        "part_b": "Click email confirmation link",
        "key_files": ["frontend/app/auth/callback/route.ts"]
    },
    {
        "id": "J1.4.2",
        "part_a": "Verify `get_onboarding_status()` RPC called",
        "part_b": "Check database for RPC execution",
        "key_files": ["frontend/app/auth/callback/route.ts"]
    },
    {
        "id": "J1.4.3",
        "part_a": "Verify redirect to /onboarding if `needs_onboarding=true`",
        "part_b": "New user → should redirect to /onboarding",
        "key_files": ["frontend/app/auth/callback/route.ts"]
    },
    {
        "id": "J1.4.4",
        "part_a": "Verify redirect to /dashboard if `needs_onboarding=false`",
        "part_b": "User with ICP confirmed → should redirect to /dashboard",
        "key_files": ["frontend/app/auth/callback/route.ts"]
    },
    {
        "id": "J1.4.5",
        "part_a": "Verify error handling redirects to `/login?error=auth_failed`",
        "part_b": "Simulate invalid code",
        "key_files": ["frontend/app/auth/callback/route.ts"]
    }
]

PASS_CRITERIA = [
    "Code exchange works",
    "New users redirect to /onboarding",
    "Returning users redirect to /dashboard",
    "Errors handled gracefully"
]

KEY_FILES = [
    "frontend/app/auth/callback/route.ts"
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
