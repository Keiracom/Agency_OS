"""
Skill: J1.6 — Onboarding Page (Website URL)
Journey: J1 - Signup & Onboarding
Checks: 6

Purpose: Verify main onboarding page accepts website URL and triggers extraction.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "test_agency": {
        "name": "Sparro Digital",
        "website": "https://sparro.com.au"
    },
    "test_user": {
        "email": "david.stephens@keiracom.com"
    }
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.6.1",
        "part_a": "Read `frontend/app/onboarding/page.tsx` — verify form exists",
        "part_b": "Load /onboarding, verify input field",
        "key_files": ["frontend/app/onboarding/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/onboarding",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["website", "URL", "Discover"]
            },
            "note": "Requires authenticated session - will redirect to /login if not logged in"
        }
    },
    {
        "id": "J1.6.2",
        "part_a": "Verify API call to `/api/v1/onboarding/analyze`",
        "part_b": "Submit URL, check network request",
        "key_files": ["frontend/app/onboarding/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/onboarding/analyze",
            "auth": True,
            "body": {
                "website_url": "https://sparro.com.au"
            },
            "expect": {
                "status": 202,
                "body_has_field": "job_id"
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/onboarding/analyze' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"website_url": "https://sparro.com.au"}'"""
        }
    },
    {
        "id": "J1.6.3",
        "part_a": "Verify Authorization header includes session token",
        "part_b": "Check request headers",
        "key_files": ["frontend/app/onboarding/page.tsx"],
        "live_test": {
            "type": "code_verify",
            "check": "fetch call includes Authorization: Bearer ${session.access_token}",
            "expect": {
                "code_contains": ["Authorization", "Bearer", "access_token"]
            }
        }
    },
    {
        "id": "J1.6.4",
        "part_a": "Verify `job_id` stored in localStorage",
        "part_b": "After submit, check localStorage",
        "key_files": ["frontend/app/onboarding/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Login and go to /onboarding",
                "2. Enter https://sparro.com.au",
                "3. Click 'Discover My ICP'",
                "4. Open DevTools > Application > Local Storage",
                "5. Verify 'icp_job_id' key exists with UUID value"
            ],
            "expect": {
                "localStorage_key": "icp_job_id",
                "localStorage_value_format": "UUID"
            }
        }
    },
    {
        "id": "J1.6.5",
        "part_a": "Verify redirect to `/dashboard?icp_job={job_id}`",
        "part_b": "After submit, verify URL",
        "key_files": ["frontend/app/onboarding/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Complete J1.6.4 steps",
                "2. Observe URL after redirect",
                "3. Verify URL is /dashboard?icp_job=<uuid>"
            ],
            "expect": {
                "url_pattern": "/dashboard?icp_job=*"
            }
        }
    },
    {
        "id": "J1.6.6",
        "part_a": "Verify 'Skip for now' link goes to /onboarding/skip",
        "part_b": "Click skip, verify navigation",
        "key_files": ["frontend/app/onboarding/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Go to /onboarding",
                "2. Click 'Skip for now' link",
                "3. Verify navigation to /onboarding/skip"
            ],
            "expect": {
                "redirect_to": "/onboarding/skip"
            }
        }
    }
]

PASS_CRITERIA = [
    "Page renders with URL input",
    "Submit triggers API call",
    "Job ID received and stored",
    "Redirect to dashboard with job param"
]

KEY_FILES = [
    "frontend/app/onboarding/page.tsx",
    "src/api/routes/onboarding.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Test Website: {LIVE_CONFIG['test_agency']['website']}")
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
        if lt.get("curl_command"):
            lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
