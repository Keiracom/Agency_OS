"""
Skill: J2B.3 — Scout Engine
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify Scout Engine orchestrates LinkedIn scraping and data enrichment.
"""

CHECKS = [
    {
        "id": "J2B.3.1",
        "part_a": "Read `src/engines/scout.py` — verify `enrich_linkedin_for_assignment` method",
        "part_b": "N/A (wiring check)",
        "key_files": ["src/engines/scout.py"]
    },
    {
        "id": "J2B.3.2",
        "part_a": "Verify scout engine calls Apify for LinkedIn person scraping",
        "part_b": "Trace call flow from scout to apify integration",
        "key_files": ["src/engines/scout.py", "src/integrations/apify.py"]
    },
    {
        "id": "J2B.3.3",
        "part_a": "Verify scout engine calls Apify for LinkedIn company scraping",
        "part_b": "Check company LinkedIn URL extraction from lead data",
        "key_files": ["src/engines/scout.py", "src/integrations/apify.py"]
    },
    {
        "id": "J2B.3.4",
        "part_a": "Verify scout engine triggers Claude personalization analysis",
        "part_b": "Check skill invocation in enrichment flow",
        "key_files": ["src/engines/scout.py", "src/agents/skills/research_skills.py"]
    },
    {
        "id": "J2B.3.5",
        "part_a": "Verify scout engine updates assignment with enrichment data",
        "part_b": "Check database write after enrichment completes",
        "key_files": ["src/engines/scout.py", "src/models/lead.py"]
    }
]

PASS_CRITERIA = [
    "Scout engine coordinates full enrichment waterfall",
    "LinkedIn person data scraped via Apify",
    "LinkedIn company data scraped via Apify",
    "Claude analysis generates personalization insights",
    "All enrichment data saved to lead_assignments table"
]

KEY_FILES = [
    "src/engines/scout.py",
    "src/integrations/apify.py",
    "src/agents/skills/research_skills.py",
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
