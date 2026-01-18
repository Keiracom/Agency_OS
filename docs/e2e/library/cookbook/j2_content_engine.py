"""
Skill: J2.9 — Content Generation
Journey: J2 - Campaign Creation & Management
Checks: 6

Purpose: Verify AI generates personalized content for sequences.

Content Types:
- Email: subject (50 chars) + body (150 words)
- SMS: 160 chars max
- LinkedIn: Connection note or message
- Voice: Call script
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "note": "Content generation uses Claude API - incurs costs"
}

# =============================================================================
# CONTENT CONSTRAINTS
# =============================================================================

CONTENT_CONSTRAINTS = {
    "email": {"subject_max": 50, "body_words": 150},
    "sms": {"max_chars": 160},
    "linkedin": {"connection_note_max": 300, "message_max": 1900},
    "voice": {"script_minutes": 2}
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2.9.1",
        "part_a": "Read `src/engines/content.py` — verify `generate_email`",
        "part_b": "Check AI prompt structure",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Content engine has generate_email method",
            "expect": {
                "code_contains": ["generate_email", "subject", "body", "prompt"]
            }
        }
    },
    {
        "id": "J2.9.2",
        "part_a": "Verify spend limiter integration (Rule 15)",
        "part_b": "Check `anthropic.complete` call",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Content generation uses spend limiter",
            "expect": {
                "code_contains": ["spend_limiter", "anthropic", "budget"]
            },
            "note": "Rule 15 requires AI spend tracking via spend limiter"
        }
    },
    {
        "id": "J2.9.3",
        "part_a": "Verify `generate_email_for_pool` for pool-first content",
        "part_b": "Test pool method",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/leads/{lead_id}/generate-content",
            "auth": True,
            "body": {
                "channel": "email",
                "sequence_step": 1
            },
            "expect": {
                "status": 200,
                "body_has_fields": ["subject", "body"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/leads/{lead_id}/generate-content' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"channel": "email", "sequence_step": 1}'""",
            "warning": "This endpoint consumes AI credits"
        }
    },
    {
        "id": "J2.9.4",
        "part_a": "Verify SMS, LinkedIn, Voice generation methods exist",
        "part_b": "Check other generators",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Content engine supports all channels",
            "expect": {
                "code_contains": ["generate_sms", "generate_linkedin", "generate_voice"]
            }
        }
    },
    {
        "id": "J2.9.5",
        "part_a": "Verify personalization uses lead data (name, company, title)",
        "part_b": "Check lead_data in prompt",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Prompts include lead personalization data",
            "expect": {
                "code_contains": ["first_name", "company_name", "title", "pain_point"]
            }
        }
    },
    {
        "id": "J2.9.6",
        "part_a": "Verify JSON response parsing (subject + body)",
        "part_b": "Check response handling",
        "key_files": ["src/engines/content.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT o.id, o.channel, o.content->>'subject' as subject,
                       LEFT(o.content->>'body', 100) as body_preview
                FROM outreach o
                WHERE o.content IS NOT NULL
                ORDER BY o.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "subject_exists": True,
                "body_exists": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Content engine generates personalized content",
    "AI spend tracked via limiter",
    "All 4 channels supported (email, SMS, LinkedIn, voice)",
    "Response properly parsed with subject + body"
]

KEY_FILES = [
    "src/engines/content.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Note: {LIVE_CONFIG['note']}")
    lines.append("")
    lines.append("### Content Constraints")
    for channel, constraints in CONTENT_CONSTRAINTS.items():
        lines.append(f"  {channel}: {constraints}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
