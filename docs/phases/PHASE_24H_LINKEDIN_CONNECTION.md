# PHASE 24G: LinkedIn Credential-Based Connection

**Status:** 📋 Planned
**Estimate:** 8 hours
**Tasks:** 10
**Priority:** P1 (Required for multi-channel outreach)
**Dependencies:** Phase 18 (Email Infra), HeyReach API key

---

## Overview

Enable clients to connect their LinkedIn accounts during onboarding for automated LinkedIn outreach via HeyReach. Uses credential-based connection where client provides LinkedIn email + password, stored encrypted, then connected to Agency OS HeyReach account.

**Why Credential-Based:**
- Industry standard for LinkedIn automation (11x, Artisan, all agencies)
- LinkedIn has no OAuth API for messaging automation
- Allows complete automation after initial connection
- Client's brand/identity used for authentic outreach

**What This Enables:**
- Personalized connection requests to prospects
- Direct messages to connections
- Follow-up sequences
- Profile views (leaves notification)
- InMails (if Sales Navigator)

**What This Does NOT Do:**
- Post content to feed
- Comment on posts
- Like posts
- Manage LinkedIn presence

---

## Database Schema

### New Table: `client_linkedin_credentials`

```sql
CREATE TABLE client_linkedin_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Encrypted credentials
    linkedin_email TEXT NOT NULL,  -- Encrypted at rest
    linkedin_password TEXT NOT NULL,  -- Encrypted at rest
    
    -- Connection status
    connection_status TEXT NOT NULL DEFAULT 'pending',
    -- Values: pending, awaiting_2fa, connecting, connected, failed, disconnected
    
    -- HeyReach integration
    heyreach_sender_id TEXT,  -- Populated once connected
    heyreach_workspace_id TEXT,
    
    -- LinkedIn profile info (populated after connection)
    linkedin_profile_url TEXT,
    linkedin_profile_name TEXT,
    linkedin_connection_count INTEGER,
    
    -- 2FA handling
    pending_2fa_code TEXT,  -- Temporary storage for async 2FA
    two_fa_requested_at TIMESTAMPTZ,
    two_fa_expires_at TIMESTAMPTZ,
    
    -- Error tracking
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    connected_at TIMESTAMPTZ,
    disconnected_at TIMESTAMPTZ,
    
    UNIQUE(client_id)  -- One LinkedIn per client
);

-- Index for status lookups
CREATE INDEX idx_linkedin_creds_status ON client_linkedin_credentials(connection_status);

-- RLS policies
ALTER TABLE client_linkedin_credentials ENABLE ROW LEVEL SECURITY;

-- Clients can only see their own
CREATE POLICY "clients_own_linkedin" ON client_linkedin_credentials
    FOR ALL USING (client_id = auth.uid());

-- Service role can see all
CREATE POLICY "service_role_linkedin" ON client_linkedin_credentials
    FOR ALL USING (auth.role() = 'service_role');
```

---

## Task Breakdown

### LI-001: Create Migration (1h)
**File:** `supabase/migrations/031_linkedin_credentials.sql`

Create `client_linkedin_credentials` table with:
- Encrypted credential storage
- Connection status tracking
- HeyReach integration fields
- 2FA handling
- Error tracking

### LI-002: Create LinkedInConnectionService (2h)
**File:** `src/services/linkedin_connection_service.py`

```python
class LinkedInConnectionService:
    async def save_credentials(
        self, 
        client_id: UUID, 
        linkedin_email: str, 
        linkedin_password: str
    ) -> LinkedInCredential:
        """Save encrypted LinkedIn credentials"""
        
    async def get_credentials(self, client_id: UUID) -> Optional[LinkedInCredential]:
        """Get credentials for a client"""
        
    async def update_status(
        self, 
        client_id: UUID, 
        status: str, 
        error: Optional[str] = None
    ) -> None:
        """Update connection status"""
        
    async def save_2fa_code(self, client_id: UUID, code: str) -> None:
        """Save 2FA code from client"""
        
    async def mark_connected(
        self, 
        client_id: UUID, 
        heyreach_sender_id: str,
        profile_url: str,
        profile_name: str,
        connection_count: int
    ) -> None:
        """Mark as successfully connected"""
        
    async def disconnect(self, client_id: UUID) -> None:
        """Disconnect LinkedIn account"""
```

### LI-003: Create Credential Encryption Utilities (1h)
**File:** `src/utils/encryption.py`

```python
from cryptography.fernet import Fernet

class CredentialEncryption:
    def __init__(self, key: str):
        self.fernet = Fernet(key.encode())
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt credential"""
        
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt credential"""
```

Environment variable: `CREDENTIAL_ENCRYPTION_KEY`

### LI-004: Create LinkedIn Connection API Endpoints (1h)
**File:** `src/api/routes/linkedin.py`

```python
@router.post("/linkedin/connect")
async def start_linkedin_connection(
    credentials: LinkedInCredentials,
    client_id: UUID = Depends(get_current_client_id)
):
    """
    Start LinkedIn connection process.
    Saves encrypted credentials, sets status to 'pending'.
    Returns instructions for next steps.
    """

@router.post("/linkedin/verify-2fa")
async def verify_2fa_code(
    code: str,
    client_id: UUID = Depends(get_current_client_id)
):
    """
    Submit 2FA code received from LinkedIn.
    """

@router.get("/linkedin/status")
async def get_linkedin_status(
    client_id: UUID = Depends(get_current_client_id)
):
    """
    Get current LinkedIn connection status.
    """

@router.post("/linkedin/disconnect")
async def disconnect_linkedin(
    client_id: UUID = Depends(get_current_client_id)
):
    """
    Disconnect LinkedIn account.
    """
```

### LI-005: Update Onboarding Flow - LinkedIn Step (1h)
**File:** `frontend/app/onboarding/linkedin/page.tsx`

```tsx
export default function LinkedInConnectionPage() {
    // States: form | verifying | connecting | success | error
    
    return (
        <OnboardingLayout step={6} title="Connect LinkedIn">
            {state === 'form' && (
                <LinkedInCredentialForm onSubmit={handleSubmit} />
            )}
            
            {state === 'verifying' && (
                <TwoFactorInput onSubmit={handleVerify} />
            )}
            
            {state === 'connecting' && (
                <ConnectionProgress />
            )}
            
            {state === 'success' && (
                <ConnectionSuccess onContinue={goToNext} />
            )}
            
            <SkipButton onClick={skipLinkedIn} />
        </OnboardingLayout>
    );
}
```

### LI-006: Create LinkedIn Credential Form Component (1h)
**File:** `frontend/components/onboarding/LinkedInCredentialForm.tsx`

```tsx
export function LinkedInCredentialForm({ onSubmit }) {
    return (
        <form onSubmit={handleSubmit}>
            <div className="space-y-4">
                <div>
                    <Label>LinkedIn Email</Label>
                    <Input 
                        type="email" 
                        placeholder="your@email.com"
                        {...register('linkedin_email')}
                    />
                </div>
                
                <div>
                    <Label>LinkedIn Password</Label>
                    <Input 
                        type="password"
                        {...register('linkedin_password')}
                    />
                </div>
                
                <SecurityNotice />
                
                <Button type="submit">Connect LinkedIn</Button>
            </div>
        </form>
    );
}

function SecurityNotice() {
    return (
        <div className="bg-blue-50 p-4 rounded-lg text-sm">
            <h4 className="font-medium">Your credentials are secure</h4>
            <ul className="mt-2 space-y-1 text-blue-700">
                <li>✓ Encrypted at rest using AES-256</li>
                <li>✓ Only used for outreach automation</li>
                <li>✓ We never post to your feed</li>
                <li>✓ Disconnect anytime from settings</li>
            </ul>
        </div>
    );
}
```

### LI-007: Create 2FA Input Component (30min)
**File:** `frontend/components/onboarding/LinkedInTwoFactor.tsx`

```tsx
export function LinkedInTwoFactor({ onSubmit, onResend }) {
    return (
        <div className="space-y-4">
            <div className="text-center">
                <PhoneIcon className="mx-auto h-12 w-12 text-blue-500" />
                <h3>Verification Required</h3>
                <p className="text-muted-foreground">
                    LinkedIn sent a code to your phone or email.
                    Enter it below to complete connection.
                </p>
            </div>
            
            <Input
                type="text"
                maxLength={6}
                placeholder="000000"
                className="text-center text-2xl tracking-widest"
                {...register('code')}
            />
            
            <Button onClick={handleSubmit}>Verify</Button>
            
            <Button variant="link" onClick={onResend}>
                Resend code
            </Button>
        </div>
    );
}
```

### LI-008: Update Settings Page - LinkedIn Section (30min)
**File:** `frontend/app/dashboard/settings/linkedin/page.tsx`

```tsx
export default function LinkedInSettingsPage() {
    const { data: status } = useLinkedInStatus();
    
    return (
        <SettingsLayout>
            <Card>
                <CardHeader>
                    <CardTitle>LinkedIn Connection</CardTitle>
                </CardHeader>
                <CardContent>
                    {status?.connected ? (
                        <ConnectedState 
                            profile={status.profile}
                            onDisconnect={handleDisconnect}
                        />
                    ) : (
                        <DisconnectedState 
                            onConnect={handleConnect}
                        />
                    )}
                </CardContent>
            </Card>
        </SettingsLayout>
    );
}
```

### LI-009: Admin Notification for Manual HeyReach Connection (30min)
**File:** Update `src/api/routes/linkedin.py`

When credentials are saved:
1. Send notification to admin (Slack/email)
2. Include client name, LinkedIn email
3. Link to HeyReach dashboard for manual connection
4. Update status via webhook when connected

```python
async def notify_admin_new_linkedin(client_id: UUID, linkedin_email: str):
    """Send notification for manual HeyReach connection"""
    # Slack webhook or email to admin
```

### LI-010: Write Tests (1h)
**File:** `tests/test_services/test_linkedin_connection_service.py`

```python
class TestLinkedInConnectionService:
    async def test_save_credentials_encrypted(self):
        """Credentials should be encrypted in database"""
        
    async def test_get_credentials_decrypted(self):
        """Retrieved credentials should be decrypted"""
        
    async def test_update_status(self):
        """Status updates should work"""
        
    async def test_2fa_flow(self):
        """2FA code submission should work"""
        
    async def test_mark_connected(self):
        """Connection completion should update all fields"""
        
    async def test_disconnect(self):
        """Disconnect should clear heyreach_sender_id"""
```

---

## Connection Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT ONBOARDING                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6: Connect LinkedIn                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  LinkedIn Email: [________________________]               │  │
│  │  LinkedIn Password: [________________________]            │  │
│  │                                                           │  │
│  │  🔒 Your credentials are encrypted and secure             │  │
│  │                                                           │  │
│  │  [Connect LinkedIn]              [Skip for Now]           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                    Client clicks "Connect"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Agency OS Backend                                               │
│  1. Encrypt credentials (AES-256)                               │
│  2. Save to client_linkedin_credentials                         │
│  3. Set status = 'pending'                                      │
│  4. Notify admin (Slack/email)                                  │
│  5. Return "awaiting verification" to client                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Admin (You) - Manual Step                                       │
│  1. Log into HeyReach                                           │
│  2. Add LinkedIn account with credentials                       │
│  3. Handle 2FA if prompted                                      │
│  4. Copy sender_id                                              │
│  5. Update Agency OS via admin endpoint                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Agency OS - Mark Connected                                      │
│  1. Save heyreach_sender_id                                     │
│  2. Save profile info                                           │
│  3. Set status = 'connected'                                    │
│  4. Notify client (email)                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LinkedIn Automation ACTIVE                                      │
│  • HeyReach API creates campaigns                               │
│  • Sends connection requests                                    │
│  • Sends messages                                               │
│  • Tracks replies                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Future Automation (Phase 2)

Currently, connecting to HeyReach is manual. Future enhancement:

**Puppeteer Automation Script:**
```python
# scripts/heyreach_connector.py
async def connect_linkedin_to_heyreach(
    linkedin_email: str,
    linkedin_password: str,
    proxy: Optional[str] = None
) -> str:
    """
    Automate HeyReach LinkedIn connection.
    Returns: heyreach_sender_id
    """
    browser = await launch_browser(headless=True)
    page = await browser.new_page()
    
    # Login to HeyReach
    await page.goto('https://app.heyreach.io/login')
    # ... login flow
    
    # Navigate to LinkedIn accounts
    await page.goto('https://app.heyreach.io/linkedin-accounts')
    
    # Click "Connect Account"
    await page.click('[data-testid="connect-account"]')
    
    # Enter credentials
    await page.fill('[name="email"]', linkedin_email)
    await page.fill('[name="password"]', linkedin_password)
    
    # Handle 2FA if prompted
    # ... 2FA detection and handling
    
    # Get sender_id from page
    sender_id = await page.evaluate('...')
    
    return sender_id
```

This would eliminate manual admin step but adds complexity. Deferred to post-launch.

---

## Environment Variables

```bash
# Credential encryption (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
CREDENTIAL_ENCRYPTION_KEY=your-32-byte-base64-encoded-key

# HeyReach (already configured)
HEYREACH_API_KEY=your-heyreach-api-key

# Admin notifications
ADMIN_SLACK_WEBHOOK_URL=https://hooks.slack.com/...
ADMIN_EMAIL=david.stephens@keiracom.com
```

---

## Security Considerations

1. **Encryption at Rest:** All LinkedIn passwords encrypted using Fernet (AES-128-CBC)
2. **Key Rotation:** CREDENTIAL_ENCRYPTION_KEY should be rotated periodically
3. **Access Control:** Only service role can decrypt credentials
4. **Audit Logging:** All credential access logged
5. **2FA Support:** Handle LinkedIn's 2FA gracefully
6. **Rate Limiting:** Prevent brute force on credential endpoints

---

## Testing Checklist

| Test | Expected | Status |
|------|----------|--------|
| Save credentials | Encrypted in DB | ⬜ |
| Get credentials | Decrypted correctly | ⬜ |
| 2FA flow | Code accepted | ⬜ |
| Skip flow | Onboarding continues | ⬜ |
| Settings page | Shows status | ⬜ |
| Disconnect | Clears sender_id | ⬜ |
| Admin notification | Slack/email sent | ⬜ |

---

## Success Criteria

- [ ] Client can enter LinkedIn credentials in onboarding
- [ ] Credentials stored encrypted
- [ ] Admin receives notification for manual connection
- [ ] Admin can update status via endpoint
- [ ] Client sees connection status in settings
- [ ] Client can disconnect anytime
- [ ] HeyReach API can use sender_id for campaigns

---

## Files to Create/Modify

**New Files:**
- `supabase/migrations/031_linkedin_credentials.sql`
- `src/services/linkedin_connection_service.py`
- `src/utils/encryption.py`
- `src/api/routes/linkedin.py`
- `frontend/app/onboarding/linkedin/page.tsx`
- `frontend/components/onboarding/LinkedInCredentialForm.tsx`
- `frontend/components/onboarding/LinkedInTwoFactor.tsx`
- `frontend/app/dashboard/settings/linkedin/page.tsx`
- `tests/test_services/test_linkedin_connection_service.py`

**Modified Files:**
- `src/api/routes/__init__.py` (add linkedin router)
- `frontend/app/onboarding/layout.tsx` (add step 6)
- `src/config/settings.py` (add encryption key)
