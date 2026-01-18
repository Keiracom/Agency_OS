"""
Skill: J11.11 — SDK E2E Flow Test
Journey: J11 - SDK Foundation
Checks: 7

Purpose: Test full flow: Lead → SDK Enrichment → SDK Email → Send.
"""

CHECKS = [
    {
        "id": "J11.11.1",
        "part_a": "Create test lead with ALS >= 85 (Hot)",
        "part_b": "Insert lead into database with required fields",
        "key_files": ["tests/e2e/sdk/test_sdk_e2e_flow.py"]
    },
    {
        "id": "J11.11.2",
        "part_a": "Trigger enrichment flow for Hot lead",
        "part_b": "Verify SDK enrichment agent called (not standard enrichment)",
        "key_files": ["src/engines/scout.py", "src/agents/sdk_agents/enrichment_agent.py"]
    },
    {
        "id": "J11.11.3",
        "part_a": "Verify enrichment data saved to lead_assignments",
        "part_b": "Check pain_points, personalization_hooks populated",
        "key_files": ["src/models/lead.py"]
    },
    {
        "id": "J11.11.4",
        "part_a": "Trigger email generation for enriched lead",
        "part_b": "Verify SDK email agent called with enrichment data",
        "key_files": ["src/engines/closer.py", "src/agents/sdk_agents/email_agent.py"]
    },
    {
        "id": "J11.11.5",
        "part_a": "Verify personalized email generated",
        "part_b": "Check email references specific enrichment hooks",
        "key_files": ["src/agents/sdk_agents/email_agent.py"]
    },
    {
        "id": "J11.11.6",
        "part_a": "Verify email sent via Salesforge (TEST_MODE)",
        "part_b": "Check activity logged with SDK-generated content",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J11.11.7",
        "part_a": "Verify total cost tracked for full flow",
        "part_b": "Check ai_costs table has enrichment + email entries",
        "key_files": ["src/models/costs.py"]
    }
]

PASS_CRITERIA = [
    "Hot lead triggers SDK path",
    "Enrichment agent produces quality data",
    "Email agent uses enrichment data",
    "Personalized email generated",
    "Email sent successfully",
    "Full flow cost tracked"
]

KEY_FILES = [
    "src/engines/scout.py",
    "src/engines/closer.py",
    "src/engines/email.py",
    "src/agents/sdk_agents/enrichment_agent.py",
    "src/agents/sdk_agents/email_agent.py"
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
