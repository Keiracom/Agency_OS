"""
Skill: J4.9 — Opt-out Handling
Journey: J4 - SMS Outreach
Checks: 4

Purpose: Verify STOP/opt-out keyword handling for SMS.
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
    "test_phone": "+61457543392"
}

# =============================================================================
# SMS DOMAIN CONSTANTS
# =============================================================================

OPTOUT_KEYWORDS = {
    "primary": ["STOP", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"],
    "case_sensitive": False,
    "exact_match": True,
    "whitespace_trimmed": True
}

OPTOUT_CONFIG = {
    "lead_status_update": "opted_out",
    "activity_action": "sms_optout",
    "block_future_sends": True,
    "auto_response": None,  # Twilio handles auto-response
    "channel": "sms"
}

SMS_COMPLIANCE = {
    "australian_spam_act": True,
    "tcpa_compliant": True,
    "mandatory_optout": True,
    "retention_days": 365
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J4.9.1",
        "part_a": "Verify STOP keyword detection in reply parsing",
        "part_b": "N/A",
        "key_files": ["src/integrations/twilio.py", "src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "STOP keyword detection in webhook handler",
            "expect": {
                "code_contains": ["STOP", "optout", "opt_out", "unsubscribe"],
                "case_insensitive_check": True
            }
        }
    },
    {
        "id": "J4.9.2",
        "part_a": "Verify lead status updated to 'opted_out' on STOP",
        "part_b": "Test STOP reply handling",
        "key_files": ["src/api/routes/webhooks.py", "src/engines/sms.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/webhooks/sms/twilio/inbound",
            "auth": False,
            "content_type": "application/x-www-form-urlencoded",
            "body": {
                "From": "+61400000000",
                "To": "+61400000001",
                "Body": "STOP",
                "MessageSid": "SM_TEST_OPTOUT_123"
            },
            "expect": {
                "status": 200,
                "lead_status_updated": "opted_out"
            },
            "curl_command": """curl -X POST '{api_url}/webhooks/sms/twilio/inbound' \\
  -H 'Content-Type: application/x-www-form-urlencoded' \\
  -d 'From=+61400000000&To=+61400000001&Body=STOP&MessageSid=SM_OPTOUT'"""
        }
    },
    {
        "id": "J4.9.3",
        "part_a": "Verify opted-out leads blocked from future sends",
        "part_b": "Attempt send to opted-out lead",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Check for opted_out status before sending",
            "expect": {
                "code_contains": ["opted_out", "status", "block", "skip"],
                "logic": "if lead.status == 'opted_out': return error/skip"
            },
            "manual_test": {
                "steps": [
                    "1. Find a lead with status='opted_out'",
                    "2. Attempt to send SMS to that lead via API",
                    "3. Verify request is rejected with appropriate error"
                ],
                "expect": {
                    "status": 400,
                    "error_contains": "opted out"
                }
            }
        }
    },
    {
        "id": "J4.9.4",
        "part_a": "Verify opt-out activity logged",
        "part_b": "Check activity record with action='sms_optout'",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.lead_id, a.action, a.channel,
                       a.content_preview,
                       metadata->>'keyword' as keyword,
                       l.status as lead_status
                FROM activity a
                JOIN leads l ON a.lead_id = l.id
                WHERE a.action = 'sms_optout'
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_rows": True,
                "action_value": "sms_optout",
                "lead_status_value": "opted_out"
            }
        }
    }
]

PASS_CRITERIA = [
    "STOP keyword detected (case-insensitive)",
    "Lead marked as opted_out",
    "Future sends blocked for opted-out leads",
    "Opt-out activity logged"
]

KEY_FILES = [
    "src/integrations/twilio.py",
    "src/api/routes/webhooks.py",
    "src/engines/sms.py"
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
    lines.append("### Opt-out Keywords")
    lines.append(f"  Primary: {', '.join(OPTOUT_KEYWORDS['primary'])}")
    lines.append(f"  Case Sensitive: {OPTOUT_KEYWORDS['case_sensitive']}")
    lines.append("")
    lines.append("### Opt-out Configuration")
    for key, value in OPTOUT_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### SMS Compliance")
    for key, value in SMS_COMPLIANCE.items():
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
