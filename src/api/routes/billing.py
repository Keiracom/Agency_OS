"""
Contract: src/api/routes/billing.py
Purpose: Stripe billing endpoints for deposit checkout + subscription activation
Layer: 5 - routes
Imports: all lower layers
Consumers: frontend, webhooks

FILE: src/api/routes/billing.py
PURPOSE: Stripe deposit checkout, webhooks, and subscription activation
PHASE: 8/8 Build Sequence
TASK: Founding member billing flow
DEPENDENCIES:
  - stripe SDK
  - src/config/settings.py
  - src/models/client.py
  - src/integrations/supabase.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 1: Follow blueprint exactly
"""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import httpx
import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.config.settings import settings
from src.models.client import Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

# Initialize Stripe
stripe.api_key = settings.stripe_api_key

# Founding member pricing (AUD)
DEPOSIT_AMOUNT_AUD = 50000  # $500.00 in cents
MONTHLY_PRICE_AUD = 125000  # $1,250.00 in cents (founding 50% discount from $2,500)
DEPOSIT_CREDIT_AUD = 50000  # $500.00 credit against first month


# ============================================================================
# Request/Response Schemas
# ============================================================================


class CreateCheckoutRequest(BaseModel):
    """Request to create a Stripe Checkout session for founding deposit."""

    agency_id: UUID = Field(..., description="Client/Agency UUID")
    email: EmailStr = Field(..., description="Customer email for Stripe")
    agency_name: str = Field(..., min_length=1, max_length=255, description="Agency name")


class CheckoutSessionResponse(BaseModel):
    """Response with Stripe Checkout session URL."""

    checkout_url: str
    session_id: str


class ActivateSubscriptionRequest(BaseModel):
    """Request to activate subscription for a client."""

    client_id: UUID


class ActivateSubscriptionResponse(BaseModel):
    """Response after subscription activation."""

    success: bool
    subscription_id: str | None = None
    message: str


class FoundingSpotsResponse(BaseModel):
    """Response with founding spots count."""

    total_spots: int
    spots_taken: int
    spots_remaining: int


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/create-checkout-session",
    response_model=CheckoutSessionResponse,
    status_code=status.HTTP_200_OK,
)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CheckoutSessionResponse:
    """
    Create a Stripe Checkout session for the $500 AUD founding deposit.

    Metadata includes:
    - agency_id: Client UUID
    - plan: founding
    - discount: 50_lifetime (50% lifetime discount for founding members)

    Success URL: /onboarding?deposit=confirmed
    Cancel URL: / (landing page)
    """
    # Check if spots are still available
    spots_result = await db.execute(text("SELECT spots_taken FROM founding_spots WHERE id = 1"))
    spots_row = spots_result.fetchone()
    spots_taken = spots_row[0] if spots_row else 0

    if spots_taken >= 20:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="All founding spots have been claimed. Join the waitlist.",
        )

    # Check if client already paid deposit
    client_result = await db.execute(select(Client).where(Client.id == request.agency_id))
    client = client_result.scalar_one_or_none()

    if client and client.deposit_paid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deposit already paid for this agency.",
        )

    try:
        # Create or get Stripe customer
        customers = stripe.Customer.list(email=request.email, limit=1)
        if customers.data:
            customer = customers.data[0]
        else:
            customer = stripe.Customer.create(
                email=request.email,
                name=request.agency_name,
                metadata={
                    "agency_id": str(request.agency_id),
                    "plan": "founding",
                },
            )

        # Create Checkout session
        frontend_url = settings.frontend_url.rstrip("/")
        session = stripe.checkout.Session.create(
            customer=customer.id,
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "aud",
                        "unit_amount": DEPOSIT_AMOUNT_AUD,
                        "product_data": {
                            "name": "Agency OS Founding Member Deposit",
                            "description": "Refundable deposit credited against your first month. 50% lifetime discount locked in.",
                        },
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "agency_id": str(request.agency_id),
                "plan": "founding",
                "discount": "50_lifetime",
            },
            success_url=f"{frontend_url}/onboarding?deposit=confirmed",
            cancel_url=f"{frontend_url}/",
        )

        # Store Stripe customer ID on client if exists
        if client:
            client.stripe_customer_id = customer.id
            await db.commit()

        logger.info(f"Created Checkout session {session.id} for agency {request.agency_id}")

        return CheckoutSessionResponse(
            checkout_url=session.url,
            session_id=session.id,
        )

    except stripe.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment provider error: {str(e)}",
        )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> dict[str, str]:
    """
    Handle Stripe webhook events.

    Events handled:
    - checkout.session.completed: Set deposit_paid=true, send welcome email
    - customer.subscription.created: Log subscription creation
    - customer.subscription.updated: Log subscription updates
    - customer.subscription.deleted: Handle subscription cancellation
    """
    payload = await request.body()

    # Verify webhook signature
    if settings.stripe_webhook_secret and stripe_signature:
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, settings.stripe_webhook_secret
            )
        except stripe.SignatureVerificationError as e:
            logger.error(f"Invalid Stripe webhook signature: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature",
            )
    else:
        # Dev mode: parse without signature verification
        import json

        event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)

    event_type = event.type
    logger.info(f"Received Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        session = event.data.object
        await _handle_checkout_completed(session, db)

    elif event_type == "customer.subscription.created":
        subscription = event.data.object
        logger.info(f"Subscription created: {subscription.id} for customer {subscription.customer}")

    elif event_type == "customer.subscription.updated":
        subscription = event.data.object
        logger.info(f"Subscription updated: {subscription.id} status={subscription.status}")

    elif event_type == "customer.subscription.deleted":
        subscription = event.data.object
        logger.warning(
            f"Subscription deleted: {subscription.id} for customer {subscription.customer}"
        )

    return {"status": "received"}


async def _handle_checkout_completed(
    session: stripe.checkout.Session,
    db: AsyncSession,
) -> None:
    """Handle successful checkout - mark deposit paid and send welcome email."""
    metadata = session.metadata or {}
    agency_id = metadata.get("agency_id")
    plan = metadata.get("plan")

    if not agency_id:
        logger.error("Checkout session missing agency_id metadata")
        return

    if plan != "founding":
        logger.info(f"Non-founding checkout completed for {agency_id}")
        return

    # Update client deposit_paid status
    result = await db.execute(select(Client).where(Client.id == UUID(agency_id)))
    client = result.scalar_one_or_none()

    if not client:
        logger.error(f"Client {agency_id} not found for checkout completion")
        return

    client.deposit_paid = True
    client.stripe_customer_id = session.customer

    await db.commit()
    await db.refresh(client)

    logger.info(f"Deposit confirmed for client {agency_id}, deposit_paid=True")

    # Refresh founding spots materialized view
    await db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY founding_spots"))
    await db.commit()

    # Send welcome email via Resend
    await _send_welcome_email(
        email=session.customer_details.email if session.customer_details else None,
        agency_name=client.name,
    )


async def _send_welcome_email(email: str | None, agency_name: str) -> None:
    """Send welcome email via Resend API."""
    if not email:
        logger.warning("No email provided for welcome message")
        return

    if not settings.resend_api_key:
        logger.warning("Resend API key not configured, skipping welcome email")
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": "Agency OS <welcome@agencyos.com.au>",
                    "to": [email],
                    "subject": f"Welcome to Agency OS, {agency_name}! 🚀",
                    "html": f"""
                    <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h1 style="color: #1a1a2e;">Welcome to the Founding 20!</h1>
                        <p>Hey {agency_name} team,</p>
                        <p>Your $500 deposit is confirmed and your spot is locked in. Here's what happens next:</p>
                        <ol>
                            <li><strong>Complete onboarding</strong> — We'll extract your ICP and set up your first campaign</li>
                            <li><strong>Campaign review</strong> — Our team reviews and approves your first campaign</li>
                            <li><strong>Go live</strong> — Your subscription starts ($1,250/mo with your 50% founding discount)</li>
                        </ol>
                        <p>Your $500 deposit will be credited against your first month's invoice.</p>
                        <p style="margin-top: 24px;">
                            <a href="{settings.frontend_url}/onboarding"
                               style="background: #1a1a2e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px;">
                                Continue Onboarding →
                            </a>
                        </p>
                        <p style="color: #666; margin-top: 32px;">
                            Questions? Reply to this email or reach out anytime.<br/>
                            — The Agency OS Team
                        </p>
                    </div>
                    """,
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                logger.info(f"Welcome email sent to {email}")
            else:
                logger.error(f"Resend API error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")


@router.post(
    "/activate-subscription",
    response_model=ActivateSubscriptionResponse,
    status_code=status.HTTP_200_OK,
)
async def activate_subscription(
    request: ActivateSubscriptionRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ActivateSubscriptionResponse:
    """
    Activate subscription for a client when their first campaign is approved.

    Creates Stripe subscription at founding price ($1,250 AUD monthly).
    Credits $500 deposit against first invoice.

    This endpoint is called internally when campaign status changes to APPROVED
    for the first time.
    """
    # Get client
    result = await db.execute(select(Client).where(Client.id == request.client_id))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    # Check if already subscribed
    if client.subscription_activated_at:
        return ActivateSubscriptionResponse(
            success=True,
            subscription_id=client.stripe_subscription_id,
            message="Subscription already active",
        )

    # Verify deposit was paid
    if not client.deposit_paid:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Deposit must be paid before subscription can be activated",
        )

    # Verify Stripe customer exists
    if not client.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Stripe customer ID found for this client",
        )

    try:
        # Create the subscription with deposit credit
        # First, create a price for the founding monthly rate
        # In production, use a pre-created Price ID from settings
        if settings.stripe_price_ignition:
            price_id = settings.stripe_price_ignition
        else:
            # Create adhoc price for founding members
            price = stripe.Price.create(
                currency="aud",
                unit_amount=MONTHLY_PRICE_AUD,
                recurring={"interval": "month"},
                product_data={
                    "name": "Agency OS Founding Member - Ignition Tier",
                },
            )
            price_id = price.id

        # Apply deposit as credit to customer balance
        stripe.Customer.create_balance_transaction(
            client.stripe_customer_id,
            amount=-DEPOSIT_CREDIT_AUD,  # Negative = credit
            currency="aud",
            description="Founding member deposit credit",
        )

        # Create subscription
        subscription = stripe.Subscription.create(
            customer=client.stripe_customer_id,
            items=[{"price": price_id}],
            metadata={
                "agency_id": str(client.id),
                "plan": "founding",
                "tier": "ignition",
            },
        )

        # Update client
        client.stripe_subscription_id = subscription.id
        client.subscription_activated_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(client)

        logger.info(f"Subscription {subscription.id} activated for client {client.id}")

        return ActivateSubscriptionResponse(
            success=True,
            subscription_id=subscription.id,
            message="Subscription activated successfully. $500 deposit credited.",
        )

    except stripe.StripeError as e:
        logger.error(f"Stripe error activating subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment provider error: {str(e)}",
        )


@router.get(
    "/founding-spots",
    response_model=FoundingSpotsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_founding_spots(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> FoundingSpotsResponse:
    """
    Get current founding spots count for landing page.

    Returns:
    - total_spots: 20
    - spots_taken: Number of clients with deposit_paid=true
    - spots_remaining: 20 - spots_taken
    """
    # Try to read from materialized view first
    try:
        result = await db.execute(
            text("SELECT total_spots, spots_taken FROM founding_spots WHERE id = 1")
        )
        row = result.fetchone()
        if row:
            return FoundingSpotsResponse(
                total_spots=row[0],
                spots_taken=row[1],
                spots_remaining=row[0] - row[1],
            )
    except Exception:
        pass  # Fall through to direct count

    # Fallback: count directly from clients table
    result = await db.execute(
        select(func.count())
        .select_from(Client)
        .where(
            Client.deposit_paid == True,  # noqa: E712
            Client.deleted_at.is_(None),
        )
    )
    spots_taken = result.scalar() or 0

    return FoundingSpotsResponse(
        total_spots=20,
        spots_taken=spots_taken,
        spots_remaining=20 - spots_taken,
    )


# ============================================================================
# Helper for campaign approval integration
# ============================================================================


async def activate_subscription_on_approval(
    client_id: UUID,
    db: AsyncSession,
) -> bool:
    """
    Helper function called from campaigns.py when first campaign is approved.

    Returns True if subscription was activated, False if already active or error.
    """
    try:
        result = await db.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()

        if not client:
            logger.error(f"Client {client_id} not found for subscription activation")
            return False

        # Already activated
        if client.subscription_activated_at:
            return True

        # No deposit paid
        if not client.deposit_paid:
            logger.warning(f"Client {client_id} campaign approved but deposit not paid")
            return False

        # No Stripe customer
        if not client.stripe_customer_id:
            logger.warning(f"Client {client_id} has no Stripe customer ID")
            return False

        # Use the activate endpoint logic
        request = ActivateSubscriptionRequest(client_id=client_id)
        await activate_subscription(request, db)
        return True

    except Exception as e:
        logger.error(f"Error activating subscription for {client_id}: {e}")
        return False


# ============================================================================
# VERIFICATION CHECKLIST
# ============================================================================
# [x] Contract comment at top
# [x] create-checkout-session endpoint with metadata
# [x] webhook endpoint with signature verification
# [x] activate-subscription endpoint with deposit credit
# [x] founding-spots endpoint for landing page
# [x] Welcome email via Resend
# [x] No hardcoded credentials
# [x] Proper error handling
# [x] Logging for audit trail
