"""
Skill: J1.10 — LinkedIn Credential Connection
Journey: J1 - Signup & Onboarding
Checks: 7

Purpose: Verify LinkedIn connection flow with 2FA support.
"""

CHECKS = [
    {
        "id": "J1.10.1",
        "part_a": "Read `frontend/app/onboarding/linkedin/page.tsx` — verify state machine",
        "part_b": "Load page, verify form",
        "key_files": ["frontend/app/onboarding/linkedin/page.tsx"]
    },
    {
        "id": "J1.10.2",
        "part_a": "Verify `useLinkedInConnect` hook calls backend",
        "part_b": "Enter credentials, submit",
        "key_files": ["frontend/hooks/use-linkedin.ts"]
    },
    {
        "id": "J1.10.3",
        "part_a": "Verify 2FA state triggers `LinkedInTwoFactor` component",
        "part_b": "If 2FA required, verify code input",
        "key_files": ["frontend/components/onboarding/LinkedInCredentialForm.tsx"]
    },
    {
        "id": "J1.10.4",
        "part_a": "Verify `useLinkedInVerify2FA` hook submits code",
        "part_b": "Enter 2FA code, submit",
        "key_files": ["frontend/hooks/use-linkedin.ts"]
    },
    {
        "id": "J1.10.5",
        "part_a": "Verify success state shows `LinkedInSuccess` component",
        "part_b": "After connect, verify success screen",
        "key_files": ["frontend/app/onboarding/linkedin/page.tsx"]
    },
    {
        "id": "J1.10.6",
        "part_a": "Verify polling for async connection completion",
        "part_b": "Check poll interval (2s, max 30 attempts)",
        "key_files": ["frontend/app/onboarding/linkedin/page.tsx"]
    },
    {
        "id": "J1.10.7",
        "part_a": "Verify 'Skip for now' bypasses connection",
        "part_b": "Click skip, verify redirect to dashboard",
        "key_files": ["frontend/app/onboarding/linkedin/page.tsx"]
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

# Connection States Reference
CONNECTION_STATES = [
    {"state": "form", "component": "LinkedInCredentialForm", "next": "Submit credentials"},
    {"state": "connecting", "component": "LinkedInConnecting", "next": "Wait for response"},
    {"state": "2fa", "component": "LinkedInTwoFactor", "next": "Enter 2FA code"},
    {"state": "success", "component": "LinkedInSuccess", "next": "Continue to dashboard"},
    {"state": "error", "component": "Error message", "next": "Retry or skip"},
]

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
