"""
Skill: J7.5 — Reply Analyzer (Phase 24D)
Journey: J7 - Reply Handling
Checks: 6

Purpose: Verify sentiment, objection, and question analysis.
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
# REPLY ANALYZER CONSTANTS
# =============================================================================

SENTIMENT_TYPES = {
    "positive": "Lead expresses enthusiasm or agreement",
    "neutral": "Lead is informational or non-committal",
    "negative": "Lead expresses dissatisfaction or rejection",
    "mixed": "Lead shows both positive and negative signals"
}

OBJECTION_TYPES = {
    "timing": "Not now, next quarter, busy period",
    "budget": "Expensive, can't afford, no budget",
    "authority": "Not my decision, need to ask boss",
    "need": "Don't need, already have solution",
    "competitor": "Using another vendor, under contract",
    "trust": "Never heard of you, is this legit"
}

ANALYSIS_COMPONENTS = {
    "sentiment_detection": "Detect positive/neutral/negative/mixed sentiment",
    "objection_extraction": "Identify specific objection types",
    "question_extraction": "Pull out questions for response",
    "topic_identification": "Identify main discussion topics"
}

FALLBACK_RULES = {
    "negative_keywords": ["no", "not interested", "unsubscribe", "stop"],
    "positive_keywords": ["yes", "interested", "sounds good", "let's talk"],
    "question_patterns": ["?", "what", "how", "when", "why", "can you"]
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.5.1",
        "part_a": "Read `src/services/reply_analyzer.py` — verify complete (501 lines)",
        "part_b": "N/A",
        "key_files": ["src/services/reply_analyzer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Reply analyzer service exists and is complete",
            "expect": {
                "code_contains": ["ReplyAnalyzer", "analyze", "sentiment", "objection"]
            }
        }
    },
    {
        "id": "J7.5.2",
        "part_a": "Verify sentiment detection (positive, neutral, negative, mixed)",
        "part_b": "Test various sentiments",
        "key_files": ["src/services/reply_analyzer.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/test/analyze-reply",
            "auth": True,
            "body": {
                "message": "I'm really excited about this opportunity!",
                "analyze_sentiment": True
            },
            "expect": {
                "status": 200,
                "body_has_field": "sentiment",
                "sentiment_in": ["positive", "neutral", "negative", "mixed"]
            },
            "warning": "May use AI credits for analysis",
            "curl_command": """curl -X POST '{api_url}/api/v1/test/analyze-reply' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"message": "I am really excited about this!", "analyze_sentiment": true}'"""
        }
    },
    {
        "id": "J7.5.3",
        "part_a": "Verify objection types (timing, budget, authority, need, competitor, trust)",
        "part_b": "Test objection replies",
        "key_files": ["src/services/reply_analyzer.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Test timing: 'We are too busy right now, maybe next quarter'",
                "2. Test budget: 'This is too expensive for our budget'",
                "3. Test authority: 'I need to run this by my manager first'",
                "4. Test need: 'We already have a solution that works for us'",
                "5. Test competitor: 'We are under contract with another vendor'",
                "6. Test trust: 'I have never heard of your company before'"
            ],
            "expect": {
                "objection_type_identified": True,
                "objection_in": ["timing", "budget", "authority", "need", "competitor", "trust"]
            }
        }
    },
    {
        "id": "J7.5.4",
        "part_a": "Verify question extraction",
        "part_b": "Test question replies",
        "key_files": ["src/services/reply_analyzer.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/test/analyze-reply",
            "auth": True,
            "body": {
                "message": "What are your pricing tiers? How long is the implementation?",
                "extract_questions": True
            },
            "expect": {
                "status": 200,
                "body_has_field": "questions",
                "questions_count_gte": 1
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/test/analyze-reply' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"message": "What are your pricing tiers?", "extract_questions": true}'"""
        }
    },
    {
        "id": "J7.5.5",
        "part_a": "Verify topic extraction",
        "part_b": "Check topics identified",
        "key_files": ["src/services/reply_analyzer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Topic extraction implemented",
            "expect": {
                "code_contains": ["topic", "extract_topics", "identify_topics"]
            }
        }
    },
    {
        "id": "J7.5.6",
        "part_a": "Verify AI analysis with rule-based fallback",
        "part_b": "Disable AI, test rules",
        "key_files": ["src/services/reply_analyzer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Rule-based fallback for when AI unavailable",
            "expect": {
                "code_contains": ["fallback", "rule_based", "pattern", "keyword"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Sentiment detected correctly",
    "Objection types identified",
    "Questions extracted",
    "Topics identified",
    "Fallback rules work"
]

KEY_FILES = [
    "src/services/reply_analyzer.py"
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
    lines.append("### Sentiment Types")
    for sentiment, description in SENTIMENT_TYPES.items():
        lines.append(f"  {sentiment}: {description}")
    lines.append("")
    lines.append("### Objection Types Reference")
    for objection, examples in OBJECTION_TYPES.items():
        lines.append(f"  {objection}: {examples}")
    lines.append("")
    lines.append("### Fallback Rules")
    for rule, keywords in FALLBACK_RULES.items():
        lines.append(f"  {rule}: {keywords[:3]}...")
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
