# Claude Code Prompt: Deploy Phase 18-24 + Build TEST_MODE + Build Phase 24H LinkedIn

**Copy everything below this line into Claude Code.**

---

## Your Role

You are the Builder and DevOps Agent for Agency OS. Your job is to:
1. Deploy all uncommitted work (Phases 18-24) to production
2. Build TEST_MODE for safe E2E testing
3. Build Phase 24H (LinkedIn Credential Connection)
4. Verify everything works

---

## Before You Start

```bash
cd C:\AI\Agency_OS

# Read current progress
head -100 PROGRESS.md

# Check git status
git status --short | wc -l

# Read the LinkedIn skill
cat skills/linkedin/LINKEDIN_CONNECTION_SKILL.md | head -100

# Read the Phase 24H spec
cat docs/phases/PHASE_24H_LINKEDIN_CONNECTION.md | head -100
```

---

## PART 1: DEPLOY EXISTING CODE

### Step 1.1: Stage and Commit

```bash
cd C:\AI\Agency_OS

git add .

git commit -m "feat: Phase 18-24 complete

Phase 18: Email Infrastructure (InfraForge/Salesforge)
Phase 19: Scraper Waterfall (5-tier fallback)
Phase 20: UI Wiring (Deep research auto-trigger)
Phase 24A-G: CIS Data Architecture

New migrations: 017-030
New services: lead_pool, jit_validator, thread, deal, meeting, crm_push, customer_import"
```

### Step 1.2: Push to GitHub

```bash
git push origin main
```

### Step 1.3: Verify Deployments

```bash
# Wait for auto-deploy
sleep 60

# Test backend
curl https://agency-os-production.up.railway.app/api/v1/health

# Test frontend  
curl -I https://agency-os-liart.vercel.app
```

### Step 1.4: Output Supabase Migrations

Read and output each migration SQL for manual application:

```bash
cat supabase/migrations/017_fix_trigger_schema.sql
cat supabase/migrations/021_deep_research.sql
cat supabase/migrations/024_lead_pool.sql
cat supabase/migrations/025_content_tracking.sql
cat supabase/migrations/026_email_engagement.sql
cat supabase/migrations/027_conversation_threads.sql
cat supabase/migrations/028_downstream_outcomes.sql
cat supabase/migrations/029_crm_push.sql
cat supabase/migrations/030_customer_import.sql
```

Tell the human: "Apply these migrations in Supabase Dashboard → SQL Editor in order."

---

## PART 2: BUILD TEST_MODE

TEST_MODE redirects all outbound to test recipients. Without it, campaigns would contact real people.

### Test Recipients (Already in Railway)

```
TEST_MODE=true
TEST_EMAIL_RECIPIENT=david.stephens@keiracom.com
TEST_SMS_RECIPIENT=+61457543392
TEST_VOICE_RECIPIENT=+61457543392
TEST_LINKEDIN_RECIPIENT=https://www.linkedin.com/in/david-stephens-8847a636a/
TEST_DAILY_EMAIL_LIMIT=15
```

### TEST-001: Add to Settings

Edit `src/config/settings.py`. Add to the Settings class:

```python
# Test Mode Configuration
TEST_MODE: bool = Field(default=False, env="TEST_MODE")
TEST_EMAIL_RECIPIENT: str = Field(
    default="david.stephens@keiracom.com",
    env="TEST_EMAIL_RECIPIENT"
)
TEST_SMS_RECIPIENT: str = Field(
    default="+61457543392",
    env="TEST_SMS_RECIPIENT"
)
TEST_VOICE_RECIPIENT: str = Field(
    default="+61457543392",
    env="TEST_VOICE_RECIPIENT"
)
TEST_LINKEDIN_RECIPIENT: str = Field(
    default="https://www.linkedin.com/in/david-stephens-8847a636a/",
    env="TEST_LINKEDIN_RECIPIENT"
)
TEST_DAILY_EMAIL_LIMIT: int = Field(default=15, env="TEST_DAILY_EMAIL_LIMIT")
```

### TEST-002: Update Email Engine

Edit `src/engines/email.py`. Find the send function and add at the start:

```python
from src.config.settings import settings

# In send function, before actual send:
if settings.TEST_MODE:
    original = recipient_email
    recipient_email = settings.TEST_EMAIL_RECIPIENT
    logger.info(f"TEST_MODE: Redirecting email {original} → {recipient_email}")
```

### TEST-003: Update SMS Engine

Edit `src/engines/sms.py`. Same pattern:

```python
if settings.TEST_MODE:
    original = phone_number
    phone_number = settings.TEST_SMS_RECIPIENT
    logger.info(f"TEST_MODE: Redirecting SMS {original} → {phone_number}")
```

### TEST-004: Update Voice Engine

Edit `src/engines/voice.py`. Same pattern:

```python
if settings.TEST_MODE:
    original = phone_number
    phone_number = settings.TEST_VOICE_RECIPIENT
    logger.info(f"TEST_MODE: Redirecting voice {original} → {phone_number}")
```

### TEST-005: Update LinkedIn Engine

Edit `src/engines/linkedin.py`. Same pattern:

```python
if settings.TEST_MODE:
    original = linkedin_url
    linkedin_url = settings.TEST_LINKEDIN_RECIPIENT
    logger.info(f"TEST_MODE: Redirecting LinkedIn {original} → {linkedin_url}")
```

### TEST-006: Daily Send Limit

Create `src/services/send_limiter.py`:

```python
"""Daily send limits during TEST_MODE to protect warmup."""

from datetime import datetime
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.models.activity import Activity


class SendLimiter:
    async def check_email_limit(self, db: AsyncSession, client_id: UUID) -> tuple[bool, int]:
        """Returns (is_allowed, current_count)."""
        if not settings.TEST_MODE:
            return True, 0
        
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        stmt = (
            select(func.count(Activity.id))
            .where(Activity.client_id == client_id)
            .where(Activity.channel == "email")
            .where(Activity.created_at >= today)
        )
        
        result = await db.execute(stmt)
        count = result.scalar() or 0
        
        return count < settings.TEST_DAILY_EMAIL_LIMIT, count


send_limiter = SendLimiter()
```

Update `src/services/__init__.py` to export it.

---

## PART 3: BUILD PHASE 24H (LINKEDIN CONNECTION)

### Read the Full Spec and Skill

```bash
cat docs/phases/PHASE_24H_LINKEDIN_CONNECTION.md
cat skills/linkedin/LINKEDIN_CONNECTION_SKILL.md
```

### LI-001: Create Migration

Create `supabase/migrations/031_linkedin_credentials.sql`:

```sql
-- Phase 24H: LinkedIn Credential Connection
-- Stores encrypted LinkedIn credentials for HeyReach automation

CREATE TABLE IF NOT EXISTS client_linkedin_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Encrypted credentials (Fernet AES-256)
    linkedin_email_encrypted TEXT NOT NULL,
    linkedin_password_encrypted TEXT NOT NULL,
    
    -- Connection status
    connection_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (connection_status IN ('pending', 'connecting', 'awaiting_2fa', 'connected', 'failed', 'disconnected')),
    
    -- HeyReach integration
    heyreach_sender_id TEXT,
    heyreach_account_id TEXT,
    
    -- LinkedIn profile info (populated after connection)
    linkedin_profile_url TEXT,
    linkedin_profile_name TEXT,
    linkedin_headline TEXT,
    linkedin_connection_count INTEGER,
    
    -- 2FA handling
    two_fa_method TEXT,
    two_fa_requested_at TIMESTAMPTZ,
    
    -- Error tracking
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    last_error_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    connected_at TIMESTAMPTZ,
    disconnected_at TIMESTAMPTZ,
    
    UNIQUE(client_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_linkedin_creds_status 
    ON client_linkedin_credentials(connection_status);
CREATE INDEX IF NOT EXISTS idx_linkedin_creds_client 
    ON client_linkedin_credentials(client_id);

-- RLS
ALTER TABLE client_linkedin_credentials ENABLE ROW LEVEL SECURITY;

CREATE POLICY "clients_own_linkedin" ON client_linkedin_credentials
    FOR ALL USING (client_id = auth.uid());

CREATE POLICY "service_role_linkedin" ON client_linkedin_credentials
    FOR ALL USING (auth.role() = 'service_role');

-- Updated at trigger
CREATE TRIGGER update_linkedin_credentials_updated_at
    BEFORE UPDATE ON client_linkedin_credentials
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### LI-002: Create Encryption Utility

Create `src/utils/encryption.py`:

```python
"""Credential encryption using Fernet (AES-256)."""

from cryptography.fernet import Fernet
from src.config.settings import settings

_fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.CREDENTIAL_ENCRYPTION_KEY
        if not key:
            raise ValueError("CREDENTIAL_ENCRYPTION_KEY not configured")
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_credential(plaintext: str) -> str:
    """Encrypt a credential string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_credential(ciphertext: str) -> str:
    """Decrypt a credential string."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def generate_encryption_key() -> str:
    """Generate a new Fernet key. Run once to get key for env var."""
    return Fernet.generate_key().decode()
```

Add to `src/config/settings.py`:

```python
# Credential Encryption
CREDENTIAL_ENCRYPTION_KEY: str = Field(default="", env="CREDENTIAL_ENCRYPTION_KEY")
```

### LI-003: Create LinkedIn Credential Model

Create `src/models/linkedin_credential.py`:

```python
"""LinkedIn credential model."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class LinkedInCredential(Base):
    __tablename__ = "client_linkedin_credentials"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    client_id = Column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Encrypted credentials
    linkedin_email_encrypted = Column(String, nullable=False)
    linkedin_password_encrypted = Column(String, nullable=False)
    
    # Status
    connection_status = Column(String, nullable=False, default="pending")
    
    # HeyReach
    heyreach_sender_id = Column(String)
    heyreach_account_id = Column(String)
    
    # Profile info
    linkedin_profile_url = Column(String)
    linkedin_profile_name = Column(String)
    linkedin_headline = Column(String)
    linkedin_connection_count = Column(Integer)
    
    # 2FA
    two_fa_method = Column(String)
    two_fa_requested_at = Column(DateTime(timezone=True))
    
    # Errors
    last_error = Column(String)
    error_count = Column(Integer, default=0)
    last_error_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    connected_at = Column(DateTime(timezone=True))
    disconnected_at = Column(DateTime(timezone=True))
    
    # Relationship
    client = relationship("Client", back_populates="linkedin_credential")
```

Update `src/models/__init__.py` to export it.

### LI-004: Create LinkedIn Connection Service

Create `src/services/linkedin_connection_service.py` following the pattern in `skills/linkedin/LINKEDIN_CONNECTION_SKILL.md`.

Key methods:
- `start_connection(db, client_id, email, password)` → Encrypt, save, call HeyReach
- `submit_2fa_code(db, client_id, code)` → Verify 2FA
- `get_status(db, client_id)` → Return connection status
- `disconnect(db, client_id)` → Remove from HeyReach, update status

### LI-005: Extend HeyReach Integration

Edit `src/integrations/heyreach.py`. Add methods:

```python
async def add_linkedin_account(self, email: str, password: str) -> dict:
    """Add LinkedIn account to HeyReach."""
    # Check HeyReach API docs for exact endpoint
    response = await self._post("/senders/linkedin", json={
        "email": email,
        "password": password
    })
    return response

async def verify_2fa(self, email: str, password: str, code: str) -> dict:
    """Submit 2FA code."""
    response = await self._post("/senders/linkedin/verify", json={
        "email": email,
        "password": password,
        "code": code
    })
    return response

async def remove_sender(self, sender_id: str) -> dict:
    """Remove sender from HeyReach."""
    response = await self._delete(f"/senders/{sender_id}")
    return response
```

**NOTE:** Check actual HeyReach API documentation for correct endpoints. The above is a best guess.

### LI-006: Create LinkedIn API Routes

Create `src/api/routes/linkedin.py`:

```python
"""LinkedIn connection endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID

from src.services.linkedin_connection_service import linkedin_connection_service
from src.api.deps import get_db, get_current_client_id


router = APIRouter(prefix="/linkedin", tags=["linkedin"])


class ConnectRequest(BaseModel):
    linkedin_email: str
    linkedin_password: str


class TwoFactorRequest(BaseModel):
    code: str


@router.post("/connect")
async def connect_linkedin(
    request: ConnectRequest,
    db=Depends(get_db),
    client_id: UUID = Depends(get_current_client_id)
):
    """Start LinkedIn connection."""
    return await linkedin_connection_service.start_connection(
        db, client_id, request.linkedin_email, request.linkedin_password
    )


@router.post("/verify-2fa")
async def verify_2fa(
    request: TwoFactorRequest,
    db=Depends(get_db),
    client_id: UUID = Depends(get_current_client_id)
):
    """Submit 2FA code."""
    return await linkedin_connection_service.submit_2fa_code(
        db, client_id, request.code
    )


@router.get("/status")
async def get_status(
    db=Depends(get_db),
    client_id: UUID = Depends(get_current_client_id)
):
    """Get connection status."""
    return await linkedin_connection_service.get_status(db, client_id)


@router.post("/disconnect")
async def disconnect(
    db=Depends(get_db),
    client_id: UUID = Depends(get_current_client_id)
):
    """Disconnect LinkedIn."""
    return await linkedin_connection_service.disconnect(db, client_id)
```

Register in `src/api/routes/__init__.py`:
```python
from src.api.routes.linkedin import router as linkedin_router
# Add to router list
```

### LI-007: Create Frontend Components

Create `frontend/app/onboarding/linkedin/page.tsx` following the pattern in the skill file.

Create `frontend/components/onboarding/LinkedInCredentialForm.tsx`:
- Email input
- Password input
- Security notice
- Submit button

Create `frontend/components/onboarding/LinkedInTwoFactor.tsx`:
- 6-digit code input
- Resend button
- Back button

Create `frontend/hooks/use-linkedin.ts`:
- useLinkedInStatus()
- useLinkedInConnect()
- useLinkedInVerify2FA()
- useLinkedInDisconnect()

Create `frontend/lib/api/linkedin.ts`:
- connect(email, password)
- verify2FA(code)
- getStatus()
- disconnect()

### LI-008: Update Onboarding Flow

Update `frontend/app/onboarding/page.tsx` to include LinkedIn as step 6.

Update onboarding navigation to route to `/onboarding/linkedin` after ICP extraction.

### LI-009: Create Settings Page

Create `frontend/app/dashboard/settings/linkedin/page.tsx`:
- Show connection status
- Connected: profile info, disconnect button
- Not connected: connect button

### LI-010: Generate Encryption Key

Run this to generate a key:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Output: Tell human to add `CREDENTIAL_ENCRYPTION_KEY=<key>` to Railway.

---

## PART 4: COMMIT AND DEPLOY

```bash
cd C:\AI\Agency_OS

git add .

git commit -m "feat: TEST_MODE + Phase 24H LinkedIn Connection

TEST_MODE:
- Email/SMS/Voice/LinkedIn redirect to test recipients
- Daily send limit safeguard

Phase 24H:
- LinkedIn credential storage (encrypted)
- HeyReach integration for account connection
- 2FA handling
- Onboarding step + settings page"

git push origin main
```

---

## PART 5: VERIFY AND REPORT

After deployment:

```bash
# Backend health
curl https://agency-os-production.up.railway.app/api/v1/health

# Check LinkedIn endpoint exists
curl https://agency-os-production.up.railway.app/api/v1/linkedin/status
```

Report to human:

1. **Git:** Commits pushed successfully?
2. **Vercel:** Frontend deployed?
3. **Railway:** Backend deployed?
4. **Migrations:** Output SQL for 017-031
5. **Encryption Key:** Generated key for Railway
6. **HeyReach API:** Note any uncertainty about endpoint structure

---

## Success Criteria

- [ ] All Phase 18-24 code committed
- [ ] TEST_MODE implemented in all 4 engines
- [ ] Phase 24H LinkedIn tables and service created
- [ ] LinkedIn API routes registered
- [ ] Frontend onboarding + settings pages created
- [ ] Encryption key generated
- [ ] Backend health returns 200
- [ ] Migrations SQL outputted

---

## Environment Variables Needed

Tell human to add to Railway:

```
CREDENTIAL_ENCRYPTION_KEY=<generated-key>
```

(TEST_MODE vars already added)

---

## Begin

Start with Part 1, Step 1.1 (git add and commit).
