"""
Skill: J1.5 — Middleware Route Protection
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify protected routes require authentication.
"""

CHECKS = [
    {
        "id": "J1.5.1",
        "part_a": "Read `frontend/middleware.ts` — verify protectedRoutes array",
        "part_b": "N/A",
        "key_files": ["frontend/middleware.ts"]
    },
    {
        "id": "J1.5.2",
        "part_a": "Verify /dashboard in protected list",
        "part_b": "Access /dashboard unauthenticated, verify redirect to /login",
        "key_files": ["frontend/middleware.ts"]
    },
    {
        "id": "J1.5.3",
        "part_a": "Verify /admin in protected list",
        "part_b": "Access /admin unauthenticated, verify redirect",
        "key_files": ["frontend/middleware.ts"]
    },
    {
        "id": "J1.5.4",
        "part_a": "Verify /onboarding in protected list",
        "part_b": "Access /onboarding unauthenticated, verify redirect",
        "key_files": ["frontend/middleware.ts"]
    },
    {
        "id": "J1.5.5",
        "part_a": "Verify public routes bypass middleware",
        "part_b": "Access /, /login, /signup without auth, verify allowed",
        "key_files": ["frontend/middleware.ts"]
    }
]

PASS_CRITERIA = [
    "Protected routes redirect to /login",
    "Redirect includes `?redirect=` param",
    "Public routes accessible without auth"
]

KEY_FILES = [
    "frontend/middleware.ts"
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
