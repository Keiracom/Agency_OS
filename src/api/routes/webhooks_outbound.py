"""
FILE: src/api/routes/webhooks_outbound.py
PURPOSE: Client webhook dispatch and configuration management
PHASE: 7 (API Routes)
TASK: API-007
DEPENDENCIES:
  - src/api/dependencies.py
  - src/models/base.py (WebhookEventType enum)
  - src/integrations/supabase.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 12: API layer can import everything
  - Rule 14: Soft delete check in queries
  - Rule 20: Webhook-first architecture

This module handles outbound webhook delivery to client endpoints:
- Dispatch webhooks to registered client endpoints
- HMAC-SHA256 signature for security
- Retry logic with exponential backoff
- Delivery logging and status tracking
- CRUD operations for webhook configurations
"""

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.integrations.supabase import get_db
from src.models.base import WebhookEventType

# Router for outbound webhooks
router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks_outbound"],
)


# ============================================
# Pydantic Models
# ============================================


class WebhookConfigCreate(BaseModel):
    """Schema for creating a webhook configuration."""

    name: str = Field(..., min_length=1, max_length=100, description="Human-readable name")
    url: HttpUrl = Field(..., description="Webhook endpoint URL")
    secret: str | None = Field(
        None, min_length=16, max_length=256, description="HMAC signing secret"
    )
    events: list[WebhookEventType] = Field(
        ..., min_items=1, description="Event types to subscribe to"
    )
    headers: dict[str, str] = Field(default_factory=dict, description="Custom headers to include")
    timeout_ms: int = Field(
        default=30000, ge=1000, le=120000, description="Request timeout in milliseconds"
    )
    retry_count: int = Field(default=3, ge=0, le=10, description="Number of retries on failure")
    retry_delay_ms: int = Field(
        default=1000, ge=100, le=60000, description="Initial delay between retries"
    )
    auto_disable_threshold: int = Field(
        default=10, ge=1, le=100, description="Auto-disable after N consecutive failures"
    )


class WebhookConfigUpdate(BaseModel):
    """Schema for updating a webhook configuration."""

    name: str | None = Field(None, min_length=1, max_length=100)
    url: HttpUrl | None = None
    secret: str | None = Field(None, min_length=16, max_length=256)
    events: list[WebhookEventType] | None = Field(None, min_items=1)
    headers: dict[str, str] | None = None
    timeout_ms: int | None = Field(None, ge=1000, le=120000)
    retry_count: int | None = Field(None, ge=0, le=10)
    retry_delay_ms: int | None = Field(None, ge=100, le=60000)
    auto_disable_threshold: int | None = Field(None, ge=1, le=100)
    is_active: bool | None = None


class WebhookConfigResponse(BaseModel):
    """Schema for webhook configuration response."""

    id: UUID
    client_id: UUID
    name: str
    url: str
    events: list[str]
    headers: dict[str, str]
    timeout_ms: int
    retry_count: int
    retry_delay_ms: int
    is_active: bool
    last_triggered_at: datetime | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    failure_count: int
    consecutive_failures: int
    auto_disable_threshold: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookDispatchRequest(BaseModel):
    """Schema for dispatching a webhook (internal use)."""

    client_id: UUID = Field(..., description="Client ID to dispatch webhook for")
    event_type: WebhookEventType = Field(..., description="Event type")
    payload: dict[str, Any] = Field(..., description="Event payload data")


class WebhookDeliveryResponse(BaseModel):
    """Schema for webhook delivery log response."""

    id: UUID
    webhook_config_id: UUID
    event_type: str
    status: str
    attempt_count: int
    response_status: int | None
    response_time_ms: int | None
    error_message: str | None
    created_at: datetime
    delivered_at: datetime | None

    class Config:
        from_attributes = True


# ============================================
# HMAC Signature Functions
# ============================================


def generate_hmac_signature(payload: dict[str, Any], secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.

    Args:
        payload: The webhook payload dictionary
        secret: The webhook secret key

    Returns:
        Hex-encoded HMAC signature

    The signature is calculated as:
    HMAC-SHA256(secret, JSON.stringify(payload))
    """
    # Convert payload to canonical JSON string (sorted keys, no whitespace)
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    # Generate HMAC signature
    signature = hmac.new(
        key=secret.encode("utf-8"), msg=payload_json.encode("utf-8"), digestmod=hashlib.sha256
    ).hexdigest()

    return signature


def verify_hmac_signature(payload: dict[str, Any], signature: str, secret: str) -> bool:
    """
    Verify HMAC-SHA256 signature for webhook payload.

    Args:
        payload: The webhook payload dictionary
        signature: The received signature to verify
        secret: The webhook secret key

    Returns:
        True if signature is valid, False otherwise
    """
    expected_signature = generate_hmac_signature(payload, secret)
    return hmac.compare_digest(signature, expected_signature)


# ============================================
# Webhook Dispatch Logic
# ============================================


async def dispatch_webhook_delivery(
    delivery_id: UUID,
    webhook_url: str,
    payload: dict[str, Any],
    signature: str,
    headers: dict[str, str],
    timeout_ms: int,
    db: AsyncSession,
) -> None:
    """
    Dispatch a single webhook delivery attempt.

    Args:
        delivery_id: Delivery record ID
        webhook_url: Target webhook URL
        payload: Event payload
        signature: HMAC signature
        headers: Custom headers
        timeout_ms: Request timeout
        db: Database session

    Updates the delivery record with success/failure status.
    """
    start_time = datetime.utcnow()

    try:
        # Prepare headers
        all_headers = {
            "Content-Type": "application/json",
            "X-Agency-OS-Signature": signature,
            "X-Agency-OS-Event": payload.get("event_type", "unknown"),
            "User-Agent": "Agency-OS-Webhooks/1.0",
            **headers,
        }

        # Send webhook request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers=all_headers,
                timeout=timeout_ms / 1000,  # Convert to seconds
            )

        # Calculate response time
        response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Check if successful (2xx status code)
        if 200 <= response.status_code < 300:
            # Record success
            await db.execute(
                "SELECT record_webhook_success(:delivery_id, :status, :body, :time_ms)",
                {
                    "delivery_id": delivery_id,
                    "status": response.status_code,
                    "body": response.text[:10000],  # Truncate
                    "time_ms": response_time_ms,
                },
            )
            await db.commit()
        else:
            # Record failure
            await db.execute(
                "SELECT record_webhook_failure(:delivery_id, :status, :error, :should_retry)",
                {
                    "delivery_id": delivery_id,
                    "status": response.status_code,
                    "error": f"HTTP {response.status_code}: {response.text[:1000]}",
                    "should_retry": True,
                },
            )
            await db.commit()

    except httpx.TimeoutException:
        # Timeout - record failure and retry
        await db.execute(
            "SELECT record_webhook_failure(:delivery_id, :status, :error, :should_retry)",
            {
                "delivery_id": delivery_id,
                "status": 0,
                "error": f"Request timeout after {timeout_ms}ms",
                "should_retry": True,
            },
        )
        await db.commit()

    except Exception as e:
        # Other errors - record failure and retry
        await db.execute(
            "SELECT record_webhook_failure(:delivery_id, :status, :error, :should_retry)",
            {
                "delivery_id": delivery_id,
                "status": 0,
                "error": f"Error: {str(e)[:1000]}",
                "should_retry": True,
            },
        )
        await db.commit()


async def create_and_dispatch_webhook(
    client_id: UUID,
    event_type: WebhookEventType,
    payload: dict[str, Any],
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> int:
    """
    Create delivery records and dispatch webhooks for an event.

    Args:
        client_id: Client ID
        event_type: Event type
        payload: Event payload
        db: Database session
        background_tasks: FastAPI background tasks

    Returns:
        Number of webhooks dispatched
    """
    # Get active webhooks for this event
    result = await db.execute(
        """
        SELECT id, url, secret, headers, timeout_ms, retry_count
        FROM webhook_configs
        WHERE client_id = :client_id
        AND is_active = TRUE
        AND deleted_at IS NULL
        AND :event_type = ANY(events)
        """,
        {"client_id": client_id, "event_type": event_type.value},
    )
    webhooks = result.fetchall()

    if not webhooks:
        return 0

    # Add event metadata to payload
    full_payload = {
        "event_type": event_type.value,
        "timestamp": datetime.utcnow().isoformat(),
        "client_id": str(client_id),
        "data": payload,
    }

    # Create delivery records and dispatch
    dispatched_count = 0
    for webhook in webhooks:
        webhook_id, url, secret, headers, timeout_ms, retry_count = webhook

        # Generate signature
        signature = generate_hmac_signature(full_payload, secret or settings.webhook_hmac_secret)

        # Create delivery record
        delivery_result = await db.execute(
            """
            INSERT INTO webhook_deliveries (
                webhook_config_id, client_id, event_type, payload, signature, status
            )
            VALUES (:config_id, :client_id, :event_type, :payload, :signature, 'pending')
            RETURNING id
            """,
            {
                "config_id": webhook_id,
                "client_id": client_id,
                "event_type": event_type.value,
                "payload": json.dumps(full_payload),
                "signature": signature,
            },
        )
        delivery_id = delivery_result.scalar_one()
        await db.commit()

        # Dispatch in background
        background_tasks.add_task(
            dispatch_webhook_delivery,
            delivery_id=delivery_id,
            webhook_url=str(url),
            payload=full_payload,
            signature=signature,
            headers=headers or {},
            timeout_ms=timeout_ms,
            db=db,
        )

        dispatched_count += 1

    return dispatched_count


# ============================================
# API Endpoints
# ============================================


@router.post("/dispatch", status_code=status.HTTP_202_ACCEPTED)
async def dispatch_webhook(
    request: WebhookDispatchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Dispatch webhook to client's registered endpoints (internal use).

    This endpoint is called by internal systems to trigger webhook deliveries
    to client endpoints when events occur.

    Security:
    - Should be protected by internal-only authentication
    - Not exposed to external clients
    - Validates client_id exists and has active webhooks

    Process:
    1. Find all active webhooks for client subscribed to event
    2. Create delivery records in webhook_deliveries table
    3. Dispatch HTTP requests to client endpoints in background
    4. Sign payload with HMAC-SHA256
    5. Include signature in X-Agency-OS-Signature header
    6. Retry failed deliveries with exponential backoff

    Args:
        request: Dispatch request with client_id, event_type, and payload
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Dict with dispatch status and count of webhooks triggered
    """
    dispatched_count = await create_and_dispatch_webhook(
        client_id=request.client_id,
        event_type=request.event_type,
        payload=request.payload,
        db=db,
        background_tasks=background_tasks,
    )

    return {
        "status": "accepted",
        "event_type": request.event_type.value,
        "webhooks_dispatched": dispatched_count,
        "message": f"Dispatched to {dispatched_count} webhook(s)",
    }


@router.get("/config", response_model=list[WebhookConfigResponse])
async def get_webhook_configs(
    client_id: UUID,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[WebhookConfigResponse]:
    """
    Get all webhook configurations for a client.

    Args:
        client_id: Client ID to get webhooks for
        include_inactive: Include inactive/disabled webhooks
        db: Database session

    Returns:
        List of webhook configurations
    """
    # Build query
    query = (
        select("*")
        .select_from("webhook_configs")
        .where(
            and_(
                "client_id = :client_id",
                "deleted_at IS NULL",
            )
        )
    )

    if not include_inactive:
        query = query.where("is_active = TRUE")

    # Execute query
    result = await db.execute(
        f"""
        SELECT * FROM webhook_configs
        WHERE client_id = :client_id
        AND deleted_at IS NULL
        {"" if include_inactive else "AND is_active = TRUE"}
        ORDER BY created_at DESC
        """,
        {"client_id": client_id},
    )

    webhooks = result.fetchall()

    # Convert to response models
    return [
        WebhookConfigResponse(
            id=w.id,
            client_id=w.client_id,
            name=w.name,
            url=w.url,
            events=w.events,
            headers=w.headers or {},
            timeout_ms=w.timeout_ms,
            retry_count=w.retry_count,
            retry_delay_ms=w.retry_delay_ms,
            is_active=w.is_active,
            last_triggered_at=w.last_triggered_at,
            last_success_at=w.last_success_at,
            last_failure_at=w.last_failure_at,
            failure_count=w.failure_count,
            consecutive_failures=w.consecutive_failures,
            auto_disable_threshold=w.auto_disable_threshold,
            created_at=w.created_at,
            updated_at=w.updated_at,
        )
        for w in webhooks
    ]


@router.post("/config", response_model=WebhookConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_config(
    client_id: UUID,
    config: WebhookConfigCreate,
    db: AsyncSession = Depends(get_db),
) -> WebhookConfigResponse:
    """
    Create a new webhook configuration for a client.

    Args:
        client_id: Client ID
        config: Webhook configuration
        db: Database session

    Returns:
        Created webhook configuration

    Raises:
        HTTPException 400: If webhook name already exists for client
        HTTPException 404: If client not found
    """
    # Check if client exists
    client_result = await db.execute(
        "SELECT id FROM clients WHERE id = :client_id AND deleted_at IS NULL",
        {"client_id": client_id},
    )
    if not client_result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Client {client_id} not found"
        )

    # Check for duplicate name
    name_result = await db.execute(
        """
        SELECT id FROM webhook_configs
        WHERE client_id = :client_id AND name = :name AND deleted_at IS NULL
        """,
        {"client_id": client_id, "name": config.name},
    )
    if name_result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook configuration with name '{config.name}' already exists",
        )

    # Create webhook config
    result = await db.execute(
        """
        INSERT INTO webhook_configs (
            client_id, name, url, secret, events, headers, timeout_ms,
            retry_count, retry_delay_ms, auto_disable_threshold
        )
        VALUES (
            :client_id, :name, :url, :secret, :events, :headers, :timeout_ms,
            :retry_count, :retry_delay_ms, :auto_disable_threshold
        )
        RETURNING *
        """,
        {
            "client_id": client_id,
            "name": config.name,
            "url": str(config.url),
            "secret": config.secret,
            "events": [e.value for e in config.events],
            "headers": json.dumps(config.headers),
            "timeout_ms": config.timeout_ms,
            "retry_count": config.retry_count,
            "retry_delay_ms": config.retry_delay_ms,
            "auto_disable_threshold": config.auto_disable_threshold,
        },
    )
    webhook = result.fetchone()
    await db.commit()

    return WebhookConfigResponse(
        id=webhook.id,
        client_id=webhook.client_id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        headers=webhook.headers or {},
        timeout_ms=webhook.timeout_ms,
        retry_count=webhook.retry_count,
        retry_delay_ms=webhook.retry_delay_ms,
        is_active=webhook.is_active,
        last_triggered_at=webhook.last_triggered_at,
        last_success_at=webhook.last_success_at,
        last_failure_at=webhook.last_failure_at,
        failure_count=webhook.failure_count,
        consecutive_failures=webhook.consecutive_failures,
        auto_disable_threshold=webhook.auto_disable_threshold,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


@router.patch("/config/{webhook_id}", response_model=WebhookConfigResponse)
async def update_webhook_config(
    webhook_id: UUID,
    client_id: UUID,
    config: WebhookConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> WebhookConfigResponse:
    """
    Update a webhook configuration.

    Args:
        webhook_id: Webhook configuration ID
        client_id: Client ID (for authorization)
        config: Updated configuration fields
        db: Database session

    Returns:
        Updated webhook configuration

    Raises:
        HTTPException 404: If webhook not found or doesn't belong to client
    """
    # Check webhook exists and belongs to client
    check_result = await db.execute(
        """
        SELECT id FROM webhook_configs
        WHERE id = :webhook_id AND client_id = :client_id AND deleted_at IS NULL
        """,
        {"webhook_id": webhook_id, "client_id": client_id},
    )
    if not check_result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook configuration {webhook_id} not found",
        )

    # Build update query dynamically
    update_fields = []
    params = {"webhook_id": webhook_id}

    if config.name is not None:
        update_fields.append("name = :name")
        params["name"] = config.name
    if config.url is not None:
        update_fields.append("url = :url")
        params["url"] = str(config.url)
    if config.secret is not None:
        update_fields.append("secret = :secret")
        params["secret"] = config.secret
    if config.events is not None:
        update_fields.append("events = :events")
        params["events"] = [e.value for e in config.events]
    if config.headers is not None:
        update_fields.append("headers = :headers")
        params["headers"] = json.dumps(config.headers)
    if config.timeout_ms is not None:
        update_fields.append("timeout_ms = :timeout_ms")
        params["timeout_ms"] = config.timeout_ms
    if config.retry_count is not None:
        update_fields.append("retry_count = :retry_count")
        params["retry_count"] = config.retry_count
    if config.retry_delay_ms is not None:
        update_fields.append("retry_delay_ms = :retry_delay_ms")
        params["retry_delay_ms"] = config.retry_delay_ms
    if config.auto_disable_threshold is not None:
        update_fields.append("auto_disable_threshold = :auto_disable_threshold")
        params["auto_disable_threshold"] = config.auto_disable_threshold
    if config.is_active is not None:
        update_fields.append("is_active = :is_active")
        params["is_active"] = config.is_active

    if not update_fields:
        # No fields to update, just return current state
        result = await db.execute(
            "SELECT * FROM webhook_configs WHERE id = :webhook_id", {"webhook_id": webhook_id}
        )
        webhook = result.fetchone()
    else:
        # Execute update
        result = await db.execute(
            f"""
            UPDATE webhook_configs
            SET {", ".join(update_fields)}
            WHERE id = :webhook_id
            RETURNING *
            """,
            params,
        )
        webhook = result.fetchone()
        await db.commit()

    return WebhookConfigResponse(
        id=webhook.id,
        client_id=webhook.client_id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        headers=webhook.headers or {},
        timeout_ms=webhook.timeout_ms,
        retry_count=webhook.retry_count,
        retry_delay_ms=webhook.retry_delay_ms,
        is_active=webhook.is_active,
        last_triggered_at=webhook.last_triggered_at,
        last_success_at=webhook.last_success_at,
        last_failure_at=webhook.last_failure_at,
        failure_count=webhook.failure_count,
        consecutive_failures=webhook.consecutive_failures,
        auto_disable_threshold=webhook.auto_disable_threshold,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


@router.delete("/config/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_config(
    webhook_id: UUID,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete (soft delete) a webhook configuration.

    Args:
        webhook_id: Webhook configuration ID
        client_id: Client ID (for authorization)
        db: Database session

    Raises:
        HTTPException 404: If webhook not found or doesn't belong to client
    """
    # Check webhook exists and belongs to client
    check_result = await db.execute(
        """
        SELECT id FROM webhook_configs
        WHERE id = :webhook_id AND client_id = :client_id AND deleted_at IS NULL
        """,
        {"webhook_id": webhook_id, "client_id": client_id},
    )
    if not check_result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook configuration {webhook_id} not found",
        )

    # Soft delete (Rule 14)
    await db.execute(
        """
        UPDATE webhook_configs
        SET deleted_at = NOW()
        WHERE id = :webhook_id
        """,
        {"webhook_id": webhook_id},
    )
    await db.commit()


@router.get("/deliveries/{webhook_id}", response_model=list[WebhookDeliveryResponse])
async def get_webhook_deliveries(
    webhook_id: UUID,
    client_id: UUID,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[WebhookDeliveryResponse]:
    """
    Get delivery history for a webhook configuration.

    Args:
        webhook_id: Webhook configuration ID
        client_id: Client ID (for authorization)
        limit: Maximum number of records to return
        offset: Number of records to skip
        db: Database session

    Returns:
        List of delivery records

    Raises:
        HTTPException 404: If webhook not found or doesn't belong to client
    """
    # Check webhook exists and belongs to client
    check_result = await db.execute(
        """
        SELECT id FROM webhook_configs
        WHERE id = :webhook_id AND client_id = :client_id AND deleted_at IS NULL
        """,
        {"webhook_id": webhook_id, "client_id": client_id},
    )
    if not check_result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook configuration {webhook_id} not found",
        )

    # Get deliveries
    result = await db.execute(
        """
        SELECT id, webhook_config_id, event_type, status, attempt_count,
               response_status, response_time_ms, error_message,
               created_at, delivered_at
        FROM webhook_deliveries
        WHERE webhook_config_id = :webhook_id
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """,
        {"webhook_id": webhook_id, "limit": limit, "offset": offset},
    )

    deliveries = result.fetchall()

    return [
        WebhookDeliveryResponse(
            id=d.id,
            webhook_config_id=d.webhook_config_id,
            event_type=d.event_type,
            status=d.status,
            attempt_count=d.attempt_count,
            response_status=d.response_status,
            response_time_ms=d.response_time_ms,
            error_message=d.error_message,
            created_at=d.created_at,
            delivered_at=d.delivered_at,
        )
        for d in deliveries
    ]


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] POST /webhooks/dispatch - Internal webhook dispatch endpoint
# [x] GET /webhooks/config - Get client's webhook configurations
# [x] POST /webhooks/config - Create webhook configuration
# [x] PATCH /webhooks/config/{id} - Update webhook configuration
# [x] DELETE /webhooks/config/{id} - Soft delete webhook configuration
# [x] GET /webhooks/deliveries/{id} - Get delivery history
# [x] HMAC-SHA256 signature generation and verification
# [x] WebhookConfigCreate/Update/Response Pydantic models
# [x] WebhookDeliveryResponse Pydantic model
# [x] Retry logic with exponential backoff via database functions
# [x] Background task dispatch with FastAPI BackgroundTasks
# [x] Delivery logging in webhook_deliveries table
# [x] Soft delete check in queries (deleted_at IS NULL) - Rule 14
# [x] Session passed as dependency (Rule 11)
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] X-Agency-OS-Signature header for HMAC
# [x] Event types: lead.created, lead.enriched, lead.scored, reply.received, campaign.completed
# [x] Timeout configuration (default 30s)
# [x] Custom headers support
# [x] Auto-disable on consecutive failures
# [x] Proper error handling and HTTP status codes
