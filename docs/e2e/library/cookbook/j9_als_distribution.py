"""
Skill: J9.4 — ALS Distribution Widget
Journey: J9 - Client Dashboard
Checks: 6

Purpose: Verify ALS (Agency Lead Score) distribution widget displays correct
tier breakdown (Hot, Warm, Cool, Cold, Dead) with accurate counts and visual chart.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "client_id": "81dbaee6-4e71-48ad-be40-fa915fae66e0",
    "user_id": "a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2",
    "test_email": "david.stephens@keiracom.com",
    "test_phone": "+61457543392",
}

# =============================================================================
# ALS TIER DEFINITIONS (CRITICAL - MUST MATCH SPEC)
# =============================================================================

ALS_TIERS = {
    "hot": {
        "min_score": 85,
        "max_score": 100,
        "color": "#22c55e",  # green-500
        "label": "Hot",
        "description": "Ready to buy, high intent",
    },
    "warm": {
        "min_score": 60,
        "max_score": 84,
        "color": "#eab308",  # yellow-500
        "label": "Warm",
        "description": "Engaged, nurturing needed",
    },
    "cool": {
        "min_score": 35,
        "max_score": 59,
        "color": "#f97316",  # orange-500
        "label": "Cool",
        "description": "Some interest, needs warming",
    },
    "cold": {
        "min_score": 20,
        "max_score": 34,
        "color": "#3b82f6",  # blue-500
        "label": "Cold",
        "description": "Low engagement",
    },
    "dead": {
        "min_score": 0,
        "max_score": 19,
        "color": "#6b7280",  # gray-500
        "label": "Dead",
        "description": "No engagement, consider removal",
    },
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.4.1",
        "part_a": "Verify ALS distribution widget renders",
        "part_b": "Check widget displays on dashboard with chart visualization",
        "key_files": ["frontend/app/dashboard/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard (authenticated)",
                "2. Look for ALS distribution widget (usually a donut/pie chart)",
                "3. Verify chart renders without errors",
                "4. Check that tier labels are visible (Hot, Warm, Cool, Cold, Dead)"
            ],
            "expect": {
                "widget_visible": True,
                "chart_rendered": True,
                "tier_labels_shown": True
            }
        }
    },
    {
        "id": "J9.4.2",
        "part_a": "Verify correct tier thresholds are used",
        "part_b": "Hot: 85-100, Warm: 60-84, Cool: 35-59, Cold: 20-34, Dead: <20",
        "key_files": ["frontend/app/dashboard/page.tsx", "src/engines/scorer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify tier thresholds in scorer.py and frontend match spec",
            "expect": {
                "hot_threshold": {"min": 85, "max": 100},
                "warm_threshold": {"min": 60, "max": 84},
                "cool_threshold": {"min": 35, "max": 59},
                "cold_threshold": {"min": 20, "max": 34},
                "dead_threshold": {"min": 0, "max": 19}
            }
        }
    },
    {
        "id": "J9.4.3",
        "part_a": "Verify Hot tier count matches database",
        "part_b": "Count leads with score >= 85 for tenant, compare to widget",
        "key_files": ["src/api/routes/leads.py"],
        "live_test": {
            "type": "db_query",
            "description": "Query leads with ALS >= 85 and compare to widget",
            "query": """SELECT COUNT(*) as hot_count
                       FROM leads
                       WHERE client_id = '{client_id}'
                       AND als_score >= 85
                       AND deleted_at IS NULL""",
            "expect": {
                "hot_count_matches_widget": True
            },
            "curl_command": """curl '{api_url}/api/v1/leads/distribution' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.4.4",
        "part_a": "Verify all tier counts sum to total leads",
        "part_b": "Hot + Warm + Cool + Cold + Dead = Total Leads",
        "key_files": ["frontend/app/dashboard/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/leads/distribution",
            "auth": True,
            "expect": {
                "status": 200,
                "validation": "hot + warm + cool + cold + dead == total_leads"
            },
            "curl_command": """curl '{api_url}/api/v1/leads/distribution' \\
  -H 'Authorization: Bearer {token}' | jq '. | .hot + .warm + .cool + .cold + .dead'"""
        }
    },
    {
        "id": "J9.4.5",
        "part_a": "Verify tier colors are visually distinct",
        "part_b": "Check each tier has appropriate color coding (green, yellow, orange, blue, gray)",
        "key_files": ["frontend/app/dashboard/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard (authenticated)",
                "2. Look at ALS distribution chart",
                "3. Verify Hot tier is green",
                "4. Verify Warm tier is yellow",
                "5. Verify Cool tier is orange",
                "6. Verify Cold tier is blue",
                "7. Verify Dead tier is gray"
            ],
            "expect": {
                "hot_color": "green",
                "warm_color": "yellow",
                "cool_color": "orange",
                "cold_color": "blue",
                "dead_color": "gray"
            }
        }
    },
    {
        "id": "J9.4.6",
        "part_a": "Verify clicking tier filters leads list",
        "part_b": "Click on a tier segment, navigate to leads filtered by that tier",
        "key_files": ["frontend/app/dashboard/page.tsx", "frontend/app/dashboard/leads/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard (authenticated)",
                "2. Click on 'Hot' segment in ALS distribution chart",
                "3. Verify navigation to /dashboard/leads?tier=hot",
                "4. Verify leads list shows only Hot tier leads (score >= 85)",
                "5. Repeat for other tiers"
            ],
            "expect": {
                "click_navigates_to_filtered_list": True,
                "url_contains_tier_param": True,
                "filtered_leads_match_tier": True
            }
        }
    },
]

PASS_CRITERIA = [
    "ALS distribution widget renders with chart",
    "Tier thresholds match spec (Hot: 85-100, etc.)",
    "Tier counts match database records",
    "All tier counts sum to total leads",
    "Each tier has distinct color coding",
    "Clicking tier filters leads list correctly",
]

KEY_FILES = [
    "frontend/app/dashboard/page.tsx",
    "frontend/components/leads/ALSScorecard.tsx",
    "src/engines/scorer.py",
    "src/api/routes/leads.py",
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_tier_for_score(score: int) -> str:
    """Get tier name for a given ALS score."""
    if score >= 85:
        return "hot"
    elif score >= 60:
        return "warm"
    elif score >= 35:
        return "cool"
    elif score >= 20:
        return "cold"
    else:
        return "dead"


def get_live_url(path: str) -> str:
    """Get full URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"


def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"


def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### ALS Tier Thresholds (CRITICAL)")
    for tier, config in ALS_TIERS.items():
        lines.append(f"  {config['label']}: {config['min_score']}-{config['max_score']} ({config['color']})")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
            if lt.get("url"):
                lines.append(f"  URL: {lt['url']}")
            if lt.get("steps"):
                lines.append("  Steps:")
                for step in lt["steps"]:
                    lines.append(f"    {step}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    lines.append("")
    lines.append("### Key Files")
    for f in KEY_FILES:
        lines.append(f"- {f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_instructions())
