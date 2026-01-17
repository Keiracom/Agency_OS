"""
Skill: J10.1 — Admin Access Control
Journey: J10 - Admin Dashboard
Checks: 5

Purpose: Verify admin-only access control for admin routes.
"""

CHECKS = [
    {
        "id": "J10.1.1",
        "part_a": "Read `frontend/middleware.ts` — verify admin route protection",
        "part_b": "Check that /admin routes require admin role",
        "key_files": ["frontend/middleware.ts"]
    },
    {
        "id": "J10.1.2",
        "part_a": "Read `frontend/app/admin/layout.tsx` — verify admin layout guards",
        "part_b": "Load /admin as non-admin user, verify redirect to unauthorized",
        "key_files": ["frontend/app/admin/layout.tsx"]
    },
    {
        "id": "J10.1.3",
        "part_a": "Verify Supabase RLS policies for admin tables",
        "part_b": "Attempt direct API access without admin role",
        "key_files": ["src/api/routes/admin.py"]
    },
    {
        "id": "J10.1.4",
        "part_a": "Read `src/api/routes/admin.py` — verify admin dependency",
        "part_b": "Verify `get_current_admin` dependency on all admin routes",
        "key_files": ["src/api/routes/admin.py"]
    },
    {
        "id": "J10.1.5",
        "part_a": "Verify admin role assignment in user model",
        "part_b": "Check admin role is properly stored and retrieved",
        "key_files": ["src/models/user.py", "frontend/lib/auth.ts"]
    }
]

PASS_CRITERIA = [
    "Non-admins cannot access admin pages",
    "Admin role check works in middleware",
    "Backend admin routes protected by dependency",
    "RLS policies block unauthorized access",
    "Admin role properly assigned and checked"
]

KEY_FILES = [
    "frontend/middleware.ts",
    "frontend/app/admin/layout.tsx",
    "src/api/routes/admin.py",
    "src/models/user.py"
]

# Role Verification Reference
ROLE_CHECKS = {
    "middleware": "Check request.auth.role === 'admin'",
    "layout": "useUser() hook with role check",
    "backend": "get_current_admin dependency injection",
    "database": "RLS policy: auth.jwt()->>'role' = 'admin'"
}

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
