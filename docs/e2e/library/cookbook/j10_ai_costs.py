"""
Skill: J10.10 — AI Costs Page
Journey: J10 - Admin Dashboard
Checks: 6

Purpose: Verify AI/LLM cost tracking and budget management.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "test_admin": {
        "email": "david.stephens@keiracom.com",
        "role": "admin"
    }
}

# =============================================================================
# AI COST TRACKING CONSTANTS
# =============================================================================

AI_COST_CATEGORIES = [
    {"category": "ICP Analysis", "models": ["claude-3-opus", "gpt-4"], "typical_cost": "$0.10-0.50 per analysis"},
    {"category": "Email Generation", "models": ["claude-3-haiku", "gpt-3.5-turbo"], "typical_cost": "$0.01-0.05 per email"},
    {"category": "Lead Scoring", "models": ["claude-3-haiku"], "typical_cost": "$0.005 per lead"},
    {"category": "Reply Classification", "models": ["claude-3-haiku"], "typical_cost": "$0.01 per reply"},
    {"category": "Content Personalization", "models": ["claude-3-sonnet"], "typical_cost": "$0.02-0.10 per message"}
]

AI_MODELS = {
    "claude-3-opus": {"provider": "Anthropic", "input_cost": 15.00, "output_cost": 75.00, "unit": "per 1M tokens"},
    "claude-3-sonnet": {"provider": "Anthropic", "input_cost": 3.00, "output_cost": 15.00, "unit": "per 1M tokens"},
    "claude-3-haiku": {"provider": "Anthropic", "input_cost": 0.25, "output_cost": 1.25, "unit": "per 1M tokens"},
    "gpt-4": {"provider": "OpenAI", "input_cost": 30.00, "output_cost": 60.00, "unit": "per 1M tokens"},
    "gpt-3.5-turbo": {"provider": "OpenAI", "input_cost": 0.50, "output_cost": 1.50, "unit": "per 1M tokens"}
}

BUDGET_THRESHOLDS = {
    "warning": 0.8,  # 80% of budget
    "critical": 0.95  # 95% of budget
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.10.1",
        "part_a": "Read `frontend/app/admin/costs/ai/page.tsx` — verify cost display",
        "part_b": "Load AI costs page, verify metrics render",
        "key_files": ["frontend/app/admin/costs/ai/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin/costs/ai",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["AI Costs", "Budget", "Spend"]
            },
            "manual_steps": [
                "1. Login as admin user",
                "2. Navigate to {frontend_url}/admin/costs/ai",
                "3. Verify AI costs page loads",
                "4. Check key metrics display: Total Spend, Budget, Usage"
            ]
        }
    },
    {
        "id": "J10.10.2",
        "part_a": "Verify total AI spend displays correctly",
        "part_b": "Check spend matches llm_usage table sum",
        "key_files": ["frontend/app/admin/costs/ai/page.tsx", "src/api/routes/admin.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/costs/ai/summary",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["total_cost", "budget", "period", "usage_percentage"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/costs/ai/summary' \\
  -H 'Authorization: Bearer {token}'""",
            "db_verify": {
                "query": """
                    SELECT SUM(cost_usd) as total_cost
                    FROM llm_usage
                    WHERE created_at >= date_trunc('month', CURRENT_DATE);
                """,
                "expect": "API cost matches database sum for current month"
            }
        }
    },
    {
        "id": "J10.10.3",
        "part_a": "Verify cost breakdown by model",
        "part_b": "Check GPT-4, Claude costs display separately",
        "key_files": ["frontend/app/admin/costs/ai/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/costs/ai/by-model",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["model", "cost", "token_count"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/costs/ai/by-model' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/costs/ai page, locate 'Cost by Model' section",
                "2. Verify each model shows: name, total cost, token usage",
                "3. Check pie/bar chart shows model distribution",
                "4. Verify totals sum correctly"
            ]
        }
    },
    {
        "id": "J10.10.4",
        "part_a": "Verify cost breakdown by feature",
        "part_b": "Check ICP analysis, email generation, etc. costs",
        "key_files": ["frontend/app/admin/costs/ai/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/costs/ai/by-feature",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["feature", "cost", "usage_count"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/costs/ai/by-feature' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/costs/ai page, locate 'Cost by Feature' section",
                "2. Verify features show: ICP Analysis, Email Generation, Lead Scoring",
                "3. Check each feature shows cost and usage count",
                "4. Verify breakdown helps identify expensive operations"
            ]
        }
    },
    {
        "id": "J10.10.5",
        "part_a": "Verify budget vs actual comparison",
        "part_b": "Check budget threshold warnings work",
        "key_files": ["frontend/app/admin/costs/ai/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. On /admin/costs/ai page, locate budget progress bar",
                "2. Verify current spend / budget ratio is displayed",
                "3. Check color coding: green (<80%), yellow (80-95%), red (>95%)",
                "4. If over 80%, verify warning message displays",
                "5. Check 'Set Budget' button allows adjusting monthly budget"
            ],
            "expect": {
                "budget_bar_visible": True,
                "threshold_colors_correct": True,
                "warnings_display_at_threshold": True
            }
        }
    },
    {
        "id": "J10.10.6",
        "part_a": "Verify cost trend chart displays",
        "part_b": "Check historical cost data renders in chart",
        "key_files": ["frontend/app/admin/costs/ai/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/costs/ai/trend?period=day&range=30",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["date", "cost"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/costs/ai/trend?period=day&range=30' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/costs/ai page, locate cost trend chart",
                "2. Verify chart displays 30 days of data by default",
                "3. Hover over points to see daily cost",
                "4. Change date range and verify chart updates"
            ]
        }
    }
]

PASS_CRITERIA = [
    "AI costs page loads correctly",
    "Total spend is accurate",
    "Model breakdown is accurate",
    "Feature breakdown is accurate",
    "Budget warnings function",
    "Cost trend chart displays"
]

KEY_FILES = [
    "frontend/app/admin/costs/ai/page.tsx",
    "src/api/routes/admin.py",
    "src/models/llm_usage.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_frontend_url(path: str) -> str:
    """Get full frontend URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append(f"- AI Costs Page: {LIVE_CONFIG['frontend_url']}/admin/costs/ai")
    lines.append("")
    lines.append("### AI Cost Categories")
    for cat in AI_COST_CATEGORIES:
        lines.append(f"  - {cat['category']}: {cat['typical_cost']}")
        lines.append(f"    Models: {', '.join(cat['models'])}")
    lines.append("")
    lines.append("### Budget Thresholds")
    lines.append(f"  Warning: {BUDGET_THRESHOLDS['warning']*100}%")
    lines.append(f"  Critical: {BUDGET_THRESHOLDS['critical']*100}%")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("type"):
            lines.append(f"  Live Test Type: {lt['type']}")
        if lt.get("curl_command"):
            lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
