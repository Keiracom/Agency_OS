---
name: Fix 34 - Security Architecture Documentation
description: Creates SECURITY.md documenting security architecture
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
  - Glob
---

# Fix 34: SECURITY.md Missing

## Gap Reference
- **TODO.md Item:** #34
- **Priority:** P5 Future
- **Location:** `docs/architecture/foundation/SECURITY.md`
- **Issue:** Auth, RBAC, API keys, data encryption, audit logging not documented

## Pre-Flight Checks

1. Check if file exists:
   ```bash
   ls docs/architecture/foundation/SECURITY.md
   ```

2. Inventory existing security code:
   ```bash
   grep -rn "auth\|jwt\|token\|encrypt\|hash\|rbac\|permission" src/
   ```

3. Check Supabase auth usage:
   ```bash
   grep -rn "supabase.*auth\|get_current_user" src/api/
   ```

4. Check for existing security docs:
   ```bash
   find docs/ -name "*security*" -o -name "*auth*"
   ```

## Implementation Steps

1. **Create SECURITY.md:**
   ```markdown
   # Security Architecture

   **Purpose:** Document all security mechanisms in Agency OS
   **Last Updated:** [DATE]

   ---

   ## Overview

   Agency OS implements defense-in-depth security across:
   - Authentication (who you are)
   - Authorization (what you can do)
   - Data protection (encryption, handling)
   - Audit logging (what happened)
   - API security (rate limiting, validation)

   ---

   ## Authentication

   ### Provider: Supabase Auth

   | Component | Implementation |
   |-----------|----------------|
   | Identity Provider | Supabase Auth |
   | Token Type | JWT (RS256) |
   | Token Lifetime | 1 hour (configurable) |
   | Refresh Token | 7 days |
   | Session Storage | HttpOnly cookies |

   ### Authentication Flow

   ```
   1. User submits credentials
   2. Supabase validates and returns JWT + refresh token
   3. Frontend stores in HttpOnly cookie
   4. Backend validates JWT on each request
   5. Token auto-refreshes before expiry
   ```

   ### Backend Verification

   ```python
   # src/api/dependencies/auth.py
   from fastapi import Depends, HTTPException
   from src.integrations.supabase import supabase_client

   async def get_current_user(token: str = Depends(oauth2_scheme)):
       user = supabase_client.auth.get_user(token)
       if not user:
           raise HTTPException(401, "Invalid token")
       return user
   ```

   ---

   ## Authorization (RBAC)

   ### Role Hierarchy

   | Role | Level | Permissions |
   |------|-------|-------------|
   | super_admin | 100 | All actions, all clients |
   | admin | 80 | All actions, own client only |
   | manager | 60 | Manage campaigns, view reports |
   | user | 40 | View dashboards, limited actions |
   | readonly | 20 | View only |

   ### Permission Checks

   ```python
   # src/api/dependencies/permissions.py
   def require_role(min_role: str):
       def checker(user = Depends(get_current_user)):
           if user.role_level < ROLE_LEVELS[min_role]:
               raise HTTPException(403, "Insufficient permissions")
           return user
       return checker

   # Usage
   @router.delete("/campaigns/{id}")
   async def delete_campaign(
       id: UUID,
       user = Depends(require_role("manager"))
   ):
       ...
   ```

   ### Client Isolation

   - Users can only access their own client's data
   - All queries filter by `client_id`
   - Super admins can switch client context

   ---

   ## API Security

   ### Rate Limiting

   | Endpoint Type | Limit | Window |
   |---------------|-------|--------|
   | Auth endpoints | 10 | 1 minute |
   | API endpoints | 100 | 1 minute |
   | Webhook endpoints | 1000 | 1 minute |
   | Export endpoints | 5 | 1 minute |

   ### Input Validation

   - All inputs validated via Pydantic schemas
   - SQL injection prevented via SQLAlchemy ORM
   - XSS prevented via output encoding
   - Path traversal prevented via path validation

   ### API Key Management

   ```python
   # API keys for external integrations
   class APIKey(Base):
       id: UUID
       client_id: UUID
       key_hash: str  # bcrypt hashed
       prefix: str    # First 8 chars for identification
       scopes: List[str]
       expires_at: Optional[datetime]
       last_used_at: Optional[datetime]
   ```

   ---

   ## Data Protection

   ### Encryption

   | Data Type | At Rest | In Transit |
   |-----------|---------|------------|
   | Database | AES-256 (Supabase managed) | TLS 1.3 |
   | Credentials | bcrypt (passwords), AES-256 (API keys) | TLS 1.3 |
   | PII | Column-level encryption where required | TLS 1.3 |
   | Backups | Encrypted (Supabase managed) | TLS 1.3 |

   ### Sensitive Data Handling

   ```python
   # Fields that are encrypted/hashed
   SENSITIVE_FIELDS = [
       "password",      # bcrypt hashed
       "api_key",       # AES-256 encrypted
       "access_token",  # AES-256 encrypted
       "phone",         # Plain but access controlled
       "email",         # Plain but access controlled
   ]

   # Never logged
   NEVER_LOG_FIELDS = [
       "password",
       "api_key",
       "access_token",
       "credit_card",
   ]
   ```

   ### Data Retention

   | Data Type | Retention | Deletion |
   |-----------|-----------|----------|
   | User data | Until account deletion | Hard delete on request |
   | Leads | Configurable (default 2 years) | Soft delete |
   | Activity logs | 90 days | Auto-purge |
   | Voice recordings | 90 days | Auto-purge |
   | Audit logs | 7 years | Archived |

   ---

   ## Audit Logging

   ### What's Logged

   | Event Type | Details Captured |
   |------------|------------------|
   | Authentication | Login, logout, failed attempts |
   | Authorization | Permission denials |
   | Data access | Who accessed what |
   | Data changes | Create, update, delete |
   | API calls | External integration calls |
   | Admin actions | User management, settings changes |

   ### Audit Log Schema

   ```python
   class AuditLog(Base):
       id: UUID
       timestamp: datetime
       user_id: Optional[UUID]
       client_id: Optional[UUID]
       action: str
       resource_type: str
       resource_id: Optional[UUID]
       old_value: Optional[JSONB]
       new_value: Optional[JSONB]
       ip_address: str
       user_agent: str
       success: bool
       error_message: Optional[str]
   ```

   ---

   ## Security Headers

   ```python
   # Applied via middleware
   SECURITY_HEADERS = {
       "X-Content-Type-Options": "nosniff",
       "X-Frame-Options": "DENY",
       "X-XSS-Protection": "1; mode=block",
       "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
       "Content-Security-Policy": "default-src 'self'",
       "Referrer-Policy": "strict-origin-when-cross-origin",
   }
   ```

   ---

   ## Secrets Management

   ### Environment Variables

   | Secret | Storage | Rotation |
   |--------|---------|----------|
   | DATABASE_URL | Railway env | Manual |
   | SUPABASE_KEY | Railway env | Manual |
   | JWT_SECRET | Railway env | Manual (coordinate with Supabase) |
   | API keys (3rd party) | Railway env | Manual |

   ### Never Commit

   ```
   .env
   .env.local
   *.pem
   *.key
   credentials.json
   ```

   ---

   ## Compliance Considerations

   ### Australian Privacy Act

   - Consent required for data collection
   - Right to access and deletion
   - Data breach notification (72 hours)
   - Cross-border data transfer restrictions

   ### DNCR Compliance

   - Check DNCR before voice/SMS outreach
   - Maintain internal suppression list
   - Quarterly DNCR list updates

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

   1. Identify and contain
   2. Assess impact
   3. Notify stakeholders (if required)
   4. Remediate
   5. Post-incident review

   ---

   For gaps and implementation status, see `../TODO.md`.
   ```

2. **Add to ARCHITECTURE_INDEX.md**

3. **Update TODO.md** — delete gap row #34

## Acceptance Criteria

- [ ] SECURITY.md created with all sections
- [ ] Authentication documented (Supabase, JWT)
- [ ] Authorization documented (RBAC, roles)
- [ ] API security documented (rate limits, validation)
- [ ] Data protection documented (encryption, PII)
- [ ] Audit logging documented
- [ ] Compliance considerations documented
- [ ] Added to ARCHITECTURE_INDEX.md

## Validation

```bash
# Check file exists
ls docs/architecture/foundation/SECURITY.md

# Check all sections present
grep -n "Authentication\|Authorization\|Data Protection\|Audit" docs/architecture/foundation/SECURITY.md

# Check in index
grep -n "SECURITY" docs/architecture/ARCHITECTURE_INDEX.md
```

## Post-Fix

1. Update TODO.md — delete gap row #34
2. Report: "Fixed #34. SECURITY.md created with auth, RBAC, encryption, audit logging."
