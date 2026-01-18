"""
Skill: J1.1 — Login Page
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify login page renders and authenticates users.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "test_user": {
        "email": "david.stephens@keiracom.com",
        "password": "{{TEST_USER_PASSWORD}}",  # From environment
    },
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.1.1",
        "part_a": "Read `frontend/app/(auth)/login/page.tsx` — verify Supabase `signInWithPassword`",
        "part_b": "Load /login, verify form renders",
        "key_files": ["frontend/app/(auth)/login/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/login",
            "auth": False,
            "expect": {
                "status": 200,
                "body_contains": ["email", "password", "Sign in"]
            }
        }
    },
    {
        "id": "J1.1.2",
        "part_a": "Verify `createBrowserClient()` import from `@/lib/supabase`",
        "part_b": "Submit valid credentials, observe redirect to /dashboard",
        "key_files": ["frontend/lib/supabase.ts"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/login in browser",
                "2. Enter test credentials: {test_user.email}",
                "3. Click 'Sign in'",
                "4. Verify redirect to /dashboard or /onboarding"
            ],
            "expect": {
                "redirect_to": ["/dashboard", "/onboarding"]
            }
        }
    },
    {
        "id": "J1.1.3",
        "part_a": "Verify Google OAuth uses `signInWithOAuth` with provider 'google'",
        "part_b": "Click Google button, observe OAuth flow",
        "key_files": ["frontend/app/(auth)/login/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/login",
                "2. Click 'Continue with Google' button",
                "3. Verify redirect to Google OAuth consent screen",
                "4. URL should contain accounts.google.com"
            ],
            "expect": {
                "redirect_contains": "accounts.google.com"
            }
        }
    },
    {
        "id": "J1.1.4",
        "part_a": "Verify redirect URL is `${window.location.origin}/auth/callback`",
        "part_b": "After OAuth, verify callback handles redirect",
        "key_files": ["frontend/app/(auth)/login/page.tsx"],
        "live_test": {
            "type": "code_verify",
            "check": "redirectTo parameter in signInWithOAuth contains '/auth/callback'",
            "expect": {
                "code_contains": "/auth/callback"
            }
        }
    },
    {
        "id": "J1.1.5",
        "part_a": "Verify error toast on failed login",
        "part_b": "Submit invalid credentials, verify error message",
        "key_files": ["frontend/app/(auth)/login/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/login",
                "2. Enter email: invalid@test.com",
                "3. Enter password: wrongpassword",
                "4. Click 'Sign in'",
                "5. Verify error toast appears"
            ],
            "expect": {
                "shows_error": True,
                "error_contains": ["Invalid", "credentials", "failed"]
            }
        }
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

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_live_url(path: str) -> str:
    """Get full URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Test User: {LIVE_CONFIG['test_user']['email']}")
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
                for step in lt["steps"]:
                    lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
