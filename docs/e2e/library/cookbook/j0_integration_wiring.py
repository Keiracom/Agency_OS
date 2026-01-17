"""
Skill: J0.5 — Integration Wiring Audit
Journey: J0 - Infrastructure & Wiring Audit
Checks: 9

Purpose: Verify each integration client is properly configured.
"""

CHECKS = [
    {
        "id": "J0.5.1",
        "part_a": "Read src/integrations/anthropic.py — verify AsyncAnthropic init",
        "part_b": "Make test completion call (budget check)",
        "key_files": ["src/integrations/anthropic.py"]
    },
    {
        "id": "J0.5.2",
        "part_a": "Verify AI spend limiter checks Redis",
        "part_b": "Check `v1:ai_spend:daily:YYYY-MM-DD` key",
        "key_files": ["src/integrations/anthropic.py"]
    },
    {
        "id": "J0.5.3",
        "part_a": "Read src/integrations/apollo.py — verify httpx client",
        "part_b": "Call Apollo health/status (if available)",
        "key_files": ["src/integrations/apollo.py"]
    },
    {
        "id": "J0.5.4",
        "part_a": "Read src/integrations/resend.py — verify API key set",
        "part_b": "Send test email (TEST_MODE)",
        "key_files": ["src/integrations/resend.py"]
    },
    {
        "id": "J0.5.5",
        "part_a": "Read src/integrations/twilio.py — verify Client init",
        "part_b": "Send test SMS (TEST_MODE)",
        "key_files": ["src/integrations/twilio.py"]
    },
    {
        "id": "J0.5.6",
        "part_a": "Read src/integrations/heyreach.py — verify httpx client",
        "part_b": "Check API key validity",
        "key_files": ["src/integrations/heyreach.py"]
    },
    {
        "id": "J0.5.7",
        "part_a": "Read src/integrations/vapi.py — verify httpx client",
        "part_b": "Check API key validity",
        "key_files": ["src/integrations/vapi.py"]
    },
    {
        "id": "J0.5.8",
        "part_a": "Read src/integrations/redis.py — verify async client",
        "part_b": "PING Redis via health check",
        "key_files": ["src/integrations/redis.py"]
    },
    {
        "id": "J0.5.9",
        "part_a": "Read src/integrations/sentry_utils.py — verify init",
        "part_b": "Trigger test error, check Sentry",
        "key_files": ["src/integrations/sentry_utils.py"]
    }
]

PASS_CRITERIA = [
    "All integration files exist",
    "All clients initialize without errors",
    "API keys are valid (test calls succeed)",
    "AI spend limiter functional"
]

KEY_FILES = [
    "src/integrations/anthropic.py",
    "src/integrations/apollo.py",
    "src/integrations/resend.py",
    "src/integrations/twilio.py",
    "src/integrations/heyreach.py",
    "src/integrations/vapi.py",
    "src/integrations/redis.py",
    "src/integrations/sentry_utils.py"
]

# Integration Status Matrix
INTEGRATIONS = [
    {"name": "Anthropic", "file": "anthropic.py", "client": "AsyncAnthropic", "async": True, "spend_limit": True},
    {"name": "Apollo", "file": "apollo.py", "client": "httpx.AsyncClient", "async": True, "spend_limit": False},
    {"name": "Apify", "file": "apify.py", "client": "ApifyClient", "async": True, "spend_limit": False},
    {"name": "Clay", "file": "clay.py", "client": "httpx.AsyncClient", "async": True, "spend_limit": False},
    {"name": "Resend", "file": "resend.py", "client": "resend SDK", "async": True, "spend_limit": False},
    {"name": "Postmark", "file": "postmark.py", "client": "httpx.AsyncClient", "async": True, "spend_limit": False},
    {"name": "Twilio", "file": "twilio.py", "client": "twilio.rest.Client", "async": False, "spend_limit": False},
    {"name": "HeyReach", "file": "heyreach.py", "client": "httpx.AsyncClient", "async": True, "spend_limit": False},
    {"name": "Vapi", "file": "vapi.py", "client": "httpx.AsyncClient", "async": True, "spend_limit": False},
    {"name": "ElevenLabs", "file": "elevenlabs.py", "client": "httpx.AsyncClient", "async": True, "spend_limit": False},
    {"name": "ClickSend", "file": "clicksend.py", "client": "httpx.AsyncClient", "async": True, "spend_limit": False},
    {"name": "DataForSEO", "file": "dataforseo.py", "client": "httpx + Basic Auth", "async": True, "spend_limit": False},
    {"name": "Redis", "file": "redis.py", "client": "redis.asyncio", "async": True, "spend_limit": None},
    {"name": "Supabase", "file": "supabase.py", "client": "SQLAlchemy", "async": True, "spend_limit": None},
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
