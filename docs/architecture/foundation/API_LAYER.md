# API Layer — Agency OS

**Purpose:** FastAPI RESTful API with Supabase Auth, RBAC, and multi-tenancy for lead generation SaaS.
**Status:** IMPLEMENTED
**Last Updated:** 2026-01-21

---

## 1. Overview

The Agency OS API is built on **FastAPI** with async support throughout. It provides RESTful endpoints for managing campaigns, leads, webhooks, reports, and integrations.

### Key Characteristics

| Aspect | Implementation |
|--------|----------------|
| Framework | FastAPI 0.100+ |
| Async | Full async/await support via SQLAlchemy 2.0 |
| Auth | Supabase Auth with JWT validation |
| RBAC | Role-based access via Membership model |
| Multi-tenancy | Client ID isolation on all queries |
| Versioning | `/api/v1/` prefix for all routes |
| Docs | OpenAPI at `/docs` (disabled in production) |

### Middleware Stack (Order of Execution)

1. **RequestLoggingMiddleware** - Logs all requests with timing (outermost)
2. **ClientContextMiddleware** - Initializes client context for multi-tenancy
3. **CORSMiddleware** - Handles cross-origin requests

---

## 2. Code Locations

| File | Purpose |
|------|---------|
| `src/api/main.py` | FastAPI app entry point, middleware, exception handlers |
| `src/api/dependencies.py` | Auth, RBAC, and multi-tenancy dependencies |
| `src/api/routes/health.py` | Health check endpoints (liveness, readiness) |
| `src/api/routes/campaigns.py` | Campaign CRUD operations |
| `src/api/routes/campaign_generation.py` | AI-powered campaign generation from ICP |
| `src/api/routes/leads.py` | Lead management and ALS scoring |
| `src/api/routes/webhooks.py` | Inbound webhooks (Postmark, Twilio, Unipile, Vapi) |
| `src/api/routes/webhooks_outbound.py` | Outbound webhook dispatch and configuration |
| `src/api/routes/reports.py` | Metrics, analytics, and reporting |
| `src/api/routes/admin.py` | Platform admin operations |
| `src/api/routes/onboarding.py` | ICP extraction and client onboarding |
| `src/api/routes/patterns.py` | Conversion Intelligence pattern APIs |
| `src/api/routes/replies.py` | Reply inbox management |
| `src/api/routes/meetings.py` | Meeting tracking and management |
| `src/api/routes/crm.py` | CRM integrations (HubSpot, Pipedrive, Close) |
| `src/api/routes/customers.py` | Customer import and suppression lists |
| `src/api/routes/linkedin.py` | LinkedIn connection via Unipile |
| `src/api/routes/pool.py` | Lead pool management and population |

---

## 3. Authentication

### Supabase Auth + JWT

All authenticated endpoints use Supabase Auth with JWT token validation.

```python
# src/api/dependencies.py

async def get_current_user_from_token(
    authorization: Annotated[Optional[str], Header()] = None,
    db: AsyncSession = Depends(get_db_session),
) -> CurrentUser:
    """
    Extract and validate user from JWT token.

    1. Extract Bearer token from Authorization header
    2. Decode JWT using Supabase JWT secret (HS256)
    3. Extract user_id from 'sub' claim
    4. Look up user in database (with soft delete check)
    5. Return CurrentUser with id, email, full_name, is_platform_admin
    """
```

### Request Flow

```
Request
   │
   ▼
Authorization: Bearer <jwt_token>
   │
   ▼
get_current_user_from_token()
   │
   ├─► Decode JWT (HS256, Supabase JWT secret)
   ├─► Extract user_id from 'sub' claim
   ├─► Query users table (soft delete check)
   │
   ▼
CurrentUser(id, email, full_name, is_platform_admin)
```

### CurrentUser Model

```python
class CurrentUser(BaseModel):
    id: UUID                      # User UUID from Supabase Auth
    email: str                    # User email address
    full_name: Optional[str]      # User full name
    is_platform_admin: bool       # Platform admin flag (default: False)
```

### API Key Authentication (Webhooks)

For webhook endpoints that don't use JWT:

```python
async def verify_api_key(
    x_api_key: Annotated[Optional[str], Header()] = None,
) -> bool:
    """Verify API key for webhook endpoints using HMAC secret."""
```

---

## 4. RBAC (Role-Based Access Control)

### Membership Roles

| Role | Value | Permissions |
|------|-------|-------------|
| OWNER | `owner` | Full access, can delete client |
| ADMIN | `admin` | Full access except delete client |
| MEMBER | `member` | Read/write access to campaigns and leads |
| VIEWER | `viewer` | Read-only access |

### RBAC Dependencies

```python
# Pre-built role dependencies
require_owner = require_role(MembershipRole.OWNER)
require_admin = require_role(MembershipRole.OWNER, MembershipRole.ADMIN)
require_member = require_role(MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.MEMBER)
require_authenticated = Depends(get_current_client)

# Usage in endpoints
@router.post("/campaigns")
async def create_campaign(
    ctx: ClientContext = Depends(require_member),  # Requires member+ role
):
    ...
```

### ClientContext Model

```python
class ClientContext(BaseModel):
    client: Client           # Client object
    membership: Membership   # User's membership in this client
    user: CurrentUser        # Current user

    @property
    def client_id(self) -> UUID: ...

    @property
    def user_id(self) -> UUID: ...

    @property
    def role(self) -> MembershipRole: ...

    def has_role(self, *roles: MembershipRole) -> bool: ...
    def require_role(self, *roles: MembershipRole) -> None: ...
```

### Platform Admin

For system-wide admin operations:

```python
async def require_platform_admin(
    user: CurrentUser = Depends(get_current_user_from_token),
) -> CurrentUser:
    """Require platform admin access for admin-only endpoints."""
    if not user.is_platform_admin:
        raise AuthorizationError("Platform admin access required")
    return user
```

---

## 5. Multi-Tenancy

### Client ID Isolation

Every data query includes `client_id` filtering to ensure data isolation between clients.

```python
async def get_current_client(
    client_id: UUID,
    user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session),
) -> ClientContext:
    """
    Get client context and verify user has access.

    Steps:
    1. Query client by ID (with soft delete check)
    2. Query membership for user + client (with soft delete check)
    3. Verify membership is accepted
    4. Return ClientContext with client, membership, user
    """
```

### Query Pattern

All queries MUST include client_id filtering:

```python
# Correct - includes client_id filter
stmt = select(Lead).where(
    and_(
        Lead.client_id == client.client_id,
        Lead.deleted_at.is_(None),
    )
)

# WRONG - missing client_id filter (multi-tenancy violation)
stmt = select(Lead).where(Lead.deleted_at.is_(None))
```

### Soft Delete Enforcement (Rule 14)

All queries check `deleted_at IS NULL`:

```python
stmt = select(Client).where(
    and_(
        Client.id == client_id,
        Client.deleted_at.is_(None),  # Rule 14: Soft delete check
    )
)
```

---

## 6. Route Summary

### Health Routes (`/api/v1/health`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | Basic health check (returns 200) |
| GET | `/health/ready` | None | Readiness check (database, Redis, Prefect) |
| GET | `/health/live` | None | Liveness check (process alive) |

### Campaign Routes (`/api/v1/campaigns`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/clients/{client_id}/campaigns` | Member | List campaigns for client |
| POST | `/clients/{client_id}/campaigns` | Member | Create new campaign |
| GET | `/clients/{client_id}/campaigns/{campaign_id}` | Member | Get campaign details |
| PATCH | `/clients/{client_id}/campaigns/{campaign_id}` | Member | Update campaign |
| DELETE | `/clients/{client_id}/campaigns/{campaign_id}` | Admin | Soft delete campaign |
| POST | `/clients/{client_id}/campaigns/{campaign_id}/launch` | Admin | Launch campaign |
| POST | `/clients/{client_id}/campaigns/{campaign_id}/pause` | Admin | Pause campaign |

### Campaign Generation Routes (`/api/v1/campaigns`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/clients/{client_id}/campaigns/generate` | Member | Generate campaign from ICP |
| GET | `/clients/{client_id}/campaigns/templates` | Member | List available templates |

### Lead Routes (`/api/v1/leads`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/clients/{client_id}/leads` | Member | List leads with filtering |
| POST | `/clients/{client_id}/leads` | Member | Create new lead |
| GET | `/clients/{client_id}/leads/{lead_id}` | Member | Get lead details |
| PATCH | `/clients/{client_id}/leads/{lead_id}` | Member | Update lead |
| DELETE | `/clients/{client_id}/leads/{lead_id}` | Admin | Soft delete lead |
| POST | `/clients/{client_id}/leads/{lead_id}/enrich` | Member | Trigger lead enrichment |
| POST | `/clients/{client_id}/leads/{lead_id}/score` | Member | Recalculate ALS score |

### Onboarding Routes (`/api/v1/onboarding`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/onboarding/analyze` | User | Start ICP extraction job |
| GET | `/onboarding/status/{job_id}` | User | Get job status |
| GET | `/onboarding/result/{job_id}` | User | Get extraction result |
| POST | `/onboarding/confirm` | User | Confirm and save ICP |
| GET | `/clients/{client_id}/icp` | Member | Get client's ICP profile |
| PUT | `/clients/{client_id}/icp` | Admin | Update ICP profile |

### Reports Routes (`/api/v1/reports`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/reports/campaigns/{campaign_id}` | Member | Campaign metrics summary |
| GET | `/reports/campaigns/{campaign_id}/daily` | Member | Daily campaign metrics |
| GET | `/reports/clients/{client_id}` | Member | Client-wide metrics |
| GET | `/reports/leads/distribution` | Member | ALS tier distribution |
| GET | `/reports/leads/{lead_id}/engagement` | Member | Lead engagement history |
| GET | `/reports/activity/daily` | Member | Daily activity summary |
| GET | `/reports/pool/analytics` | Member | Lead pool analytics |

### Reply Routes (`/api/v1`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/clients/{client_id}/replies` | Member | List reply inbox |
| GET | `/clients/{client_id}/replies/{reply_id}` | Member | Get reply details |
| PATCH | `/clients/{client_id}/replies/{reply_id}/handled` | Member | Mark reply as handled |

### Meeting Routes (`/api/v1`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/clients/{client_id}/meetings` | Member | List meetings |
| GET | `/clients/{client_id}/meetings/{meeting_id}` | Member | Get meeting details |
| POST | `/clients/{client_id}/meetings` | Member | Create meeting |
| PATCH | `/clients/{client_id}/meetings/{meeting_id}` | Member | Update meeting |

### CRM Routes (`/api/v1/crm`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/crm/{client_id}/connections` | Member | List CRM connections |
| POST | `/crm/{client_id}/hubspot/oauth` | Admin | Start HubSpot OAuth |
| GET | `/crm/{client_id}/hubspot/callback` | None | HubSpot OAuth callback |
| POST | `/crm/{client_id}/pipedrive/connect` | Admin | Connect Pipedrive (API key) |
| POST | `/crm/{client_id}/close/connect` | Admin | Connect Close (API key) |
| DELETE | `/crm/{client_id}/connections/{connection_id}` | Admin | Disconnect CRM |
| POST | `/crm/{client_id}/sync` | Admin | Trigger CRM sync |

### LinkedIn Routes (`/api/v1/linkedin`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/linkedin/connect` | User | Get Unipile hosted auth URL |
| GET | `/linkedin/status` | User | Get connection status |
| POST | `/linkedin/disconnect` | User | Disconnect LinkedIn account |
| POST | `/linkedin/refresh` | User | Refresh account status |

### Pool Routes (`/api/v1/pool`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/pool/populate` | User | Trigger pool population from Apollo |
| POST | `/pool/clients/{client_id}/populate` | User | Populate for specific client |
| GET | `/pool/stats` | User | Get pool statistics |

### Patterns Routes (`/api/v1/patterns`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/patterns` | Member | List all patterns for client |
| GET | `/patterns/{pattern_type}` | Member | Get specific pattern (who/what/when/how) |
| GET | `/patterns/recommendations/channels` | Member | Get channel recommendations |
| GET | `/patterns/recommendations/timing` | Member | Get timing recommendations |
| GET | `/patterns/weights` | Member | Get current ALS weights |
| GET | `/patterns/history` | Member | Get pattern history |
| POST | `/patterns/trigger` | Member | Trigger pattern learning |

### Admin Routes (`/api/v1/admin`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/admin/clients` | Platform Admin | List all clients |
| GET | `/admin/clients/{client_id}` | Platform Admin | Get client details |
| POST | `/admin/clients` | Platform Admin | Create client |
| PATCH | `/admin/clients/{client_id}` | Platform Admin | Update client |
| GET | `/admin/users` | Platform Admin | List all users |
| GET | `/admin/costs/ai` | Platform Admin | Get AI usage costs |
| GET | `/admin/health/detailed` | Platform Admin | Detailed system health |

### Webhook Routes (Inbound) (`/api/v1/webhooks`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/webhooks/postmark/inbound` | Signature | Inbound email replies |
| POST | `/webhooks/postmark/bounce` | Signature | Email bounces |
| POST | `/webhooks/postmark/spam` | Signature | Spam complaints |
| POST | `/webhooks/twilio/inbound` | Signature | Inbound SMS replies |
| POST | `/webhooks/twilio/status` | Signature | SMS delivery status |
| POST | `/webhooks/unipile/account` | None | LinkedIn connection events |
| POST | `/webhooks/unipile/message` | None | LinkedIn messages/replies |
| POST | `/webhooks/vapi` | None | Voice call completion |
| POST | `/webhooks/smartlead/events` | Signature | Email engagement (opens, clicks) |
| POST | `/webhooks/salesforge/events` | Signature | Email engagement events |
| POST | `/webhooks/resend/events` | Signature | Email engagement events |
| POST | `/webhooks/crm/deal` | API Key | CRM deal updates |
| POST | `/webhooks/crm/meeting` | None | Calendar meeting events |

### Webhook Routes (Outbound) (`/api/v1/webhooks-outbound`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/webhooks/dispatch` | Internal | Dispatch webhook to client endpoints |
| GET | `/webhooks/config` | Member | Get webhook configurations |
| POST | `/webhooks/config` | Admin | Create webhook configuration |
| PATCH | `/webhooks/config/{webhook_id}` | Admin | Update webhook configuration |
| DELETE | `/webhooks/config/{webhook_id}` | Admin | Delete webhook configuration |
| GET | `/webhooks/deliveries/{webhook_id}` | Member | Get delivery history |

---

## 7. Webhook Handling

### Inbound Webhooks

Inbound webhooks receive events from external services:

| Provider | Events | Signature Method |
|----------|--------|------------------|
| Postmark | Inbound email, bounce, spam | Custom HMAC (placeholder) |
| Twilio | Inbound SMS, delivery status | HMAC-SHA1 |
| Unipile | Account connection, LinkedIn messages | None (IP allowlist) |
| Vapi | Call started, ended, transcript | None |
| Smartlead | Opens, clicks, bounces, replies | HMAC-SHA256 |
| Salesforge | Opens, clicks, bounces, replies | HMAC-SHA256 |
| Resend | Opens, clicks, bounces, complaints | Svix HMAC-SHA256 |

### Webhook Processing Pattern

```python
@router.post("/webhooks/{provider}/inbound")
async def handle_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    # 1. Get raw payload
    payload = await request.json()
    signature = request.headers.get("X-Signature")

    # 2. Verify signature (in production)
    if settings.is_production and not verify_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 3. Parse webhook
    parsed = parse_webhook(payload)

    # 4. Find related entity (lead, activity, etc.)
    lead = await find_lead_by_email(db, parsed["email"])
    if not lead:
        return {"status": "ignored", "reason": "lead_not_found"}

    # 5. Check for duplicates
    if await check_duplicate(db, lead.id, parsed["message_id"]):
        return {"status": "ignored", "reason": "already_processed"}

    # 6. Process via engine
    result = await engine.process(db=db, lead_id=lead.id, ...)

    # 7. Return success (always 200 to prevent retries)
    return {"status": "processed", "lead_id": str(lead.id)}
```

### Outbound Webhooks

Outbound webhooks dispatch events to client endpoints:

```python
# Dispatch webhook to client
await create_and_dispatch_webhook(
    client_id=client_id,
    event_type=WebhookEventType.LEAD_CREATED,
    payload={"lead_id": str(lead.id), "email": lead.email},
    db=db,
    background_tasks=background_tasks,
)
```

**Event Types:**
- `lead.created` - New lead added
- `lead.enriched` - Lead enrichment completed
- `lead.scored` - ALS score updated
- `reply.received` - Reply processed
- `campaign.completed` - Campaign finished

**Security:**
- HMAC-SHA256 signature in `X-Agency-OS-Signature` header
- Per-client webhook secrets
- Retry with exponential backoff
- Auto-disable after consecutive failures

---

## 8. Error Handling

### Custom Exception Classes

| Exception | HTTP Status | Use Case |
|-----------|-------------|----------|
| `ValidationError` | 400 | Invalid input data |
| `RequestValidationError` | 422 | Pydantic validation failure |
| `AuthenticationError` | 401 | Missing or invalid token |
| `AuthorizationError` | 403 | Insufficient permissions |
| `ResourceNotFoundError` | 404 | Entity not found |
| `ResourceDeletedError` | 410 | Entity was soft-deleted |
| `RateLimitError` | 429 | Rate limit exceeded |
| `AISpendLimitError` | 429 | AI usage limit exceeded |
| `AgencyOSError` | 500 | Generic internal error |

### Exception Handlers

```python
# src/api/main.py

@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "authentication_error",
            "message": str(exc),
        },
    )

@app.exception_handler(ResourceNotFoundError)
async def not_found_error_handler(request: Request, exc: ResourceNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "not_found",
            "message": str(exc),
            "resource": exc.details.get("resource_type"),
            "resource_id": exc.details.get("resource_id"),
        },
    )
```

### Error Response Format

```json
{
    "error": "error_code",
    "message": "Human-readable error message",
    "field": "field_name",       // For validation errors
    "resource": "Lead",          // For not found errors
    "resource_id": "uuid"        // For not found errors
}
```

### Sentry Integration

All unhandled exceptions are captured in Sentry:

```python
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    sentry_sdk.capture_exception(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": str(exc) if settings.ENV != "production" else "An error occurred",
        },
    )
```

---

## 9. Key Rules

### Rule 11: Session Passed as Argument

Database sessions are always passed as dependencies, never created inside functions:

```python
# Correct
@router.get("/leads")
async def list_leads(
    db: AsyncSession = Depends(get_db_session),  # Session from dependency
):
    ...

# Wrong - creating session inside function
async def list_leads():
    async with get_session() as db:  # DON'T DO THIS
        ...
```

### Rule 12: API Layer Import Hierarchy

API routes (Layer 5) can import from all layers below:

```
Layer 5: src/api/routes/     ← Can import ALL
Layer 4: src/orchestration/  ← Can import engines, integrations, models
Layer 3: src/engines/        ← Can import integrations, models
Layer 2: src/integrations/   ← Can import models
Layer 1: src/models/         ← Base layer
```

### Rule 14: Soft Deletes Only

Never use hard DELETE. Always check `deleted_at IS NULL`:

```python
# Query with soft delete check
stmt = select(Lead).where(
    and_(
        Lead.client_id == client_id,
        Lead.deleted_at.is_(None),  # Soft delete check
    )
)

# Soft delete operation
lead.deleted_at = datetime.utcnow()
await db.commit()
```

### Rule 20: Webhook-First Architecture

Webhooks are the primary method for real-time event processing:

```python
# Webhook receives reply -> Closer engine processes -> Activity logged
@router.post("/webhooks/postmark/inbound")
async def handle_reply(request: Request, db: AsyncSession):
    # Process via Closer engine
    result = await closer.process_reply(
        db=db,
        lead_id=lead.id,
        message=message,
        channel=ChannelType.EMAIL,
    )
```

### Pydantic Response Models

All endpoints use Pydantic models for request/response validation:

```python
class LeadResponse(BaseModel):
    id: UUID
    email: str
    als_score: int
    status: str

    class Config:
        from_attributes = True  # Enable ORM mode
```

---

## 10. Cross-References

| Topic | Document |
|-------|----------|
| Database Schema | `docs/specs/database/SCHEMA_OVERVIEW.md` |
| Import Hierarchy | `docs/architecture/foundation/IMPORT_HIERARCHY.md` |
| Authentication | `docs/specs/integrations/SUPABASE.md` |
| Webhook Events | `docs/architecture/distribution/EMAIL.md` |
| ALS Scoring | `docs/specs/engines/SCORER_ENGINE.md` |
| Multi-tenancy | `docs/architecture/foundation/DECISIONS.md` |
| Error Tracking | Sentry dashboard |

---

## Appendix: Request Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HTTP Request                                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RequestLoggingMiddleware                          │
│                    (timing, request ID)                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ClientContextMiddleware                           │
│                    (initialize context)                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       CORSMiddleware                                 │
│                    (cross-origin handling)                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Route Handler                                 │
│                                                                      │
│   Dependencies:                                                      │
│   ├── get_db_session() ─────► AsyncSession                          │
│   ├── get_current_user_from_token() ─────► CurrentUser              │
│   └── get_current_client() ─────► ClientContext                     │
│                                                                      │
│   Logic:                                                             │
│   ├── Validate request (Pydantic)                                   │
│   ├── Check RBAC (require_member, require_admin)                    │
│   ├── Query database (with client_id filter)                        │
│   └── Return response (Pydantic model)                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Exception Handlers                              │
│                (if error occurs at any stage)                        │
│                                                                      │
│   AuthenticationError ─────► 401                                    │
│   AuthorizationError ──────► 403                                    │
│   ResourceNotFoundError ───► 404                                    │
│   ValidationError ─────────► 400                                    │
│   Exception ───────────────► 500 (+ Sentry capture)                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        HTTP Response                                 │
│                 (JSON + timing header)                               │
└─────────────────────────────────────────────────────────────────────┘
```
