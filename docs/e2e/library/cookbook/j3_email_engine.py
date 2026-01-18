"""
Skill: J3.3 - Email Engine Implementation
Journey: J3 - Email Outreach
Checks: 7

Purpose: Verify email engine is fully implemented with all required methods.
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
# EMAIL ENGINE CONSTANTS
# =============================================================================

EMAIL_ENGINE_METHODS = {
    "required": ["send", "send_batch", "_log_activity", "_get_thread_info", "_validate_email"],
    "optional": ["_build_headers", "_track_rate_limit"],
}

EMAIL_THREADING = {
    "headers": ["In-Reply-To", "References", "Message-ID"],
    "rule": "Rule 18 - Email Threading Required",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.3.1",
        "part_a": "Read `src/engines/email.py` - verify `send` method implementation",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Email engine has send method with full implementation",
            "expect": {
                "code_contains": ["async def send", "to_email", "subject", "body", "from_email", "EngineResult"]
            }
        }
    },
    {
        "id": "J3.3.2",
        "part_a": "Verify no TODO/FIXME/pass in email.py via grep",
        "part_b": "Run `grep -n \"TODO\\|FIXME\\|pass\" src/engines/email.py`",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "code_verify",
            "check": "No incomplete implementations in email engine",
            "expect": {
                "code_not_contains": ["TODO", "FIXME", "pass  #", "raise NotImplementedError"]
            },
            "manual_steps": [
                "1. Run: grep -n 'TODO\\|FIXME' src/engines/email.py",
                "2. Should return no results (or only informational comments)",
                "3. Run: grep -n '^\\s*pass$' src/engines/email.py",
                "4. Should return no standalone pass statements"
            ]
        }
    },
    {
        "id": "J3.3.3",
        "part_a": "Verify `send_batch` method for bulk sends",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Email engine has send_batch method for bulk operations",
            "expect": {
                "code_contains": ["async def send_batch", "List[", "emails", "results"]
            }
        }
    },
    {
        "id": "J3.3.4",
        "part_a": "Verify subject and from_email validation logic",
        "part_b": "Test with missing required fields, verify error",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/outreach/send-test-email",
            "auth": True,
            "body": {
                "to_email": "test@example.com",
                "subject": "",
                "body": "Test body without subject"
            },
            "expect": {
                "status": [400, 422],
                "body_contains": ["subject", "required", "validation"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/outreach/send-test-email' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{\"to_email\": \"test@example.com\", \"subject\": \"\", \"body\": \"Test\"}'"""
        }
    },
    {
        "id": "J3.3.5",
        "part_a": "Verify OutreachEngine base class is extended correctly",
        "part_b": "Check class definition and inheritance",
        "key_files": ["src/engines/email.py", "src/engines/base.py"],
        "live_test": {
            "type": "code_verify",
            "check": "EmailEngine extends OutreachEngine base class",
            "expect": {
                "code_contains": ["class EmailEngine", "OutreachEngine", "def send", "EngineResult"]
            }
        }
    },
    {
        "id": "J3.3.6",
        "part_a": "Verify `_get_thread_info` method for email threading (Rule 18)",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Thread info method exists for email threading support",
            "expect": {
                "code_contains": ["_get_thread_info", "thread_id", "message_id", "In-Reply-To"]
            }
        }
    },
    {
        "id": "J3.3.7",
        "part_a": "Verify In-Reply-To and References headers set for follow-ups",
        "part_b": "Send follow-up email, check headers in received email",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, metadata->>'in_reply_to' as in_reply_to,
                       metadata->>'references' as references,
                       metadata->>'thread_id' as thread_id,
                       metadata->>'sequence_step' as step
                FROM activities
                WHERE channel = 'email' AND (metadata->>'sequence_step')::int > 1
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_exist": True,
                "in_reply_to_set": True,
                "thread_id_consistent": True
            },
            "manual_steps": [
                "1. Send initial email (step 1)",
                "2. Send follow-up email (step 2) to same recipient",
                "3. Check received email headers for In-Reply-To",
                "4. Verify References header contains original Message-ID"
            ]
        }
    }
]

PASS_CRITERIA = [
    "No incomplete implementations (no TODO/FIXME/pass)",
    "All methods have implementations",
    "Validation for required fields works",
    "Extends OutreachEngine correctly",
    "Email threading implemented with In-Reply-To + References",
    "Single send and batch send both work",
    "TEST_MODE redirect integrated"
]

KEY_FILES = [
    "src/engines/email.py",
    "src/engines/base.py",
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
    lines.append("### Email Engine Methods")
    lines.append(f"  Required: {', '.join(EMAIL_ENGINE_METHODS['required'])}")
    lines.append(f"  Optional: {', '.join(EMAIL_ENGINE_METHODS['optional'])}")
    lines.append("")
    lines.append("### Email Threading (Rule 18)")
    lines.append(f"  Headers: {', '.join(EMAIL_THREADING['headers'])}")
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
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
