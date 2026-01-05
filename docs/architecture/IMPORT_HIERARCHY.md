# Import Hierarchy — Agency OS

**Status:** ENFORCED  
**Violations:** Will cause circular import errors

---

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 4 (Top)                            │
│                 src/orchestration/                          │
│                                                             │
│  • The glue layer                                           │
│  • CAN import from everything below                         │
│  • Coordinates engines, never imported by them              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       LAYER 3                               │
│                    src/engines/                             │
│                                                             │
│  • Business logic                                           │
│  • CAN import from src/models/                              │
│  • CAN import from src/integrations/                        │
│  • NO imports from other engines (pass data as args)        │
│  • NO imports from src/orchestration/                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       LAYER 2                               │
│                  src/integrations/                          │
│                                                             │
│  • External API wrappers                                    │
│  • CAN import from src/models/                              │
│  • NO imports from src/engines/                             │
│  • NO imports from src/orchestration/                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1 (Bottom)                         │
│                     src/models/                             │
│                                                             │
│  • Pure Pydantic models + SQLAlchemy                        │
│  • NO imports from src/engines/                             │
│  • NO imports from src/orchestration/                       │
│  • CAN import from src/exceptions.py                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Import Rules by Layer

### Layer 1: Models (`src/models/`)
```python
# ALLOWED
from src.exceptions import AgencyOSError
from pydantic import BaseModel
from sqlalchemy import Column

# FORBIDDEN
from src.engines import *        # ❌ NEVER
from src.orchestration import *  # ❌ NEVER
from src.integrations import *   # ❌ NEVER
```

### Layer 2: Integrations (`src/integrations/`)
```python
# ALLOWED
from src.models.lead import Lead
from src.models.client import Client
from src.exceptions import APIError

# FORBIDDEN
from src.engines import *        # ❌ NEVER
from src.orchestration import *  # ❌ NEVER
```

### Layer 3: Engines (`src/engines/`)
```python
# ALLOWED
from src.models.lead import Lead
from src.integrations.apollo import ApolloClient
from src.integrations.resend import ResendClient

# FORBIDDEN
from src.engines.scorer import ScorerEngine  # ❌ No cross-engine imports
from src.orchestration import *               # ❌ NEVER
```

### Layer 4: Orchestration (`src/orchestration/`)
```python
# ALLOWED - Everything below
from src.models.lead import Lead
from src.integrations.apollo import ApolloClient
from src.engines.scorer import ScorerEngine
from src.engines.allocator import AllocatorEngine
```

---

## Dependency Injection Pattern

Engines accept database sessions as arguments, never instantiate them:

```python
class ScorerEngine:
    """
    RULE: Session passed by caller, never instantiated here.
    """
    
    async def score(
        self, 
        db: AsyncSession,  # Passed by caller
        lead_id: str
    ) -> int:
        ...
```

---

## Violation Detection

If you see this error, you've violated the hierarchy:
```
ImportError: cannot import name 'X' from partially initialized module 'src.Y'
(most likely due to a circular import)
```

**Fix:** Check which layer is importing from a higher layer and refactor.
