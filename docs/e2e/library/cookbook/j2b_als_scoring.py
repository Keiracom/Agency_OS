"""
Skill: J2B.5 — ALS Scoring Engine
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify ALS scoring engine calculates scores with LinkedIn boost (up to 10 points).
"""

CHECKS = [
    {
        "id": "J2B.5.1",
        "part_a": "Read `src/engines/scorer.py` — verify `_get_linkedin_boost` method exists",
        "part_b": "N/A (wiring check)",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J2B.5.2",
        "part_a": "Verify MAX_LINKEDIN_BOOST = 10 constant defined",
        "part_b": "Check boost cap in scoring calculation",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J2B.5.3",
        "part_a": "Verify LinkedIn boost signals: person_posts (+3), company_posts (+2)",
        "part_b": "Check LINKEDIN_PERSON_POSTS_BOOST and LINKEDIN_COMPANY_POSTS_BOOST constants",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J2B.5.4",
        "part_a": "Verify connections boost (+2 for 500+) and followers boost (+2 for 1000+)",
        "part_b": "Check LINKEDIN_HIGH_CONNECTIONS_BOOST and LINKEDIN_HIGH_FOLLOWERS_BOOST",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J2B.5.5",
        "part_a": "Verify recent_activity boost (+1 for posts in last 30 days)",
        "part_b": "Test scoring with recent vs stale LinkedIn activity",
        "key_files": ["src/engines/scorer.py"]
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
