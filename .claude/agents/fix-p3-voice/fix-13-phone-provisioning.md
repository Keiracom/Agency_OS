---
name: Fix 13 - Phone Pool Provisioning
description: Implements automated phone number provisioning
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 13: Phone Pool Provisioning

## Gap Reference
- **TODO.md Item:** #13
- **Priority:** P3 Medium (Voice Engine)
- **Location:** `src/engines/voice.py` or `src/services/`
- **Issue:** No automated number provisioning

## Pre-Flight Checks

1. Check existing phone/resource management:
   ```bash
   grep -rn "provision\|phone.*pool\|number.*pool" src/
   ```

2. Check Twilio integration:
   ```bash
   grep -rn "twilio\|Twilio" src/integrations/
   ```

3. Review VOICE.md spec:
   ```bash
   cat docs/architecture/distribution/VOICE.md
   ```

## Implementation Steps

1. **Create phone provisioning service:**
   ```python
   # src/services/phone_provisioning.py
   """
   Contract: src/services/phone_provisioning.py
   Purpose: Automated phone number provisioning via Twilio
   Layer: 3 - services
   Imports: models, integrations
   Consumers: orchestration, voice engine
   """

   from src.integrations.twilio import TwilioClient
   from typing import Optional, List
   from uuid import UUID

   class PhoneProvisioningService:
       def __init__(self, twilio: TwilioClient):
           self.twilio = twilio

       async def provision_number(
           self,
           db: Session,
           client_id: UUID,
           area_code: Optional[str] = None,
           country: str = "AU"
       ) -> PhoneNumber:
           """Provision a new phone number for a client."""
           # Search available numbers
           available = await self.twilio.search_available_numbers(
               country=country,
               area_code=area_code,
               voice_enabled=True,
               sms_enabled=True
           )

           if not available:
               raise NoNumbersAvailableError(f"No numbers in {area_code or country}")

           # Purchase first available
           number = await self.twilio.purchase_number(available[0].phone_number)

           # Configure webhooks
           await self.twilio.configure_number(
               number.sid,
               voice_url=f"{settings.BASE_URL}/api/v1/webhooks/twilio/voice",
               sms_url=f"{settings.BASE_URL}/api/v1/webhooks/twilio/sms"
           )

           # Store in database
           phone_resource = PhoneResource(
               client_id=client_id,
               phone_number=number.phone_number,
               twilio_sid=number.sid,
               status="active",
               provisioned_at=datetime.utcnow()
           )
           db.add(phone_resource)
           db.commit()

           return phone_resource

       async def release_number(
           self,
           db: Session,
           phone_resource_id: UUID
       ) -> bool:
           """Release a phone number back to pool."""
           resource = db.query(PhoneResource).get(phone_resource_id)
           if not resource:
               return False

           await self.twilio.release_number(resource.twilio_sid)
           resource.status = "released"
           resource.released_at = datetime.utcnow()
           db.commit()
           return True

       async def check_pool_health(
           self,
           db: Session,
           client_id: UUID,
           min_numbers: int = 2
       ) -> dict:
           """Check if client has enough active numbers."""
           active = db.query(PhoneResource).filter(
               PhoneResource.client_id == client_id,
               PhoneResource.status == "active"
           ).count()

           return {
               "active_count": active,
               "min_required": min_numbers,
               "needs_provisioning": active < min_numbers
           }
   ```

2. **Add to resource pool flow:**
   - Check pool health during client setup
   - Auto-provision when below minimum

## Acceptance Criteria

- [ ] PhoneProvisioningService class created
- [ ] provision_number() searches and purchases from Twilio
- [ ] Webhooks configured on new numbers
- [ ] Numbers stored in database with client association
- [ ] release_number() returns number to Twilio
- [ ] check_pool_health() monitors pool size

## Validation

```bash
# Check service exists
ls -la src/services/phone_provisioning.py

# Verify no syntax errors
python -m py_compile src/services/phone_provisioning.py

# Type check
mypy src/services/phone_provisioning.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #13
2. Report: "Fixed #13. Phone provisioning service implemented with Twilio integration."
