"""
Skill: J7.4 — Closer Engine Intent Classification
Journey: J7 - Reply Handling
Checks: 5

Purpose: Verify AI-powered intent classification works correctly.
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
# INTENT CLASSIFICATION CONSTANTS
# =============================================================================

INTENT_TYPES = {
    "meeting_request": "Lead wants to schedule a meeting",
    "interested": "Lead shows interest but no meeting request",
    "question": "Lead asks a question about the offering",
    "not_interested": "Lead declines or shows no interest",
    "unsubscribe": "Lead requests removal from communications",
    "out_of_office": "Automated OOO response",
    "auto_reply": "Other automated response"
}

INTENT_MAP = {
    "meeting_request": "IntentType.MEETING_REQUEST",
    "interested": "IntentType.INTERESTED",
    "question": "IntentType.QUESTION",
    "not_interested": "IntentType.NOT_INTERESTED",
    "unsubscribe": "IntentType.UNSUBSCRIBE",
    "out_of_office": "IntentType.OUT_OF_OFFICE",
    "auto_reply": "IntentType.AUTO_REPLY"
}

CONFIDENCE_THRESHOLDS = {
    "high": 0.85,
    "medium": 0.70,
    "low": 0.50,
    "fallback_trigger": 0.50
}

SENTIMENT_TYPES = ["positive", "neutral", "negative", "mixed"]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.4.1",
        "part_a": "Read `src/engines/closer.py` — verify 7 intent types (lines 39-47)",
        "part_b": "N/A",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "All 7 intent types defined in Closer engine",
            "expect": {
                "code_contains": [
                    "meeting_request", "interested", "question",
                    "not_interested", "unsubscribe", "out_of_office", "auto_reply"
                ]
            }
        }
    },
    {
        "id": "J7.4.2",
        "part_a": "Verify `anthropic.classify_intent` call (line 164)",
        "part_b": "Test classification",
        "key_files": ["src/engines/closer.py", "src/integrations/anthropic.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/test/classify-intent",
            "auth": True,
            "body": {
                "message": "Yes, I would love to schedule a call next week to discuss further.",
                "context": {
                    "lead_name": "Test Lead",
                    "previous_messages": []
                }
            },
            "expect": {
                "status": 200,
                "body_has_field": "intent",
                "intent_in": ["meeting_request", "interested"]
            },
            "warning": "Uses Claude API credits",
            "curl_command": """curl -X POST '{api_url}/api/v1/test/classify-intent' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"message": "Yes, I would love to schedule a call next week"}'"""
        }
    },
    {
        "id": "J7.4.3",
        "part_a": "Verify confidence score returned",
        "part_b": "Check confidence > 0.7",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.intent, a.intent_confidence, a.created_at
                FROM activities a
                WHERE a.action = 'replied'
                AND a.intent IS NOT NULL
                AND a.intent_confidence IS NOT NULL
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "intent", "intent_confidence"],
                "confidence_range": [0.0, 1.0]
            }
        }
    },
    {
        "id": "J7.4.4",
        "part_a": "Verify reasoning captured",
        "part_b": "Check reasoning in result",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Intent classification captures reasoning",
            "expect": {
                "code_contains": ["reasoning", "classification_result", "confidence"]
            }
        }
    },
    {
        "id": "J7.4.5",
        "part_a": "Test all 7 intent types",
        "part_b": "Send 7 different replies",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. meeting_request: 'Yes, let's schedule a call for Tuesday'",
                "2. interested: 'This sounds interesting, tell me more'",
                "3. question: 'What are your pricing options?'",
                "4. not_interested: 'Thanks but we are not interested'",
                "5. unsubscribe: 'Please remove me from your list'",
                "6. out_of_office: 'I am out of office until Jan 25'",
                "7. auto_reply: 'Thank you for your email. This is an automated response.'"
            ],
            "expect": {
                "all_intents_classified": True,
                "confidence_above_threshold": 0.70
            }
        }
    }
]

PASS_CRITERIA = [
    "All 7 intent types recognized",
    "Confidence scores returned",
    "AI reasoning captured",
    "Low-confidence triggers fallback"
]

KEY_FILES = [
    "src/engines/closer.py",
    "src/integrations/anthropic.py"
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
    lines.append("### Intent Types")
    for intent, description in INTENT_TYPES.items():
        lines.append(f"  {intent}: {description}")
    lines.append("")
    lines.append("### Confidence Thresholds")
    for level, threshold in CONFIDENCE_THRESHOLDS.items():
        lines.append(f"  {level}: {threshold}")
    lines.append("")
    lines.append("### Intent Types Reference")
    lines.append("```python")
    lines.append("INTENT_MAP = {")
    for intent, enum_val in INTENT_MAP.items():
        lines.append(f'    "{intent}": {enum_val},')
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
            if lt.get("warning"):
                lines.append(f"  Warning: {lt['warning']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
