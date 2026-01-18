"""
Skill: J2B.3 — Scout Engine
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify Scout Engine orchestrates LinkedIn scraping and data enrichment.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "warning": "Scout engine uses Apify credits - CEO approval required"
}

# =============================================================================
# SCOUT ENGINE COMPONENTS
# =============================================================================

SCOUT_COMPONENTS = {
    "linkedin_person": "Apify LinkedIn profile scraper",
    "linkedin_company": "Apify LinkedIn company scraper",
    "claude_analysis": "Personalization and pain point analysis",
    "data_persistence": "Store results in lead_assignments"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2B.3.1",
        "part_a": "Read `src/engines/scout.py` — verify `enrich_linkedin_for_assignment` method",
        "part_b": "N/A (wiring check)",
        "key_files": ["src/engines/scout.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Scout engine has enrich_linkedin_for_assignment method",
            "expect": {
                "code_contains": ["enrich_linkedin_for_assignment", "assignment_id", "apify"]
            }
        }
    },
    {
        "id": "J2B.3.2",
        "part_a": "Verify scout engine calls Apify for LinkedIn person scraping",
        "part_b": "Trace call flow from scout to apify integration",
        "key_files": ["src/engines/scout.py", "src/integrations/apify.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Scout calls Apify for person scraping",
            "expect": {
                "code_contains": ["scrape_linkedin_profile", "linkedin_url", "apify"]
            }
        }
    },
    {
        "id": "J2B.3.3",
        "part_a": "Verify scout engine calls Apify for LinkedIn company scraping",
        "part_b": "Check company LinkedIn URL extraction from lead data",
        "key_files": ["src/engines/scout.py", "src/integrations/apify.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Scout calls Apify for company scraping",
            "expect": {
                "code_contains": ["scrape_linkedin_company", "company_linkedin_url"]
            }
        }
    },
    {
        "id": "J2B.3.4",
        "part_a": "Verify scout engine triggers Claude personalization analysis",
        "part_b": "Check skill invocation in enrichment flow",
        "key_files": ["src/engines/scout.py", "src/agents/skills/research_skills.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Scout engine calls Claude for analysis",
            "expect": {
                "code_contains": ["analyze_lead", "personalization", "pain_point", "icebreaker"]
            }
        }
    },
    {
        "id": "J2B.3.5",
        "part_a": "Verify scout engine updates assignment with enrichment data",
        "part_b": "Check database write after enrichment completes",
        "key_files": ["src/engines/scout.py", "src/models/lead.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id, la.pool_lead_id,
                       la.linkedin_person_data IS NOT NULL as has_person_data,
                       la.linkedin_company_data IS NOT NULL as has_company_data,
                       la.personalization_data IS NOT NULL as has_personalization,
                       la.enrichment_completed_at
                FROM lead_assignments la
                WHERE la.enrichment_completed_at IS NOT NULL
                ORDER BY la.enrichment_completed_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_person_data": True,
                "has_company_data": True,
                "has_personalization": True
            }
        }
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
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### Scout Components")
    for component, description in SCOUT_COMPONENTS.items():
        lines.append(f"  {component}: {description}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
