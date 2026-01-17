"""
Skill: J1.1 — Login Page
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify login page renders and authenticates users.
"""

CHECKS = [
    {
        "id": "J1.1.1",
        "part_a": "Read `frontend/app/(auth)/login/page.tsx` — verify Supabase `signInWithPassword`",
        "part_b": "Load /login, verify form renders",
        "key_files": ["frontend/app/(auth)/login/page.tsx"]
    },
    {
        "id": "J1.1.2",
        "part_a": "Verify `createBrowserClient()` import from `@/lib/supabase`",
        "part_b": "Submit valid credentials, observe redirect to /dashboard",
        "key_files": ["frontend/lib/supabase.ts"]
    },
    {
        "id": "J1.1.3",
        "part_a": "Verify Google OAuth uses `signInWithOAuth` with provider 'google'",
        "part_b": "Click Google button, observe OAuth flow",
        "key_files": ["frontend/app/(auth)/login/page.tsx"]
    },
    {
        "id": "J1.1.4",
        "part_a": "Verify redirect URL is `${window.location.origin}/auth/callback`",
        "part_b": "After OAuth, verify callback handles redirect",
        "key_files": ["frontend/app/(auth)/login/page.tsx"]
    },
    {
        "id": "J1.1.5",
        "part_a": "Verify error toast on failed login",
        "part_b": "Submit invalid credentials, verify error message",
        "key_files": ["frontend/app/(auth)/login/page.tsx"]
    }
]

PASS_CRITERIA = [
    "Login page renders without console errors",
    "Email/password login works",
    "Google OAuth redirects to callback",
    "Error handling shows toast"
]

KEY_FILES = [
    "frontend/app/(auth)/login/page.tsx",
    "frontend/lib/supabase.ts"
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
