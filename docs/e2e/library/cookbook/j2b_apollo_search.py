"""
Skill: J2B.1 — Apollo Search Integration
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify Apollo search integration for lead discovery and initial data population.
"""

CHECKS = [
    {
        "id": "J2B.1.1",
        "part_a": "Read `src/integrations/apollo.py` — verify search endpoint configuration",
        "part_b": "Test Apollo search API connection",
        "key_files": ["src/integrations/apollo.py"]
    },
    {
        "id": "J2B.1.2",
        "part_a": "Verify `search_people` method accepts ICP filters (title, industry, company_size)",
        "part_b": "Execute search with test ICP criteria",
        "key_files": ["src/integrations/apollo.py"]
    },
    {
        "id": "J2B.1.3",
        "part_a": "Verify pagination handling for large result sets",
        "part_b": "Test pagination with maxResults > 100",
        "key_files": ["src/integrations/apollo.py"]
    },
    {
        "id": "J2B.1.4",
        "part_a": "Verify rate limiting compliance (Apollo API limits)",
        "part_b": "Check rate limit headers in response",
        "key_files": ["src/integrations/apollo.py"]
    },
    {
        "id": "J2B.1.5",
        "part_a": "Verify search results mapped to lead_pool schema",
        "part_b": "Confirm field mapping (name, email, company, title, linkedin_url)",
        "key_files": ["src/integrations/apollo.py", "src/models/lead.py"]
    }
]

PASS_CRITERIA = [
    "Apollo API credentials configured and working",
    "Search returns valid lead data with required fields",
    "Pagination handles large result sets correctly",
    "Rate limits respected to avoid API throttling",
    "Results properly mapped to internal lead schema"
]

KEY_FILES = [
    "src/integrations/apollo.py",
    "src/models/lead.py",
    "config/RAILWAY_ENV_VARS.txt"
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
