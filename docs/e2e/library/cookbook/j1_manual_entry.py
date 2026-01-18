"""
Skill: J1.9 — Manual Entry Fallback
Journey: J1 - Signup & Onboarding
Checks: 7

Purpose: Verify manual entry page handles scraper failures.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "test_content": """
        Sparro is a Melbourne-based digital marketing agency specializing in
        performance marketing for e-commerce brands. We help DTC companies
        scale their paid media campaigns with data-driven strategies.
        Our clients include fashion, beauty, and consumer goods brands.
    """,
    "test_linkedin": "https://www.linkedin.com/company/sparro-digital"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.9.1",
        "part_a": "Read `frontend/app/onboarding/manual-entry/page.tsx` — verify 3 tabs",
        "part_b": "Load page, verify tabs",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/onboarding/manual-entry",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Paste Content", "Use LinkedIn", "Skip"]
            }
        }
    },
    {
        "id": "J1.9.2",
        "part_a": "Verify 'Paste Content' tab calls `/api/v1/onboarding/analyze-content`",
        "part_b": "Paste content, submit",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/onboarding/analyze-content",
            "auth": True,
            "body": {
                "content": "Sparro is a Melbourne-based digital marketing agency..."
            },
            "expect": {
                "status": 202,
                "body_has_field": "job_id"
            }
        }
    },
    {
        "id": "J1.9.3",
        "part_a": "Verify min 100 character validation",
        "part_b": "Submit short content, verify error",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Go to /onboarding/manual-entry",
                "2. Select 'Paste Content' tab",
                "3. Enter: 'Short text'",
                "4. Try to submit",
                "5. Verify validation error"
            ],
            "expect": {
                "validation_error": True,
                "error_contains": ["100", "characters"]
            }
        }
    },
    {
        "id": "J1.9.4",
        "part_a": "Verify 'Use LinkedIn' tab calls `/api/v1/onboarding/analyze-linkedin`",
        "part_b": "Enter LinkedIn URL, submit",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/onboarding/analyze-linkedin",
            "auth": True,
            "body": {
                "linkedin_url": "https://www.linkedin.com/company/sparro-digital"
            },
            "expect": {
                "status": 202,
                "body_has_field": "job_id"
            }
        }
    },
    {
        "id": "J1.9.5",
        "part_a": "Verify LinkedIn URL validation (must contain linkedin.com/company)",
        "part_b": "Enter invalid URL, verify error",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Go to /onboarding/manual-entry",
                "2. Select 'Use LinkedIn' tab",
                "3. Enter: 'https://google.com'",
                "4. Try to submit",
                "5. Verify validation error"
            ],
            "expect": {
                "validation_error": True,
                "error_contains": ["LinkedIn", "company"]
            }
        }
    },
    {
        "id": "J1.9.6",
        "part_a": "Verify 'Skip' tab calls `/api/v1/onboarding/skip-icp`",
        "part_b": "Enter company name, skip",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/onboarding/skip-icp",
            "auth": True,
            "body": {
                "company_name": "Test Agency"
            },
            "expect": {
                "status": 200
            },
            "verify_db": "Client should have basic profile with icp_skipped=true"
        }
    },
    {
        "id": "J1.9.7",
        "part_a": "Verify failedUrl preserved from query param",
        "part_b": "Access with ?url=xxx, verify shown",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/onboarding/manual-entry?url=https://failed-site.com",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["failed-site.com"]
            }
        }
    }
]

PASS_CRITERIA = [
    "All 3 tabs render",
    "Paste content validated (min 100 chars)",
    "LinkedIn URL validated",
    "Skip creates basic profile",
    "Failed URL shown to user"
]

KEY_FILES = [
    "frontend/app/onboarding/manual-entry/page.tsx"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Manual Entry: {LIVE_CONFIG['frontend_url']}/onboarding/manual-entry")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("steps"):
            lines.append("  Steps:")
            for step in lt["steps"]:
                lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
