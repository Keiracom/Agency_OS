"""src/integrations/pipedrive_client.py — Pipedrive CRM REST client (v2).

Directive: first CRM integration — Pipedrive MVP endpoints.
Skill spec: skills/pipedrive/SKILL.md (ratified 2026-05-06).

LAW XII: This module is the CANONICAL interface to Pipedrive. Direct httpx calls
to Pipedrive outside this module are forbidden. All callers must go through
the skill (skills/pipedrive/SKILL.md) which wraps this module.

LAW XIII: Any change to Pipedrive call patterns must update skills/pipedrive/SKILL.md
in the same PR.

STATUS GUARD:
  API token NOT provisioned per tenant — do NOT call until per-tenant
  PIPEDRIVE_API_TOKEN is configured. See skills/pipedrive/SKILL.md.
  Verify token first via verify_token() during tenant onboarding; block all
  writes on non-200 response.

MVP endpoints implemented:
  - verify_token         GET  /users/me
  - search_person_by_email GET /persons/search
  - create_person        POST /persons
  - update_person        PATCH /persons/{id}
  - create_deal          POST /deals

Deferred to v2 (not in scope):
  - Activities, Notes, Organisations, Leads, personFields cache,
    webhooks-subscription CRUD — see skill spec.
"""

from __future__ import annotations

import base64
import hmac
import logging
import os
import re
import time

import httpx

LOGGER = logging.getLogger(__name__)

# ── Status guard ──────────────────────────────────────────────────────────────
__status__ = (
    "NOT_PROVISIONED — PIPEDRIVE_API_TOKEN not set per tenant. "
    "Do NOT call until configured. See skills/pipedrive/SKILL.md."
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_AU_PHONE_RE = re.compile(r"^\+61\d{9}$")
_REQUEST_TIMEOUT = 20.0  # seconds


class BudgetError(RuntimeError):
    """Raised when the tenant has exceeded their Pipedrive plan limits (402)."""


# ── Low-level helpers ─────────────────────────────────────────────────────────


def _dsn_base(company_domain: str) -> str:
    """Assemble the per-tenant v2 base URL. Raises ValueError on empty domain."""
    if not company_domain or not company_domain.strip():
        raise ValueError("company_domain must not be empty")
    return f"https://{company_domain.strip()}.pipedrive.com/api/v2"


def _api_token() -> str:
    """Read PIPEDRIVE_API_TOKEN from env. Returns '' if unset; callers handle 401."""
    return os.environ.get("PIPEDRIVE_API_TOKEN", "")


def _request(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
) -> dict | None:
    """httpx.Client wrapper. x-api-token header; 429 backoff 1s/2s/4s; 5xx retry once.

    Returns parsed dict or None on 404. Raises ValueError(400), PermissionError(401/403),
    BudgetError(402), RuntimeError(410/exhausted). Logs at INFO with [pipedrive] prefix.
    """
    token = _api_token()
    headers = {"x-api-token": token, "Content-Type": "application/json"}

    LOGGER.info("[pipedrive] %s %s", method, path)

    backoff_delays = [1, 2, 4]
    last_exc: Exception | None = None

    for attempt in range(4):  # initial + up to 3 retries for 429
        try:
            with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
                response = client.request(
                    method,
                    path,
                    headers=headers,
                    params=params,
                    json=json_body,
                )
        except httpx.RequestError as exc:
            LOGGER.error("[pipedrive] request error %s %s: %s", method, path, exc)
            raise

        status = response.status_code

        if status in (200, 201):
            return response.json()

        if status == 400:
            LOGGER.error("[pipedrive] 400 caller_error %s: %s", path, response.text)
            raise ValueError(f"[pipedrive] 400 bad request: {response.text}")

        if status == 401:
            LOGGER.error("[pipedrive] 401 auth_error %s", path)
            raise PermissionError(f"[pipedrive] 401 invalid/revoked API token: {path}")

        if status == 402:
            LOGGER.error("[pipedrive] 402 budget_error %s", path)
            raise BudgetError(f"[pipedrive] 402 plan limit or trial lapsed: {path}")

        if status == 403:
            LOGGER.error("[pipedrive] 403 permission_error %s", path)
            raise PermissionError(f"[pipedrive] 403 forbidden: {path}")

        if status == 404:
            LOGGER.info("[pipedrive] 404 not_found %s", path)
            return None

        if status == 410:
            msg = f"[pipedrive] 410 v1 sunset endpoint reached — check for v1 URL: {path}"
            LOGGER.error(msg)
            raise RuntimeError(msg)

        if status == 429:
            if attempt < 3:
                delay = backoff_delays[attempt]
                LOGGER.warning(
                    "[pipedrive] 429 rate_limit, backoff %ds (attempt %d)", delay, attempt + 1
                )
                time.sleep(delay)
                last_exc = RuntimeError(f"[pipedrive] 429 rate limit after {attempt + 1} attempts")
                continue
            raise RuntimeError(f"[pipedrive] 429 rate limit — exhausted retries: {path}")

        if status >= 500:
            if attempt == 0:
                LOGGER.warning("[pipedrive] %d transient error %s, retry after 5s", status, path)
                time.sleep(5)
                continue
            LOGGER.error("[pipedrive] %d persistent server error %s", status, path)
            raise RuntimeError(f"[pipedrive] {status} server error: {path}")

        LOGGER.error("[pipedrive] unexpected status %d %s", status, path)
        raise RuntimeError(f"[pipedrive] unexpected status {status}: {path}")

    raise RuntimeError(f"[pipedrive] request failed after retries: {path}") from last_exc


# ── Public API ─────────────────────────────────────────────────────────────────


def verify_token(company_domain: str) -> dict | None:
    """Verify API token — call during tenant onboarding only, not per request.

    Returns user dict on success, None on any failure (catches all exceptions).
    """
    try:
        base = _dsn_base(company_domain)
        result = _request("GET", f"{base}/users/me")
        if result and "data" in result:
            return result["data"]
        return result
    except (PermissionError, BudgetError, RuntimeError, ValueError) as exc:
        LOGGER.warning("[pipedrive] verify_token failed: %s", exc)
        return None


def search_person_by_email(company_domain: str, email: str) -> dict | None:
    """Find existing Person by email (exact match). Returns first hit or None."""
    base = _dsn_base(company_domain)
    result = _request(
        "GET",
        f"{base}/persons/search",
        params={"term": email, "fields": "email", "exact_match": "true"},
    )
    if not result:
        return None
    items = result.get("data", {}).get("items", [])
    if not items:
        return None
    return items[0].get("item")


def create_person(
    company_domain: str,
    *,
    name: str,
    email: str,
    phone: str | None = None,
    owner_id: int,
    custom_fields: dict | None = None,
) -> dict:
    """Create Person from BU row. Validates name (≤120), email regex, AU phone E.164.

    Raises ValueError on any validation failure.
    """
    name = name.strip() if name else ""
    if not name:
        raise ValueError("[pipedrive] create_person: name must not be empty")
    if len(name) > 120:
        raise ValueError(f"[pipedrive] create_person: name exceeds 120 chars ({len(name)})")
    if not _EMAIL_RE.match(email):
        raise ValueError(f"[pipedrive] create_person: invalid email format: {email!r}")
    if phone is not None and not _AU_PHONE_RE.match(phone):
        raise ValueError(
            f"[pipedrive] create_person: phone must be AU E.164 (^\\+61\\d{{9}}$), got: {phone!r}"
        )

    if custom_fields:
        reserved = {"name", "email", "phone", "owner_id"} & custom_fields.keys()
        if reserved:
            raise ValueError(
                f"[pipedrive] create_person: custom_fields cannot include reserved "
                f"structural keys {sorted(reserved)}. Use the named arguments instead."
            )

    body: dict = {
        "name": name,
        "email": [{"value": email, "primary": True, "label": "work"}],
        "owner_id": owner_id,
    }
    if phone is not None:
        body["phone"] = [{"value": phone, "primary": True, "label": "work"}]
    if custom_fields:
        body.update(custom_fields)

    base = _dsn_base(company_domain)
    result = _request("POST", f"{base}/persons", json_body=body)
    data = result.get("data") if result else None
    return data if data is not None else result


def update_person(company_domain: str, person_id: int, **fields) -> dict:
    """PATCH an existing Person. Pass fields as kwargs; returns updated person dict."""
    base = _dsn_base(company_domain)
    result = _request("PATCH", f"{base}/persons/{person_id}", json_body=fields)
    data = result.get("data") if result else None
    return data if data is not None else result


def create_deal(
    company_domain: str,
    *,
    title: str,
    value: int | float,
    stage_id: int,
    person_id: int,
    pipeline_id: int,
) -> dict:
    """Create Deal. Currency hardcoded AUD (LAW II). Raises ValueError: title>255 or value<=0."""
    if len(title) > 255:
        raise ValueError(f"[pipedrive] create_deal: title exceeds 255 chars ({len(title)})")
    if value <= 0:
        raise ValueError(f"[pipedrive] create_deal: value must be > 0 (AUD), got {value}")

    body = {
        "title": title,
        "value": value,
        "currency": "AUD",  # LAW II — hardcoded, no other currency accepted
        "stage_id": stage_id,
        "person_id": person_id,
        "pipeline_id": pipeline_id,
    }
    base = _dsn_base(company_domain)
    result = _request("POST", f"{base}/deals", json_body=body)
    data = result.get("data") if result else None
    return data if data is not None else result


def verify_webhook_basic_auth(
    auth_header: str | None,
    expected_secret: str,
) -> bool:
    """Verify 'Authorization: Basic <b64>' header against per-tenant secret.

    Constant-time compare on password component. Returns False on any malformed input.
    """
    if not auth_header or not expected_secret:
        return False

    try:
        scheme, _, encoded = auth_header.strip().partition(" ")
        if scheme.lower() != "basic" or not encoded:
            return False
        decoded = base64.b64decode(encoded.strip()).decode("utf-8")
        # Format is "user:password" — password is the secret we care about
        _user, _, password = decoded.partition(":")
        return hmac.compare_digest(password, expected_secret)
    except Exception:
        return False
