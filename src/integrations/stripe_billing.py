"""
Stripe Billing Integration
Agency OS - Subscription management, webhooks, and customer portal

Environment Variables Required:
- STRIPE_SECRET_KEY: API secret key
- STRIPE_WEBHOOK_SECRET: Webhook signing secret
- STRIPE_FOUNDING_PRICE_ID: Price ID for founding member plan
- STRIPE_STANDARD_PRICE_ID: Price ID for standard plan
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass
from enum import Enum

import stripe
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel, EmailStr

from src.integrations.supabase import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
FOUNDING_PRICE_ID = os.getenv("STRIPE_FOUNDING_PRICE_ID")
STANDARD_PRICE_ID = os.getenv("STRIPE_STANDARD_PRICE_ID")


class PlanType(str, Enum):
    FOUNDING = "founding"
    STANDARD = "standard"


@dataclass
class SubscriptionResult:
    success: bool
    customer_id: Optional[str] = None
    subscription_id: Optional[str] = None
    checkout_url: Optional[str] = None
    error: Optional[str] = None


class CreateCheckoutRequest(BaseModel):
    email: EmailStr
    plan_type: PlanType = PlanType.STANDARD
    success_url: str
    cancel_url: str
    lead_id: Optional[str] = None


class CustomerPortalRequest(BaseModel):
    customer_id: str
    return_url: str


# =============================================================================
# Core Stripe Operations
# =============================================================================

async def create_customer(
    email: str,
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> stripe.Customer:
    """Create a Stripe customer."""
    try:
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata=metadata or {}
        )
        logger.info(f"Created Stripe customer: {customer.id} for {email}")
        return customer
    except stripe.StripeError as e:
        logger.error(f"Failed to create customer: {e}")
        raise


async def create_checkout_session(
    email: str,
    plan_type: PlanType,
    success_url: str,
    cancel_url: str,
    lead_id: Optional[str] = None
) -> SubscriptionResult:
    """
    Create a Stripe Checkout session for subscription.
    
    For founding members, applies the 40% discount automatically
    via the founding member price ID.
    """
    try:
        # Determine price ID
        price_id = FOUNDING_PRICE_ID if plan_type == PlanType.FOUNDING else STANDARD_PRICE_ID
        
        if not price_id:
            return SubscriptionResult(
                success=False,
                error=f"Price ID not configured for {plan_type.value} plan"
            )
        
        # Check founding spots if requesting founding plan
        if plan_type == PlanType.FOUNDING:
            spots = await get_remaining_founding_spots()
            if spots <= 0:
                return SubscriptionResult(
                    success=False,
                    error="All founding member spots have been claimed"
                )
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=email,
            line_items=[{
                "price": price_id,
                "quantity": 1
            }],
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={
                "lead_id": lead_id or "",
                "plan_type": plan_type.value,
                "is_founding": str(plan_type == PlanType.FOUNDING).lower()
            },
            subscription_data={
                "metadata": {
                    "lead_id": lead_id or "",
                    "plan_type": plan_type.value
                }
            },
            allow_promotion_codes=True  # Allow coupon codes
        )
        
        logger.info(f"Created checkout session: {session.id} for {email}")
        return SubscriptionResult(
            success=True,
            checkout_url=session.url
        )
        
    except stripe.StripeError as e:
        logger.error(f"Stripe checkout error: {e}")
        return SubscriptionResult(success=False, error=str(e))


async def create_customer_portal_session(
    customer_id: str,
    return_url: str
) -> str:
    """Create a Stripe Customer Portal session for self-service billing."""
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )
        return session.url
    except stripe.StripeError as e:
        logger.error(f"Portal session error: {e}")
        raise


async def cancel_subscription(
    subscription_id: str,
    cancel_at_period_end: bool = True
) -> stripe.Subscription:
    """Cancel a subscription (at period end by default)."""
    try:
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=cancel_at_period_end
        )
        logger.info(f"Cancelled subscription: {subscription_id}")
        return subscription
    except stripe.StripeError as e:
        logger.error(f"Cancel subscription error: {e}")
        raise


# =============================================================================
# Founding Member Helpers
# =============================================================================

async def get_remaining_founding_spots() -> int:
    """Get remaining founding member spots."""
    try:
        supabase = get_supabase_client()
        result = supabase.rpc("get_remaining_founding_spots").execute()
        return result.data if result.data else 0
    except Exception as e:
        logger.error(f"Error getting founding spots: {e}")
        return 0


async def reserve_founding_spot(
    email: str,
    company_name: Optional[str] = None,
    lead_id: Optional[str] = None
) -> Optional[int]:
    """
    Reserve a founding member spot.
    Returns spot number if successful, None if spots full.
    """
    try:
        supabase = get_supabase_client()
        
        # Get next available spot
        result = supabase.rpc("get_next_founding_spot").execute()
        spot_number = result.data
        
        if not spot_number:
            # Add to waitlist instead
            supabase.table("founding_waitlist").insert({
                "email": email,
                "company_name": company_name
            }).execute()
            logger.info(f"Added {email} to founding waitlist")
            return None
        
        # Reserve the spot
        supabase.table("founding_members").insert({
            "email": email,
            "company_name": company_name,
            "lead_id": lead_id,
            "spot_number": spot_number,
            "status": "reserved"
        }).execute()
        
        logger.info(f"Reserved founding spot #{spot_number} for {email}")
        return spot_number
        
    except Exception as e:
        logger.error(f"Error reserving founding spot: {e}")
        return None


async def activate_founding_member(
    email: str,
    stripe_customer_id: str,
    stripe_subscription_id: str
) -> bool:
    """Activate a reserved founding member after successful payment."""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table("founding_members").update({
            "status": "active",
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
            "activated_at": datetime.utcnow().isoformat()
        }).eq("email", email).execute()
        
        return len(result.data) > 0
        
    except Exception as e:
        logger.error(f"Error activating founding member: {e}")
        return False


# =============================================================================
# Webhook Handlers
# =============================================================================

async def handle_checkout_completed(session: Dict[str, Any]) -> None:
    """Handle successful checkout completion."""
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    customer_email = session.get("customer_email")
    metadata = session.get("metadata", {})
    
    plan_type = metadata.get("plan_type", "standard")
    lead_id = metadata.get("lead_id")
    
    logger.info(f"Checkout completed: {customer_email} - {plan_type} plan")
    
    # Update sales pipeline if lead_id present
    if lead_id:
        try:
            supabase = get_supabase_client()
            supabase.table("sales_pipeline").update({
                "stage": "closed_won"
            }).eq("lead_id", lead_id).execute()
        except Exception as e:
            logger.error(f"Failed to update pipeline: {e}")
    
    # Activate founding member if applicable
    if plan_type == "founding" and customer_email:
        await activate_founding_member(
            email=customer_email,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id
        )


async def handle_subscription_updated(subscription: Dict[str, Any]) -> None:
    """Handle subscription updates (upgrades, downgrades, renewals)."""
    sub_id = subscription.get("id")
    status = subscription.get("status")
    customer_id = subscription.get("customer")
    
    logger.info(f"Subscription {sub_id} updated: status={status}")
    
    # Update founding member status if churned
    if status in ("canceled", "unpaid"):
        try:
            supabase = get_supabase_client()
            supabase.table("founding_members").update({
                "status": "churned"
            }).eq("stripe_subscription_id", sub_id).execute()
        except Exception as e:
            logger.error(f"Failed to update founding member status: {e}")


async def handle_invoice_paid(invoice: Dict[str, Any]) -> None:
    """Handle successful invoice payment."""
    customer_id = invoice.get("customer")
    amount_paid = invoice.get("amount_paid", 0) / 100  # Convert from cents
    currency = invoice.get("currency", "aud").upper()
    
    logger.info(f"Invoice paid: {customer_id} - ${amount_paid} {currency}")
    # Could trigger internal notifications, update metrics, etc.


async def handle_invoice_failed(invoice: Dict[str, Any]) -> None:
    """Handle failed invoice payment."""
    customer_id = invoice.get("customer")
    attempt_count = invoice.get("attempt_count", 1)
    
    logger.warning(f"Invoice failed: {customer_id} - attempt #{attempt_count}")
    # Could trigger dunning emails, Slack alerts, etc.


# =============================================================================
# API Routes
# =============================================================================

@router.post("/create-checkout")
async def api_create_checkout(request: CreateCheckoutRequest):
    """Create a Stripe Checkout session."""
    result = await create_checkout_session(
        email=request.email,
        plan_type=request.plan_type,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        lead_id=request.lead_id
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return {"checkout_url": result.checkout_url}


@router.post("/customer-portal")
async def api_customer_portal(request: CustomerPortalRequest):
    """Create a Customer Portal session for billing management."""
    try:
        url = await create_customer_portal_session(
            customer_id=request.customer_id,
            return_url=request.return_url
        )
        return {"portal_url": url}
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/founding-spots")
async def api_founding_spots():
    """Get founding member spots status for landing page."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("founding_spots_status").select("*").single().execute()
        return result.data
    except Exception as e:
        # Fallback if view doesn't exist yet
        spots = await get_remaining_founding_spots()
        return {
            "total_spots": 20,
            "spots_remaining": spots,
            "spots_taken": 20 - spots,
            "is_full": spots <= 0
        }


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    """
    Stripe webhook endpoint.
    
    Handles:
    - checkout.session.completed
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.paid
    - invoice.payment_failed
    """
    if not WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_type = event["type"]
    data = event["data"]["object"]
    
    logger.info(f"Stripe webhook received: {event_type}")
    
    # Route to appropriate handler
    handlers = {
        "checkout.session.completed": handle_checkout_completed,
        "customer.subscription.updated": handle_subscription_updated,
        "customer.subscription.deleted": handle_subscription_updated,
        "invoice.paid": handle_invoice_paid,
        "invoice.payment_failed": handle_invoice_failed,
    }
    
    handler = handlers.get(event_type)
    if handler:
        await handler(data)
    else:
        logger.debug(f"Unhandled webhook event type: {event_type}")
    
    return {"status": "ok"}


# =============================================================================
# Usage Example
# =============================================================================
"""
# In main.py or routes:
from src.integrations.stripe_billing import router as billing_router
app.include_router(billing_router)

# Create checkout for founding member:
result = await create_checkout_session(
    email="founder@example.com",
    plan_type=PlanType.FOUNDING,
    success_url="https://app.keiracom.com/welcome",
    cancel_url="https://keiracom.com/pricing",
    lead_id="uuid-here"
)

# Get founding spots for landing page:
spots = await get_remaining_founding_spots()
# Returns: 17 (meaning 3 spots taken, 17 remaining)
"""
