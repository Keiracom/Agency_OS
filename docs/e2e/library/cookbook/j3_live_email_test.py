"""
Skill: J3.12 - Live Email Test
Journey: J3 - Email Outreach
Checks: 6

Purpose: Verify emails land in inbox (not spam) with correct formatting.
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
# EMAIL DELIVERABILITY CONSTANTS
# =============================================================================

EMAIL_AUTHENTICATION = {
    "spf": {
        "required": True,
        "check": "dig TXT {domain} | grep spf",
    },
    "dkim": {
        "required": True,
        "selector": "default._domainkey",
    },
    "dmarc": {
        "required": True,
        "check": "dig TXT _dmarc.{domain}",
    },
}

TEST_RECIPIENT = {
    "email": "david.stephens@keiracom.com",
    "check_spam_folder": True,
    "check_inbox": True,
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.12.1",
        "part_a": "Verify sender domain has SPF/DKIM/DMARC records configured",
        "part_b": "Check DNS records for sender domain",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Identify sender domain from Salesforge/Warmforge",
                "2. Run: dig TXT {domain} | grep spf",
                "3. Run: dig TXT default._domainkey.{domain}",
                "4. Run: dig TXT _dmarc.{domain}",
                "5. Verify all three records exist and are valid"
            ],
            "expect": {
                "spf_exists": True,
                "dkim_exists": True,
                "dmarc_exists": True
            },
            "tools": [
                "https://mxtoolbox.com/SuperTool.aspx",
                "https://dmarcian.com/domain-checker/"
            ]
        }
    },
    {
        "id": "J3.12.2",
        "part_a": "Verify from_email is valid and matches sender domain",
        "part_b": "Check sender configuration in Salesforge",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Login to Salesforge dashboard",
                "2. Navigate to Mailboxes/Senders",
                "3. Verify from_email domain matches SPF/DKIM records",
                "4. Verify mailbox is warmed and active",
                "5. Check daily send limit remaining"
            ],
            "expect": {
                "mailbox_configured": True,
                "domain_verified": True,
                "warmup_complete": True
            }
        }
    },
    {
        "id": "J3.12.3",
        "part_a": "N/A (live test only)",
        "part_b": "Send real email via TEST_MODE to david.stephens@keiracom.com",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/outreach/send-test-email",
            "auth": True,
            "body": {
                "to_email": "fake@example.com",
                "subject": "J3.12 Live Email Test - {timestamp}",
                "body": "This is a live deliverability test for J3.12.\n\nThe email should:\n- Land in inbox (not spam)\n- Display proper formatting\n- Show correct sender info"
            },
            "expect": {
                "status": [200, 202],
                "body_has_fields": ["message_id", "status"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/outreach/send-test-email' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{\"to_email\": \"fake@example.com\", \"subject\": \"Live Test\", \"body\": \"Test body\"}'""",
            "warning": "Sends real email - will be redirected to test recipient in TEST_MODE"
        }
    },
    {
        "id": "J3.12.4",
        "part_a": "N/A (live test only)",
        "part_b": "Check inbox (not spam folder) for delivered email",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open Gmail for david.stephens@keiracom.com",
                "2. Check Primary inbox for test email",
                "3. If not in inbox, check Spam folder",
                "4. If in spam, click 'Not spam' and investigate why",
                "5. Check email headers for authentication results"
            ],
            "expect": {
                "in_inbox": True,
                "not_in_spam": True,
                "received_within_minutes": 5
            }
        }
    },
    {
        "id": "J3.12.5",
        "part_a": "N/A (live test only)",
        "part_b": "Verify content, personalization, and HTML formatting correct",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open received test email",
                "2. Verify subject line displays correctly",
                "3. Verify body content renders properly",
                "4. Check for broken HTML or formatting issues",
                "5. Verify personalization variables replaced (not showing {{first_name}})"
            ],
            "expect": {
                "subject_correct": True,
                "body_renders": True,
                "no_broken_html": True,
                "personalization_replaced": True
            }
        }
    },
    {
        "id": "J3.12.6",
        "part_a": "N/A (live test only)",
        "part_b": "Verify threading works in inbox view (send follow-up)",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Send follow-up email (step 2) to same recipient",
                "2. Wait for delivery",
                "3. Open Gmail and find email thread",
                "4. Verify follow-up appears in same thread as original",
                "5. Verify email client shows conversation view"
            ],
            "expect": {
                "emails_threaded": True,
                "conversation_view": True,
                "in_reply_to_working": True
            },
            "note": "Requires sending two emails - initial and follow-up"
        }
    }
]

PASS_CRITERIA = [
    "Email lands in inbox (not spam)",
    "Subject displays correctly",
    "Body renders properly (HTML)",
    "Personalization fields replaced",
    "Threading displays correctly for follow-ups",
    "SPF/DKIM/DMARC pass checks"
]

KEY_FILES = [
    "src/engines/email.py",
    "src/integrations/salesforge.py",
    "src/orchestration/flows/outreach_flow.py"
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
    lines.append(f"- API URL: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend URL: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase URL: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect URL: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Test Recipient")
    lines.append(f"  Email: {TEST_RECIPIENT['email']}")
    lines.append("  (All TEST_MODE emails redirect here)")
    lines.append("")
    lines.append("### Email Authentication")
    lines.append("  SPF: Required - validates sender IP")
    lines.append("  DKIM: Required - validates email integrity")
    lines.append("  DMARC: Required - policy for failed auth")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
            if lt.get("warning"):
                lines.append(f"  Warning: {lt['warning']}")
            if lt.get("steps"):
                lines.append("  Steps:")
                for step in lt["steps"][:3]:
                    lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
