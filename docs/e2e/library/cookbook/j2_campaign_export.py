"""
Skill: J2.11 — Campaign Metrics
Journey: J2 - Campaign Creation & Management
Checks: 5

Purpose: Verify campaign metrics are calculated correctly.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co"
}

# =============================================================================
# METRICS DEFINITIONS
# =============================================================================

METRICS_DEFINITIONS = {
    "total_leads": "COUNT of leads assigned to campaign",
    "leads_contacted": "COUNT of leads with at least one outreach activity",
    "leads_replied": "COUNT of leads with reply activity",
    "reply_rate": "(leads_replied / leads_contacted) * 100"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2.11.1",
        "part_a": "Verify `total_leads` count in campaign response",
        "part_b": "Check API response",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/campaigns/{campaign_id}",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["total_leads", "leads_contacted", "leads_replied", "reply_rate"]
            },
            "db_verify": """
                SELECT c.id, c.name,
                       (SELECT COUNT(*) FROM leads l WHERE l.campaign_id = c.id) as actual_total_leads
                FROM campaigns c
                WHERE c.id = '{campaign_id}';
            """
        }
    },
    {
        "id": "J2.11.2",
        "part_a": "Verify `leads_contacted` count",
        "part_b": "Check activity-based count",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT c.id as campaign_id,
                       COUNT(DISTINCT a.lead_id) as leads_contacted
                FROM campaigns c
                LEFT JOIN activities a ON a.campaign_id = c.id
                    AND a.event_type IN ('email_sent', 'sms_sent', 'linkedin_sent', 'call_made')
                WHERE c.id = '{campaign_id}'
                GROUP BY c.id;
            """,
            "expect": {
                "leads_contacted_matches_api": True
            }
        }
    },
    {
        "id": "J2.11.3",
        "part_a": "Verify `leads_replied` count",
        "part_b": "Check reply detection",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT c.id as campaign_id,
                       COUNT(DISTINCT a.lead_id) as leads_replied
                FROM campaigns c
                LEFT JOIN activities a ON a.campaign_id = c.id
                    AND a.event_type IN ('email_replied', 'sms_replied', 'linkedin_replied', 'call_answered')
                WHERE c.id = '{campaign_id}'
                GROUP BY c.id;
            """,
            "expect": {
                "leads_replied_matches_api": True
            }
        }
    },
    {
        "id": "J2.11.4",
        "part_a": "Verify `reply_rate` calculation (replied/contacted)",
        "part_b": "Verify percentage",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/campaigns/{campaign_id}",
            "auth": True,
            "expect": {
                "status": 200,
                "reply_rate_formula": "(leads_replied / leads_contacted) * 100"
            },
            "manual_verify": [
                "1. Get campaign metrics from API",
                "2. Calculate: (leads_replied / leads_contacted) * 100",
                "3. Verify matches reply_rate in response",
                "4. Handle division by zero (contacted=0 → rate=0)"
            ]
        }
    },
    {
        "id": "J2.11.5",
        "part_a": "Verify metrics update in real-time",
        "part_b": "Make activity, check update",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Get initial campaign metrics via API",
                "2. Create a new activity (e.g., email_sent) for a lead",
                "3. Immediately re-fetch campaign metrics",
                "4. Verify leads_contacted increased by 1",
                "5. Create a reply activity",
                "6. Verify leads_replied increased"
            ],
            "expect": {
                "metrics_update_realtime": True,
                "no_cache_delay": True
            }
        }
    }
]

PASS_CRITERIA = [
    "All metrics calculated from activities table",
    "Metrics reflect real data (not hardcoded)",
    "Reply rate percentage accurate",
    "Metrics update in real-time"
]

KEY_FILES = [
    "src/api/routes/campaigns.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append("")
    lines.append("### Metrics Definitions")
    for metric, definition in METRICS_DEFINITIONS.items():
        lines.append(f"  {metric}: {definition}")
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
