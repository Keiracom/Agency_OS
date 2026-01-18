"""
Skill: J1.5 — Middleware Route Protection
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify protected routes require authentication.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "protected_routes": ["/dashboard", "/admin", "/onboarding"],
    "public_routes": ["/", "/login", "/signup", "/about", "/pricing"]
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.5.1",
        "part_a": "Read `frontend/middleware.ts` — verify protectedRoutes array",
        "part_b": "N/A (code verification only)",
        "key_files": ["frontend/middleware.ts"],
        "live_test": {
            "type": "code_verify",
            "check": "protectedRoutes array contains /dashboard, /admin, /onboarding",
            "expect": {
                "code_contains": ["protectedRoutes", "/dashboard", "/admin", "/onboarding"]
            }
        }
    },
    {
        "id": "J1.5.2",
        "part_a": "Verify /dashboard in protected list",
        "part_b": "Access /dashboard unauthenticated, verify redirect to /login",
        "key_files": ["frontend/middleware.ts"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/dashboard",
            "auth": False,
            "follow_redirects": False,
            "expect": {
                "status": 307,
                "header_location_contains": "/login?redirect="
            },
            "curl_command": "curl -I -s 'https://agency-os-liart.vercel.app/dashboard' | grep -i location"
        }
    },
    {
        "id": "J1.5.3",
        "part_a": "Verify /admin in protected list",
        "part_b": "Access /admin unauthenticated, verify redirect",
        "key_files": ["frontend/middleware.ts"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin",
            "auth": False,
            "follow_redirects": False,
            "expect": {
                "status": 307,
                "header_location_contains": "/login?redirect="
            },
            "curl_command": "curl -I -s 'https://agency-os-liart.vercel.app/admin' | grep -i location"
        }
    },
    {
        "id": "J1.5.4",
        "part_a": "Verify /onboarding in protected list",
        "part_b": "Access /onboarding unauthenticated, verify redirect",
        "key_files": ["frontend/middleware.ts"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/onboarding",
            "auth": False,
            "follow_redirects": False,
            "expect": {
                "status": 307,
                "header_location_contains": "/login?redirect="
            },
            "curl_command": "curl -I -s 'https://agency-os-liart.vercel.app/onboarding' | grep -i location"
        }
    },
    {
        "id": "J1.5.5",
        "part_a": "Verify public routes bypass middleware",
        "part_b": "Access /, /login, /signup without auth, verify allowed",
        "key_files": ["frontend/middleware.ts"],
        "live_test": {
            "type": "http_batch",
            "requests": [
                {"method": "GET", "url": "{frontend_url}/", "expect_status": 200},
                {"method": "GET", "url": "{frontend_url}/login", "expect_status": 200},
                {"method": "GET", "url": "{frontend_url}/signup", "expect_status": 200}
            ],
            "curl_commands": [
                "curl -s -o /dev/null -w '%{http_code}' 'https://agency-os-liart.vercel.app/'",
                "curl -s -o /dev/null -w '%{http_code}' 'https://agency-os-liart.vercel.app/login'",
                "curl -s -o /dev/null -w '%{http_code}' 'https://agency-os-liart.vercel.app/signup'"
            ],
            "expect": {
                "all_status": 200
            }
        }
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

# =============================================================================
# CURL COMMANDS FOR QUICK TESTING
# =============================================================================

CURL_TESTS = """
# Test protected routes (should return 307 redirect)
curl -I -s 'https://agency-os-liart.vercel.app/dashboard' | head -5
curl -I -s 'https://agency-os-liart.vercel.app/admin' | head -5
curl -I -s 'https://agency-os-liart.vercel.app/onboarding' | head -5

# Test public routes (should return 200)
curl -s -o /dev/null -w '%{http_code}\\n' 'https://agency-os-liart.vercel.app/'
curl -s -o /dev/null -w '%{http_code}\\n' 'https://agency-os-liart.vercel.app/login'
curl -s -o /dev/null -w '%{http_code}\\n' 'https://agency-os-liart.vercel.app/signup'
"""

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Protected: {', '.join(LIVE_CONFIG['protected_routes'])}")
    lines.append(f"- Public: {', '.join(LIVE_CONFIG['public_routes'])}")
    lines.append("")
    lines.append("### Quick Test Commands")
    lines.append("```bash")
    lines.append(CURL_TESTS.strip())
    lines.append("```")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("curl_command"):
            lines.append(f"  Curl: {lt['curl_command']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
