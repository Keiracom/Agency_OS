"""
FILE: tests/fixtures/webhook_payloads.py
PURPOSE: Webhook payload fixtures for inbound webhook testing
PHASE: 9 (Integration Testing)
TASK: TST-002
"""

import uuid
import hmac
import hashlib
import base64
from datetime import datetime
from typing import Any


# ============================================================================
# Postmark Webhook Payloads
# ============================================================================

def postmark_inbound_email(
    from_email: str = "lead@techcompany.io",
    to_email: str = "campaign@agency.com",
    subject: str = "Re: Quick question about TechCompany",
    body: str = "Thanks for reaching out! I'd love to learn more. Can we schedule a call?",
    message_id: str | None = None,
) -> dict[str, Any]:
    """Create a Postmark inbound email webhook payload."""
    return {
        "MessageID": message_id or f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:12]}",
        "From": from_email,
        "FromName": "Jane Smith",
        "FromFull": {
            "Email": from_email,
            "Name": "Jane Smith",
        },
        "To": to_email,
        "ToFull": [
            {
                "Email": to_email,
                "Name": "",
            }
        ],
        "Cc": "",
        "CcFull": [],
        "Bcc": "",
        "BccFull": [],
        "OriginalRecipient": to_email,
        "ReplyTo": from_email,
        "Subject": subject,
        "Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S %z"),
        "MailboxHash": "",
        "TextBody": body,
        "HtmlBody": f"<html><body><p>{body}</p></body></html>",
        "StrippedTextReply": body,
        "Tag": "campaign_123",
        "Headers": [
            {"Name": "Message-ID", "Value": f"<{uuid.uuid4().hex}@techcompany.io>"},
            {"Name": "In-Reply-To", "Value": f"<original_{uuid.uuid4().hex}@agency.com>"},
            {"Name": "References", "Value": f"<original_{uuid.uuid4().hex}@agency.com>"},
        ],
        "Attachments": [],
    }


def postmark_bounce_webhook(
    email: str = "bounced@invalid.com",
    bounce_type: str = "HardBounce",
) -> dict[str, Any]:
    """Create a Postmark bounce webhook payload."""
    return {
        "RecordType": "Bounce",
        "Type": bounce_type,
        "TypeCode": 1,
        "Name": "Hard bounce",
        "Tag": "campaign_123",
        "MessageID": f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:12]}",
        "ServerID": 12345,
        "MessageStream": "outbound",
        "Description": "The server was unable to deliver your message",
        "Details": "smtp;550 5.1.1 The email account does not exist",
        "Email": email,
        "From": "outreach@agency.com",
        "BouncedAt": datetime.utcnow().isoformat() + "Z",
        "DumpAvailable": True,
        "Inactive": True,
        "CanActivate": False,
        "Subject": "Quick question about TechCompany",
    }


def postmark_spam_complaint_webhook(
    email: str = "complained@company.io",
) -> dict[str, Any]:
    """Create a Postmark spam complaint webhook payload."""
    return {
        "RecordType": "SpamComplaint",
        "ID": 123456789,
        "Type": "SpamComplaint",
        "TypeCode": 512,
        "Name": "Spam complaint",
        "Tag": "campaign_123",
        "MessageID": f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:12]}",
        "ServerID": 12345,
        "MessageStream": "outbound",
        "Description": "The subscriber marked a message as spam",
        "Email": email,
        "From": "outreach@agency.com",
        "BouncedAt": datetime.utcnow().isoformat() + "Z",
        "Subject": "Quick question",
    }


def postmark_delivery_webhook(
    email: str = "lead@techcompany.io",
) -> dict[str, Any]:
    """Create a Postmark delivery webhook payload."""
    return {
        "RecordType": "Delivery",
        "ServerID": 12345,
        "MessageStream": "outbound",
        "MessageID": f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:12]}",
        "Recipient": email,
        "Tag": "campaign_123",
        "DeliveredAt": datetime.utcnow().isoformat() + "Z",
        "Details": "Test delivery",
    }


def postmark_open_webhook(
    email: str = "lead@techcompany.io",
) -> dict[str, Any]:
    """Create a Postmark open tracking webhook payload."""
    return {
        "RecordType": "Open",
        "FirstOpen": True,
        "Client": {
            "Name": "Chrome",
            "Company": "Google",
            "Family": "Chrome",
        },
        "OS": {
            "Name": "macOS",
            "Company": "Apple",
            "Family": "macOS",
        },
        "Platform": "Desktop",
        "UserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "ReadSeconds": 5,
        "Geo": {
            "CountryISOCode": "AU",
            "Country": "Australia",
            "Region": "NSW",
            "City": "Sydney",
        },
        "MessageID": f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:12]}",
        "MessageStream": "outbound",
        "ReceivedAt": datetime.utcnow().isoformat() + "Z",
        "Tag": "campaign_123",
        "Recipient": email,
    }


# ============================================================================
# Twilio Webhook Payloads
# ============================================================================

def twilio_inbound_sms(
    from_number: str = "+61412345678",
    to_number: str = "+61499999999",
    body: str = "Yes, interested! Can we chat tomorrow?",
    message_sid: str | None = None,
) -> dict[str, Any]:
    """Create a Twilio inbound SMS webhook payload."""
    return {
        "ToCountry": "AU",
        "ToState": "",
        "SmsMessageSid": message_sid or f"SM{uuid.uuid4().hex[:32]}",
        "NumMedia": "0",
        "ToCity": "",
        "FromZip": "",
        "SmsSid": message_sid or f"SM{uuid.uuid4().hex[:32]}",
        "FromState": "",
        "SmsStatus": "received",
        "FromCity": "",
        "Body": body,
        "FromCountry": "AU",
        "To": to_number,
        "ToZip": "",
        "NumSegments": "1",
        "ReferralNumMedia": "0",
        "MessageSid": message_sid or f"SM{uuid.uuid4().hex[:32]}",
        "AccountSid": "AC_test_account",
        "From": from_number,
        "ApiVersion": "2010-04-01",
    }


def twilio_sms_status_callback(
    message_sid: str | None = None,
    status: str = "delivered",
    to_number: str = "+61412345678",
) -> dict[str, Any]:
    """Create a Twilio SMS status callback payload."""
    return {
        "SmsSid": message_sid or f"SM{uuid.uuid4().hex[:32]}",
        "SmsStatus": status,
        "MessageStatus": status,
        "To": to_number,
        "MessageSid": message_sid or f"SM{uuid.uuid4().hex[:32]}",
        "AccountSid": "AC_test_account",
        "From": "+61499999999",
        "ApiVersion": "2010-04-01",
    }


def generate_twilio_signature(
    url: str,
    params: dict[str, Any],
    auth_token: str = "test-twilio-token",
) -> str:
    """Generate a Twilio webhook signature for testing."""
    # Sort parameters and concatenate
    sorted_params = sorted(params.items())
    param_string = url + "".join(f"{k}{v}" for k, v in sorted_params)

    # Generate HMAC-SHA1 signature
    signature = hmac.new(
        auth_token.encode("utf-8"),
        param_string.encode("utf-8"),
        hashlib.sha1,
    ).digest()

    return base64.b64encode(signature).decode("utf-8")


# ============================================================================
# HeyReach Webhook Payloads
# ============================================================================

def heyreach_message_received(
    linkedin_url: str = "https://linkedin.com/in/janesmith",
    message: str = "Thanks for connecting! I'd be interested to learn more.",
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """Create a HeyReach message received webhook payload."""
    return {
        "event_type": "message_received",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "message_id": f"msg_{uuid.uuid4().hex[:12]}",
            "conversation_id": conversation_id or f"conv_{uuid.uuid4().hex[:12]}",
            "sender": {
                "linkedin_url": linkedin_url,
                "name": "Jane Smith",
                "headline": "CTO at TechCompany",
            },
            "message": {
                "text": message,
                "sent_at": datetime.utcnow().isoformat() + "Z",
            },
            "seat_id": "seat_001",
        },
    }


def heyreach_connection_accepted(
    linkedin_url: str = "https://linkedin.com/in/janesmith",
) -> dict[str, Any]:
    """Create a HeyReach connection accepted webhook payload."""
    return {
        "event_type": "connection_accepted",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "connection_id": f"conn_{uuid.uuid4().hex[:12]}",
            "profile": {
                "linkedin_url": linkedin_url,
                "name": "Jane Smith",
                "headline": "CTO at TechCompany",
                "company": "TechCompany",
                "location": "Sydney, Australia",
            },
            "seat_id": "seat_001",
            "accepted_at": datetime.utcnow().isoformat() + "Z",
        },
    }


def heyreach_connection_request_sent(
    linkedin_url: str = "https://linkedin.com/in/janesmith",
) -> dict[str, Any]:
    """Create a HeyReach connection request sent webhook payload."""
    return {
        "event_type": "connection_request_sent",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
            "profile": {
                "linkedin_url": linkedin_url,
                "name": "Jane Smith",
            },
            "message": "Hi Jane, I'd love to connect and discuss AI trends in Sydney...",
            "seat_id": "seat_001",
            "sent_at": datetime.utcnow().isoformat() + "Z",
        },
    }


# ============================================================================
# Synthflow Webhook Payloads
# ============================================================================

def synthflow_call_completed(
    call_id: str | None = None,
    outcome: str = "interested",
    duration_seconds: int = 180,
) -> dict[str, Any]:
    """Create a Synthflow call completed webhook payload."""
    return {
        "event_type": "call_completed",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "call_id": call_id or f"call_{uuid.uuid4().hex[:12]}",
            "status": "completed",
            "to": "+61412345678",
            "from": "+61488888888",
            "duration_seconds": duration_seconds,
            "outcome": outcome,
            "transcript": [
                {"speaker": "agent", "text": "Hi, this is Alex from Agency OS..."},
                {"speaker": "prospect", "text": "Hi Alex, how can I help you?"},
                {"speaker": "agent", "text": "I noticed TechCompany is expanding..."},
                {"speaker": "prospect", "text": "Yes, that sounds interesting!"},
            ],
            "summary": "Prospect expressed interest in learning more",
            "sentiment": "positive",
            "next_step": "schedule_meeting",
            "recording_url": f"https://synthflow.ai/recordings/{uuid.uuid4().hex}",
        },
    }


def synthflow_call_failed(
    call_id: str | None = None,
    failure_reason: str = "no_answer",
) -> dict[str, Any]:
    """Create a Synthflow call failed webhook payload."""
    return {
        "event_type": "call_failed",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "call_id": call_id or f"call_{uuid.uuid4().hex[:12]}",
            "status": "failed",
            "to": "+61412345678",
            "from": "+61488888888",
            "failure_reason": failure_reason,
            "retry_recommended": failure_reason in ["no_answer", "busy"],
        },
    }


# ============================================================================
# Stripe Webhook Payloads (for billing tests)
# ============================================================================

def stripe_subscription_created(
    customer_id: str | None = None,
    subscription_id: str | None = None,
) -> dict[str, Any]:
    """Create a Stripe subscription created webhook payload."""
    return {
        "id": f"evt_{uuid.uuid4().hex[:24]}",
        "object": "event",
        "api_version": "2023-10-16",
        "created": int(datetime.utcnow().timestamp()),
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": subscription_id or f"sub_{uuid.uuid4().hex[:14]}",
                "object": "subscription",
                "customer": customer_id or f"cus_{uuid.uuid4().hex[:14]}",
                "status": "active",
                "current_period_start": int(datetime.utcnow().timestamp()),
                "current_period_end": int((datetime.utcnow().timestamp()) + 2592000),  # 30 days
                "items": {
                    "data": [
                        {
                            "id": f"si_{uuid.uuid4().hex[:14]}",
                            "price": {
                                "id": "price_velocity_monthly",
                                "product": "prod_velocity",
                                "unit_amount": 49900,  # $499 AUD
                                "currency": "aud",
                            },
                        }
                    ]
                },
                "metadata": {
                    "tier": "velocity",
                    "credits": "5000",
                },
            }
        },
    }


def stripe_invoice_paid(
    customer_id: str | None = None,
    amount: int = 49900,
) -> dict[str, Any]:
    """Create a Stripe invoice paid webhook payload."""
    return {
        "id": f"evt_{uuid.uuid4().hex[:24]}",
        "object": "event",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": f"in_{uuid.uuid4().hex[:24]}",
                "object": "invoice",
                "customer": customer_id or f"cus_{uuid.uuid4().hex[:14]}",
                "amount_paid": amount,
                "currency": "aud",
                "status": "paid",
                "paid": True,
                "subscription": f"sub_{uuid.uuid4().hex[:14]}",
            }
        },
    }


def stripe_subscription_cancelled(
    customer_id: str | None = None,
    subscription_id: str | None = None,
) -> dict[str, Any]:
    """Create a Stripe subscription cancelled webhook payload."""
    return {
        "id": f"evt_{uuid.uuid4().hex[:24]}",
        "object": "event",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": subscription_id or f"sub_{uuid.uuid4().hex[:14]}",
                "object": "subscription",
                "customer": customer_id or f"cus_{uuid.uuid4().hex[:14]}",
                "status": "canceled",
                "canceled_at": int(datetime.utcnow().timestamp()),
            }
        },
    }


# ============================================================================
# HMAC Signature Helpers
# ============================================================================

def generate_webhook_signature(
    payload: str,
    secret: str,
    algorithm: str = "sha256",
) -> str:
    """Generate a generic HMAC webhook signature."""
    if algorithm == "sha256":
        signature = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    elif algorithm == "sha1":
        signature = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha1,
        ).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    return signature


# ============================================================================
# Verification Checklist
# ============================================================================
# [x] Contract comment at top
# [x] Postmark payloads (inbound, bounce, spam, delivery, open)
# [x] Twilio payloads (inbound SMS, status callback, signature generation)
# [x] HeyReach payloads (message, connection accepted, connection sent)
# [x] Synthflow payloads (call completed, call failed)
# [x] Stripe payloads (subscription created, invoice paid, cancelled)
# [x] HMAC signature generation helpers
