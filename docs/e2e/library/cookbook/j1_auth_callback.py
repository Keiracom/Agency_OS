"""
Skill: J1.4 — Auth Callback
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify callback exchanges code and checks onboarding status.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "test_user": {
        "email": "david.stephens@keiracom.com",
    }
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.4.1",
        "part_a": "Read `frontend/app/auth/callback/route.ts` — verify `exchangeCodeForSession`",
        "part_b": "Click email confirmation link",
        "key_files": ["frontend/app/auth/callback/route.ts"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Sign up with new email (or request password reset)",
                "2. Check email for confirmation/magic link",
                "3. Click link - should hit /auth/callback?code=xxx",
                "4. Observe redirect after callback completes"
            ],
            "expect": {
                "callback_processes": True,
                "redirect_to": ["/onboarding", "/dashboard"]
            }
        }
    },
    {
        "id": "J1.4.2",
        "part_a": "Verify `get_onboarding_status()` RPC called",
        "part_b": "Check database for RPC execution",
        "key_files": ["frontend/app/auth/callback/route.ts"],
        "live_test": {
            "type": "code_verify",
            "check": "Callback route calls supabase.rpc('get_onboarding_status')",
            "expect": {
                "code_contains": ["rpc", "get_onboarding_status"]
            }
        }
    },
    {
        "id": "J1.4.3",
        "part_a": "Verify redirect to /onboarding if `needs_onboarding=true`",
        "part_b": "New user → should redirect to /onboarding",
        "key_files": ["frontend/app/auth/callback/route.ts"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Create NEW user (no ICP confirmed)",
                "2. Confirm email via callback",
                "3. Observe final redirect URL"
            ],
            "expect": {
                "redirect_to": "/onboarding"
            },
            "condition": "User has NOT confirmed ICP (icp_confirmed_at IS NULL)"
        }
    },
    {
        "id": "J1.4.4",
        "part_a": "Verify redirect to /dashboard if `needs_onboarding=false`",
        "part_b": "User with ICP confirmed → should redirect to /dashboard",
        "key_files": ["frontend/app/auth/callback/route.ts"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Login as user WITH confirmed ICP",
                "2. Or set icp_confirmed_at in DB: UPDATE clients SET icp_confirmed_at = NOW()",
                "3. Go through callback flow",
                "4. Observe final redirect URL"
            ],
            "expect": {
                "redirect_to": "/dashboard"
            },
            "condition": "User HAS confirmed ICP (icp_confirmed_at IS NOT NULL)"
        }
    },
    {
        "id": "J1.4.5",
        "part_a": "Verify error handling redirects to `/login?error=auth_failed`",
        "part_b": "Simulate invalid code",
        "key_files": ["frontend/app/auth/callback/route.ts"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/auth/callback?code=invalid_code_12345",
            "auth": False,
            "expect": {
                "status": 302,
                "redirect_contains": "/login"
            }
        }
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

# =============================================================================
# ONBOARDING STATUS CHECK
# =============================================================================

ONBOARDING_STATUS_QUERY = """
-- Check if user needs onboarding
SELECT
    c.icp_confirmed_at IS NULL as needs_onboarding,
    c.icp_confirmed_at
FROM clients c
JOIN memberships m ON m.client_id = c.id
JOIN users u ON u.id = m.user_id
WHERE u.email = '{test_email}';
"""

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Callback: {LIVE_CONFIG['frontend_url']}/auth/callback")
    lines.append("")
    lines.append("### Onboarding Status Query")
    lines.append("```sql")
    lines.append(ONBOARDING_STATUS_QUERY.strip())
    lines.append("```")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("steps"):
            lines.append("  Steps:")
            for step in lt["steps"]:
                lines.append(f"    {step}")
        if lt.get("condition"):
            lines.append(f"  Condition: {lt['condition']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
