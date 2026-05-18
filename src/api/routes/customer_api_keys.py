"""
FILE: src/api/routes/customer_api_keys.py
PURPOSE: BYO customer API key entry endpoint — KEI-155 (KEI-113B).

Wraps src.security.customer_api_keys.store_key() behind an authenticated
POST /api/v1/dispatcher/byo-key.

Plaintext NEVER persisted. The route accepts the plaintext key in the request
body, hands it directly to store_key() (which pgp_sym_encrypts via pgcrypto
and stores ciphertext + SHA-256 lookup_hash), and discards the plaintext.

customer_id is the authenticated user's id. The customer_api_keys.customer_id
column has no FK constraint per KEI-116A migration — the intent is "the
authenticated principal who owns this key", which for the dispatcher BYO
self-onboarding flow is the auth user itself.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import CurrentUser, get_current_user_from_token
from src.security import customer_api_keys as keys_service

router = APIRouter(prefix="/dispatcher", tags=["dispatcher"])


class ByoKeyRequest(BaseModel):
    provider: Literal["anthropic", "openai"] = Field(
        ..., description="LLM provider — anthropic or openai only"
    )
    plaintext: str = Field(
        ..., min_length=8, description="Customer API key (plaintext, in transit only)"
    )


class ByoKeyResponse(BaseModel):
    id: str = Field(..., description="UUID of the stored customer_api_keys row")
    provider: str = Field(..., description="Provider echoed for confirmation")


@router.post("/byo-key", status_code=status.HTTP_201_CREATED)
async def store_byo_key(
    body: ByoKeyRequest,
    user: Annotated[CurrentUser, Depends(get_current_user_from_token)],
) -> ByoKeyResponse:
    """Encrypt + store a customer-supplied LLM API key.

    On success the plaintext is dropped (not logged, not returned).
    Raises 500 if CUSTOMER_KEY_ENCRYPTION_KEY env var is unset on the server.
    """
    try:
        row_id = keys_service.store_key(
            customer_id=user.id,
            provider=body.provider,
            plaintext=body.plaintext,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"key storage misconfigured: {exc}",
        ) from exc
    return ByoKeyResponse(id=str(row_id), provider=body.provider)
