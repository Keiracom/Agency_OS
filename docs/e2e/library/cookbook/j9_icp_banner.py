"""
Skill: J9.13 — ICP Banner and Modal
Journey: J9 - Client Dashboard
Checks: 4

Purpose: Verify ICP (Ideal Customer Profile) progress banner displays completion
status and modal allows review and editing of ICP criteria.
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
# ICP BANNER CONSTANTS
# =============================================================================

ICP_COMPLETION_STAGES = [
    {"stage": "industries", "weight": 20, "label": "Target Industries"},
    {"stage": "company_sizes", "weight": 20, "label": "Company Sizes"},
    {"stage": "job_titles", "weight": 20, "label": "Job Titles"},
    {"stage": "locations", "weight": 15, "label": "Target Locations"},
    {"stage": "pain_points", "weight": 15, "label": "Pain Points"},
    {"stage": "exclusions", "weight": 10, "label": "Exclusion Criteria"},
]

ICP_MODAL_SECTIONS = [
    "overview",
    "industries",
    "company_sizes",
    "job_titles",
    "locations",
    "pain_points",
    "signals",
    "exclusions",
]

BANNER_STATES = {
    "incomplete": {"color": "yellow", "message": "Complete your ICP to improve lead quality"},
    "complete": {"color": "green", "message": "ICP configured - generating leads"},
    "needs_review": {"color": "blue", "message": "Review your ICP settings"},
}

# =============================================================================
# API ENDPOINTS
# =============================================================================

API_ENDPOINTS = [
    {"method": "GET", "path": "/api/v1/onboarding/icp", "purpose": "Get ICP data", "auth": True},
    {"method": "GET", "path": "/api/v1/onboarding/icp/progress", "purpose": "Get completion progress", "auth": True},
    {"method": "PUT", "path": "/api/v1/onboarding/icp", "purpose": "Update ICP settings", "auth": True},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.13.1",
        "part_a": "Verify ICP progress banner renders",
        "part_b": "Check ICPProgressBanner component displays on dashboard",
        "key_files": ["frontend/components/icp-progress-banner.tsx", "frontend/app/dashboard/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard (authenticated)",
                "2. Look for ICP progress banner (usually near top of page)",
                "3. Verify banner is visible with progress indicator",
                "4. Check banner color matches ICP status (yellow=incomplete, green=complete)"
            ],
            "expect": {
                "banner_visible": True,
                "progress_indicator_shown": True,
                "color_matches_status": True
            }
        }
    },
    {
        "id": "J9.13.2",
        "part_a": "Verify banner shows completion percentage",
        "part_b": "Banner displays ICP completion progress (e.g., '75% complete')",
        "key_files": ["frontend/components/icp-progress-banner.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/onboarding/icp/progress",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["completion_percentage", "completed_stages", "total_stages"]
            },
            "curl_command": """curl '{api_url}/api/v1/onboarding/icp/progress' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.13.3",
        "part_a": "Verify clicking banner opens ICP modal",
        "part_b": "Click banner, ICPReviewModal opens with ICP criteria",
        "key_files": ["frontend/components/icp-progress-banner.tsx", "frontend/components/icp-review-modal.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard (authenticated)",
                "2. Locate the ICP progress banner",
                "3. Click on the banner or 'Review ICP' button",
                "4. Verify modal opens with ICP review content",
                "5. Check modal is scrollable and contains all sections"
            ],
            "expect": {
                "click_opens_modal": True,
                "modal_displays_icp": True,
                "modal_scrollable": True
            }
        }
    },
    {
        "id": "J9.13.4",
        "part_a": "Verify ICP modal displays criteria",
        "part_b": "Modal shows industries, company sizes, job titles, locations",
        "key_files": ["frontend/components/icp-review-modal.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/onboarding/icp",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["industries", "company_sizes", "job_titles", "locations", "pain_points"]
            },
            "curl_command": """curl '{api_url}/api/v1/onboarding/icp' \\
  -H 'Authorization: Bearer {token}' | jq 'keys'"""
        }
    },
]

PASS_CRITERIA = [
    "ICP progress banner renders on dashboard",
    "Banner shows accurate completion percentage",
    "Clicking banner opens ICP review modal",
    "Modal displays all ICP criteria fields",
]

KEY_FILES = [
    "frontend/components/icp-progress-banner.tsx",
    "frontend/components/icp-review-modal.tsx",
    "frontend/app/dashboard/page.tsx",
    "src/api/routes/onboarding.py",
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def calculate_icp_completion(completed_stages: list) -> int:
    """Calculate ICP completion percentage based on completed stages."""
    total_weight = sum(s["weight"] for s in ICP_COMPLETION_STAGES)
    completed_weight = sum(
        s["weight"] for s in ICP_COMPLETION_STAGES
        if s["stage"] in completed_stages
    )
    return int((completed_weight / total_weight) * 100)


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
    lines.append("### ICP Completion Stages")
    for stage in ICP_COMPLETION_STAGES:
        lines.append(f"  - {stage['stage']}: {stage['label']} ({stage['weight']}%)")
    lines.append("")
    lines.append("### Banner States")
    for state, config in BANNER_STATES.items():
        lines.append(f"  - {state}: {config['message']} ({config['color']})")
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
