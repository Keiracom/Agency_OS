"""KEI-151 (KEI-112B) — Subscription CRUD endpoints + tier-code mapping.

POST   /api/v1/subscriptions          — create
GET    /api/v1/subscriptions/{id}     — fetch
PATCH  /api/v1/subscriptions/{id}     — update tier
DELETE /api/v1/subscriptions/{id}     — soft-cancel (status=canceled)

Tier limits come from src.dispatcher.tier_limits.TIER_LIMITS (KEI-172).
GET response embeds the resolved (limit, window_size_s) so the customer's
frontend can render the tier ceiling without a second round-trip.

Soft-cancel pattern: DELETE marks status='canceled' + canceled_at=NOW().
The partial unique index ``customer_subscriptions_active_per_customer``
allows a new active row to be created after cancellation. Hard DELETE is
not exposed — audit trail preservation is a regulatory requirement.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.dispatcher.tier_limits import TIER_LIMITS, Tier, limits_for

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

_NOT_FOUND_DETAIL = "subscription not found"


class SubscriptionCreate(BaseModel):
    customer_id: UUID
    tier_code: Tier
    paddle_subscription_id: str | None = Field(default=None, max_length=128)


class SubscriptionUpdate(BaseModel):
    tier_code: Tier


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    tier_code: Tier
    paddle_subscription_id: str | None
    status: str
    limit_per_window: int
    window_size_s: int
    created_at: datetime
    updated_at: datetime
    canceled_at: datetime | None


def _row_to_read(row) -> SubscriptionRead:
    """Build a SubscriptionRead from a SQLAlchemy Row, attaching the
    tier's (limit, window) so the response doesn't force another lookup."""
    tier_code: Tier = row.tier_code  # type: ignore[assignment]
    limit, window_size_s = limits_for(tier_code)
    return SubscriptionRead(
        id=row.id,
        customer_id=row.customer_id,
        tier_code=tier_code,
        paddle_subscription_id=row.paddle_subscription_id,
        status=row.status,
        limit_per_window=limit,
        window_size_s=window_size_s,
        created_at=row.created_at,
        updated_at=row.updated_at,
        canceled_at=row.canceled_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    payload: SubscriptionCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SubscriptionRead:
    """Create an active subscription for a customer.

    Returns 409 if the customer already has an active subscription (the
    partial unique index blocks duplicates; cancel the existing one first
    via DELETE /subscriptions/<old-id>).
    """
    if payload.tier_code not in TIER_LIMITS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unknown tier_code: {payload.tier_code!r}",
        )
    try:
        result = await db.execute(
            text(
                """
                INSERT INTO public.customer_subscriptions
                    (customer_id, tier_code, paddle_subscription_id)
                VALUES (:customer_id, :tier_code, :paddle_subscription_id)
                RETURNING id, customer_id, tier_code, paddle_subscription_id,
                          status, created_at, updated_at, canceled_at
                """
            ),
            {
                "customer_id": str(payload.customer_id),
                "tier_code": payload.tier_code,
                "paddle_subscription_id": payload.paddle_subscription_id,
            },
        )
        row = result.one()
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="customer already has an active subscription",
        ) from exc
    return _row_to_read(row)


@router.get("/{subscription_id}")
async def get_subscription(
    subscription_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SubscriptionRead:
    """Fetch a subscription by id, including its tier-derived limits."""
    result = await db.execute(
        text(
            """
            SELECT id, customer_id, tier_code, paddle_subscription_id,
                   status, created_at, updated_at, canceled_at
            FROM public.customer_subscriptions
            WHERE id = :id
            """
        ),
        {"id": str(subscription_id)},
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL)
    return _row_to_read(row)


@router.patch("/{subscription_id}")
async def update_subscription_tier(
    subscription_id: UUID,
    payload: SubscriptionUpdate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SubscriptionRead:
    """Update tier_code on an active subscription. Canceled rows are
    immutable — caller must create a fresh subscription instead.
    """
    if payload.tier_code not in TIER_LIMITS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unknown tier_code: {payload.tier_code!r}",
        )
    result = await db.execute(
        text(
            """
            UPDATE public.customer_subscriptions
            SET tier_code = :tier_code,
                updated_at = NOW()
            WHERE id = :id AND status = 'active'
            RETURNING id, customer_id, tier_code, paddle_subscription_id,
                      status, created_at, updated_at, canceled_at
            """
        ),
        {"id": str(subscription_id), "tier_code": payload.tier_code},
    )
    row = result.one_or_none()
    if row is None:
        # Either id not found or row is canceled — distinguish in the message
        # via a second cheap query.
        check = await db.execute(
            text("SELECT status FROM public.customer_subscriptions WHERE id = :id"),
            {"id": str(subscription_id)},
        )
        existing = check.one_or_none()
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"subscription is {existing.status}, not active — cannot update tier",
        )
    await db.commit()
    return _row_to_read(row)


@router.delete("/{subscription_id}")
async def cancel_subscription(
    subscription_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SubscriptionRead:
    """Soft-cancel: status='canceled', canceled_at=NOW(). Idempotent —
    a second call on an already-canceled row returns the same row with
    no change. Hard DELETE is not exposed (audit trail preservation)."""
    now = datetime.now(UTC)
    result = await db.execute(
        text(
            """
            UPDATE public.customer_subscriptions
            SET status = 'canceled',
                canceled_at = COALESCE(canceled_at, :now),
                updated_at = :now
            WHERE id = :id
            RETURNING id, customer_id, tier_code, paddle_subscription_id,
                      status, created_at, updated_at, canceled_at
            """
        ),
        {"id": str(subscription_id), "now": now},
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL)
    await db.commit()
    return _row_to_read(row)
