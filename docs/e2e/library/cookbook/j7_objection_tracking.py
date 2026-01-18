"""
Skill: J7.8 — Objection Tracking (Phase 24D)
Journey: J7 - Reply Handling
Checks: 5

Purpose: Verify objections are tracked for CIS learning.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app"
}

# =============================================================================
# OBJECTION TRACKING CONSTANTS
# =============================================================================

OBJECTION_TYPES = {
    "timing": "timing_not_now",
    "budget": "budget_constraints",
    "authority": "not_decision_maker",
    "need": "no_need",
    "competitor": "using_competitor",
    "trust": "other",
    "do_not_contact": "do_not_contact"
}

REJECTION_REASON_MAP = {
    "timing": "timing_not_now",
    "budget": "budget_constraints",
    "authority": "not_decision_maker",
    "need": "no_need",
    "competitor": "using_competitor",
    "trust": "other",
    "do_not_contact": "do_not_contact",
    "other": "not_interested_generic"
}

CIS_LEARNING_FIELDS = {
    "rejection_reason": "Categorized rejection type",
    "rejection_at": "Timestamp of rejection",
    "objections_raised": "Array of all objections from this lead"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.8.1",
        "part_a": "Read `_record_rejection` method (closer.py lines 500-538)",
        "part_b": "N/A",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "_record_rejection method exists",
            "expect": {
                "code_contains": ["_record_rejection", "rejection_reason", "rejection_at"]
            }
        }
    },
    {
        "id": "J7.8.2",
        "part_a": "Verify rejection_reason field updated",
        "part_b": "Check lead.rejection_reason",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.rejection_reason, l.status, l.updated_at
                FROM leads l
                WHERE l.rejection_reason IS NOT NULL
                ORDER BY l.updated_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "rejection_reason"],
                "rejection_reason_in": [
                    "timing_not_now", "budget_constraints", "not_decision_maker",
                    "no_need", "using_competitor", "not_interested_generic", "other"
                ]
            }
        }
    },
    {
        "id": "J7.8.3",
        "part_a": "Verify rejection_at timestamp set",
        "part_b": "Check lead.rejection_at",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.rejection_at, l.rejection_reason
                FROM leads l
                WHERE l.rejection_at IS NOT NULL
                ORDER BY l.rejection_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "rejection_at", "rejection_reason"]
            }
        }
    },
    {
        "id": "J7.8.4",
        "part_a": "Read `_add_objection_to_history` method (lines 540-566)",
        "part_b": "N/A",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "_add_objection_to_history method exists",
            "expect": {
                "code_contains": ["objection", "history", "append", "objections_raised"]
            }
        }
    },
    {
        "id": "J7.8.5",
        "part_a": "Verify objections_raised array updated",
        "part_b": "Check lead.objections_raised",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.objections_raised
                FROM leads l
                WHERE l.objections_raised IS NOT NULL
                AND jsonb_array_length(l.objections_raised) > 0
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "objections_raised"],
                "objections_is_array": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Rejection reason recorded",
    "Timestamp captured",
    "Objections added to history array",
    "CIS can query rejection patterns"
]

KEY_FILES = [
    "src/engines/closer.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Objection Types")
    for objection, reason in OBJECTION_TYPES.items():
        lines.append(f"  {objection}: {reason}")
    lines.append("")
    lines.append("### CIS Learning Fields")
    for field, description in CIS_LEARNING_FIELDS.items():
        lines.append(f"  {field}: {description}")
    lines.append("")
    lines.append("### Rejection Reason Mapping Reference")
    lines.append("```python")
    lines.append("rejection_map = {")
    for objection, reason in REJECTION_REASON_MAP.items():
        lines.append(f'    "{objection}": "{reason}",')
    lines.append("}")
    lines.append("```")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
