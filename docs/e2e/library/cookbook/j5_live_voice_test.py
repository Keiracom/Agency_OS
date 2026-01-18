"""
Skill: J5.13 — Live Voice Call Test
Journey: J5 - Voice Outreach
Checks: 8

Purpose: Verify real AI voice call works end-to-end.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "test_phone": "+61457543392",  # CEO test phone
    "client_id": "81dbaee6-4e71-48ad-be40-fa915fae66e0",
    "user_id": "a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2",
    "test_email": "david.stephens@keiracom.com",
    "warning": "LIVE CALL TEST - Will initiate real phone call, costs money"
}

# =============================================================================
# LIVE CALL TEST REQUIREMENTS
# =============================================================================

LIVE_CALL_REQUIREMENTS = {
    "test_mode_required": True,
    "test_recipient": "+61457543392",
    "expected_call_duration": "30-300 seconds",
    "quality_checks": [
        "Voice clarity",
        "Response latency",
        "Personalization accuracy",
        "Conversation flow"
    ],
    "post_call_verification": [
        "Activity record created",
        "Transcript captured",
        "Recording accessible",
        "Lead status updated"
    ]
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.13.1",
        "part_a": "Verify test phone ready",
        "part_b": "Have phone (+61457543392) available",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Ensure test phone (+61457543392) is charged and nearby",
                "2. Verify phone ringer is ON",
                "3. Be prepared to answer within 30 seconds"
            ],
            "expect": {
                "phone_ready": True
            }
        }
    },
    {
        "id": "J5.13.2",
        "part_a": "N/A",
        "part_b": "Initiate call via TEST_MODE",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/voice/test-call",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "campaign_id": "{test_campaign_id}",
                "test_mode": True
            },
            "expect": {
                "status": [200, 201, 202],
                "body_has_field": "call_id",
                "call_initiated": True
            },
            "warning": "Initiates real call - CEO approval required",
            "curl_command": """curl -X POST '{api_url}/api/v1/voice/test-call' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{lead_id}", "campaign_id": "{campaign_id}", "test_mode": true}'"""
        }
    },
    {
        "id": "J5.13.3",
        "part_a": "N/A",
        "part_b": "Answer phone, talk to AI agent",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Answer incoming call from Vapi number",
                "2. Listen to AI agent introduction",
                "3. Engage in brief conversation (1-2 minutes)",
                "4. Test various responses (interested, questions, objections)"
            ],
            "expect": {
                "call_answered": True,
                "ai_speaks": True
            }
        }
    },
    {
        "id": "J5.13.4",
        "part_a": "N/A",
        "part_b": "Verify conversation quality",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Rate voice clarity (1-5)",
                "2. Rate response speed (1-5)",
                "3. Rate natural flow (1-5)",
                "4. Note any issues (stuttering, delays, misunderstanding)"
            ],
            "expect": {
                "voice_clarity": ">= 4",
                "response_speed": ">= 3",
                "natural_flow": ">= 3"
            }
        }
    },
    {
        "id": "J5.13.5",
        "part_a": "N/A",
        "part_b": "Verify personalization spoken correctly",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Listen for lead's name pronunciation",
                "2. Listen for company name pronunciation",
                "3. Verify context is correct (industry, role)",
                "4. Check if opener is personalized"
            ],
            "expect": {
                "name_correct": True,
                "company_correct": True,
                "context_accurate": True
            }
        }
    },
    {
        "id": "J5.13.6",
        "part_a": "N/A",
        "part_b": "Check activity record after call",
        "key_files": [],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, lead_id, campaign_id, channel, metadata, created_at
                FROM activity
                WHERE channel = 'voice'
                ORDER BY created_at DESC
                LIMIT 1;
            """,
            "expect": {
                "activity_exists": True,
                "channel_is_voice": True,
                "metadata_not_empty": True
            }
        }
    },
    {
        "id": "J5.13.7",
        "part_a": "N/A",
        "part_b": "Check transcript captured",
        "key_files": [],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id,
                       metadata->>'transcript' as transcript,
                       LENGTH(metadata->>'transcript') as transcript_length
                FROM activity
                WHERE channel = 'voice'
                ORDER BY created_at DESC
                LIMIT 1;
            """,
            "expect": {
                "transcript_present": True,
                "transcript_length": "> 100"
            }
        }
    },
    {
        "id": "J5.13.8",
        "part_a": "N/A",
        "part_b": "Check recording accessible",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Query for recording_url from latest voice activity",
                "2. Open URL in browser",
                "3. Verify audio plays",
                "4. Verify conversation matches what was spoken"
            ],
            "expect": {
                "recording_url_valid": True,
                "audio_plays": True,
                "matches_conversation": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Call connects successfully",
    "AI agent speaks clearly",
    "AI agent responds appropriately",
    "Personalization works",
    "Transcript captured",
    "Recording accessible"
]

KEY_FILES = [
    "src/engines/voice.py",
    "src/integrations/vapi.py"
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
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Test Phone: {LIVE_CONFIG['test_phone']}")
    lines.append(f"- WARNING: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### Live Call Requirements")
    lines.append(f"  Test Mode Required: {LIVE_CALL_REQUIREMENTS['test_mode_required']}")
    lines.append(f"  Test Recipient: {LIVE_CALL_REQUIREMENTS['test_recipient']}")
    lines.append(f"  Expected Duration: {LIVE_CALL_REQUIREMENTS['expected_call_duration']}")
    lines.append("  Quality Checks:")
    for check in LIVE_CALL_REQUIREMENTS['quality_checks']:
        lines.append(f"    - {check}")
    lines.append("  Post-Call Verification:")
    for verification in LIVE_CALL_REQUIREMENTS['post_call_verification']:
        lines.append(f"    - {verification}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
            if lt.get("warning"):
                lines.append(f"  Warning: {lt['warning']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
