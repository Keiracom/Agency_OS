"""
Skill: J4.10 — Error Handling
Journey: J4 - SMS Outreach
Checks: 4

Purpose: Verify graceful error handling for SMS operations.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app"
}

# =============================================================================
# SMS DOMAIN CONSTANTS
# =============================================================================

ERROR_TYPES = {
    "twilio_errors": {
        "class": "TwilioRestException",
        "common_codes": [21211, 21614, 21608, 30003, 30005],
        "retriable": [30003, 30005]
    },
    "dncr_errors": {
        "class": "DNCRError",
        "action": "rejected_dncr",
        "retriable": False
    },
    "rate_limit_errors": {
        "class": "ResourceRateLimitError",
        "http_status": 429,
        "retriable": True
    }
}

RETRY_CONFIG = {
    "max_retries": 2,
    "retry_delay_seconds": 10,
    "exponential_backoff": False,
    "retriable_errors": ["timeout", "rate_limit", "temporary_failure"]
}

ENGINE_RESULT_CONFIG = {
    "success_class": "EngineResult.success",
    "fail_class": "EngineResult.fail",
    "required_fields": ["success", "error", "metadata"]
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J4.10.1",
        "part_a": "Verify Twilio errors caught (TwilioRestException)",
        "part_b": "Check exception handling in twilio.py",
        "key_files": ["src/integrations/twilio.py"],
        "live_test": {
            "type": "code_verify",
            "check": "TwilioRestException is caught and handled",
            "expect": {
                "code_contains": ["TwilioRestException", "except", "try"],
                "pattern": "try:.*send.*except.*Twilio"
            }
        }
    },
    {
        "id": "J4.10.2",
        "part_a": "Verify DNCR errors caught (DNCRError)",
        "part_b": "Check exception handling in sms.py",
        "key_files": ["src/engines/sms.py", "src/integrations/dncr.py"],
        "live_test": {
            "type": "code_verify",
            "check": "DNCRError is caught and handled gracefully",
            "expect": {
                "code_contains": ["DNCRError", "except", "rejected_dncr"],
                "returns_engine_result": True
            }
        }
    },
    {
        "id": "J4.10.3",
        "part_a": "Verify EngineResult.fail returned on error",
        "part_b": "Check return structure",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "EngineResult.fail is returned on errors",
            "expect": {
                "code_contains": ["EngineResult.fail", "EngineResult.success"],
                "error_info_captured": True
            }
        }
    },
    {
        "id": "J4.10.4",
        "part_a": "Verify retry logic in outreach_flow",
        "part_b": "Check @task decorator for retries=2, retry_delay_seconds=10",
        "key_files": ["src/orchestration/flows/outreach_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "@task decorator has retry configuration",
            "expect": {
                "code_contains": ["@task", "retries", "retry_delay"],
                "values": {
                    "retries": 2,
                    "retry_delay_seconds": 10
                }
            },
            "curl_command": """# Check Prefect task retry config:
grep -A5 "@task" src/orchestration/flows/outreach_flow.py | grep -E "retries|retry_delay\""""
        }
    }
]

PASS_CRITERIA = [
    "Errors don't crash the flow",
    "DNCR rejections handled gracefully",
    "Failed sends logged with reason",
    "Retries attempted (2x with 10s delay)"
]

KEY_FILES = [
    "src/integrations/twilio.py",
    "src/integrations/dncr.py",
    "src/engines/sms.py",
    "src/orchestration/flows/outreach_flow.py"
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
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Error Types")
    for error_type, config in ERROR_TYPES.items():
        lines.append(f"  {error_type}:")
        lines.append(f"    Class: {config.get('class', 'N/A')}")
        lines.append(f"    Retriable: {config.get('retriable', 'N/A')}")
    lines.append("")
    lines.append("### Retry Configuration")
    for key, value in RETRY_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### EngineResult Configuration")
    for key, value in ENGINE_RESULT_CONFIG.items():
        lines.append(f"  {key}: {value}")
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
            if lt.get("check"):
                lines.append(f"  Check: {lt['check']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
