"""
Skill: J2B.6 — Tier Assignment
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify ALS score maps to correct tier and all enrichment data stored in assignments.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co"
}

# =============================================================================
# TIER BOUNDARIES (CRITICAL - from CLAUDE.md)
# =============================================================================

TIER_BOUNDARIES = {
    "hot": {"min": 85, "max": 100, "note": "NOT 80-100"},
    "warm": {"min": 60, "max": 84},
    "cool": {"min": 35, "max": 59},
    "cold": {"min": 20, "max": 34},
    "dead": {"min": 0, "max": 19}
}

EDGE_CASES = [
    {"score": 85, "expected_tier": "hot", "note": "Lower boundary of hot"},
    {"score": 84, "expected_tier": "warm", "note": "Upper boundary of warm"},
    {"score": 60, "expected_tier": "warm", "note": "Lower boundary of warm"},
    {"score": 59, "expected_tier": "cool", "note": "Upper boundary of cool"}
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2B.6.1",
        "part_a": "Verify tier boundaries: Hot (85-100), Warm (60-84), Cool (35-59), Cold (20-34), Dead (<20)",
        "part_b": "Test tier assignment for edge case scores (84, 85, 59, 60)",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT als_score, als_tier,
                       CASE
                           WHEN als_score >= 85 THEN 'hot'
                           WHEN als_score >= 60 THEN 'warm'
                           WHEN als_score >= 35 THEN 'cool'
                           WHEN als_score >= 20 THEN 'cold'
                           ELSE 'dead'
                       END as expected_tier,
                       CASE WHEN als_tier = (
                           CASE
                               WHEN als_score >= 85 THEN 'hot'
                               WHEN als_score >= 60 THEN 'warm'
                               WHEN als_score >= 35 THEN 'cool'
                               WHEN als_score >= 20 THEN 'cold'
                               ELSE 'dead'
                           END
                       ) THEN 'CORRECT' ELSE 'MISMATCH' END as status
                FROM lead_assignments
                WHERE als_score IS NOT NULL
                ORDER BY als_score DESC
                LIMIT 20;
            """,
            "expect": {
                "all_status": "CORRECT"
            }
        }
    },
    {
        "id": "J2B.6.2",
        "part_a": "Verify `als_score`, `als_tier`, `als_components` fields in lead_assignments",
        "part_b": "Query assignment record for score fields",
        "key_files": ["src/models/lead.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'lead_assignments'
                AND column_name IN ('als_score', 'als_tier', 'als_components');
            """,
            "expect": {
                "columns_exist": ["als_score", "als_tier", "als_components"]
            }
        }
    },
    {
        "id": "J2B.6.3",
        "part_a": "Verify `linkedin_person_data` and `linkedin_company_data` JSONB columns exist",
        "part_b": "Check schema for JSONB fields",
        "key_files": ["src/models/lead.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'lead_assignments'
                AND column_name IN ('linkedin_person_data', 'linkedin_company_data');
            """,
            "expect": {
                "data_type": "jsonb"
            }
        }
    },
    {
        "id": "J2B.6.4",
        "part_a": "Verify `personalization_data`, `pain_points`, `icebreaker_hooks` stored",
        "part_b": "Query assignment for Claude analysis results",
        "key_files": ["src/models/lead.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id,
                       la.personalization_data IS NOT NULL as has_personalization,
                       la.pain_points IS NOT NULL as has_pain_points,
                       la.icebreaker_hooks IS NOT NULL as has_icebreakers
                FROM lead_assignments la
                WHERE la.enrichment_completed_at IS NOT NULL
                ORDER BY la.enrichment_completed_at DESC
                LIMIT 10;
            """,
            "expect": {
                "has_personalization": True,
                "has_pain_points": True,
                "has_icebreakers": True
            }
        }
    },
    {
        "id": "J2B.6.5",
        "part_a": "Verify enrichment timestamps: `linkedin_person_scraped_at`, `enrichment_completed_at`",
        "part_b": "Check timestamps populated after enrichment flow",
        "key_files": ["src/models/lead.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id,
                       la.linkedin_person_scraped_at,
                       la.linkedin_company_scraped_at,
                       la.enrichment_completed_at,
                       la.enrichment_completed_at > la.linkedin_person_scraped_at as correct_order
                FROM lead_assignments la
                WHERE la.enrichment_completed_at IS NOT NULL
                ORDER BY la.enrichment_completed_at DESC
                LIMIT 5;
            """,
            "expect": {
                "timestamps_populated": True,
                "correct_order": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Tier boundaries match CLAUDE.md specification",
    "ALS score and components persisted to assignment",
    "LinkedIn data stored in JSONB columns",
    "Claude analysis results (pain_points, hooks) stored",
    "Enrichment timestamps track progress"
]

KEY_FILES = [
    "src/engines/scorer.py",
    "src/models/lead.py",
    "CLAUDE.md"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append("")
    lines.append("### Tier Boundaries (CRITICAL)")
    for tier, bounds in TIER_BOUNDARIES.items():
        note = f" ({bounds.get('note', '')})" if bounds.get('note') else ""
        lines.append(f"  {tier.upper()}: {bounds['min']}-{bounds['max']}{note}")
    lines.append("")
    lines.append("### Edge Case Tests")
    for case in EDGE_CASES:
        lines.append(f"  Score {case['score']} → {case['expected_tier']} ({case['note']})")
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
