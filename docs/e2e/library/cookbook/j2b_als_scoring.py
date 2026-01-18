"""
Skill: J2B.5 — ALS Scoring Engine
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify ALS scoring engine calculates scores with LinkedIn boost (up to 10 points).
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co"
}

# =============================================================================
# LINKEDIN BOOST FORMULA
# =============================================================================

LINKEDIN_BOOST = {
    "max_boost": 10,
    "person_posts": {"points": 3, "condition": "Has recent LinkedIn posts"},
    "company_posts": {"points": 2, "condition": "Company has recent posts"},
    "high_connections": {"points": 2, "condition": "500+ connections"},
    "high_followers": {"points": 2, "condition": "1000+ followers"},
    "recent_activity": {"points": 1, "condition": "Posts in last 30 days"}
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2B.5.1",
        "part_a": "Read `src/engines/scorer.py` — verify `_get_linkedin_boost` method exists",
        "part_b": "N/A (wiring check)",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Scorer has _get_linkedin_boost method",
            "expect": {
                "code_contains": ["_get_linkedin_boost", "linkedin", "boost"]
            }
        }
    },
    {
        "id": "J2B.5.2",
        "part_a": "Verify MAX_LINKEDIN_BOOST = 10 constant defined",
        "part_b": "Check boost cap in scoring calculation",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "LinkedIn boost capped at 10",
            "expect": {
                "code_contains": ["MAX_LINKEDIN_BOOST", "10", "min("]
            }
        }
    },
    {
        "id": "J2B.5.3",
        "part_a": "Verify LinkedIn boost signals: person_posts (+3), company_posts (+2)",
        "part_b": "Check LINKEDIN_PERSON_POSTS_BOOST and LINKEDIN_COMPANY_POSTS_BOOST constants",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Person and company post boosts defined",
            "expect": {
                "code_contains": ["person_posts", "company_posts", "3", "2"]
            }
        }
    },
    {
        "id": "J2B.5.4",
        "part_a": "Verify connections boost (+2 for 500+) and followers boost (+2 for 1000+)",
        "part_b": "Check LINKEDIN_HIGH_CONNECTIONS_BOOST and LINKEDIN_HIGH_FOLLOWERS_BOOST",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Connections and followers boosts defined",
            "expect": {
                "code_contains": ["connections", "followers", "500", "1000"]
            }
        }
    },
    {
        "id": "J2B.5.5",
        "part_a": "Verify recent_activity boost (+1 for posts in last 30 days)",
        "part_b": "Test scoring with recent vs stale LinkedIn activity",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id, la.als_score,
                       la.als_components->>'linkedin_boost' as linkedin_boost,
                       la.als_components->>'data_quality' as data_quality,
                       la.als_components->>'authority' as authority
                FROM lead_assignments la
                WHERE la.als_components IS NOT NULL
                AND la.als_components->>'linkedin_boost' IS NOT NULL
                ORDER BY la.als_score DESC
                LIMIT 10;
            """,
            "expect": {
                "linkedin_boost_tracked": True,
                "boost_in_range": "0-10"
            }
        }
    }
]

PASS_CRITERIA = [
    "LinkedIn boost calculated from enrichment data",
    "All 5 signal types checked (person posts, company posts, connections, followers, recency)",
    "Boost capped at 10 points maximum",
    "Boost added to final ALS score",
    "Signals logged in als_components for transparency"
]

KEY_FILES = [
    "src/engines/scorer.py",
    "src/models/lead.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append("")
    lines.append("### LinkedIn Boost Formula")
    lines.append(f"  Max Boost: {LINKEDIN_BOOST['max_boost']} points")
    for signal, config in LINKEDIN_BOOST.items():
        if signal != "max_boost":
            lines.append(f"  {signal}: +{config['points']} ({config['condition']})")
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
