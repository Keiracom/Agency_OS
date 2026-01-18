"""
Skill: J10.14 — Compliance Pages
Journey: J10 - Admin Dashboard
Checks: 6

Purpose: Verify compliance management including suppression lists and bounces.
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
    }
}

# =============================================================================
# COMPLIANCE CONSTANTS
# =============================================================================

COMPLIANCE_TYPES = [
    {"type": "suppression", "reason": "Unsubscribe request", "action": "Never email again"},
    {"type": "hard_bounce", "reason": "Invalid email", "action": "Add to suppression"},
    {"type": "soft_bounce", "reason": "Temporary failure", "action": "Retry later"},
    {"type": "spam_complaint", "reason": "Marked as spam", "action": "Add to suppression"},
    {"type": "dncr", "reason": "Do Not Call Registry", "action": "Never call/SMS"}
]

BOUNCE_CATEGORIES = {
    "hard": {
        "examples": ["Invalid email", "Domain not found", "User unknown"],
        "action": "Permanent suppression",
        "color": "red"
    },
    "soft": {
        "examples": ["Mailbox full", "Server temporarily unavailable", "Rate limited"],
        "action": "Retry up to 3 times",
        "color": "yellow"
    }
}

DNCR_CONFIG = {
    "registry": "Australian Do Not Call Register",
    "check_frequency": "Before every SMS/Voice outreach",
    "cache_duration": "24 hours"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.14.1",
        "part_a": "Read `frontend/app/admin/compliance/page.tsx` — verify layout",
        "part_b": "Load compliance page, verify sections render",
        "key_files": ["frontend/app/admin/compliance/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin/compliance",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Compliance", "Suppression", "Bounces"]
            },
            "manual_steps": [
                "1. Login as admin user",
                "2. Navigate to {frontend_url}/admin/compliance",
                "3. Verify compliance overview page loads",
                "4. Check sections: Suppression List, Bounces, DNCR"
            ]
        }
    },
    {
        "id": "J10.14.2",
        "part_a": "Read `frontend/app/admin/compliance/suppression/page.tsx` — verify list",
        "part_b": "Load suppression page, verify suppressed emails display",
        "key_files": ["frontend/app/admin/compliance/suppression/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/compliance/suppression?limit=20",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["email", "reason", "suppressed_at"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/compliance/suppression?limit=20' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J10.14.3",
        "part_a": "Verify suppression list add functionality",
        "part_b": "Add email to suppression, verify it appears in list",
        "key_files": ["frontend/app/admin/compliance/suppression/page.tsx", "src/api/routes/admin.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/admin/compliance/suppression",
            "auth": True,
            "body": {
                "email": "test-suppression@e2e-test.com",
                "reason": "E2E test - manual suppression"
            },
            "expect": {
                "status": [200, 201],
                "body_has_field": "id"
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/admin/compliance/suppression' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"email": "test@example.com", "reason": "Manual suppression"}'""",
            "cleanup": "Remove test email from suppression after test",
            "manual_steps": [
                "1. On /admin/compliance/suppression page, click 'Add to Suppression'",
                "2. Enter test email address",
                "3. Select reason (manual/unsubscribe/spam)",
                "4. Click Submit",
                "5. Verify email appears in suppression list"
            ]
        }
    },
    {
        "id": "J10.14.4",
        "part_a": "Read `frontend/app/admin/compliance/bounces/page.tsx` — verify display",
        "part_b": "Load bounces page, verify bounce list renders",
        "key_files": ["frontend/app/admin/compliance/bounces/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/compliance/bounces?limit=20",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["email", "bounce_type", "bounced_at", "error_message"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/compliance/bounces?limit=20' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J10.14.5",
        "part_a": "Verify bounce categorization",
        "part_b": "Check hard/soft bounce categories display correctly",
        "key_files": ["frontend/app/admin/compliance/bounces/page.tsx"],
        "live_test": {
            "type": "api_batch",
            "tests": [
                {
                    "name": "Filter hard bounces",
                    "method": "GET",
                    "url": "{api_url}/api/v1/admin/compliance/bounces?type=hard&limit=10",
                    "expect": {"all_items_have": {"bounce_type": "hard"}}
                },
                {
                    "name": "Filter soft bounces",
                    "method": "GET",
                    "url": "{api_url}/api/v1/admin/compliance/bounces?type=soft&limit=10",
                    "expect": {"all_items_have": {"bounce_type": "soft"}}
                }
            ],
            "auth": True,
            "curl_command": """curl '{api_url}/api/v1/admin/compliance/bounces?type=hard&limit=10' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/compliance/bounces page, locate bounce filter",
                "2. Select 'Hard Bounces' filter",
                "3. Verify only hard bounces show (red indicators)",
                "4. Select 'Soft Bounces' filter",
                "5. Verify only soft bounces show (yellow indicators)"
            ]
        }
    },
    {
        "id": "J10.14.6",
        "part_a": "Verify DNCR (Do Not Call Registry) integration",
        "part_b": "Check DNCR status for phone numbers displays",
        "key_files": ["frontend/app/admin/compliance/page.tsx", "src/integrations/dncr.py"],
        "live_test": {
            "type": "code_verify",
            "check": "DNCR integration exists and is configured",
            "expect": {
                "code_contains": ["dncr", "do_not_call", "check_number"]
            },
            "manual_steps": [
                "1. On /admin/compliance page, locate DNCR section",
                "2. Check DNCR integration status shows connected",
                "3. View DNCR blocked numbers count",
                "4. Verify DNCR check happens before SMS/Voice outreach"
            ],
            "note": "DNCR is Australian Do Not Call Register - required for SMS/Voice compliance"
        }
    }
]

PASS_CRITERIA = [
    "Compliance page loads correctly",
    "Suppression list displays and is manageable",
    "Adding to suppression works",
    "Bounce list displays correctly",
    "Bounce categories are accurate",
    "DNCR status is visible"
]

KEY_FILES = [
    "frontend/app/admin/compliance/page.tsx",
    "frontend/app/admin/compliance/suppression/page.tsx",
    "frontend/app/admin/compliance/bounces/page.tsx",
    "src/api/routes/admin.py",
    "src/integrations/dncr.py"
]

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
    lines.append(f"- Compliance Page: {LIVE_CONFIG['frontend_url']}/admin/compliance")
    lines.append("")
    lines.append("### Compliance Types")
    for ct in COMPLIANCE_TYPES:
        lines.append(f"  - {ct['type']}: {ct['reason']} -> {ct['action']}")
    lines.append("")
    lines.append("### Bounce Categories")
    for category, info in BOUNCE_CATEGORIES.items():
        lines.append(f"  - {category}: {info['action']} ({info['color']})")
        lines.append(f"    Examples: {', '.join(info['examples'][:2])}")
    lines.append("")
    lines.append("### DNCR Configuration")
    lines.append(f"  Registry: {DNCR_CONFIG['registry']}")
    lines.append(f"  Check Frequency: {DNCR_CONFIG['check_frequency']}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("type"):
            lines.append(f"  Live Test Type: {lt['type']}")
        if lt.get("curl_command"):
            lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
