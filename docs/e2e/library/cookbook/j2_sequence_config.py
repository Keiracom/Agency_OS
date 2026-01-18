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

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co"
}

# =============================================================================
# ALS SCORING FORMULA
# =============================================================================

ALS_FORMULA = {
    "data_quality": {"max": 20, "email_verified": 8, "phone": 6, "linkedin": 4, "personal_email": 2},
    "authority": {"max": 25, "owner_ceo": 25, "c_level": 22, "vp": 18, "director": 14, "manager": 10},
    "company_fit": {"max": 25, "industry_match": 10, "employee_count": 8, "country_match": 7},
    "timing": {"max": 15, "new_role": 6, "hiring": 5, "funding": 4},
    "risk": {"max": 15, "bounced": -10, "unsubscribed": -15, "complained": -15}
}

TIER_THRESHOLDS = {
    "hot": {"min": 85, "max": 100},
    "warm": {"min": 60, "max": 84},
    "cool": {"min": 35, "max": 59},
    "cold": {"min": 20, "max": 34},
    "dead": {"min": 0, "max": 19}
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2.7.1",
        "part_a": "Read `src/engines/scorer.py` — verify 5-component formula",
        "part_b": "Check scoring constants",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Scorer has all 5 components",
            "expect": {
                "code_contains": ["data_quality", "authority", "company_fit", "timing", "risk"]
            }
        }
    },
    {
        "id": "J2.7.2",
        "part_a": "Verify tier thresholds: Hot=85+, Warm=60-84, Cool=35-59, Cold=20-34, Dead<20",
        "part_b": "Check TIER_* constants",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Tier thresholds are correct (Hot starts at 85, NOT 80)",
            "expect": {
                "hot_min": 85,
                "warm_range": [60, 84],
                "cool_range": [35, 59],
                "cold_range": [20, 34],
                "dead_max": 19
            },
            "critical": "Hot threshold MUST be 85, not 80"
        }
    },
    {
        "id": "J2.7.3",
        "part_a": "Verify `score_lead` method calculates all components",
        "part_b": "Run scoring on test lead",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/leads/{lead_id}/score",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["als_score", "als_tier", "score_breakdown"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/leads/{lead_id}/score' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J2.7.4",
        "part_a": "Verify `score_pool_lead` works for pool-first scoring",
        "part_b": "Score pool lead",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, email, als_score, als_tier
                FROM lead_pool
                WHERE als_score IS NOT NULL
                ORDER BY als_score DESC
                LIMIT 10;
            """,
            "expect": {
                "als_score_populated": True,
                "als_tier_populated": True
            }
        }
    },
    {
        "id": "J2.7.5",
        "part_a": "Verify learned weights from conversion patterns (Phase 16)",
        "part_b": "Check `_get_learned_weights`",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Scorer uses learned weights from conversions",
            "expect": {
                "code_contains": ["learned_weights", "conversion", "weight"]
            },
            "note": "Phase 16 feature - may not be implemented yet"
        }
    },
    {
        "id": "J2.7.6",
        "part_a": "Verify buyer signal boost (Phase 24F)",
        "part_b": "Check `_get_buyer_boost`",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Buyer signal boost function exists",
            "expect": {
                "code_contains": ["buyer", "boost", "signal"]
            },
            "note": "Phase 24F feature - may not be implemented yet"
        }
    },
    {
        "id": "J2.7.7",
        "part_a": "Verify LinkedIn engagement boost (Phase 24A+)",
        "part_b": "Check `_get_linkedin_boost`",
        "key_files": ["src/engines/scorer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "LinkedIn engagement boost function exists",
            "expect": {
                "code_contains": ["linkedin", "boost", "engagement"]
            },
            "note": "Phase 24A+ feature - may not be implemented yet"
        }
    }
]

PASS_CRITERIA = [
    "All 5 components calculated correctly",
    "Hot threshold is 85 (NOT 80)",
    "Tier determines available channels",
    "Buyer/LinkedIn boosts applied when applicable",
    "Scores stored in lead record"
]

KEY_FILES = [
    "src/engines/scorer.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append("")
    lines.append("### ALS Formula (Max 100)")
    for component, details in ALS_FORMULA.items():
        lines.append(f"  {component}: max {details['max']} points")
    lines.append("")
    lines.append("### Tier Thresholds (CRITICAL: Hot = 85+)")
    for tier, bounds in TIER_THRESHOLDS.items():
        lines.append(f"  {tier.upper()}: {bounds['min']}-{bounds['max']}")
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
