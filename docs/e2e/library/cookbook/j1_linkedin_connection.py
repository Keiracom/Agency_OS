"""
Skill: J1.10 — LinkedIn Credential Connection
Journey: J1 - Signup & Onboarding
Checks: 7

Purpose: Verify LinkedIn connection flow with 2FA support.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "note": "LinkedIn connection requires real credentials - use test account"
}

# =============================================================================
# CONNECTION STATES
# =============================================================================

CONNECTION_STATES = [
    {"state": "form", "component": "LinkedInCredentialForm", "next": "Submit credentials"},
    {"state": "connecting", "component": "LinkedInConnecting", "next": "Wait for response"},
    {"state": "2fa", "component": "LinkedInTwoFactor", "next": "Enter 2FA code"},
    {"state": "success", "component": "LinkedInSuccess", "next": "Continue to dashboard"},
    {"state": "error", "component": "Error message", "next": "Retry or skip"},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.10.1",
        "part_a": "Read `frontend/app/onboarding/linkedin/page.tsx` — verify state machine",
        "part_b": "Load page, verify form",
        "key_files": ["frontend/app/onboarding/linkedin/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/onboarding/linkedin",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["LinkedIn", "email", "password", "Connect"]
            }
        }
    },
    {
        "id": "J1.10.2",
        "part_a": "Verify `useLinkedInConnect` hook calls backend",
        "part_b": "Enter credentials, submit",
        "key_files": ["frontend/hooks/use-linkedin.ts"],
        "live_test": {
            "type": "code_verify",
            "check": "Hook calls /api/v1/linkedin/connect with credentials",
            "expect": {
                "code_contains": ["linkedin/connect", "email", "password"]
            },
            "note": "Live test requires real LinkedIn credentials"
        }
    },
    {
        "id": "J1.10.3",
        "part_a": "Verify 2FA state triggers `LinkedInTwoFactor` component",
        "part_b": "If 2FA required, verify code input",
        "key_files": ["frontend/components/onboarding/LinkedInCredentialForm.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Enter LinkedIn credentials (for account with 2FA)",
                "2. Submit form",
                "3. If 2FA required, verify code input appears",
                "4. Check for 6-digit input field"
            ],
            "expect": {
                "2fa_input_shown": True,
                "input_type": "6-digit code"
            },
            "condition": "Only if LinkedIn account has 2FA enabled"
        }
    },
    {
        "id": "J1.10.4",
        "part_a": "Verify `useLinkedInVerify2FA` hook submits code",
        "part_b": "Enter 2FA code, submit",
        "key_files": ["frontend/hooks/use-linkedin.ts"],
        "live_test": {
            "type": "code_verify",
            "check": "Hook calls /api/v1/linkedin/verify-2fa with code",
            "expect": {
                "code_contains": ["linkedin/verify", "code"]
            }
        }
    },
    {
        "id": "J1.10.5",
        "part_a": "Verify success state shows `LinkedInSuccess` component",
        "part_b": "After connect, verify success screen",
        "key_files": ["frontend/app/onboarding/linkedin/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Complete LinkedIn connection (with real credentials)",
                "2. Wait for connection to complete",
                "3. Verify success screen shows profile info"
            ],
            "expect": {
                "shows_success": True,
                "shows_profile": True
            }
        }
    },
    {
        "id": "J1.10.6",
        "part_a": "Verify polling for async connection completion",
        "part_b": "Check poll interval (2s, max 30 attempts)",
        "key_files": ["frontend/app/onboarding/linkedin/page.tsx"],
        "live_test": {
            "type": "code_verify",
            "check": "Polling logic with interval and max attempts",
            "expect": {
                "code_contains": ["setInterval", "poll", "2000", "30"]
            }
        }
    },
    {
        "id": "J1.10.7",
        "part_a": "Verify 'Skip for now' bypasses connection",
        "part_b": "Click skip, verify redirect to dashboard",
        "key_files": ["frontend/app/onboarding/linkedin/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Go to /onboarding/linkedin",
                "2. Click 'Skip for now' link",
                "3. Verify redirect to /dashboard"
            ],
            "expect": {
                "redirect_to": "/dashboard"
            }
        }
    }
]

PASS_CRITERIA = [
    "Credential form renders",
    "Connection attempt triggers backend",
    "2FA handled when required",
    "Success displays profile info",
    "Skip allows bypass"
]

KEY_FILES = [
    "frontend/app/onboarding/linkedin/page.tsx",
    "frontend/hooks/use-linkedin.ts",
    "frontend/components/onboarding/LinkedInCredentialForm.tsx"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- LinkedIn Page: {LIVE_CONFIG['frontend_url']}/onboarding/linkedin")
    lines.append("")
    lines.append("### Connection State Flow")
    for state in CONNECTION_STATES:
        lines.append(f"  {state['state']}: {state['component']} → {state['next']}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("condition"):
            lines.append(f"  Condition: {lt['condition']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
