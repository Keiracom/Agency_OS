"""
FILE: tests/fixtures/api_responses.py
PURPOSE: Mock API response fixtures for external services
PHASE: 9 (Integration Testing)
TASK: TST-002
"""

import uuid
from datetime import datetime, timedelta, UTC
from typing import Any

# ============================================================================
# Clay API Responses
# ============================================================================

def clay_enrichment_success() -> dict[str, Any]:
    """Successful Clay enrichment response."""
    return {
        "id": f"clay_{uuid.uuid4().hex[:12]}",
        "status": "completed",
        "data": {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@techcompany.io",
            "email_verified": True,
            "title": "CTO",
            "seniority": "Executive",
            "company": {
                "name": "TechCompany",
                "domain": "techcompany.io",
                "industry": "Technology",
                "size": "51-200",
                "location": "Sydney, Australia",
                "funding_stage": "Series A",
                "technologies": ["AWS", "Python", "Kubernetes"],
            },
            "linkedin": "https://linkedin.com/in/janesmith",
            "phone": "+61412345678",
            "location": {
                "city": "Sydney",
                "state": "NSW",
                "country": "Australia",
            },
        },
        "credits_used": 1,
    }


def clay_enrichment_pending() -> dict[str, Any]:
    """Clay enrichment still processing."""
    return {
        "id": f"clay_{uuid.uuid4().hex[:12]}",
        "status": "pending",
        "data": None,
        "estimated_completion": datetime.now(UTC) + timedelta(seconds=30),
    }


# ============================================================================
# Resend API Responses
# ============================================================================

def resend_send_success() -> dict[str, Any]:
    """Successful Resend email send response."""
    return {
        "id": f"email_{uuid.uuid4().hex[:12]}",
        "from": "outreach@agency.com",
        "to": ["jane.smith@techcompany.io"],
        "subject": "Quick question about TechCompany",
        "created_at": datetime.now(UTC).isoformat(),
    }


def resend_send_bounced() -> dict[str, Any]:
    """Resend email bounced response."""
    return {
        "id": f"email_{uuid.uuid4().hex[:12]}",
        "from": "outreach@agency.com",
        "to": ["invalid@bounced.com"],
        "error": {
            "type": "invalid_email",
            "message": "Email address does not exist",
        },
    }


def resend_rate_limited() -> dict[str, Any]:
    """Resend rate limit exceeded."""
    return {
        "statusCode": 429,
        "message": "Rate limit exceeded. Retry after 60 seconds.",
        "name": "rate_limit_exceeded",
    }


# ============================================================================
# Twilio API Responses
# ============================================================================

def twilio_sms_success() -> dict[str, Any]:
    """Successful Twilio SMS send."""
    return {
        "sid": f"SM{uuid.uuid4().hex[:32]}",
        "account_sid": "AC_test_account",
        "to": "+61412345678",
        "from_": "+61499999999",
        "body": "Hi Jane, quick question about TechCompany...",
        "status": "queued",
        "date_created": datetime.now(UTC).isoformat(),
        "direction": "outbound-api",
        "price": None,
        "error_code": None,
        "error_message": None,
    }


def twilio_sms_delivered() -> dict[str, Any]:
    """Twilio SMS delivered status."""
    return {
        "sid": f"SM{uuid.uuid4().hex[:32]}",
        "status": "delivered",
        "date_sent": datetime.now(UTC).isoformat(),
        "error_code": None,
    }


def twilio_sms_failed() -> dict[str, Any]:
    """Twilio SMS failed status."""
    return {
        "sid": f"SM{uuid.uuid4().hex[:32]}",
        "status": "failed",
        "error_code": 30003,
        "error_message": "Unreachable destination handset",
    }


def twilio_dncr_registered() -> dict[str, Any]:
    """Phone number on DNCR (Do Not Call Register)."""
    return {
        "number": "+61412345678",
        "registered": True,
        "registration_date": "2023-06-15",
        "message": "This number is registered on the Australian DNCR",
    }


def twilio_dncr_not_registered() -> dict[str, Any]:
    """Phone number NOT on DNCR."""
    return {
        "number": "+61412345678",
        "registered": False,
        "message": "This number is not registered on the Australian DNCR",
    }


# ============================================================================
# HeyReach API Responses
# ============================================================================

def heyreach_connection_request_success() -> dict[str, Any]:
    """Successful HeyReach connection request."""
    return {
        "id": f"conn_{uuid.uuid4().hex[:12]}",
        "status": "pending",
        "linkedin_url": "https://linkedin.com/in/janesmith",
        "message": "Hi Jane, I'd love to connect and discuss AI trends in Sydney...",
        "sent_at": datetime.now(UTC).isoformat(),
        "seat_id": "seat_001",
    }


def heyreach_message_success() -> dict[str, Any]:
    """Successful HeyReach direct message."""
    return {
        "id": f"msg_{uuid.uuid4().hex[:12]}",
        "status": "sent",
        "conversation_id": f"conv_{uuid.uuid4().hex[:12]}",
        "linkedin_url": "https://linkedin.com/in/janesmith",
        "message": "Hi Jane, following up on our connection...",
        "sent_at": datetime.now(UTC).isoformat(),
    }


def heyreach_rate_limited() -> dict[str, Any]:
    """HeyReach daily limit exceeded (17/day/seat)."""
    return {
        "error": "daily_limit_exceeded",
        "message": "Daily limit of 17 connection requests per seat exceeded",
        "seat_id": "seat_001",
        "limit": 17,
        "used": 17,
        "reset_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
    }


def heyreach_daily_usage() -> dict[str, Any]:
    """HeyReach daily usage response."""
    return {
        "seat_id": "seat_001",
        "connection_requests": {
            "used": 5,
            "limit": 17,
            "remaining": 12,
        },
        "messages": {
            "used": 10,
            "limit": 50,
            "remaining": 40,
        },
        "reset_at": (datetime.now(UTC).replace(hour=0, minute=0, second=0) + timedelta(days=1)).isoformat(),
    }


# ============================================================================
# Synthflow API Responses
# ============================================================================

def synthflow_call_initiated() -> dict[str, Any]:
    """Successful Synthflow voice call initiation."""
    return {
        "call_id": f"call_{uuid.uuid4().hex[:12]}",
        "status": "initiated",
        "to": "+61412345678",
        "from": "+61488888888",
        "agent_id": "agent_sales_001",
        "script_id": "script_intro_001",
        "created_at": datetime.now(UTC).isoformat(),
    }


def synthflow_call_completed() -> dict[str, Any]:
    """Synthflow call completed with transcript."""
    return {
        "call_id": f"call_{uuid.uuid4().hex[:12]}",
        "status": "completed",
        "duration_seconds": 180,
        "outcome": "interested",
        "transcript": [
            {"speaker": "agent", "text": "Hi Jane, this is Alex from Agency..."},
            {"speaker": "prospect", "text": "Hi Alex, how can I help you?"},
            {"speaker": "agent", "text": "I noticed TechCompany is expanding..."},
            {"speaker": "prospect", "text": "Yes, that's interesting. Tell me more."},
        ],
        "summary": "Prospect expressed interest in learning more about the offering",
        "next_step": "schedule_meeting",
        "completed_at": datetime.now(UTC).isoformat(),
    }


def synthflow_call_failed() -> dict[str, Any]:
    """Synthflow call failed (no answer)."""
    return {
        "call_id": f"call_{uuid.uuid4().hex[:12]}",
        "status": "failed",
        "failure_reason": "no_answer",
        "duration_seconds": 0,
        "retry_recommended": True,
        "completed_at": datetime.now(UTC).isoformat(),
    }


# ============================================================================
# Anthropic API Responses
# ============================================================================

def anthropic_message_success() -> dict[str, Any]:
    """Successful Anthropic message generation."""
    return {
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Hi Jane,\n\nI noticed TechCompany recently raised a Series A - congratulations! I work with tech startups to help streamline their outbound efforts.\n\nWould you be open to a 15-minute call next week to discuss how we're helping similar companies?\n\nBest,\nAlex",
            }
        ],
        "model": "claude-sonnet-4-20250514",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 150,
            "output_tokens": 85,
        },
    }


def anthropic_intent_classification() -> dict[str, Any]:
    """Anthropic intent classification response."""
    return {
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": '{"intent": "interested", "confidence": 0.92, "reasoning": "The reply expresses clear interest with phrases like \'love to learn more\' and asks to schedule a call, indicating buying intent."}',
            }
        ],
        "model": "claude-sonnet-4-20250514",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 200,
            "output_tokens": 45,
        },
    }


def anthropic_rate_limited() -> dict[str, Any]:
    """Anthropic rate limit exceeded."""
    return {
        "type": "error",
        "error": {
            "type": "rate_limit_error",
            "message": "Rate limit exceeded. Please retry after 60 seconds.",
        },
    }


def anthropic_budget_exceeded() -> dict[str, Any]:
    """Anthropic daily budget exceeded (Rule 15)."""
    return {
        "type": "error",
        "error": {
            "type": "budget_exceeded",
            "message": "Daily AI spend limit of $50 AUD exceeded",
            "daily_limit": 50.00,
            "current_spend": 51.25,
            "currency": "AUD",
        },
    }


# ============================================================================
# Verification Checklist
# ============================================================================
# [x] Contract comment at top
# [x] Clay responses (success, pending)
# [x] Resend responses (success, bounced, rate_limited)
# [x] Twilio responses (success, delivered, failed, DNCR checks)
# [x] HeyReach responses (connection, message, rate_limited, usage)
# [x] Synthflow responses (initiated, completed, failed)
# [x] Anthropic responses (message, classification, rate_limited, budget)
# [x] All responses include realistic UUIDs and timestamps
