"""
Skill: J1.2 — Signup Page & Validation
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify signup page collects required metadata and creates auth user.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "test_signup": {
        "email": "test-{timestamp}@keiracom.com",  # Use unique email
        "password": "TestPass123!",
        "full_name": "E2E Test User",
        "company_name": "E2E Test Agency"
    }
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.2.1",
        "part_a": "Read `frontend/app/(auth)/signup/page.tsx` — verify fields: email, password, full_name, company_name",
        "part_b": "Load /signup, verify all 4 fields present",
        "key_files": ["frontend/app/(auth)/signup/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/signup",
            "auth": False,
            "expect": {
                "status": 200,
                "body_contains": ["email", "password", "name", "company", "Sign up"]
            }
        }
    },
    {
        "id": "J1.2.2",
        "part_a": "Verify `signUp()` passes metadata in `options.data`",
        "part_b": "Fill form, submit, check Supabase auth.users",
        "key_files": ["frontend/app/(auth)/signup/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/signup",
                "2. Fill: email=test-{timestamp}@keiracom.com",
                "3. Fill: password=TestPass123!",
                "4. Fill: full_name=E2E Test User",
                "5. Fill: company_name=E2E Test Agency",
                "6. Click 'Sign up'",
                "7. Query Supabase: SELECT raw_user_meta_data FROM auth.users WHERE email='...'"
            ],
            "expect": {
                "db_contains": {
                    "table": "auth.users",
                    "field": "raw_user_meta_data",
                    "has_keys": ["full_name", "company_name"]
                }
            }
        }
    },
    {
        "id": "J1.2.3",
        "part_a": "Verify password minLength=8 attribute",
        "part_b": "Submit short password, verify validation",
        "key_files": ["frontend/app/(auth)/signup/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/signup",
                "2. Fill email and name fields",
                "3. Enter password: 'short'",
                "4. Try to submit",
                "5. Verify validation error appears"
            ],
            "expect": {
                "validation_error": True,
                "error_contains": ["8", "characters", "password"]
            }
        }
    },
    {
        "id": "J1.2.4",
        "part_a": "Verify `emailRedirectTo` is `/auth/callback`",
        "part_b": "After signup, check email for correct link",
        "key_files": ["frontend/app/(auth)/signup/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Complete signup with valid data",
                "2. Check email inbox for david.stephens@keiracom.com",
                "3. Inspect confirmation link URL",
                "4. Verify link contains '/auth/callback'"
            ],
            "expect": {
                "email_link_contains": "/auth/callback"
            }
        }
    },
    {
        "id": "J1.2.5",
        "part_a": "Verify success redirects to /login with 'check email' message",
        "part_b": "Submit valid signup, verify redirect + toast",
        "key_files": ["frontend/app/(auth)/signup/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Complete signup with valid data",
                "2. Observe redirect to /login",
                "3. Verify toast/message about checking email"
            ],
            "expect": {
                "redirect_to": "/login",
                "message_contains": ["check", "email", "confirm"]
            }
        }
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

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_live_url(path: str) -> str:
    """Get full URL for live testing."""
    return f"{LIVE_CONFIG['frontend_url']}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
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
            if lt.get("steps"):
                lines.append("  Steps:")
                for step in lt["steps"]:
                    lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
