"""
Skill: J3.10 - Error Handling
Journey: J3 - Email Outreach
Checks: 4

Purpose: Verify graceful error handling in email sending flow.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
}

# =============================================================================
# ERROR HANDLING CONSTANTS
# =============================================================================

ERROR_HANDLING_CONFIG = {
    "sentry_enabled": True,
    "sentry_dsn_env_var": "SENTRY_DSN",
    "log_errors": True,
    "return_engine_result": True,
}

RETRY_CONFIG = {
    "max_retries": 2,
    "retry_delay_seconds": 10,
    "exponential_backoff": False,
    "task_decorator": "@task(retries=2, retry_delay_seconds=10)",
}

ERROR_TYPES = {
    "api_error": "SalesforgeAPIError",
    "rate_limit": "ResourceRateLimitError",
    "validation": "ValidationError",
    "timeout": "TimeoutError",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.10.1",
        "part_a": "Verify Salesforge/API errors caught and logged in email engine",
        "part_b": "Simulate API failure, check error handling",
        "key_files": ["src/engines/email.py", "src/integrations/salesforge.py"],
        "live_test": {
            "type": "code_verify",
            "check": "API errors caught with try/except and logged",
            "expect": {
                "code_contains": ["try:", "except", "SalesforgeAPIError", "logger.error", "EngineResult.fail"]
            }
        }
    },
    {
        "id": "J3.10.2",
        "part_a": "Verify Sentry capture on failures via sentry_sdk calls",
        "part_b": "Check Sentry dashboard for captured exceptions",
        "key_files": ["src/engines/email.py", "src/integrations/sentry_utils.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Sentry captures exceptions with context",
            "expect": {
                "code_contains": ["sentry_sdk", "capture_exception", "capture_message", "set_context"]
            },
            "manual_steps": [
                "1. Check src/engines/email.py for sentry_sdk imports",
                "2. Verify capture_exception called in except blocks",
                "3. Check Sentry dashboard: https://david-stephens-1q.sentry.io/issues/",
                "4. Look for email engine errors with context"
            ]
        }
    },
    {
        "id": "J3.10.3",
        "part_a": "Verify EngineResult.fail returned on error (not exception raised)",
        "part_b": "Check return structure on failed send",
        "key_files": ["src/engines/email.py", "src/engines/base.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Errors return EngineResult.fail instead of raising exceptions",
            "expect": {
                "code_contains": ["EngineResult", "fail", "success=False", "error_message"]
            },
            "manual_steps": [
                "1. Check email.py send method",
                "2. Verify try/except returns EngineResult.fail()",
                "3. Verify orchestration layer handles EngineResult properly",
                "4. Verify no unhandled exceptions propagate to flow"
            ]
        }
    },
    {
        "id": "J3.10.4",
        "part_a": "Verify retry logic in outreach_flow via @task decorator",
        "part_b": "Check task configuration: retries=2, retry_delay_seconds=10",
        "key_files": ["src/orchestration/flows/outreach_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Prefect task has retry configuration",
            "expect": {
                "code_contains": ["@task", "retries=2", "retry_delay_seconds"]
            },
            "manual_steps": [
                "1. Check outreach_flow.py for @task decorators",
                "2. Verify retries parameter is set",
                "3. Verify retry_delay_seconds is set",
                "4. Check Prefect UI for retry behavior on failed tasks"
            ]
        }
    }
]

PASS_CRITERIA = [
    "Errors do not crash the flow",
    "Sentry captures exceptions with context",
    "Failed sends logged with reason",
    "Retries attempted (2x with 10s delay)"
]

KEY_FILES = [
    "src/engines/email.py",
    "src/integrations/salesforge.py",
    "src/integrations/sentry_utils.py",
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
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API URL: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend URL: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase URL: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect URL: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Error Handling Configuration")
    lines.append(f"  Sentry Enabled: {ERROR_HANDLING_CONFIG['sentry_enabled']}")
    lines.append(f"  Log Errors: {ERROR_HANDLING_CONFIG['log_errors']}")
    lines.append(f"  Return EngineResult: {ERROR_HANDLING_CONFIG['return_engine_result']}")
    lines.append("")
    lines.append("### Retry Configuration")
    lines.append(f"  Max Retries: {RETRY_CONFIG['max_retries']}")
    lines.append(f"  Retry Delay: {RETRY_CONFIG['retry_delay_seconds']}s")
    lines.append(f"  Task Decorator: {RETRY_CONFIG['task_decorator']}")
    lines.append("")
    lines.append("### Error Types")
    for name, cls in ERROR_TYPES.items():
        lines.append(f"  {name}: {cls}")
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
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
