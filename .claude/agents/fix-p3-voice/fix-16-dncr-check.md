---
name: Fix 16 - DNCR Check for Voice
description: Adds DNCR registry check before voice calls
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 16: DNCR Check for Voice

## Gap Reference
- **TODO.md Item:** #16
- **Priority:** P3 Medium (Voice Engine)
- **Location:** `src/engines/voice.py`
- **Issue:** Voice calls not checking DNCR registry

## Pre-Flight Checks

1. Check existing DNCR/DNC handling:
   ```bash
   grep -rn "dncr\|dnc\|do.not.call" src/
   ```

2. Check if SMS already has DNC logic (can reuse):
   ```bash
   grep -rn "dncr\|dnc" src/engines/sms.py
   ```

3. Check suppression service:
   ```bash
   grep -rn "suppression\|suppress" src/services/
   ```

## Implementation Steps

1. **Check if DNCR integration exists:**
   ```bash
   ls src/integrations/dncr.py
   ```

2. **If no DNCR integration, create one:**
   ```python
   # src/integrations/dncr.py
   """
   Contract: src/integrations/dncr.py
   Purpose: Australian DNCR (Do Not Call Register) lookup
   Layer: 2 - integrations
   Imports: models only
   Consumers: engines, services
   """

   from typing import Optional
   import httpx

   class DNCRClient:
       """Australian Do Not Call Register API client."""

       def __init__(self, api_key: str, account_id: str):
           self.api_key = api_key
           self.account_id = account_id
           self.base_url = "https://api.dncr.gov.au/v1"

       async def is_registered(self, phone_number: str) -> bool:
           """Check if phone number is on DNCR.

           Returns True if number is registered (DO NOT CALL).
           """
           # Normalize phone number
           normalized = self._normalize_number(phone_number)

           async with httpx.AsyncClient() as client:
               response = await client.post(
                   f"{self.base_url}/lookup",
                   headers={"Authorization": f"Bearer {self.api_key}"},
                   json={
                       "account_id": self.account_id,
                       "numbers": [normalized]
                   }
               )
               response.raise_for_status()
               result = response.json()

           return result.get("registered", False)

       def _normalize_number(self, phone: str) -> str:
           """Normalize to E.164 format."""
           # Remove spaces, dashes
           clean = "".join(c for c in phone if c.isdigit() or c == "+")
           # Add AU country code if missing
           if not clean.startswith("+"):
               if clean.startswith("0"):
                   clean = "+61" + clean[1:]
               else:
                   clean = "+61" + clean
           return clean
   ```

3. **Add DNCR check to voice.py:**
   ```python
   from src.integrations.dncr import DNCRClient

   dncr_client = DNCRClient(
       api_key=settings.DNCR_API_KEY,
       account_id=settings.DNCR_ACCOUNT_ID
   )

   async def initiate_call(db: Session, lead_id: UUID, ...) -> CallResult:
       lead = db.query(Lead).get(lead_id)

       # DNCR check (legal requirement in Australia)
       if await dncr_client.is_registered(lead.phone):
           # Mark lead as suppressed
           lead.suppressed = True
           lead.suppression_reason = "dncr_registered"
           db.commit()

           return CallResult(
               status="blocked",
               reason="dncr_registered",
               message="Number registered on Do Not Call Register"
           )

       # Proceed with call...
   ```

4. **Add caching** to avoid repeated lookups:
   ```python
   # Cache DNCR results for 24 hours (numbers don't change often)
   from functools import lru_cache
   import time

   @lru_cache(maxsize=10000)
   def _cached_dncr_check(phone: str, cache_key: int) -> bool:
       # cache_key = current_day to invalidate daily
       return asyncio.run(dncr_client.is_registered(phone))

   async def check_dncr_cached(phone: str) -> bool:
       cache_key = int(time.time() // 86400)  # Day number
       return _cached_dncr_check(phone, cache_key)
   ```

## Acceptance Criteria

- [ ] DNCRClient integration exists (or equivalent)
- [ ] Voice calls check DNCR before dialing
- [ ] Registered numbers blocked with clear reason
- [ ] Lead marked as suppressed with reason
- [ ] Results cached to minimize API calls
- [ ] Logging for blocked calls

## Validation

```bash
# Check DNCR integration exists
ls -la src/integrations/dncr.py

# Check voice.py has DNCR check
grep -n "dncr\|DNCR" src/engines/voice.py

# Verify no syntax errors
python -m py_compile src/engines/voice.py

# Type check
mypy src/engines/voice.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #16
2. Report: "Fixed #16. DNCR check added to voice engine with caching."
