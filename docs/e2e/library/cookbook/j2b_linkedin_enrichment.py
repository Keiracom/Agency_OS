"""
Skill: J2B.4 — LinkedIn Data Enrichment
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify Apify scrapes LinkedIn person and company profiles with posts.
"""

CHECKS = [
    {
        "id": "J2B.4.1",
        "part_a": "Read `src/integrations/apify.py` — verify LinkedIn person actor configuration",
        "part_b": "Check actor ID for LinkedIn profile scraper",
        "key_files": ["src/integrations/apify.py"]
    },
    {
        "id": "J2B.4.2",
        "part_a": "Verify person profile fields captured: headline, about, connections",
        "part_b": "Test scrape returns expected data structure",
        "key_files": ["src/integrations/apify.py"]
    },
    {
        "id": "J2B.4.3",
        "part_a": "Verify person posts scraped with engagement metrics (likes, comments)",
        "part_b": "Check posts array in scrape result",
        "key_files": ["src/integrations/apify.py"]
    },
    {
        "id": "J2B.4.4",
        "part_a": "Verify LinkedIn company actor configuration",
        "part_b": "Check actor ID for company profile scraper",
        "key_files": ["src/integrations/apify.py"]
    },
    {
        "id": "J2B.4.5",
        "part_a": "Verify company fields captured: description, specialties, followers, posts",
        "part_b": "Test company scrape returns all required fields",
        "key_files": ["src/integrations/apify.py"]
    }
]

PASS_CRITERIA = [
    "Apify LinkedIn person actor runs successfully",
    "Person profile data captured (headline, about, connections)",
    "Person posts scraped with dates and engagement metrics",
    "Apify LinkedIn company actor runs successfully",
    "Company profile and posts captured with followers count"
]

KEY_FILES = [
    "src/integrations/apify.py",
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
