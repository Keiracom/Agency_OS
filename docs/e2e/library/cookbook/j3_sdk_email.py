"""
Skill: J3.13 — SDK Email Personalization
Journey: J3 - Email Outreach
Checks: 6

Purpose: Verify SDK email agent generates personalized emails using enrichment data.
"""

CHECKS = [
    {
        "id": "J3.13.1",
        "part_a": "Verify SDK email agent called for enriched leads",
        "part_b": "Check closer engine calls email_agent when enrichment_data exists",
        "key_files": ["src/engines/closer.py", "src/agents/sdk_agents/email_agent.py"]
    },
    {
        "id": "J3.13.2",
        "part_a": "Verify email agent receives enrichment data",
        "part_b": "Check EmailInput includes enrichment field with pain_points, hooks",
        "key_files": ["src/agents/sdk_agents/email_agent.py", "src/agents/sdk_agents/sdk_models.py"]
    },
    {
        "id": "J3.13.3",
        "part_a": "Verify template augmentation approach used",
        "part_b": "Check email uses template with AI-filled [HOOK] and [PROOF] placeholders",
        "key_files": ["src/agents/sdk_agents/email_agent.py", "config/sdk_config.json"]
    },
    {
        "id": "J3.13.4",
        "part_a": "Verify email references specific personalization",
        "part_b": "Generated email mentions actual company news/hiring/initiatives",
        "key_files": ["src/agents/sdk_agents/email_agent.py"]
    },
    {
        "id": "J3.13.5",
        "part_a": "Verify email output matches schema",
        "part_b": "Check: subject, body, hook_used, personalization_type, confidence",
        "key_files": ["src/agents/sdk_agents/sdk_models.py", "config/sdk_schemas.json"]
    },
    {
        "id": "J3.13.6",
        "part_a": "Verify email sent via Salesforge with SDK content",
        "part_b": "Check activity log shows SDK-generated subject/body",
        "key_files": ["src/engines/email.py", "src/integrations/salesforge.py"]
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
