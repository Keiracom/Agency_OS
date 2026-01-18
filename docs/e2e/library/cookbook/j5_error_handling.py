"""
Skill: J5.12 — Error Handling
Journey: J5 - Voice Outreach
Checks: 4

Purpose: Verify graceful error handling.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "client_id": "81dbaee6-4e71-48ad-be40-fa915fae66e0",
    "user_id": "a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2",
    "test_email": "david.stephens@keiracom.com",
    "test_phone": "+61457543392",
    "warning": "Error handling tests should use invalid inputs, not crash production"
}

# =============================================================================
# ERROR HANDLING REQUIREMENTS
# =============================================================================

ERROR_HANDLING = {
    "expected_errors": [
        "VapiError",
        "ValidationError",
        "RateLimitError",
        "AuthenticationError"
    ],
    "required_validations": [
        "assistant_id required",
        "phone number required",
        "lead_id required",
        "campaign_id required"
    ],
    "error_response_format": {
        "success": False,
        "error": "<error message>",
        "error_type": "<error type>"
    },
    "return_type": "EngineResult"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.12.1",
        "part_a": "Verify Vapi errors caught",
        "part_b": "Check exception handling in voice.py",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Vapi errors are caught and handled",
            "expect": {
                "code_contains": ["except", "VapiError", "Exception", "try"]
            }
        }
    },
    {
        "id": "J5.12.2",
        "part_a": "Verify EngineResult.fail returned on error",
        "part_b": "Check return structure on failures",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "EngineResult.fail() used for error responses",
            "expect": {
                "code_contains": ["EngineResult", "fail", "success=False"]
            }
        }
    },
    {
        "id": "J5.12.3",
        "part_a": "Verify missing assistant_id handled",
        "part_b": "Test without assistant_id, verify error message",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/voice/calls",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "campaign_id": "{test_campaign_id}"
                # Missing assistant_id intentionally
            },
            "expect": {
                "status": [400, 422],
                "body_contains": ["assistant_id", "required"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/voice/calls' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{lead_id}", "campaign_id": "{campaign_id}"}'"""
        }
    },
    {
        "id": "J5.12.4",
        "part_a": "Verify missing phone handled",
        "part_b": "Test without phone, verify error message",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/voice/calls",
            "auth": True,
            "body": {
                "lead_id": "{lead_without_phone}",
                "assistant_id": "{test_assistant_id}"
            },
            "test_setup": "Use lead ID with no phone number",
            "expect": {
                "status": 400,
                "body_contains": ["phone", "required", "missing"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/voice/calls' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{lead_without_phone}", "assistant_id": "{assistant_id}"}'"""
        }
    }
]

PASS_CRITERIA = [
    "Errors don't crash the flow",
    "Clear error messages returned",
    "Required fields validated"
]

KEY_FILES = [
    "src/engines/voice.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### Error Handling Requirements")
    lines.append(f"  Expected Errors: {', '.join(ERROR_HANDLING['expected_errors'])}")
    lines.append("  Required Validations:")
    for validation in ERROR_HANDLING['required_validations']:
        lines.append(f"    - {validation}")
    lines.append(f"  Return Type: {ERROR_HANDLING['return_type']}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
            if lt.get("test_setup"):
                lines.append(f"  Setup: {lt['test_setup']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
