# SKILL.md — LinkedIn Credential Connection

**Skill:** LinkedIn Credential-Based Connection for HeyReach  
**Author:** Dave + Claude  
**Version:** 1.0  
**Created:** January 7, 2026  
**Phase:** 24H

---

## Purpose

Enable Agency OS to:
1. Collect LinkedIn credentials securely during onboarding
2. Store encrypted credentials for HeyReach connection
3. Handle 2FA flow when LinkedIn requires verification
4. Connect credentials to HeyReach API for automated outreach
5. Manage connection status and allow disconnection

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CLIENT ONBOARDING                                │
│                                                                         │
│   Step 5: Website/ICP ──► Step 6: LinkedIn ──► Step 7: Webhook ──► Done│
│                                   │                                     │
│                                   ▼                                     │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │  LinkedIn Credential Form                                        │  │
│   │  ┌─────────────────────────────────────────────────────────┐    │  │
│   │  │  Email: [_______________________________]                │    │  │
│   │  │  Password: [_______________________________]             │    │  │
│   │  │                                                          │    │  │
│   │  │  🔒 Encrypted with AES-256. Only used for outreach.      │    │  │
│   │  │                                                          │    │  │
│   │  │  [Connect LinkedIn]              [Skip for Now]          │    │  │
│   │  └─────────────────────────────────────────────────────────┘    │  │
│   └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          BACKEND FLOW                                   │
│                                                                         │
│   1. Encrypt credentials (Fernet/AES-256)                              │
│   2. Save to client_linkedin_credentials                               │
│   3. Call HeyReach API to add sender                                   │
│   4. If 2FA required → Return to client for code                       │
│   5. Submit 2FA → Complete connection                                  │
│   6. Save heyreach_sender_id                                           │
│   7. Mark status = 'connected'                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       LINKEDIN AUTOMATION                               │
│                                                                         │
│   LinkedIn Engine ──► HeyReach API ──► LinkedIn                        │
│                                                                         │
│   • Connection requests                                                 │
│   • Direct messages                                                     │
│   • Follow-up sequences                                                 │
│   • Profile views                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Table: `client_linkedin_credentials`

```sql
CREATE TABLE client_linkedin_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Encrypted credentials (Fernet AES-256)
    linkedin_email_encrypted TEXT NOT NULL,
    linkedin_password_encrypted TEXT NOT NULL,
    
    -- Connection status
    connection_status TEXT NOT NULL DEFAULT 'pending',
    -- Values: pending, connecting, awaiting_2fa, connected, failed, disconnected
    
    -- HeyReach integration
    heyreach_sender_id TEXT,
    heyreach_account_id TEXT,
    
    -- LinkedIn profile info (populated after connection)
    linkedin_profile_url TEXT,
    linkedin_profile_name TEXT,
    linkedin_headline TEXT,
    linkedin_connection_count INTEGER,
    
    -- 2FA handling
    two_fa_method TEXT,  -- 'sms', 'email', 'authenticator'
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

-- RLS policies
ALTER TABLE client_linkedin_credentials ENABLE ROW LEVEL SECURITY;

CREATE POLICY "clients_own_linkedin" ON client_linkedin_credentials
    FOR ALL USING (client_id = auth.uid());

CREATE POLICY "service_role_all" ON client_linkedin_credentials
    FOR ALL USING (auth.role() = 'service_role');
```

---

## File Structure

```
src/
├── services/
│   └── linkedin_connection_service.py   # Core service
├── utils/
│   └── encryption.py                    # Credential encryption
├── api/routes/
│   └── linkedin.py                      # API endpoints
├── integrations/
│   └── heyreach.py                      # HeyReach API (exists, extend)

frontend/
├── app/onboarding/
│   └── linkedin/
│       └── page.tsx                     # Onboarding step
├── app/dashboard/settings/
│   └── linkedin/
│       └── page.tsx                     # Settings page
├── components/onboarding/
│   ├── LinkedInCredentialForm.tsx
│   └── LinkedInTwoFactor.tsx
├── hooks/
│   └── use-linkedin.ts                  # React Query hooks
├── lib/api/
│   └── linkedin.ts                      # API fetchers

supabase/migrations/
└── 031_linkedin_credentials.sql
```

---

## Service Implementation

### LinkedInConnectionService

```python
# src/services/linkedin_connection_service.py

from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.models.linkedin_credential import LinkedInCredential
from src.utils.encryption import encrypt_credential, decrypt_credential
from src.integrations.heyreach import heyreach_client
from src.config.settings import settings


class LinkedInConnectionService:
    """Manages LinkedIn credential storage and HeyReach connection."""
    
    async def start_connection(
        self,
        db: AsyncSession,
        client_id: UUID,
        linkedin_email: str,
        linkedin_password: str
    ) -> dict:
        """
        Start LinkedIn connection process.
        
        1. Encrypt and store credentials
        2. Call HeyReach API to add sender
        3. Return status (connected, awaiting_2fa, or error)
        """
        # Encrypt credentials
        email_encrypted = encrypt_credential(linkedin_email)
        password_encrypted = encrypt_credential(linkedin_password)
        
        # Check if record exists
        existing = await self.get_credential(db, client_id)
        
        if existing:
            # Update existing record
            existing.linkedin_email_encrypted = email_encrypted
            existing.linkedin_password_encrypted = password_encrypted
            existing.connection_status = 'connecting'
            existing.last_error = None
            await db.commit()
            credential = existing
        else:
            # Create new record
            credential = LinkedInCredential(
                client_id=client_id,
                linkedin_email_encrypted=email_encrypted,
                linkedin_password_encrypted=password_encrypted,
                connection_status='connecting'
            )
            db.add(credential)
            await db.commit()
        
        # Attempt HeyReach connection
        try:
            result = await heyreach_client.add_linkedin_account(
                email=linkedin_email,
                password=linkedin_password
            )
            
            if result.get('requires_2fa'):
                credential.connection_status = 'awaiting_2fa'
                credential.two_fa_method = result.get('2fa_method', 'unknown')
                credential.two_fa_requested_at = datetime.utcnow()
                await db.commit()
                
                return {
                    'status': 'awaiting_2fa',
                    'method': result.get('2fa_method'),
                    'message': 'Please enter the verification code sent to you'
                }
            
            elif result.get('success'):
                await self._mark_connected(
                    db, credential, result
                )
                return {
                    'status': 'connected',
                    'profile_url': result.get('profile_url'),
                    'profile_name': result.get('profile_name')
                }
            
            else:
                credential.connection_status = 'failed'
                credential.last_error = result.get('error', 'Unknown error')
                credential.error_count += 1
                credential.last_error_at = datetime.utcnow()
                await db.commit()
                
                return {
                    'status': 'failed',
                    'error': result.get('error')
                }
                
        except Exception as e:
            credential.connection_status = 'failed'
            credential.last_error = str(e)
            credential.error_count += 1
            await db.commit()
            raise
    
    async def submit_2fa_code(
        self,
        db: AsyncSession,
        client_id: UUID,
        code: str
    ) -> dict:
        """Submit 2FA verification code."""
        credential = await self.get_credential(db, client_id)
        
        if not credential or credential.connection_status != 'awaiting_2fa':
            raise ValueError("No pending 2FA verification")
        
        # Decrypt credentials to resubmit with 2FA
        email = decrypt_credential(credential.linkedin_email_encrypted)
        password = decrypt_credential(credential.linkedin_password_encrypted)
        
        result = await heyreach_client.verify_2fa(
            email=email,
            password=password,
            code=code
        )
        
        if result.get('success'):
            await self._mark_connected(db, credential, result)
            return {'status': 'connected'}
        else:
            credential.last_error = result.get('error', 'Invalid code')
            await db.commit()
            return {'status': 'failed', 'error': result.get('error')}
    
    async def _mark_connected(
        self,
        db: AsyncSession,
        credential: LinkedInCredential,
        result: dict
    ) -> None:
        """Mark credential as connected with HeyReach data."""
        credential.connection_status = 'connected'
        credential.heyreach_sender_id = result.get('sender_id')
        credential.heyreach_account_id = result.get('account_id')
        credential.linkedin_profile_url = result.get('profile_url')
        credential.linkedin_profile_name = result.get('profile_name')
        credential.linkedin_headline = result.get('headline')
        credential.linkedin_connection_count = result.get('connection_count')
        credential.connected_at = datetime.utcnow()
        credential.last_error = None
        await db.commit()
    
    async def get_credential(
        self,
        db: AsyncSession,
        client_id: UUID
    ) -> Optional[LinkedInCredential]:
        """Get LinkedIn credential for client."""
        stmt = select(LinkedInCredential).where(
            LinkedInCredential.client_id == client_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_status(
        self,
        db: AsyncSession,
        client_id: UUID
    ) -> dict:
        """Get connection status for client."""
        credential = await self.get_credential(db, client_id)
        
        if not credential:
            return {'status': 'not_connected'}
        
        return {
            'status': credential.connection_status,
            'profile_url': credential.linkedin_profile_url,
            'profile_name': credential.linkedin_profile_name,
            'headline': credential.linkedin_headline,
            'connection_count': credential.linkedin_connection_count,
            'connected_at': credential.connected_at.isoformat() if credential.connected_at else None,
            'error': credential.last_error if credential.connection_status == 'failed' else None
        }
    
    async def disconnect(
        self,
        db: AsyncSession,
        client_id: UUID
    ) -> dict:
        """Disconnect LinkedIn account."""
        credential = await self.get_credential(db, client_id)
        
        if not credential:
            raise ValueError("No LinkedIn connection found")
        
        # Remove from HeyReach if connected
        if credential.heyreach_sender_id:
            try:
                await heyreach_client.remove_sender(credential.heyreach_sender_id)
            except Exception as e:
                # Log but don't fail - still disconnect locally
                logger.warning(f"Failed to remove from HeyReach: {e}")
        
        credential.connection_status = 'disconnected'
        credential.heyreach_sender_id = None
        credential.disconnected_at = datetime.utcnow()
        await db.commit()
        
        return {'status': 'disconnected'}


# Singleton
linkedin_connection_service = LinkedInConnectionService()
```

---

## Encryption Utility

```python
# src/utils/encryption.py

from cryptography.fernet import Fernet
from src.config.settings import settings


# Initialize Fernet with key from settings
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
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_credential(ciphertext: str) -> str:
    """Decrypt a credential string."""
    fernet = _get_fernet()
    return fernet.decrypt(ciphertext.encode()).decode()


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key().decode()
```

---

## API Endpoints

```python
# src/api/routes/linkedin.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID

from src.services.linkedin_connection_service import linkedin_connection_service
from src.api.deps import get_db, get_current_client_id


router = APIRouter(prefix="/linkedin", tags=["linkedin"])


class LinkedInConnectRequest(BaseModel):
    linkedin_email: str
    linkedin_password: str


class TwoFactorRequest(BaseModel):
    code: str


@router.post("/connect")
async def start_linkedin_connection(
    request: LinkedInConnectRequest,
    db = Depends(get_db),
    client_id: UUID = Depends(get_current_client_id)
):
    """Start LinkedIn connection process."""
    result = await linkedin_connection_service.start_connection(
        db=db,
        client_id=client_id,
        linkedin_email=request.linkedin_email,
        linkedin_password=request.linkedin_password
    )
    return result


@router.post("/verify-2fa")
async def verify_2fa(
    request: TwoFactorRequest,
    db = Depends(get_db),
    client_id: UUID = Depends(get_current_client_id)
):
    """Submit 2FA verification code."""
    result = await linkedin_connection_service.submit_2fa_code(
        db=db,
        client_id=client_id,
        code=request.code
    )
    return result


@router.get("/status")
async def get_linkedin_status(
    db = Depends(get_db),
    client_id: UUID = Depends(get_current_client_id)
):
    """Get LinkedIn connection status."""
    return await linkedin_connection_service.get_status(db, client_id)


@router.post("/disconnect")
async def disconnect_linkedin(
    db = Depends(get_db),
    client_id: UUID = Depends(get_current_client_id)
):
    """Disconnect LinkedIn account."""
    return await linkedin_connection_service.disconnect(db, client_id)
```

---

## HeyReach Integration Extension

```python
# src/integrations/heyreach.py (extend existing)

async def add_linkedin_account(
    self,
    email: str,
    password: str
) -> dict:
    """
    Add a LinkedIn account to HeyReach.
    
    Returns:
        {
            'success': bool,
            'requires_2fa': bool,
            '2fa_method': str,  # 'sms', 'email', 'authenticator'
            'sender_id': str,
            'account_id': str,
            'profile_url': str,
            'profile_name': str,
            'headline': str,
            'connection_count': int,
            'error': str
        }
    """
    # HeyReach API endpoint for adding LinkedIn account
    # This may vary based on HeyReach's actual API
    response = await self._post(
        "/senders/linkedin",
        json={
            "email": email,
            "password": password
        }
    )
    return response


async def verify_2fa(
    self,
    email: str,
    password: str,
    code: str
) -> dict:
    """Submit 2FA code to complete LinkedIn connection."""
    response = await self._post(
        "/senders/linkedin/verify",
        json={
            "email": email,
            "password": password,
            "code": code
        }
    )
    return response


async def remove_sender(self, sender_id: str) -> dict:
    """Remove a LinkedIn sender from HeyReach."""
    response = await self._delete(f"/senders/{sender_id}")
    return response


async def get_sender(self, sender_id: str) -> dict:
    """Get sender details from HeyReach."""
    response = await self._get(f"/senders/{sender_id}")
    return response
```

---

## Frontend Components

### Onboarding Page

```tsx
// frontend/app/onboarding/linkedin/page.tsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { OnboardingLayout } from '@/components/onboarding/OnboardingLayout';
import { LinkedInCredentialForm } from '@/components/onboarding/LinkedInCredentialForm';
import { LinkedInTwoFactor } from '@/components/onboarding/LinkedInTwoFactor';
import { LinkedInConnecting } from '@/components/onboarding/LinkedInConnecting';
import { LinkedInSuccess } from '@/components/onboarding/LinkedInSuccess';
import { useLinkedInConnect, useLinkedInVerify2FA } from '@/hooks/use-linkedin';
import { Button } from '@/components/ui/button';

type State = 'form' | 'connecting' | '2fa' | 'success' | 'error';

export default function LinkedInOnboardingPage() {
    const router = useRouter();
    const [state, setState] = useState<State>('form');
    const [error, setError] = useState<string | null>(null);
    const [twoFaMethod, setTwoFaMethod] = useState<string | null>(null);
    
    const connectMutation = useLinkedInConnect();
    const verify2FAMutation = useLinkedInVerify2FA();
    
    const handleConnect = async (email: string, password: string) => {
        setState('connecting');
        setError(null);
        
        try {
            const result = await connectMutation.mutateAsync({ 
                linkedin_email: email, 
                linkedin_password: password 
            });
            
            if (result.status === 'connected') {
                setState('success');
            } else if (result.status === 'awaiting_2fa') {
                setTwoFaMethod(result.method);
                setState('2fa');
            } else {
                setError(result.error || 'Connection failed');
                setState('error');
            }
        } catch (err) {
            setError(err.message);
            setState('error');
        }
    };
    
    const handleVerify2FA = async (code: string) => {
        setState('connecting');
        
        try {
            const result = await verify2FAMutation.mutateAsync({ code });
            
            if (result.status === 'connected') {
                setState('success');
            } else {
                setError(result.error || 'Verification failed');
                setState('2fa');
            }
        } catch (err) {
            setError(err.message);
            setState('2fa');
        }
    };
    
    const handleSkip = () => {
        router.push('/onboarding/webhook');
    };
    
    const handleContinue = () => {
        router.push('/onboarding/webhook');
    };
    
    return (
        <OnboardingLayout 
            step={6} 
            totalSteps={7}
            title="Connect LinkedIn"
            description="Enable automated LinkedIn outreach to your prospects"
        >
            {state === 'form' && (
                <>
                    <LinkedInCredentialForm 
                        onSubmit={handleConnect}
                        error={error}
                    />
                    <div className="mt-4 text-center">
                        <Button variant="ghost" onClick={handleSkip}>
                            Skip for now
                        </Button>
                    </div>
                </>
            )}
            
            {state === 'connecting' && (
                <LinkedInConnecting />
            )}
            
            {state === '2fa' && (
                <LinkedInTwoFactor
                    method={twoFaMethod}
                    onSubmit={handleVerify2FA}
                    onBack={() => setState('form')}
                    error={error}
                />
            )}
            
            {state === 'success' && (
                <LinkedInSuccess onContinue={handleContinue} />
            )}
            
            {state === 'error' && (
                <div className="text-center">
                    <p className="text-red-500 mb-4">{error}</p>
                    <Button onClick={() => setState('form')}>
                        Try Again
                    </Button>
                    <Button variant="ghost" onClick={handleSkip} className="ml-2">
                        Skip for now
                    </Button>
                </div>
            )}
        </OnboardingLayout>
    );
}
```

### React Query Hooks

```tsx
// frontend/hooks/use-linkedin.ts

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { linkedinApi } from '@/lib/api/linkedin';

export function useLinkedInStatus() {
    return useQuery({
        queryKey: ['linkedin', 'status'],
        queryFn: linkedinApi.getStatus
    });
}

export function useLinkedInConnect() {
    const queryClient = useQueryClient();
    
    return useMutation({
        mutationFn: linkedinApi.connect,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['linkedin'] });
        }
    });
}

export function useLinkedInVerify2FA() {
    const queryClient = useQueryClient();
    
    return useMutation({
        mutationFn: linkedinApi.verify2FA,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['linkedin'] });
        }
    });
}

export function useLinkedInDisconnect() {
    const queryClient = useQueryClient();
    
    return useMutation({
        mutationFn: linkedinApi.disconnect,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['linkedin'] });
        }
    });
}
```

---

## Environment Variables

```bash
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CREDENTIAL_ENCRYPTION_KEY=your-fernet-key-here

# HeyReach (already exists)
HEYREACH_API_KEY=existing-key
```

---

## Testing Checklist

| Test | Expected | Status |
|------|----------|--------|
| Encrypt/decrypt roundtrip | Original value returned | ⬜ |
| Save credentials | Encrypted in database | ⬜ |
| Start connection | HeyReach API called | ⬜ |
| 2FA flow | Code submission works | ⬜ |
| Connection success | Status = connected | ⬜ |
| Get status | Returns correct state | ⬜ |
| Disconnect | Removes from HeyReach | ⬜ |
| Skip flow | Onboarding continues | ⬜ |
| Settings page | Shows connection | ⬜ |

---

## Security Considerations

1. **Encryption:** Fernet (AES-128-CBC with HMAC)
2. **Key Storage:** CREDENTIAL_ENCRYPTION_KEY in Railway env only
3. **Access Control:** RLS ensures clients only see their own credentials
4. **Decryption:** Only done server-side when calling HeyReach
5. **Logging:** Never log plaintext credentials
6. **2FA:** Handled via HeyReach, we just relay the code

---

## Error Handling

| Error | User Message | Action |
|-------|--------------|--------|
| Invalid credentials | "LinkedIn email or password incorrect" | Show form again |
| 2FA timeout | "Verification expired, please try again" | Restart flow |
| HeyReach API error | "Connection service unavailable" | Retry with backoff |
| Account locked | "LinkedIn account is locked" | Instruct to unlock |
| Rate limited | "Too many attempts, try later" | Show cooldown timer |
