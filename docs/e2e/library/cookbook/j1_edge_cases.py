"""
Skill: J1.15 — Edge Cases & Error Handling
Journey: J1 - Signup & Onboarding
Checks: 7

Purpose: Test failure scenarios and edge cases.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "test_user": {
        "email": "david.stephens@keiracom.com"
    },
    "test_data": {
        "existing_email": "david.stephens@keiracom.com",
        "invalid_url": "not-a-valid-url",
        "slow_site": "https://archive.org",
        "malformed_url": "htp://missing-t.com"
    }
}

# =============================================================================
# EDGE CASE SCENARIOS
# =============================================================================

EDGE_CASES = [
    {"scenario": "session_expiry", "expected": "Redirect to /login"},
    {"scenario": "duplicate_email", "expected": "Error: Email already registered"},
    {"scenario": "invalid_url", "expected": "422 validation error"},
    {"scenario": "extraction_timeout", "expected": "Graceful timeout, manual fallback offered"},
    {"scenario": "browser_refresh", "expected": "Job continues, progress preserved"},
    {"scenario": "concurrent_jobs", "expected": "Each job tracked independently"},
    {"scenario": "deleted_user", "expected": "401 Unauthorized"},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.15.1",
        "part_a": "Verify session expiry handled",
        "part_b": "Let session expire, verify redirect to login",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Login to the application",
                "2. Copy the JWT token from localStorage or cookies",
                "3. Wait for token to expire (or manually invalidate)",
                "4. Try to access /dashboard",
                "5. Verify redirect to /login",
                "6. Verify no error page shown"
            ],
            "expect": {
                "redirect_to": "/login",
                "error_page_shown": False
            },
            "alternative": "Use browser DevTools to clear session, then refresh"
        }
    },
    {
        "id": "J1.15.2",
        "part_a": "Verify duplicate email rejected",
        "part_b": "Try signup with existing email",
        "key_files": [],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{supabase_url}/auth/v1/signup",
            "headers": {
                "apikey": "{anon_key}",
                "Content-Type": "application/json"
            },
            "body": {
                "email": "david.stephens@keiracom.com",
                "password": "TestPassword123!"
            },
            "expect": {
                "status": 400,
                "body_contains": ["already registered", "exists"]
            },
            "curl_command": """curl -X POST '{supabase_url}/auth/v1/signup' \\
  -H 'apikey: {anon_key}' \\
  -H 'Content-Type: application/json' \\
  -d '{"email": "existing@email.com", "password": "Test123!"}'"""
        }
    },
    {
        "id": "J1.15.3",
        "part_a": "Verify invalid URL rejected",
        "part_b": "Submit malformed URL",
        "key_files": [],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/onboarding/analyze",
            "auth": True,
            "body": {"website_url": "not-a-valid-url"},
            "expect": {
                "status": 422,
                "body_contains": ["invalid", "URL"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/onboarding/analyze' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"website_url": "not-a-valid-url"}'"""
        }
    },
    {
        "id": "J1.15.4",
        "part_a": "Verify extraction timeout handled",
        "part_b": "Submit slow site, check timeout behavior",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Submit a known slow/problematic site to /onboarding/analyze",
                "2. Monitor job status polling",
                "3. Wait for timeout (usually 5-10 minutes)",
                "4. Verify job status = 'failed' or 'timeout'",
                "5. Verify manual entry fallback URL offered"
            ],
            "test_urls": [
                "https://archive.org (slow)",
                "https://this-site-will-timeout.fake (unreachable)"
            ],
            "expect": {
                "graceful_failure": True,
                "fallback_offered": True,
                "error_message_helpful": True
            }
        }
    },
    {
        "id": "J1.15.5",
        "part_a": "Verify browser refresh preserves job_id",
        "part_b": "Refresh during extraction, verify continues",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Start extraction with POST /onboarding/analyze",
                "2. Note the job_id returned",
                "3. Observe redirect to /dashboard?icp_job={job_id}",
                "4. Refresh browser (F5)",
                "5. Verify job_id still in URL or localStorage",
                "6. Verify extraction continues (poll status)",
                "7. Verify completion works normally"
            ],
            "expect": {
                "job_preserved": True,
                "extraction_continues": True,
                "no_duplicate_job": True
            }
        }
    },
    {
        "id": "J1.15.6",
        "part_a": "Verify concurrent extractions handled",
        "part_b": "Submit multiple URLs",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Call POST /onboarding/analyze with URL A",
                "2. Immediately call POST /onboarding/analyze with URL B",
                "3. Capture both job_ids",
                "4. Poll status for both jobs",
                "5. Verify both jobs tracked independently",
                "6. Verify no interference between jobs"
            ],
            "expect": {
                "both_jobs_created": True,
                "independent_tracking": True,
                "no_data_mixing": True
            },
            "note": "Business logic may allow only one active job per client"
        }
    },
    {
        "id": "J1.15.7",
        "part_a": "Verify deleted user/client rejected",
        "part_b": "Delete user, try access",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Create test user account",
                "2. Complete signup and get JWT",
                "3. Soft-delete user (set deleted_at)",
                "4. Try to access /dashboard with old JWT",
                "5. Verify 401 Unauthorized returned",
                "6. Try API calls with old token",
                "7. Verify all API calls rejected"
            ],
            "expect": {
                "status": 401,
                "access_denied": True,
                "session_invalidated": True
            },
            "warning": "This test modifies data - use test account only"
        }
    }
]

PASS_CRITERIA = [
    "Session expiry redirects cleanly to /login",
    "Duplicate email shows helpful error",
    "Invalid URLs rejected with 422",
    "Timeouts handled gracefully",
    "Browser refresh doesn't break flow",
    "Concurrent jobs isolated",
    "Deleted users cannot access system"
]

KEY_FILES = []

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append("")
    lines.append("### Edge Case Scenarios")
    for ec in EDGE_CASES:
        lines.append(f"  {ec['scenario']}: {ec['expected']}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("steps"):
            lines.append("  Steps:")
            for step in lt["steps"][:3]:
                lines.append(f"    {step}")
            if len(lt["steps"]) > 3:
                lines.append(f"    ... ({len(lt['steps'])-3} more steps)")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
