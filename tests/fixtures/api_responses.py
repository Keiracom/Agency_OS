"""
FILE: tests/fixtures/api_responses.py
PURPOSE: Mock API response fixtures for external services
PHASE: 9 (Integration Testing)
TASK: TST-002
"""

import uuid
from datetime import datetime, timedelta
from typing import Any


# ============================================================================
# Apollo API Responses
# ============================================================================

def apollo_person_enrichment_success() -> dict[str, Any]:
    """Successful Apollo person enrichment response."""
    return {
        "person": {
            "id": f"apollo_{uuid.uuid4().hex[:12]}",
            "first_name": "Jane",
            "last_name": "Smith",
            "name": "Jane Smith",
            "title": "Chief Technology Officer",
            "seniority": "c_suite",
            "email": "jane.smith@techcompany.io",
            "email_status": "verified",
            "linkedin_url": "https://linkedin.com/in/janesmith",
            "twitter_url": None,
            "phone_numbers": [
                {"raw_number": "+61412345678", "sanitized_number": "+61412345678", "type": "mobile"}
            ],
            "organization": {
                "id": f"org_{uuid.uuid4().hex[:12]}",
                "name": "TechCompany",
                "website_url": "https://techcompany.io",
                "linkedin_url": "https://linkedin.com/company/techcompany",
                "industry": "Technology",
                "estimated_num_employees": 75,
                "annual_revenue": 5000000,
                "founded_year": 2019,
                "primary_domain": "techcompany.io",
            },
            "city": "Sydney",
            "state": "NSW",
            "country": "Australia",
        },
        "organization": {
            "id": f"org_{uuid.uuid4().hex[:12]}",
            "name": "TechCompany",
            "website_url": "https://techcompany.io",
            "linkedin_url": "https://linkedin.com/company/techcompany",
            "industry": "Technology",
            "estimated_num_employees": 75,
            "annual_revenue": 5000000,
            "founded_year": 2019,
            "primary_domain": "techcompany.io",
            "technologies": ["AWS", "Python", "React"],
            "keywords": ["SaaS", "B2B", "AI"],
        },
    }


def apollo_person_enrichment_partial() -> dict[str, Any]:
    """Partial Apollo enrichment (missing some fields)."""
    return {
        "person": {
            "id": f"apollo_{uuid.uuid4().hex[:12]}",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@unknowncompany.com",
            "email_status": "unverified",
            "title": None,
            "linkedin_url": None,
            "phone_numbers": [],
        },
        "organization": None,
    }


def apollo_person_not_found() -> dict[str, Any]:
    """Apollo person not found response."""
    return {
        "person": None,
        "organization": None,
        "error": "Person not found",
    }


def apollo_rate_limited() -> dict[str, Any]:
    """Apollo rate limit exceeded response."""
    return {
        "error": {
            "code": "rate_limit_exceeded",
            "message": "API rate limit exceeded. Please retry after 60 seconds.",
        }
    }


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
        "estimated_completion": datetime.utcnow() + timedelta(seconds=30),
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
        "created_at": datetime.utcnow().isoformat(),
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
        "date_created": datetime.utcnow().isoformat(),
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
        "date_sent": datetime.utcnow().isoformat(),
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
        "sent_at": datetime.utcnow().isoformat(),
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
        "sent_at": datetime.utcnow().isoformat(),
    }


def heyreach_rate_limited() -> dict[str, Any]:
    """HeyReach daily limit exceeded (17/day/seat)."""
    return {
        "error": "daily_limit_exceeded",
        "message": "Daily limit of 17 connection requests per seat exceeded",
        "seat_id": "seat_001",
        "limit": 17,
        "used": 17,
        "reset_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
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
        "reset_at": (datetime.utcnow().replace(hour=0, minute=0, second=0) + timedelta(days=1)).isoformat(),
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
        "created_at": datetime.utcnow().isoformat(),
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
        "completed_at": datetime.utcnow().isoformat(),
    }


def synthflow_call_failed() -> dict[str, Any]:
    """Synthflow call failed (no answer)."""
    return {
        "call_id": f"call_{uuid.uuid4().hex[:12]}",
        "status": "failed",
        "failure_reason": "no_answer",
        "duration_seconds": 0,
        "retry_recommended": True,
        "completed_at": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Lob API Responses
# ============================================================================

def lob_letter_success() -> dict[str, Any]:
    """Successful Lob letter creation."""
    return {
        "id": f"ltr_{uuid.uuid4().hex[:12]}",
        "to": {
            "name": "Jane Smith",
            "company": "TechCompany",
            "address_line1": "123 Tech Street",
            "address_city": "Sydney",
            "address_state": "NSW",
            "address_zip": "2000",
            "address_country": "AU",
        },
        "from": {
            "name": "Agency OS",
            "address_line1": "456 Agency Lane",
            "address_city": "Melbourne",
            "address_state": "VIC",
            "address_zip": "3000",
            "address_country": "AU",
        },
        "color": True,
        "double_sided": True,
        "address_placement": "top_first_page",
        "mail_type": "usps_first_class",
        "expected_delivery_date": (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d"),
        "send_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "tracking_number": f"LB{uuid.uuid4().hex[:10].upper()}",
        "url": f"https://lob.com/letters/ltr_{uuid.uuid4().hex[:12]}",
    }


def lob_address_verification_success() -> dict[str, Any]:
    """Lob address verification successful."""
    return {
        "id": f"us_ver_{uuid.uuid4().hex[:12]}",
        "recipient": "Jane Smith",
        "primary_line": "123 Tech Street",
        "secondary_line": "",
        "urbanization": "",
        "last_line": "Sydney NSW 2000",
        "deliverability": "deliverable",
        "components": {
            "city": "Sydney",
            "state": "NSW",
            "zip_code": "2000",
            "country": "AU",
        },
        "deliverability_analysis": {
            "dpv_confirmation": "Y",
            "dpv_cmra": "N",
            "dpv_vacant": "N",
            "dpv_footnotes": ["AA", "BB"],
        },
    }


def lob_address_verification_failed() -> dict[str, Any]:
    """Lob address verification failed."""
    return {
        "id": f"us_ver_{uuid.uuid4().hex[:12]}",
        "deliverability": "undeliverable",
        "error": {
            "type": "address_not_found",
            "message": "The address could not be verified",
        },
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
# [x] Apollo responses (success, partial, not_found, rate_limited)
# [x] Clay responses (success, pending)
# [x] Resend responses (success, bounced, rate_limited)
# [x] Twilio responses (success, delivered, failed, DNCR checks)
# [x] HeyReach responses (connection, message, rate_limited, usage)
# [x] Synthflow responses (initiated, completed, failed)
# [x] Lob responses (letter, address verification)
# [x] Anthropic responses (message, classification, rate_limited, budget)
# [x] All responses include realistic UUIDs and timestamps
