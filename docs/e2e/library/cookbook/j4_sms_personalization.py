"""
Skill: J4.6 — SMS Template Personalization
Journey: J4 - SMS Outreach
Checks: 4

Purpose: Verify AI generates SMS content with length limits and personalization.
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

SMS_CHARACTER_LIMITS = {
    "gsm7_single": 160,
    "gsm7_multipart": 153,  # per segment in multipart
    "unicode_single": 70,
    "unicode_multipart": 67,  # per segment in multipart
    "max_segments": 3,
    "max_total_chars": 459  # 3 x 153
}

PERSONALIZATION_VARIABLES = {
    "lead_fields": [
        "{{first_name}}",
        "{{last_name}}",
        "{{company}}",
        "{{title}}",
        "{{industry}}"
    ],
    "sender_fields": [
        "{{sender_name}}",
        "{{sender_company}}"
    ],
    "campaign_fields": [
        "{{campaign_name}}",
        "{{sequence_step}}"
    ]
}

AI_CONTENT_CONFIG = {
    "model": "claude-3-haiku",
    "max_tokens": 200,
    "temperature": 0.7,
    "cost_tracking": True
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J4.6.1",
        "part_a": "Read `src/engines/content.py` — verify `generate_sms` method",
        "part_b": "N/A",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "code_verify",
            "check": "generate_sms method exists in ContentEngine",
            "expect": {
                "code_contains": ["def generate_sms", "async def generate_sms", "ContentEngine"]
            }
        }
    },
    {
        "id": "J4.6.2",
        "part_a": "Verify 160 character limit (GSM-7)",
        "part_b": "Check prompt constraints",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "code_verify",
            "check": "160 character limit enforced for GSM-7 SMS",
            "expect": {
                "code_contains": ["160", "character", "limit", "GSM", "truncate"]
            }
        }
    },
    {
        "id": "J4.6.3",
        "part_a": "Verify personalization uses lead data (first_name, company)",
        "part_b": "Check template variable replacement",
        "key_files": ["src/engines/content.py", "src/engines/sms.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/content/generate-sms",
            "auth": True,
            "body": {
                "lead_id": "{{test_lead_id}}",
                "template": "Hi {{first_name}}, I wanted to reach out about {{company}}",
                "context": {
                    "campaign_id": "{{test_campaign_id}}"
                }
            },
            "expect": {
                "status": 200,
                "body_has_fields": ["content", "char_count"],
                "content_personalized": True,
                "no_unresolved_vars": True
            },
            "warning": "Uses AI credits - costs ~$0.001 per generation",
            "curl_command": """curl -X POST '{api_url}/api/v1/content/generate-sms' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{{test_lead_id}}", "template": "Hi {{first_name}}"}'"""
        }
    },
    {
        "id": "J4.6.4",
        "part_a": "Verify AI spend tracked",
        "part_b": "Check cost_aud in metadata",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, action, metadata->>'cost_aud' as cost_aud,
                       metadata->>'model' as model,
                       metadata->>'tokens_used' as tokens_used
                FROM activity
                WHERE action = 'ai_content_generated'
                  AND metadata->>'content_type' = 'sms'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_rows": True,
                "required_fields": ["cost_aud", "model", "tokens_used"]
            }
        }
    }
]

PASS_CRITERIA = [
    "SMS content generated",
    "Character limit respected (160 GSM-7, 70 Unicode)",
    "Personalization variables replaced",
    "AI cost tracked"
]

KEY_FILES = [
    "src/engines/content.py",
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
    lines.append("### SMS Character Limits")
    for key, value in SMS_CHARACTER_LIMITS.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Personalization Variables")
    lines.append("  Lead Fields: " + ", ".join(PERSONALIZATION_VARIABLES["lead_fields"]))
    lines.append("  Sender Fields: " + ", ".join(PERSONALIZATION_VARIABLES["sender_fields"]))
    lines.append("")
    lines.append("### AI Content Configuration")
    for key, value in AI_CONTENT_CONFIG.items():
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
            if lt.get("warning"):
                lines.append(f"  Warning: {lt['warning']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
