"""
Skill: J2B.9 — SDK Enrichment Agent
Journey: J2B - Lead Enrichment Pipeline
Checks: 6

Purpose: Verify SDK enrichment agent provides deep research for Hot leads.
"""

CHECKS = [
    {
        "id": "J2B.9.1",
        "part_a": "Verify SDK enrichment triggered for Hot leads only",
        "part_b": "Check ALS >= 85 condition in scout engine",
        "key_files": ["src/engines/scout.py"]
    },
    {
        "id": "J2B.9.2",
        "part_a": "Verify enrichment agent uses web_search tool",
        "part_b": "Check Serper API called for company research",
        "key_files": ["src/agents/sdk_agents/enrichment_agent.py", "src/agents/sdk_agents/sdk_tools.py"]
    },
    {
        "id": "J2B.9.3",
        "part_a": "Verify enrichment agent uses web_fetch tool",
        "part_b": "Check company website content fetched and parsed",
        "key_files": ["src/agents/sdk_agents/enrichment_agent.py", "src/agents/sdk_agents/sdk_tools.py"]
    },
    {
        "id": "J2B.9.4",
        "part_a": "Verify enrichment output matches schema",
        "part_b": "Check: pain_points, recent_news, hiring_signals, personalization_hooks",
        "key_files": ["src/agents/sdk_agents/sdk_models.py", "config/sdk_schemas.json"]
    },
    {
        "id": "J2B.9.5",
        "part_a": "Verify enrichment data saved to lead_assignments",
        "part_b": "Check enrichment_data JSONB column populated",
        "key_files": ["src/models/lead.py"]
    },
    {
        "id": "J2B.9.6",
        "part_a": "Verify enrichment cost tracked",
        "part_b": "Check ai_costs table has entry with operation='sdk_enrichment'",
        "key_files": ["src/models/costs.py"]
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
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
