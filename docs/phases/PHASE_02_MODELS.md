# Phase 2: Models & Schemas

**Status:** ✅ Complete  
**Tasks:** 7  
**Dependencies:** Phase 1 complete

---

## Overview

Create Pydantic models and SQLAlchemy schemas for all core entities.

---

## Tasks

| Task ID | Task Name | Description | Files | Complexity |
|---------|-----------|-------------|-------|------------|
| MOD-001 | Base model | SoftDeleteMixin, UUIDv7 | `src/models/base.py` | M |
| MOD-002 | Client model | Client with subscription status | `src/models/client.py` | M |
| MOD-003 | User model | User profile | `src/models/user.py` | S |
| MOD-004 | Membership model | User-Client many-to-many | `src/models/membership.py` | M |
| MOD-005 | Campaign model | Campaign with allocation % | `src/models/campaign.py` | M |
| MOD-006 | Lead model | Lead with ALS fields | `src/models/lead.py` | L |
| MOD-007 | Activity model | Activity with message ID | `src/models/activity.py` | S |

---

## Layer Rules

Models are **Layer 1 (Bottom)**:
- Pure Pydantic models + SQLAlchemy
- NO imports from `src/engines/`
- NO imports from `src/orchestration/`
- CAN import from `src/exceptions.py`

---

## Key Patterns

### SoftDeleteMixin

```python
class SoftDeleteMixin:
    deleted_at: Optional[datetime] = None
    
    def soft_delete(self):
        self.deleted_at = datetime.utcnow()
```

### UUIDv7

```python
from uuid_extensions import uuid7

class BaseModel:
    id: UUID = Field(default_factory=uuid7)
```

---

## Model Relationships

```
Client (1) ──────────< Membership >────────── (N) User
   │
   └──< Campaign (N)
          │
          └──< Lead (N)
                 │
                 └──< Activity (N)
```

---

## Full Schema Details

See `docs/specs/database/SCHEMA_OVERVIEW.md` for complete SQL definitions.
