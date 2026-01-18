"""
Skill: J3.5 - Email Template Personalization
Journey: J3 - Email Outreach
Checks: 5

Purpose: Verify AI generates personalized email content with lead data.
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
# PERSONALIZATION CONSTANTS
# =============================================================================

CONTENT_LIMITS = {
    "subject_max_chars": 50,
    "body_max_words": 150,
    "max_links": 2,
}

PERSONALIZATION_FIELDS = {
    "required": ["first_name", "company_name"],
    "optional": ["title", "industry", "company_size", "recent_news", "pain_points"],
}

AI_COST_TRACKING = {
    "field": "cost_aud",
    "provider": "anthropic",
    "model": "claude-3-haiku",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.5.1",
        "part_a": "Read `src/engines/content.py` - verify `generate_email` method exists",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Content engine has generate_email method",
            "expect": {
                "code_contains": ["generate_email", "subject", "body", "lead", "async def"]
            }
        }
    },
    {
        "id": "J3.5.2",
        "part_a": "Verify subject generation with < 50 character limit",
        "part_b": "Generate test email, measure subject length",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/content/generate-email",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "campaign_id": "{test_campaign_id}",
                "sequence_step": 1
            },
            "expect": {
                "status": 200,
                "body_has_fields": ["subject", "body"],
                "subject_max_length": 50
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/content/generate-email' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{\"lead_id\": \"uuid\", \"campaign_id\": \"uuid\", \"sequence_step\": 1}'""",
            "warning": "Consumes AI credits - request CEO approval before testing"
        }
    },
    {
        "id": "J3.5.3",
        "part_a": "Verify body generation with < 150 word limit",
        "part_b": "Generate test email, count words in body",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Content engine enforces body word limit",
            "expect": {
                "code_contains": ["word", "limit", "150", "body"]
            },
            "manual_steps": [
                "1. Generate email via API or content engine",
                "2. Count words in body: len(body.split())",
                "3. Verify count <= 150",
                "4. Check multiple generations for consistency"
            ]
        }
    },
    {
        "id": "J3.5.4",
        "part_a": "Verify personalization uses lead data (first_name, company, etc.)",
        "part_b": "Check generated email contains lead-specific data",
        "key_files": ["src/engines/content.py", "src/engines/email.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.metadata->>'subject' as subject,
                       l.first_name, l.company_name
                FROM activities a
                JOIN lead_pool l ON l.id = a.lead_id
                WHERE a.channel = 'email'
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_exist": True,
                "subject_contains_personalization": True
            },
            "manual_steps": [
                "1. Query recent email activities with lead data",
                "2. Verify subject or body contains lead's first_name",
                "3. Verify company_name referenced appropriately",
                "4. Check for industry-specific language if available"
            ]
        }
    },
    {
        "id": "J3.5.5",
        "part_a": "Verify AI spend tracked in metadata (cost_aud field)",
        "part_b": "Check activity record for AI cost tracking",
        "key_files": ["src/engines/content.py", "src/engines/email.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, metadata->>'ai_cost_aud' as ai_cost,
                       metadata->>'ai_model' as model,
                       metadata->>'tokens_used' as tokens
                FROM activities
                WHERE channel = 'email' AND metadata->>'ai_cost_aud' IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_exist": True,
                "ai_cost_tracked": True,
                "model_recorded": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Subject and body both generated by AI",
    "Subject under 50 characters",
    "Body under 150 words",
    "Personalization variables replaced correctly",
    "AI cost tracked in activity metadata"
]

KEY_FILES = [
    "src/engines/content.py",
    "src/engines/email.py",
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
    lines.append("### Content Limits")
    lines.append(f"  Subject Max Chars: {CONTENT_LIMITS['subject_max_chars']}")
    lines.append(f"  Body Max Words: {CONTENT_LIMITS['body_max_words']}")
    lines.append(f"  Max Links: {CONTENT_LIMITS['max_links']}")
    lines.append("")
    lines.append("### Personalization Fields")
    lines.append(f"  Required: {', '.join(PERSONALIZATION_FIELDS['required'])}")
    lines.append(f"  Optional: {', '.join(PERSONALIZATION_FIELDS['optional'])}")
    lines.append("")
    lines.append("### AI Cost Tracking")
    lines.append(f"  Field: {AI_COST_TRACKING['field']}")
    lines.append(f"  Model: {AI_COST_TRACKING['model']}")
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
            if lt.get("warning"):
                lines.append(f"  Warning: {lt['warning']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
