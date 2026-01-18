"""
Skill: J7.13 — Error Handling
Journey: J7 - Reply Handling
Checks: 5

Purpose: Verify graceful error handling for reply processing.
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
# ERROR HANDLING CONSTANTS
# =============================================================================

ERROR_TYPES = {
    "lead_not_found": "Reply from unknown sender",
    "parse_error": "Malformed webhook payload",
    "ai_error": "Intent classification failed",
    "db_error": "Database operation failed",
    "timeout_error": "External API timeout"
}

RETRY_CONFIG = {
    "max_retries": 3,
    "retry_delay_seconds": 10,
    "exponential_backoff": True
}

WEBHOOK_RESPONSES = {
    "success": {"status": 200, "return_on": "processed"},
    "error_but_ok": {"status": 200, "return_on": "processing_error"},
    "validation_error": {"status": 400, "return_on": "invalid_payload"}
}

ENGINE_RESULT_TYPES = {
    "success": "EngineResult.success()",
    "fail": "EngineResult.fail()",
    "skip": "EngineResult.skip()"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.13.1",
        "part_a": "Verify try/catch in closer.py `process_reply` (lines 139-249)",
        "part_b": "Test invalid lead",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Exception handling in process_reply",
            "expect": {
                "code_contains": ["try:", "except", "Exception", "process_reply"]
            }
        }
    },
    {
        "id": "J7.13.2",
        "part_a": "Verify EngineResult.fail returned on error",
        "part_b": "Check return structure",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "EngineResult.fail used for errors",
            "expect": {
                "code_contains": ["EngineResult.fail", "EngineResult.success", "return"]
            }
        }
    },
    {
        "id": "J7.13.3",
        "part_a": "Verify webhook returns 200 even on processing error",
        "part_b": "Check webhook response",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/webhooks/postmark/inbound",
            "auth": False,
            "body": {
                "FromName": "Unknown Sender",
                "From": "unknown-sender-12345@nonexistent.com",
                "To": "reply@agency.com",
                "Subject": "Test",
                "TextBody": "This sender should not exist in leads"
            },
            "expect": {
                "status": 200,
                "note": "Webhook returns 200 to prevent retries even when lead not found"
            },
            "curl_command": """curl -X POST '{api_url}/webhooks/postmark/inbound' \\
  -H 'Content-Type: application/json' \\
  -d '{"From": "unknown@test.com", "TextBody": "Test"}'"""
        }
    },
    {
        "id": "J7.13.4",
        "part_a": "Verify retries on flow tasks (3x)",
        "part_b": "Check task decorator",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Retry configuration on Prefect tasks",
            "expect": {
                "code_contains": ["retries=3", "retry_delay_seconds", "@task"]
            }
        }
    },
    {
        "id": "J7.13.5",
        "part_a": "Verify unknown lead doesn't crash webhook",
        "part_b": "Test unknown sender",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Unknown sender handled gracefully",
            "expect": {
                "code_contains": ["lead", "not found", "None", "logger", "warning"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Errors don't crash webhook",
    "Retries attempted",
    "Unknown senders logged but don't crash",
    "EngineResult.fail returned on error"
]

KEY_FILES = [
    "src/engines/closer.py",
    "src/api/routes/webhooks.py",
    "src/orchestration/flows/reply_recovery_flow.py"
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
    lines.append("### Error Types")
    for error_type, description in ERROR_TYPES.items():
        lines.append(f"  {error_type}: {description}")
    lines.append("")
    lines.append("### Retry Configuration Reference")
    lines.append("```python")
    lines.append('@task(name="process_missed_reply", retries=3, retry_delay_seconds=10)')
    lines.append("```")
    lines.append("")
    lines.append("### Webhook Response Strategy")
    for response, config in WEBHOOK_RESPONSES.items():
        lines.append(f"  {response}: status={config['status']}, on={config['return_on']}")
    lines.append("")
    lines.append("### EngineResult Types")
    for result_type, example in ENGINE_RESULT_TYPES.items():
        lines.append(f"  {result_type}: {example}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
