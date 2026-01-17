"""
Skill: J2.5 — Lead Pool Population
Journey: J2 - Campaign Creation & Management
Checks: 6

Purpose: Verify Apollo search populates the platform-wide lead pool.

Pool Population Waterfall:
- Tier 1: Apollo People Search
- Tier 2: Clay Enrichment (if Apollo fails)
- Tier 3: Direct Scraping (if both fail)
"""

CHECKS = [
    {
        "id": "J2.5.1",
        "part_a": "Read `src/orchestration/flows/pool_population_flow.py`",
        "part_b": "Identify flow tasks",
        "key_files": ["src/orchestration/flows/pool_population_flow.py"]
    },
    {
        "id": "J2.5.2",
        "part_a": "Read `src/integrations/apollo.py` — verify `search_people_for_pool`",
        "part_b": "Check Apollo API calls",
        "key_files": ["src/integrations/apollo.py"]
    },
    {
        "id": "J2.5.3",
        "part_a": "Verify 3-tier waterfall: Apollo → Clay → Direct Scraping",
        "part_b": "Check tier fallback logic",
        "key_files": ["src/orchestration/flows/pool_population_flow.py"]
    },
    {
        "id": "J2.5.4",
        "part_a": "Read `src/services/lead_pool_service.py` — verify `create_or_update`",
        "part_b": "Check dedup by email",
        "key_files": ["src/services/lead_pool_service.py"]
    },
    {
        "id": "J2.5.5",
        "part_a": "Verify `lead_pool` table receives enriched data",
        "part_b": "Query table after flow",
        "key_files": ["src/services/lead_pool_service.py"]
    },
    {
        "id": "J2.5.6",
        "part_a": "Verify email_status captured from Apollo (CRITICAL for bounce prevention)",
        "part_b": "Check email_status field",
        "key_files": ["src/integrations/apollo.py"]
    }
]

PASS_CRITERIA = [
    "Pool population flow runs via Prefect",
    "Apollo integration returns enriched leads",
    "Leads stored in `lead_pool` with 50+ fields",
    "Email deduplication works (same email = update)",
    "email_status field captured"
]

KEY_FILES = [
    "src/orchestration/flows/pool_population_flow.py",
    "src/integrations/apollo.py",
    "src/services/lead_pool_service.py"
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
