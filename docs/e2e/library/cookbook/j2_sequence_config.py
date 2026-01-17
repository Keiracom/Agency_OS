"""
Skill: J2.7 — ALS Scoring Engine
Journey: J2 - Campaign Creation & Management
Checks: 7

Purpose: Verify ALS scoring formula and tier assignment.

ALS Formula:
| Component    | Max Points | Formula                                           |
|--------------|------------|---------------------------------------------------|
| Data Quality | 20         | Email verified (8) + Phone (6) + LinkedIn (4) + Personal email (2) |
| Authority    | 25         | Based on title seniority (owner/CEO = 25, VP = 18, etc.) |
| Company Fit  | 25         | Industry match (10) + Employee count (8) + Country (7) |
| Timing       | 15         | New role (6) + Hiring (5) + Recent funding (4)    |
| Risk         | 15         | Base 15 minus deductions (bounced -10, unsubscribed -15, etc.) |

Tier Thresholds:
- Hot: 85-100 (NOT 80!)
- Warm: 60-84
- Cool: 35-59
- Cold: 20-34
- Dead: 0-19
"""

CHECKS = [
    {
        "id": "J2.7.1",
        "part_a": "Read `src/engines/scorer.py` — verify 5-component formula",
        "part_b": "Check scoring constants",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J2.7.2",
        "part_a": "Verify tier thresholds: Hot=85+, Warm=60-84, Cool=35-59, Cold=20-34, Dead<20",
        "part_b": "Check TIER_* constants",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J2.7.3",
        "part_a": "Verify `score_lead` method calculates all components",
        "part_b": "Run scoring on test lead",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J2.7.4",
        "part_a": "Verify `score_pool_lead` works for pool-first scoring",
        "part_b": "Score pool lead",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J2.7.5",
        "part_a": "Verify learned weights from conversion patterns (Phase 16)",
        "part_b": "Check `_get_learned_weights`",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J2.7.6",
        "part_a": "Verify buyer signal boost (Phase 24F)",
        "part_b": "Check `_get_buyer_boost`",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J2.7.7",
        "part_a": "Verify LinkedIn engagement boost (Phase 24A+)",
        "part_b": "Check `_get_linkedin_boost`",
        "key_files": ["src/engines/scorer.py"]
    }
]

PASS_CRITERIA = [
    "All 5 components calculated correctly",
    "Hot threshold is 85 (not 80)",
    "Tier determines available channels",
    "Buyer/LinkedIn boosts applied when applicable",
    "Scores stored in lead record"
]

KEY_FILES = [
    "src/engines/scorer.py"
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
