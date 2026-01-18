"""
Skill: J6.12 — Error Handling
Journey: J6 - LinkedIn Outreach
Checks: 4

Purpose: Verify graceful error handling for LinkedIn operations.
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
}

# =============================================================================
# ERROR HANDLING CONSTANTS
# =============================================================================

UNIPILE_ERROR_CODES = {
    400: "Bad request - invalid parameters",
    401: "Unauthorized - invalid API key",
    403: "Forbidden - account not authorized",
    404: "Not found - account or profile not found",
    429: "Rate limited - too many requests",
    500: "Internal server error",
    503: "Service unavailable",
}

RETRY_CONFIG = {
    "max_attempts": 3,
    "wait_multiplier": 1,
    "wait_min": 2,
    "wait_max": 10,
    "retry_on": [429, 500, 503],
}

ERROR_RESPONSES = {
    "missing_account": "No LinkedIn account connected",
    "missing_linkedin_url": "Lead has no LinkedIn URL",
    "rate_limited": "Daily limit reached for this account",
    "connection_failed": "Failed to connect to Unipile API",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.12.1",
        "part_a": "Verify Unipile errors caught and wrapped",
        "part_b": "Check exception handling",
        "key_files": ["src/engines/linkedin.py", "src/integrations/unipile.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Unipile errors are caught and converted to EngineResult.fail",
            "expect": {
                "code_contains": ["try", "except", "IntegrationError", "EngineResult"]
            }
        }
    },
    {
        "id": "J6.12.2",
        "part_a": "Verify EngineResult.fail returned on error",
        "part_b": "Check return type",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "All error paths return EngineResult with success=False",
            "expect": {
                "code_contains": ["EngineResult", "success=False", "error"]
            }
        }
    },
    {
        "id": "J6.12.3",
        "part_a": "Verify retry logic in Unipile client (tenacity)",
        "part_b": "Check decorator",
        "key_files": ["src/integrations/unipile.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Tenacity retry decorator with exponential backoff",
            "expect": {
                "code_contains": ["@retry", "stop_after_attempt", "wait_exponential"]
            }
        }
    },
    {
        "id": "J6.12.4",
        "part_a": "Verify missing account_id handled",
        "part_b": "Test without account_id",
        "key_files": [],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/linkedin/connection",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}"
            },
            "expect": {
                "status": 400,
                "error_contains": "account"
            },
            "note": "Should return clear error when no LinkedIn account connected",
            "curl_command": """curl -X POST '{api_url}/api/v1/linkedin/connection' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "TEST_LEAD"}'"""
        }
    }
]

PASS_CRITERIA = [
    "Errors don't crash the flow - EngineResult.fail returned",
    "Retries attempted (3x with exponential backoff)",
    "Required fields validated with clear error messages",
    "Unipile API errors wrapped in IntegrationError"
]

KEY_FILES = [
    "src/engines/linkedin.py",
    "src/integrations/unipile.py"
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
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Unipile Error Codes")
    for code, description in UNIPILE_ERROR_CODES.items():
        lines.append(f"  {code}: {description}")
    lines.append("")
    lines.append("### Retry Configuration")
    for key, value in RETRY_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Error Response Messages")
    for key, message in ERROR_RESPONSES.items():
        lines.append(f"  {key}: {message}")
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
            if lt.get("note"):
                lines.append(f"  Note: {lt['note']}")
            if lt.get("curl_command"):
                lines.append(f"  curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
