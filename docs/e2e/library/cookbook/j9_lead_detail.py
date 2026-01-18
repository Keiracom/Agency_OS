"""
Skill: J9.7 — Lead Detail Page
Journey: J9 - Client Dashboard
Checks: 5

Purpose: Verify lead detail page displays complete lead information including
contact details, ALS scorecard, activity timeline, and communication history.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
}

# =============================================================================
# LEAD DETAIL CONSTANTS
# =============================================================================

LEAD_CONTACT_FIELDS = [
    "first_name",
    "last_name",
    "email",
    "phone",
    "company",
    "title",
    "linkedin_url",
    "location",
]

ALS_SCORE_FACTORS = [
    {"name": "engagement", "max_points": 30, "description": "Email opens, clicks, replies"},
    {"name": "fit", "max_points": 25, "description": "ICP match score"},
    {"name": "intent", "max_points": 20, "description": "Website visits, demo requests"},
    {"name": "recency", "max_points": 15, "description": "Days since last activity"},
    {"name": "completeness", "max_points": 10, "description": "Data completeness"},
]

ACTIVITY_TIMELINE_EVENTS = [
    "lead_created",
    "email_sent",
    "email_opened",
    "email_clicked",
    "reply_received",
    "score_updated",
    "status_changed",
    "meeting_booked",
    "call_completed",
]

# =============================================================================
# API ENDPOINTS
# =============================================================================

API_ENDPOINTS = [
    {"method": "GET", "path": "/api/v1/leads/{id}", "purpose": "Get lead details", "auth": True},
    {"method": "GET", "path": "/api/v1/leads/{id}/activity", "purpose": "Get lead activity timeline", "auth": True},
    {"method": "GET", "path": "/api/v1/leads/{id}/emails", "purpose": "Get lead email history", "auth": True},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.7.1",
        "part_a": "Verify lead detail page renders",
        "part_b": "Navigate to /dashboard/leads/[id], check page renders with lead data",
        "key_files": ["frontend/app/dashboard/leads/[id]/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/leads/{lead_id}",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["id", "first_name", "last_name", "email", "als_score"]
            },
            "curl_command": """curl '{api_url}/api/v1/leads/{lead_id}' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.7.2",
        "part_a": "Verify lead contact information displays",
        "part_b": "Page shows name, email, phone, company, title, LinkedIn URL",
        "key_files": ["frontend/app/dashboard/leads/[id]/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard/leads/{lead_id} (authenticated)",
                "2. Verify lead name is displayed prominently",
                "3. Check email address is shown (and clickable)",
                "4. Check phone number is shown (if available)",
                "5. Verify company name and title are displayed",
                "6. Check LinkedIn URL links to profile (if available)"
            ],
            "expect": {
                "name_displayed": True,
                "email_displayed": True,
                "company_displayed": True,
                "linkedin_link_works": True
            }
        }
    },
    {
        "id": "J9.7.3",
        "part_a": "Verify ALS scorecard displays with breakdown",
        "part_b": "ALSScorecard component shows total score and factor breakdown",
        "key_files": ["frontend/components/leads/ALSScorecard.tsx", "frontend/app/dashboard/leads/[id]/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard/leads/{lead_id} (authenticated)",
                "2. Look for ALS scorecard component",
                "3. Verify total score is displayed with tier color",
                "4. Check score breakdown shows factors (Engagement, Fit, Intent, etc.)",
                "5. Verify each factor shows points earned vs max points"
            ],
            "expect": {
                "total_score_displayed": True,
                "tier_color_correct": True,
                "factor_breakdown_shown": True,
                "factors": ["engagement", "fit", "intent", "recency", "completeness"]
            }
        }
    },
    {
        "id": "J9.7.4",
        "part_a": "Verify activity timeline shows all interactions",
        "part_b": "Timeline shows emails sent, replies, score changes, status updates",
        "key_files": ["frontend/app/dashboard/leads/[id]/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/leads/{lead_id}/activity",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "events_have_fields": ["event_type", "created_at", "description"]
            },
            "curl_command": """curl '{api_url}/api/v1/leads/{lead_id}/activity' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.7.5",
        "part_a": "Verify communication history displays",
        "part_b": "Email thread and/or call transcripts display with timestamps",
        "key_files": ["frontend/app/dashboard/leads/[id]/page.tsx", "frontend/components/communication/TranscriptViewer.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/leads/{lead_id}/emails",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "emails_have_fields": ["id", "subject", "body", "sent_at", "status"]
            },
            "curl_command": """curl '{api_url}/api/v1/leads/{lead_id}/emails' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
]

PASS_CRITERIA = [
    "Lead detail page renders without errors",
    "Contact information displays completely",
    "ALS scorecard shows score and breakdown",
    "Activity timeline shows all interactions",
    "Communication history displays with transcripts",
]

KEY_FILES = [
    "frontend/app/dashboard/leads/[id]/page.tsx",
    "frontend/components/leads/ALSScorecard.tsx",
    "frontend/components/communication/TranscriptViewer.tsx",
    "src/api/routes/leads.py",
    "src/models/lead.py",
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

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
    lines.append("### Lead Contact Fields")
    for field in LEAD_CONTACT_FIELDS:
        lines.append(f"  - {field}")
    lines.append("")
    lines.append("### ALS Score Factors")
    for factor in ALS_SCORE_FACTORS:
        lines.append(f"  - {factor['name']}: {factor['max_points']} pts - {factor['description']}")
    lines.append("")
    lines.append("### API Endpoints")
    for ep in API_ENDPOINTS:
        lines.append(f"  {ep['method']} {ep['path']} - {ep['purpose']}")
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
