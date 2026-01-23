# Security Architecture

**Purpose:** Document all security mechanisms in Agency OS including authentication, authorization, data protection, and audit logging.
**Last Updated:** 2026-01-23
**Status:** Foundation document

---

## Overview

Agency OS implements defense-in-depth security across multiple layers:

| Layer | Component | Implementation |
|-------|-----------|----------------|
| **Authentication** | Who you are | Supabase Auth + JWT |
| **Authorization** | What you can do | RBAC + RLS policies |
| **Data Protection** | Encryption & handling | TLS 1.3 + Fernet AES |
| **Audit Logging** | What happened | PostgreSQL triggers + Sentry |
| **API Security** | Rate limiting & validation | Pydantic + middleware |

---

## Authentication

### Provider: Supabase Auth

Agency OS uses Supabase Auth as the identity provider, handling all user authentication, session management, and token refresh.

| Component | Implementation |
|-----------|----------------|
| Identity Provider | Supabase Auth |
| Token Type | JWT (HS256) |
| Token Lifetime | 1 hour (configurable via Supabase) |
| Refresh Token | 7 days |
| Session Storage | HttpOnly cookies (frontend) |

### Authentication Flow

```
1. User submits credentials to Supabase Auth
2. Supabase validates and returns:
   - Access token (JWT, 1 hour)
   - Refresh token (7 days)
3. Frontend stores tokens securely
4. Backend validates JWT on each request via get_current_user_from_token()
5. Token auto-refreshes before expiry via Supabase client
```

### Backend JWT Verification

**Location:** `src/api/dependencies.py`

```python
async def get_current_user_from_token(
    authorization: Annotated[Optional[str], Header()] = None,
    db: AsyncSession = Depends(get_db_session),
) -> CurrentUser:
    """
    Extract and validate user from JWT token.
    Uses Supabase JWT secret for HS256 verification.
    """
    # Extract Bearer token from Authorization header
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid authorization header format")

    token = parts[1]

    # Decode JWT with Supabase JWT secret
    jwt_secret = settings.supabase_jwt_secret
    payload = jwt.decode(
        token,
        jwt_secret,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )

    # Lookup user in database
    user_id = payload.get("sub")
    user = await db.execute(select(User).where(User.id == UUID(user_id)))
    return CurrentUser(id=user.id, email=user.email, ...)
```

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_KEY` | Anon/public key (RLS enforced) | Yes |
| `SUPABASE_SERVICE_KEY` | Service role key (bypasses RLS) | Yes |
| `SUPABASE_JWT_SECRET` | JWT signing secret | Yes |

**Configuration:** `src/config/settings.py`

---

## Authorization (RBAC)

### Role Hierarchy

Agency OS uses membership-based role-based access control (RBAC) where users have roles within specific clients.

| Role | Level | Permissions |
|------|-------|-------------|
| **owner** | 100 | All actions, manage team, delete client |
| **admin** | 80 | All actions except delete client, manage team |
| **member** | 60 | CRUD campaigns/leads, view reports |
| **viewer** | 40 | View only, no modifications |

### Role Model

**Location:** `src/models/base.py`

```python
class MembershipRole(str, Enum):
    """Team membership roles."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
```

### Permission Dependencies

**Location:** `src/api/dependencies.py`

```python
# Pre-built dependency functions
require_owner = require_role(MembershipRole.OWNER)
require_admin = require_role(MembershipRole.OWNER, MembershipRole.ADMIN)
require_member = require_role(MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.MEMBER)

# Usage in routes
@router.delete("/campaigns/{id}")
async def delete_campaign(
    id: UUID,
    ctx: ClientContext = Depends(require_admin),
):
    ctx.require_role(MembershipRole.OWNER, MembershipRole.ADMIN)
    ...
```

### Multi-Tenancy (Client Isolation)

Every request is scoped to a specific client via the `ClientContext`:

```python
class ClientContext(BaseModel):
    client: Client
    membership: Membership
    user: CurrentUser

    @property
    def client_id(self) -> UUID:
        return self.client.id

    def require_role(self, *roles: MembershipRole) -> None:
        if not self.has_role(*roles):
            raise InsufficientPermissionsError(...)
```

### Row Level Security (RLS)

**Location:** `supabase/migrations/009_rls_policies.sql`

RLS policies enforce data isolation at the database level:

| Table | SELECT | INSERT | UPDATE | DELETE |
|-------|--------|--------|--------|--------|
| `clients` | Via membership | N/A | Owner/Admin | Owner |
| `campaigns` | Via membership | Member+ | Member+ | Admin+ |
| `leads` | Via membership | Member+ | Member+ | Admin+ |
| `activities` | Via membership | Member+ | N/A | N/A |
| `audit_logs` | Via membership | System only | N/A | N/A |

**Example Policy:**

```sql
-- Users can only view leads for clients they are members of
CREATE POLICY leads_select ON leads
    FOR SELECT
    USING (
        client_id IN (SELECT get_user_client_ids())
        AND deleted_at IS NULL
    );

-- Members+ can update leads
CREATE POLICY leads_update ON leads
    FOR UPDATE
    USING (
        user_has_role(client_id, ARRAY['owner', 'admin', 'member']::membership_role[])
        AND deleted_at IS NULL
    );
```

### Service Role Bypass

The service role key (`SUPABASE_SERVICE_KEY`) bypasses all RLS policies. Used only by:
- Backend services (Prefect workers)
- System operations (webhooks, scheduled jobs)

**Location:** `src/integrations/supabase.py`

```python
def get_supabase_service_client() -> Client:
    """
    Get Supabase client with service role (bypasses RLS).
    WARNING: Only use in trusted backend code.
    """
    return create_client(settings.supabase_url, settings.supabase_service_key)
```

---

## API Security

### Rate Limiting

Rate limits are enforced at the resource level (not API level) per business rules.

| Resource Type | Limit | Window | Location |
|---------------|-------|--------|----------|
| LinkedIn per seat | 17 | Per day | `settings.rate_limit_linkedin_per_seat` |
| Email per domain | 50 | Per day | `settings.rate_limit_email_per_domain` |
| SMS per number | 100 | Per day | `settings.rate_limit_sms_per_number` |
| AI daily spend | $50-200 | Per day | `settings.anthropic_daily_spend_limit` |

### Input Validation

All request inputs are validated via Pydantic schemas:

```python
# Example from src/api/routes/campaigns.py
class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    client_id: UUID
    status: CampaignStatus = CampaignStatus.DRAFT
```

**Protections:**
- SQL injection: Prevented via SQLAlchemy ORM
- XSS: Output encoding in frontend
- Path traversal: No direct file access from API

### CORS Configuration

**Location:** `src/api/main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENV == "development" else settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

| Environment | Allowed Origins |
|-------------|-----------------|
| Development | `*` (all) |
| Production | Configured in `ALLOWED_ORIGINS` |

### Security Headers

Applied via middleware in production:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Strict-Transport-Security` | `max-age=31536000` | Force HTTPS |
| `Content-Security-Policy` | `default-src 'self'` | XSS protection |

---

## Webhook Security

### Signature Verification

All webhook endpoints verify signatures to prevent spoofing.

**Location:** `src/api/routes/webhooks.py`

| Provider | Algorithm | Header | Implementation |
|----------|-----------|--------|----------------|
| Twilio | HMAC-SHA1 | `X-Twilio-Signature` | `verify_twilio_signature()` |
| Smartlead | HMAC-SHA256 | `X-Smartlead-Signature` | `verify_smartlead_signature()` |
| Salesforge | HMAC-SHA256 | `X-Salesforge-Signature` | `verify_salesforge_signature()` |
| Resend | Svix HMAC-SHA256 | `svix-signature` | `verify_resend_signature()` |
| Stripe | HMAC-SHA256 | `Stripe-Signature` | Stripe SDK |

**Example Verification:**

```python
def verify_twilio_signature(url: str, params: dict, signature: str) -> bool:
    """Verify Twilio webhook signature using HMAC-SHA1."""
    if not signature or not settings.twilio_auth_token:
        return not settings.is_production

    # Construct signature string: URL + sorted params
    signature_string = url
    for key in sorted(params.keys()):
        signature_string += f"{key}{params[key]}"

    computed = hmac.new(
        settings.twilio_auth_token.encode(),
        signature_string.encode(),
        hashlib.sha1
    ).digest()

    computed_b64 = base64.b64encode(computed).decode()
    return hmac.compare_digest(computed_b64, signature)
```

### Internal API Key Authentication

For webhook endpoints without external signatures:

```python
async def verify_api_key(x_api_key: str = Header()) -> bool:
    """Verify API key for internal webhook endpoints."""
    if x_api_key != settings.webhook_hmac_secret:
        raise AuthenticationError("Invalid API key")
    return True
```

---

## Data Protection

### Encryption

| Data Type | At Rest | In Transit |
|-----------|---------|------------|
| Database | AES-256 (Supabase managed) | TLS 1.3 |
| Credentials (LinkedIn) | Fernet AES-128-CBC | TLS 1.3 |
| API Keys (3rd party) | Environment variables | TLS 1.3 |
| Backups | Encrypted (Supabase managed) | TLS 1.3 |

### Credential Encryption

**Location:** `src/utils/encryption.py`

LinkedIn credentials and other sensitive data are encrypted using Fernet (AES-128-CBC + HMAC-SHA256):

```python
from cryptography.fernet import Fernet

def encrypt_credential(plaintext: str) -> str:
    """Encrypt a credential using Fernet (AES-128-CBC + HMAC)."""
    fernet = Fernet(settings.credential_encryption_key.encode())
    return fernet.encrypt(plaintext.encode()).decode()

def decrypt_credential(ciphertext: str) -> str:
    """Decrypt a credential."""
    fernet = Fernet(settings.credential_encryption_key.encode())
    return fernet.decrypt(ciphertext.encode()).decode()
```

**Key Management:**
- Encryption key stored in `CREDENTIAL_ENCRYPTION_KEY` environment variable
- Generate new key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### Sensitive Data Handling

**Never logged:**
- Passwords
- API keys/tokens
- Credit card numbers
- JWT tokens

**Stored encrypted:**
- LinkedIn passwords (Fernet)
- OAuth refresh tokens

**Environment variables only:**
- All third-party API keys
- Database credentials
- JWT secrets

### Data Retention

| Data Type | Retention | Deletion Method |
|-----------|-----------|-----------------|
| User data | Until account deletion | Soft delete on request |
| Leads | Configurable (default 2 years) | Soft delete |
| Activities | Indefinite | N/A |
| Voice recordings | 90 days | Hard delete from Vapi |
| Audit logs | 365 days | `cleanup_old_audit_logs()` |

---

## Audit Logging

### What's Logged

**Location:** `supabase/migrations/008_audit_logs.sql`

| Event Type | Details Captured |
|------------|------------------|
| Authentication | Login, logout, failed attempts |
| Authorization | Permission denials |
| Data access | User, client context |
| Data changes | Create, update, delete with diffs |
| API calls | Request ID, timing |
| Webhook events | Payload, status |

### Audit Log Schema

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    client_id UUID REFERENCES clients(id),
    action audit_action NOT NULL,  -- create, update, delete, login, etc.
    resource_type TEXT NOT NULL,   -- campaigns, leads, users, etc.
    resource_id UUID,
    old_values JSONB,              -- Previous state
    new_values JSONB,              -- New state
    changes JSONB,                 -- Diff of changes
    ip_address INET,
    user_agent TEXT,
    request_id TEXT,               -- For tracing
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Automatic Audit Triggers

Database triggers automatically capture changes to key tables:

```sql
-- Applied to campaigns, clients, memberships
CREATE TRIGGER campaigns_audit
    AFTER INSERT OR UPDATE OR DELETE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
```

### Sentry Error Tracking

**Location:** `src/api/main.py`

```python
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.ENV,
        traces_sample_rate=0.1,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        send_default_pii=False,  # Don't send PII
    )
```

| Component | What's Tracked |
|-----------|---------------|
| API (FastAPI) | All exceptions, 500 errors, request context |
| Prefect Worker | Flow failures, task errors |
| Integrations | Apollo/Resend/etc API failures |
| Frontend | JavaScript errors (if configured) |

---

## Secrets Management

### Environment Variables

All secrets are stored in environment variables, loaded via `src/config/settings.py`.

| Secret Category | Variables |
|-----------------|-----------|
| Database | `DATABASE_URL`, `DATABASE_URL_MIGRATIONS` |
| Supabase | `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET` |
| External APIs | `ANTHROPIC_API_KEY`, `APOLLO_API_KEY`, `TWILIO_AUTH_TOKEN`, etc. |
| Webhooks | `WEBHOOK_HMAC_SECRET`, `STRIPE_WEBHOOK_SECRET`, `SMARTLEAD_WEBHOOK_SECRET` |
| Encryption | `CREDENTIAL_ENCRYPTION_KEY` |

### Never Commit

These patterns are excluded from version control:

```
.env
.env.local
.env.production
*.pem
*.key
credentials.json
*_secret*
```

### Production Secrets

| Platform | Secret Storage | Access |
|----------|---------------|--------|
| Railway | Environment variables | Per-service |
| Vercel | Environment variables | Per-project |
| Supabase | Project settings | Dashboard |

---

## Infrastructure Security

### Railway (Backend)

| Control | Implementation |
|---------|----------------|
| Network isolation | Private networking between services |
| Environment variables | Encrypted at rest |
| Deployment | Automated from main branch |
| Logs | 7-day retention, not exposed |

### Vercel (Frontend)

| Control | Implementation |
|---------|----------------|
| HTTPS | Automatic SSL/TLS |
| Environment variables | Encrypted at rest |
| Edge functions | Isolated execution |
| Preview deployments | Protected by authentication |

### Database (Supabase)

| Control | Implementation |
|---------|----------------|
| Encryption at rest | AES-256 |
| Connection pooling | Supavisor (port 6543) |
| Row Level Security | Enabled on all tables |
| Backups | Daily automated, encrypted |
| Network | Private endpoints available |

---

## Compliance Considerations

### Australian Privacy Act

| Requirement | Implementation |
|-------------|----------------|
| Consent for data collection | Lead opt-in tracked |
| Right to access | Export via API |
| Right to deletion | Soft delete + data purge |
| Data breach notification | 72 hours via Sentry alerts |
| Cross-border restrictions | Data stored in Sydney region |

### DNCR (Do Not Call Register)

| Requirement | Implementation |
|-------------|----------------|
| DNCR check before calls | `dncr.py` integration |
| Check caching | 24 hours |
| Voice/SMS compliance | Enforced in `voice.py`, `sms.py` |
| Quarterly list updates | Scheduled via Prefect |

---

## Incident Response

### Severity Levels

| Level | Definition | Response Time |
|-------|------------|---------------|
| P0 | Active breach, data exposed | Immediate |
| P1 | Vulnerability discovered, no breach | 4 hours |
| P2 | Security weakness, no immediate risk | 24 hours |
| P3 | Security improvement | 1 week |

### Response Steps

1. **Identify and contain** - Isolate affected systems
2. **Assess impact** - Determine data exposure
3. **Notify stakeholders** - If required by law/contract
4. **Remediate** - Fix vulnerability
5. **Post-incident review** - Update security controls

### Monitoring

| System | What's Monitored | Alert Channel |
|--------|------------------|---------------|
| Sentry | Exceptions, errors | Email/Slack |
| Railway | Deployment failures | Dashboard |
| Supabase | Database health | Dashboard |
| Prefect | Flow failures | Dashboard |

---

## Security Checklist

### Code Review

- [ ] No hardcoded secrets
- [ ] Input validation via Pydantic
- [ ] SQL via ORM only (no raw queries with user input)
- [ ] Webhook signatures verified
- [ ] RLS policies enforced

### Deployment

- [ ] All environment variables set
- [ ] HTTPS enforced
- [ ] CORS configured for production
- [ ] Sentry configured
- [ ] Audit logging enabled

### Access Control

- [ ] JWT secret rotated quarterly
- [ ] API keys rotated on compromise
- [ ] Team access reviewed monthly
- [ ] Service accounts documented

---

For gaps and implementation status, see `../TODO.md`.
