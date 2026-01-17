"""
Skill: J1.2 — Signup Page & Validation
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify signup page collects required metadata and creates auth user.
"""

CHECKS = [
    {
        "id": "J1.2.1",
        "part_a": "Read `frontend/app/(auth)/signup/page.tsx` — verify fields: email, password, full_name, company_name",
        "part_b": "Load /signup, verify all 4 fields present",
        "key_files": ["frontend/app/(auth)/signup/page.tsx"]
    },
    {
        "id": "J1.2.2",
        "part_a": "Verify `signUp()` passes metadata in `options.data`",
        "part_b": "Fill form, submit, check Supabase auth.users",
        "key_files": ["frontend/app/(auth)/signup/page.tsx"]
    },
    {
        "id": "J1.2.3",
        "part_a": "Verify password minLength=8 attribute",
        "part_b": "Submit short password, verify validation",
        "key_files": ["frontend/app/(auth)/signup/page.tsx"]
    },
    {
        "id": "J1.2.4",
        "part_a": "Verify `emailRedirectTo` is `/auth/callback`",
        "part_b": "After signup, check email for correct link",
        "key_files": ["frontend/app/(auth)/signup/page.tsx"]
    },
    {
        "id": "J1.2.5",
        "part_a": "Verify success redirects to /login with 'check email' message",
        "part_b": "Submit valid signup, verify redirect + toast",
        "key_files": ["frontend/app/(auth)/signup/page.tsx"]
    }
]

PASS_CRITERIA = [
    "All 4 fields render",
    "Validation prevents weak passwords",
    "Confirmation email sent",
    "Redirect to login after signup"
]

KEY_FILES = [
    "frontend/app/(auth)/signup/page.tsx"
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
