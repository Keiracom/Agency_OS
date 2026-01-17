"""
Skill: J2.8 — Deep Research (Hot Leads)
Journey: J2 - Campaign Creation & Management
Checks: 5

Purpose: Verify deep research triggers for hot leads.
"""

CHECKS = [
    {
        "id": "J2.8.1",
        "part_a": "Verify deep research trigger at ALS >= 85",
        "part_b": "Check trigger condition",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J2.8.2",
        "part_a": "Read `/api/v1/leads/{id}/research` endpoint",
        "part_b": "Test endpoint",
        "key_files": ["src/api/routes/leads.py"]
    },
    {
        "id": "J2.8.3",
        "part_a": "Verify LinkedIn scraping for person/company",
        "part_b": "Check Apify integration",
        "key_files": ["src/integrations/apify.py"]
    },
    {
        "id": "J2.8.4",
        "part_a": "Verify icebreaker generation",
        "part_b": "Check AI call for icebreakers",
        "key_files": ["src/engines/content.py"]
    },
    {
        "id": "J2.8.5",
        "part_a": "Verify research data stored in lead_assignments",
        "part_b": "Check research_data field",
        "key_files": ["src/services/lead_allocator_service.py"]
    }
]

PASS_CRITERIA = [
    "Deep research triggers automatically at 85+ score",
    "LinkedIn profile scraped",
    "Icebreakers generated",
    "Research data stored for content personalization"
]

KEY_FILES = [
    "src/engines/scorer.py",
    "src/api/routes/leads.py",
    "src/integrations/apify.py",
    "src/engines/content.py",
    "src/services/lead_allocator_service.py"
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
