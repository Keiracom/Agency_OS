"""
Skill: J6.3 — LinkedIn Engine Implementation
Journey: J6 - LinkedIn Outreach
Checks: 7

Purpose: Verify LinkedIn engine is fully implemented with Unipile integration.
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
# LINKEDIN ENGINE CONSTANTS
# =============================================================================

LINKEDIN_ENGINE_METHODS = {
    "core": ["send", "send_batch", "send_connection_request", "send_message"],
    "status": ["get_seat_status", "get_account_status"],
    "utility": ["_log_activity", "_validate_linkedin_url"],
}

ENGINE_ACTIONS = {
    "connection": "Send LinkedIn connection request with optional note",
    "message": "Send direct message to connected contact",
    "view_profile": "View profile (for warming)",
}

OUTREACH_ENGINE_BASE = {
    "required_methods": ["send", "validate", "log_activity"],
    "optional_methods": ["send_batch", "get_quota"],
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.3.1",
        "part_a": "Read `src/engines/linkedin.py` — verify `send` method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "LinkedIn engine has send method with proper signature",
            "expect": {
                "code_contains": ["async def send", "lead", "action", "EngineResult"]
            }
        }
    },
    {
        "id": "J6.3.2",
        "part_a": "Verify no TODO/FIXME/pass in linkedin.py",
        "part_b": "Run grep",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "No incomplete implementations in linkedin.py",
            "grep_command": "grep -n 'TODO\\|FIXME\\|pass$' src/engines/linkedin.py",
            "expect": {
                "no_matches": True,
                "allowed_exceptions": ["# TODO: Future enhancement"]
            }
        }
    },
    {
        "id": "J6.3.3",
        "part_a": "Verify `send_connection_request` convenience method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "send_connection_request is implemented as wrapper around send",
            "expect": {
                "code_contains": ["send_connection_request", "connection", "note"]
            }
        }
    },
    {
        "id": "J6.3.4",
        "part_a": "Verify `send_message` convenience method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "send_message is implemented for DMs to connections",
            "expect": {
                "code_contains": ["send_message", "message"]
            }
        }
    },
    {
        "id": "J6.3.5",
        "part_a": "Verify `send_batch` method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "send_batch handles multiple leads with rate limiting",
            "expect": {
                "code_contains": ["send_batch", "leads", "for lead in"]
            }
        }
    },
    {
        "id": "J6.3.6",
        "part_a": "Verify `get_seat_status` or `get_account_status` method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/linkedin/status",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["connected", "daily_remaining"]
            },
            "curl_command": """curl '{api_url}/api/v1/linkedin/status' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J6.3.7",
        "part_a": "Verify OutreachEngine base class extended",
        "part_b": "Check class definition",
        "key_files": ["src/engines/linkedin.py", "src/engines/base.py"],
        "live_test": {
            "type": "code_verify",
            "check": "LinkedInEngine extends OutreachEngine or has compatible interface",
            "expect": {
                "code_contains": ["class LinkedInEngine", "OutreachEngine", "EngineResult"]
            }
        }
    }
]

PASS_CRITERIA = [
    "No incomplete implementations (no TODO/FIXME/pass)",
    "All core methods functional (send, send_batch, send_connection_request, send_message)",
    "Extends OutreachEngine correctly or implements compatible interface",
    "Returns EngineResult for all operations"
]

KEY_FILES = [
    "src/engines/linkedin.py",
    "src/engines/base.py"
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
    lines.append("### LinkedIn Engine Methods")
    for category, methods in LINKEDIN_ENGINE_METHODS.items():
        lines.append(f"  {category}: {', '.join(methods)}")
    lines.append("")
    lines.append("### Engine Actions")
    for action, desc in ENGINE_ACTIONS.items():
        lines.append(f"  {action}: {desc}")
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
            if lt.get("curl_command"):
                lines.append(f"  curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
