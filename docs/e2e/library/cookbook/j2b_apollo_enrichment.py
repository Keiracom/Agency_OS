"""
Skill: J2B.2 — Apollo Enrichment
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify Apollo enrichment adds detailed person and company data to leads.
"""

CHECKS = [
    {
        "id": "J2B.2.1",
        "part_a": "Read `src/integrations/apollo.py` — verify `enrich_person` method exists",
        "part_b": "Test enrichment with known email address",
        "key_files": ["src/integrations/apollo.py"]
    },
    {
        "id": "J2B.2.2",
        "part_a": "Verify person enrichment captures: email, phone, linkedin_url, employment history",
        "part_b": "Check enriched data structure contains all fields",
        "key_files": ["src/integrations/apollo.py"]
    },
    {
        "id": "J2B.2.3",
        "part_a": "Read `enrich_organization` method for company data",
        "part_b": "Test organization enrichment returns industry, employee_count, revenue",
        "key_files": ["src/integrations/apollo.py"]
    },
    {
        "id": "J2B.2.4",
        "part_a": "Verify credit usage tracking for enrichment calls",
        "part_b": "Check credit balance before/after enrichment",
        "key_files": ["src/integrations/apollo.py"]
    },
    {
        "id": "J2B.2.5",
        "part_a": "Verify enrichment data stored in lead_pool table",
        "part_b": "Query database for enriched lead record",
        "key_files": ["src/integrations/apollo.py", "src/models/lead.py"]
    }
]

PASS_CRITERIA = [
    "Person enrichment returns complete profile data",
    "Company enrichment returns industry and size metrics",
    "Credit usage tracked for cost monitoring",
    "Enriched data persisted to database",
    "Missing data handled gracefully (no crashes on partial data)"
]

KEY_FILES = [
    "src/integrations/apollo.py",
    "src/models/lead.py",
    "src/engines/scout.py"
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
