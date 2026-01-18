"""
Skill: J3.13 - SDK Email Personalization
Journey: J3 - Email Outreach
Checks: 6

Purpose: Verify SDK email agent generates personalized emails using enrichment data.
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
# SDK EMAIL CONSTANTS
# =============================================================================

SDK_CONFIG = {
    "agent_file": "src/agents/sdk_agents/email_agent.py",
    "model_file": "src/agents/sdk_agents/sdk_models.py",
    "schema_file": "config/sdk_schemas.json",
    "config_file": "config/sdk_config.json",
}

EMAIL_AGENT_OUTPUT = {
    "required_fields": ["subject", "body", "hook_used", "personalization_type", "confidence"],
    "optional_fields": ["html_body", "reasoning", "alternative_hooks"],
}

PERSONALIZATION_TYPES = {
    "company_news": "References recent company news/announcements",
    "hiring_signals": "References job postings or growth signals",
    "technology_stack": "References specific technologies used",
    "industry_trends": "References industry-specific challenges",
    "mutual_connections": "References shared connections or networks",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.13.1",
        "part_a": "Verify SDK email agent called for enriched leads",
        "part_b": "Check closer engine calls email_agent when enrichment_data exists",
        "key_files": ["src/engines/closer.py", "src/agents/sdk_agents/email_agent.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Closer engine calls SDK email agent for enriched leads",
            "expect": {
                "code_contains": ["email_agent", "enrichment_data", "generate", "EmailInput"]
            }
        }
    },
    {
        "id": "J3.13.2",
        "part_a": "Verify email agent receives enrichment data",
        "part_b": "Check EmailInput includes enrichment field with pain_points, hooks",
        "key_files": ["src/agents/sdk_agents/email_agent.py", "src/agents/sdk_agents/sdk_models.py"],
        "live_test": {
            "type": "code_verify",
            "check": "EmailInput model includes enrichment data fields",
            "expect": {
                "code_contains": ["EmailInput", "enrichment", "pain_points", "hooks", "company_news"]
            }
        }
    },
    {
        "id": "J3.13.3",
        "part_a": "Verify template augmentation approach used",
        "part_b": "Check email uses template with AI-filled [HOOK] and [PROOF] placeholders",
        "key_files": ["src/agents/sdk_agents/email_agent.py", "config/sdk_config.json"],
        "live_test": {
            "type": "code_verify",
            "check": "Template augmentation fills [HOOK] and [PROOF] placeholders",
            "expect": {
                "code_contains": ["[HOOK]", "[PROOF]", "template", "augment", "placeholder"]
            },
            "manual_steps": [
                "1. Check config/sdk_config.json for email templates",
                "2. Verify templates have [HOOK] and [PROOF] placeholders",
                "3. Check email_agent.py fills these with AI-generated content",
                "4. Verify final output has no remaining placeholders"
            ]
        }
    },
    {
        "id": "J3.13.4",
        "part_a": "Verify email references specific personalization",
        "part_b": "Generated email mentions actual company news/hiring/initiatives",
        "key_files": ["src/agents/sdk_agents/email_agent.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.metadata->>'subject' as subject,
                       a.metadata->>'personalization_type' as personalization,
                       a.metadata->>'hook_used' as hook,
                       l.company_name, l.enrichment_data
                FROM activities a
                JOIN lead_pool l ON l.id = a.lead_id
                WHERE a.channel = 'email' AND a.metadata->>'personalization_type' IS NOT NULL
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_exist": True,
                "personalization_specific": True,
                "hook_matches_enrichment": True
            },
            "warning": "Requires enriched leads to test - may need to run enrichment first"
        }
    },
    {
        "id": "J3.13.5",
        "part_a": "Verify email output matches schema",
        "part_b": "Check: subject, body, hook_used, personalization_type, confidence",
        "key_files": ["src/agents/sdk_agents/sdk_models.py", "config/sdk_schemas.json"],
        "live_test": {
            "type": "code_verify",
            "check": "EmailOutput model has all required fields with proper types",
            "expect": {
                "code_contains": ["EmailOutput", "subject: str", "body: str", "hook_used", "personalization_type", "confidence"]
            },
            "manual_steps": [
                "1. Check sdk_models.py for EmailOutput class",
                "2. Verify all required fields are defined",
                "3. Check config/sdk_schemas.json for JSON schema",
                "4. Verify types match between Pydantic model and JSON schema"
            ]
        }
    },
    {
        "id": "J3.13.6",
        "part_a": "Verify email sent via Salesforge with SDK content",
        "part_b": "Check activity log shows SDK-generated subject/body",
        "key_files": ["src/engines/email.py", "src/integrations/salesforge.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, metadata->>'subject' as subject,
                       metadata->>'content_source' as source,
                       metadata->>'ai_model' as model,
                       metadata->>'confidence' as confidence
                FROM activities
                WHERE channel = 'email' AND metadata->>'content_source' = 'sdk_agent'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_exist": True,
                "content_source_sdk": True,
                "confidence_tracked": True
            },
            "manual_steps": [
                "1. Send email to enriched lead via Prefect flow",
                "2. Query activities table for the email",
                "3. Verify content_source = 'sdk_agent'",
                "4. Verify subject/body are personalized (not generic)"
            ]
        }
    }
]

PASS_CRITERIA = [
    "SDK email agent called for enriched leads",
    "Enrichment data passed to agent",
    "Template augmentation produces consistent format",
    "Email contains specific, real personalization",
    "Output validates against schema",
    "Email sent successfully via Salesforge"
]

KEY_FILES = [
    "src/engines/closer.py",
    "src/engines/email.py",
    "src/agents/sdk_agents/email_agent.py",
    "src/agents/sdk_agents/sdk_models.py",
    "src/integrations/salesforge.py"
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
    lines.append("### SDK Configuration Files")
    for name, path in SDK_CONFIG.items():
        lines.append(f"  {name}: {path}")
    lines.append("")
    lines.append("### Email Agent Output Fields")
    lines.append(f"  Required: {', '.join(EMAIL_AGENT_OUTPUT['required_fields'])}")
    lines.append(f"  Optional: {', '.join(EMAIL_AGENT_OUTPUT['optional_fields'])}")
    lines.append("")
    lines.append("### Personalization Types")
    for ptype, description in PERSONALIZATION_TYPES.items():
        lines.append(f"  {ptype}: {description}")
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
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
