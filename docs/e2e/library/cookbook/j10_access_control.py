"""
Skill: J10.1 — Admin Access Control
Journey: J10 - Admin Dashboard
Checks: 5

Purpose: Verify admin-only access control for admin routes.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "test_admin": {
        "email": "david.stephens@keiracom.com",
        "role": "admin"
    },
    "test_user": {
        "email": "test@example.com",
        "role": "user"
    }
}

# =============================================================================
# RBAC CONSTANTS
# =============================================================================

ADMIN_ROLES = ["admin", "super_admin"]
USER_ROLES = ["user", "client"]

PROTECTED_ROUTES = [
    "/admin",
    "/admin/clients",
    "/admin/revenue",
    "/admin/costs",
    "/admin/system",
    "/admin/settings"
]

RLS_POLICIES = {
    "admin_only_tables": ["system_config", "admin_audit_log", "global_settings"],
    "client_isolated_tables": ["leads", "campaigns", "outreach_log"],
    "role_check": "auth.jwt()->>'role' IN ('admin', 'super_admin')"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.1.1",
        "part_a": "Read `frontend/middleware.ts` — verify admin route protection",
        "part_b": "Check that /admin routes require admin role",
        "key_files": ["frontend/middleware.ts"],
        "live_test": {
            "type": "code_verify",
            "check": "Middleware protects /admin routes with role check",
            "expect": {
                "code_contains": ["/admin", "role", "admin", "redirect"]
            }
        }
    },
    {
        "id": "J10.1.2",
        "part_a": "Read `frontend/app/admin/layout.tsx` — verify admin layout guards",
        "part_b": "Load /admin as non-admin user, verify redirect to unauthorized",
        "key_files": ["frontend/app/admin/layout.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Log out of any admin account",
                "2. Log in as a regular user (non-admin role)",
                "3. Navigate directly to {frontend_url}/admin",
                "4. Verify redirect to /unauthorized or /dashboard",
                "5. Check no admin content is visible"
            ],
            "expect": {
                "redirect_to": ["/unauthorized", "/dashboard", "/login"],
                "admin_content_hidden": True
            }
        }
    },
    {
        "id": "J10.1.3",
        "part_a": "Verify Supabase RLS policies for admin tables",
        "part_b": "Attempt direct API access without admin role",
        "key_files": ["src/api/routes/admin.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/clients",
            "auth": False,
            "expect": {
                "status": [401, 403],
                "error_message": True
            },
            "curl_command": """curl '{api_url}/api/v1/admin/clients' \\
  -H 'Content-Type: application/json'
# Expected: 401 Unauthorized or 403 Forbidden"""
        }
    },
    {
        "id": "J10.1.4",
        "part_a": "Read `src/api/routes/admin.py` — verify admin dependency",
        "part_b": "Verify `get_current_admin` dependency on all admin routes",
        "key_files": ["src/api/routes/admin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "All admin routes use get_current_admin dependency",
            "expect": {
                "code_contains": ["get_current_admin", "Depends", "admin"]
            }
        }
    },
    {
        "id": "J10.1.5",
        "part_a": "Verify admin role assignment in user model",
        "part_b": "Check admin role is properly stored and retrieved",
        "key_files": ["src/models/user.py", "frontend/lib/auth.ts"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, email, role, created_at
                FROM auth.users
                WHERE raw_user_meta_data->>'role' = 'admin'
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "email", "role"],
                "role_value": "admin"
            },
            "note": "Query checks admin users exist and have proper role assignment"
        }
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

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_frontend_url(path: str) -> str:
    """Get full frontend URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append(f"- Test Admin: {LIVE_CONFIG['test_admin']['email']}")
    lines.append("")
    lines.append("### RBAC Configuration")
    lines.append(f"  Admin Roles: {', '.join(ADMIN_ROLES)}")
    lines.append(f"  Protected Routes: {', '.join(PROTECTED_ROUTES[:3])}...")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
            if lt.get("url"):
                lines.append(f"  URL: {lt['url']}")
            if lt.get("steps"):
                lines.append("  Steps:")
                for step in lt["steps"][:3]:
                    lines.append(f"    {step}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
