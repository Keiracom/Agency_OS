"""
Skill: J2B.9 — SDK Enrichment Agent
Journey: J2B - Lead Enrichment Pipeline
Checks: 6

Purpose: Verify SDK enrichment agent provides deep research for Hot leads.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "warning": "SDK enrichment consumes AI credits - Hot leads only"
}

# =============================================================================
# SDK ENRICHMENT CONFIG
# =============================================================================

SDK_ENRICHMENT = {
    "trigger_condition": "ALS score >= 85 (Hot tier)",
    "tools_used": ["web_search", "web_fetch"],
    "output_schema": {
        "pain_points": "List of likely challenges based on role/industry",
        "recent_news": "Company news and announcements",
        "hiring_signals": "Job postings and team growth indicators",
        "personalization_hooks": "Specific talking points for outreach"
    },
    "cost_operation": "sdk_enrichment"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2B.9.1",
        "part_a": "Verify SDK enrichment triggered for Hot leads only",
        "part_b": "Check ALS >= 85 condition in scout engine",
        "key_files": ["src/engines/scout.py"],
        "live_test": {
            "type": "code_verify",
            "check": "SDK enrichment only for Hot tier",
            "expect": {
                "code_contains": ["85", "hot", "sdk", "enrichment"]
            }
        }
    },
    {
        "id": "J2B.9.2",
        "part_a": "Verify enrichment agent uses web_search tool",
        "part_b": "Check Serper API called for company research",
        "key_files": ["src/agents/sdk_agents/enrichment_agent.py", "src/agents/sdk_agents/sdk_tools.py"],
        "live_test": {
            "type": "code_verify",
            "check": "SDK uses web_search tool",
            "expect": {
                "code_contains": ["web_search", "search", "serper"]
            }
        }
    },
    {
        "id": "J2B.9.3",
        "part_a": "Verify enrichment agent uses web_fetch tool",
        "part_b": "Check company website content fetched and parsed",
        "key_files": ["src/agents/sdk_agents/enrichment_agent.py", "src/agents/sdk_agents/sdk_tools.py"],
        "live_test": {
            "type": "code_verify",
            "check": "SDK uses web_fetch tool",
            "expect": {
                "code_contains": ["web_fetch", "fetch", "url", "content"]
            }
        }
    },
    {
        "id": "J2B.9.4",
        "part_a": "Verify enrichment output matches schema",
        "part_b": "Check: pain_points, recent_news, hiring_signals, personalization_hooks",
        "key_files": ["src/agents/sdk_agents/sdk_models.py", "config/sdk_schemas.json"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id, la.als_score, la.als_tier,
                       la.enrichment_data->>'pain_points' IS NOT NULL as has_pain_points,
                       la.enrichment_data->>'recent_news' IS NOT NULL as has_news,
                       la.enrichment_data->>'personalization_hooks' IS NOT NULL as has_hooks
                FROM lead_assignments la
                WHERE la.als_tier = 'hot'
                AND la.enrichment_data IS NOT NULL
                ORDER BY la.enrichment_completed_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_pain_points": True,
                "has_hooks": True
            }
        }
    },
    {
        "id": "J2B.9.5",
        "part_a": "Verify enrichment data saved to lead_assignments",
        "part_b": "Check enrichment_data JSONB column populated",
        "key_files": ["src/models/lead.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id, la.als_tier,
                       pg_column_size(la.enrichment_data) as data_size_bytes,
                       la.enrichment_completed_at
                FROM lead_assignments la
                WHERE la.enrichment_data IS NOT NULL
                ORDER BY la.enrichment_completed_at DESC
                LIMIT 10;
            """,
            "expect": {
                "data_size_bytes": "> 0",
                "enrichment_completed_at": "NOT NULL"
            }
        }
    },
    {
        "id": "J2B.9.6",
        "part_a": "Verify enrichment cost tracked",
        "part_b": "Check ai_costs table has entry with operation='sdk_enrichment'",
        "key_files": ["src/models/costs.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, client_id, operation, model,
                       input_tokens, output_tokens, cost_aud
                FROM ai_costs
                WHERE operation = 'sdk_enrichment'
                ORDER BY created_at DESC
                LIMIT 10;
            """,
            "expect": {
                "operation": "sdk_enrichment",
                "cost_tracked": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Only Hot leads (ALS >= 85) use SDK enrichment",
    "Web search provides company intelligence",
    "Web fetch extracts website content",
    "Output includes actionable personalization hooks",
    "Data persisted to database",
    "Cost tracked accurately"
]

KEY_FILES = [
    "src/engines/scout.py",
    "src/agents/sdk_agents/enrichment_agent.py",
    "src/agents/sdk_agents/sdk_tools.py",
    "src/agents/sdk_agents/sdk_models.py",
    "src/models/lead.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### SDK Enrichment Config")
    lines.append(f"  Trigger: {SDK_ENRICHMENT['trigger_condition']}")
    lines.append(f"  Tools: {', '.join(SDK_ENRICHMENT['tools_used'])}")
    lines.append("  Output Schema:")
    for field, desc in SDK_ENRICHMENT['output_schema'].items():
        lines.append(f"    - {field}: {desc}")
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
