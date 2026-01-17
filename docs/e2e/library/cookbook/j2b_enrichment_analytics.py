"""
Skill: J2B.8 — Enrichment Analytics
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify enrichment API endpoints and analytics tracking for monitoring.
"""

CHECKS = [
    {
        "id": "J2B.8.1",
        "part_a": "Read `src/api/routes/leads.py` — verify `/api/v1/leads/{id}/research` endpoint",
        "part_b": "Test endpoint triggers enrichment flow",
        "key_files": ["src/api/routes/leads.py"]
    },
    {
        "id": "J2B.8.2",
        "part_a": "Verify response includes enrichment status and estimated completion time",
        "part_b": "Check API response structure",
        "key_files": ["src/api/routes/leads.py"]
    },
    {
        "id": "J2B.8.3",
        "part_a": "Verify batch enrichment endpoint exists for bulk operations",
        "part_b": "Test batch endpoint with multiple assignment IDs",
        "key_files": ["src/api/routes/leads.py"]
    },
    {
        "id": "J2B.8.4",
        "part_a": "Verify AI cost tracking: tokens_used, cost_aud logged for Claude analysis",
        "part_b": "Check ai_costs table after enrichment",
        "key_files": ["src/agents/skills/research_skills.py", "src/models/ai_cost.py"]
    },
    {
        "id": "J2B.8.5",
        "part_a": "Verify Apify cost tracking for LinkedIn scrapes",
        "part_b": "Check external API costs logged",
        "key_files": ["src/integrations/apify.py"]
    }
]

PASS_CRITERIA = [
    "Manual enrichment can be triggered via API endpoint",
    "Enrichment status returned in API response",
    "Batch enrichment supported for efficiency",
    "AI costs (Claude tokens) tracked and logged",
    "External API costs (Apify) tracked for budgeting"
]

KEY_FILES = [
    "src/api/routes/leads.py",
    "src/agents/skills/research_skills.py",
    "src/integrations/apify.py",
    "src/models/ai_cost.py"
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
