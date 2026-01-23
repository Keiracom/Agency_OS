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

---

## Additional Layers: Agents, Services, Detectors

The core 4-layer hierarchy above is extended with specialized layers that follow consistent import rules.

### Updated Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 5 (Top)                                │
│                 src/orchestration/                              │
│                                                                 │
│  • The glue layer                                               │
│  • CAN import from ALL layers below                             │
│  • Coordinates engines, agents, services, detectors             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 4                                      │
│                 src/agents/                                     │
│                                                                 │
│  • AI-powered automation layer                                  │
│  • CAN import from: models, integrations, engines, services     │
│  • NO imports from src/orchestration/                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 3                                      │
│       src/engines/  |  src/services/  |  src/detectors/         │
│                                                                 │
│  • Business logic (engines)                                     │
│  • Business services (services)                                 │
│  • Pattern detection (detectors)                                │
│  • CAN import from: models, integrations                        │
│  • NO cross-imports between engines/services/detectors          │
│  • NO imports from src/agents/ or src/orchestration/            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       LAYER 2                                   │
│                  src/integrations/                              │
│                                                                 │
│  • External API wrappers                                        │
│  • CAN import from src/models/                                  │
│  • NO imports from layers above                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 1 (Bottom)                             │
│                     src/models/                                 │
│                                                                 │
│  • Pure Pydantic models + SQLAlchemy                            │
│  • CAN import from src/exceptions.py                            │
│  • NO imports from any other src/ layer                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 0 (Base)                               │
│                  src/exceptions.py                              │
│                                                                 │
│  • Base exception classes                                       │
│  • NO imports from any src/ layer                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 4: Agents (`src/agents/`)

**Purpose:** AI-powered agents for specialized automation tasks using Pydantic AI framework.

**Can Import:** models, integrations, engines, services
**Cannot Import:** orchestration
**Consumers:** orchestration flows only

### Core Agents

| File | Purpose | Key Imports |
|------|---------|-------------|
| `base_agent.py` | Abstract base agent with shared functionality | `exceptions` |
| `cmo_agent.py` | CMO agent for campaign orchestration decisions | `models.campaign`, `models.lead`, `models.base` |
| `content_agent.py` | Content generation for personalized copy | `engines.content`, `models.campaign`, `models.lead` |
| `reply_agent.py` | Reply handling and intent classification | `models.activity`, `models.lead`, `models.base` |
| `icp_discovery_agent.py` | ICP extraction from website analysis | `engines.icp_scraper`, `integrations.anthropic`, `integrations.apify` |
| `campaign_generation_agent.py` | Auto-generate campaign configurations | `models`, `integrations` |

### SDK Agents (`src/agents/sdk_agents/`)

Hot leads (ALS 85+) use SDK-enhanced agents for hyper-personalization.

| File | Purpose | Key Imports |
|------|---------|-------------|
| `sdk_eligibility.py` | Gate functions for SDK routing | None (pure logic) |
| `sdk_tools.py` | Web search/fetch tools for agents | `config.settings` |
| `enrichment_agent.py` | Deep research for hot leads | `integrations.sdk_brain` |
| `email_agent.py` | Personalized email generation | `integrations.sdk_brain` |
| `voice_kb_agent.py` | Voice knowledge base generation | `integrations.sdk_brain` |
| `icp_agent.py` | ICP extraction with web research | `integrations.sdk_brain` |

### Campaign Evolution Agents (`src/agents/campaign_evolution/`)

| File | Purpose | Key Imports |
|------|---------|-------------|
| `who_analyzer_agent.py` | Analyze WHO (audience) performance | `integrations.sdk_brain` |
| `what_analyzer_agent.py` | Analyze WHAT (content) performance | `integrations.sdk_brain` |
| `how_analyzer_agent.py` | Analyze HOW (channel) performance | `integrations.sdk_brain` |
| `campaign_orchestrator_agent.py` | Orchestrate campaign evolution | `integrations.sdk_brain` |

### Skills (`src/agents/skills/`)

Modular AI skills that can be composed into agents.

| File | Purpose | Key Imports |
|------|---------|-------------|
| `base_skill.py` | Abstract base skill with registry | `exceptions` |
| `website_parser.py` | Parse and extract website content | `base_skill` |
| `service_extractor.py` | Extract services from website | `base_skill`, `website_parser` |
| `value_prop_extractor.py` | Extract value propositions | `base_skill`, `website_parser` |
| `portfolio_extractor.py` | Extract client portfolio | `base_skill`, `website_parser` |
| `industry_classifier.py` | Classify industry from content | `base_skill`, `portfolio_extractor` |
| `company_size_estimator.py` | Estimate company size | `base_skill`, `website_parser` |
| `icp_deriver.py` | Derive ICP from analysis | `base_skill`, `industry_classifier` |
| `als_weight_suggester.py` | Suggest ALS scoring weights | `base_skill`, `icp_deriver` |
| `sequence_builder.py` | Build outreach sequences | `base_skill` |
| `messaging_generator.py` | Generate messaging variants | `base_skill` |
| `campaign_splitter.py` | Split campaigns by criteria | `base_skill` |
| `social_enricher.py` | Enrich with social data | `base_skill` |
| `social_profile_discovery.py` | Discover social profiles | `base_skill` |
| `research_skills.py` | Web research utilities | `base_skill`, `integrations.anthropic`, `integrations.apify` |
| `industry_researcher.py` | Industry research | `base_skill`, `integrations.serper` |
| `portfolio_fallback.py` | Fallback portfolio extraction | `base_skill`, `portfolio_extractor` |

### Agent Import Rules

```python
# ALLOWED in agents
from src.models.lead import Lead
from src.models.campaign import Campaign
from src.integrations.anthropic import AnthropicClient
from src.integrations.sdk_brain import create_sdk_brain
from src.engines.content import ContentEngine
from src.exceptions import ValidationError

# FORBIDDEN in agents
from src.orchestration import *  # ❌ NEVER
```

---

## Layer 3: Services (`src/services/`)

**Purpose:** Business logic services for data operations, validation, and specialized functionality.

**Can Import:** models, integrations, config, exceptions
**Cannot Import:** engines, agents, orchestration
**Consumers:** engines, orchestration, API routes

### Core Services

| File | Purpose | Key Imports |
|------|---------|-------------|
| `lead_pool_service.py` | Centralized lead pool CRUD | models |
| `lead_allocator_service.py` | Assign leads to clients | `exceptions` |
| `jit_validator.py` | Just-in-time pre-send validation | models |
| `suppression_service.py` | Lead suppression management | models |
| `customer_import_service.py` | CSV/CRM customer import | `config.settings`, `crm_push_service` |
| `crm_push_service.py` | Push data to client CRMs | `config.settings` |

### Email & Domain Services

| File | Purpose | Key Imports |
|------|---------|-------------|
| `email_events_service.py` | Email engagement event ingestion | `models.activity` |
| `domain_health_service.py` | Domain health (bounce/complaint rates) | `models.activity`, `models.resource_pool` |
| `domain_capacity_service.py` | Domain capacity with health reduction | `models.activity`, `models.resource_pool` |
| `send_limiter.py` | Daily send limits (TEST_MODE) | `config.settings`, `models.activity` |

### Conversation & Reply Services

| File | Purpose | Key Imports |
|------|---------|-------------|
| `thread_service.py` | Conversation thread management | `exceptions` |
| `reply_analyzer.py` | AI-powered reply analysis | `exceptions` |
| `conversation_analytics_service.py` | Conversation analytics for CIS | models |
| `response_timing_service.py` | Response delay calculation | models |

### LinkedIn Services

| File | Purpose | Key Imports |
|------|---------|-------------|
| `linkedin_connection_service.py` | LinkedIn connection management | `config.settings` |
| `linkedin_warmup_service.py` | LinkedIn seat warmup | `models.linkedin_seat` |
| `linkedin_health_service.py` | LinkedIn seat health monitoring | `models.linkedin_seat`, `models.linkedin_connection` |

### Other Services

| File | Purpose | Key Imports |
|------|---------|-------------|
| `timezone_service.py` | Timezone lookup for leads | models |
| `resource_assignment_service.py` | Assign resources to clients | `models.resource_pool`, `models.base` |
| `sequence_generator_service.py` | Auto-generate outreach sequences | models |
| `buyer_signal_service.py` | Query platform buyer signals | models |
| `deal_service.py` | Deal/opportunity management | `exceptions` |
| `meeting_service.py` | Meeting scheduling | `exceptions` |
| `who_refinement_service.py` | Refine WHO from conversion patterns | `models.conversion_patterns` |
| `content_qa_service.py` | Content quality validation | models |
| `digest_service.py` | Daily digest email generation | `models.activity`, `models.campaign`, `models.client`, `models.lead` |
| `voice_retry_service.py` | Voice call retry scheduling | `models.activity`, `models.base` |
| `sdk_usage_service.py` | SDK usage tracking | models |

### Service Import Rules

```python
# ALLOWED in services
from src.models.lead import Lead
from src.models.activity import Activity
from src.config.settings import settings
from src.exceptions import NotFoundError, ValidationError

# FORBIDDEN in services
from src.engines import *        # ❌ NEVER
from src.agents import *         # ❌ NEVER
from src.orchestration import *  # ❌ NEVER
```

**Note:** Services can import other services (e.g., `customer_import_service` imports `crm_push_service`), but this should be minimized to avoid tight coupling.

---

## Layer 3: Detectors (`src/detectors/`)

**Purpose:** Pattern detection and learning from conversion data (Conversion Intelligence System).

**Can Import:** models ONLY
**Cannot Import:** integrations, engines, agents, services, orchestration
**Consumers:** orchestration flows, optimization loops

### Detector Files

| File | Purpose | Key Imports |
|------|---------|-------------|
| `base.py` | Abstract base detector | `models.conversion_patterns` |
| `who_detector.py` | Detect WHO patterns (audience) | `models.base`, `models.conversion_patterns`, `models.lead` |
| `what_detector.py` | Detect WHAT patterns (content) | `models.activity`, `models.conversion_patterns` |
| `when_detector.py` | Detect WHEN patterns (timing) | `models.activity`, `models.conversion_patterns` |
| `how_detector.py` | Detect HOW patterns (channels) | `models.activity`, `models.base`, `models.conversion_patterns`, `models.lead` |
| `funnel_detector.py` | Detect funnel conversion patterns | `models.conversion_patterns` |
| `weight_optimizer.py` | Optimize ALS weights from patterns | `models.base`, `models.lead` |

### Detector Import Rules

```python
# ALLOWED in detectors
from src.models.lead import Lead
from src.models.activity import Activity
from src.models.conversion_patterns import ConversionPattern
from src.models.base import LeadStatus
from src.detectors.base import BaseDetector

# FORBIDDEN in detectors
from src.integrations import *   # ❌ NEVER
from src.engines import *        # ❌ NEVER
from src.services import *       # ❌ NEVER
from src.agents import *         # ❌ NEVER
from src.orchestration import *  # ❌ NEVER
```

---

## Cross-Layer Import Rules Summary

| From Layer | Can Import | Cannot Import |
|------------|------------|---------------|
| orchestration (5) | ALL layers below | - |
| agents (4) | models, integrations, engines, services | orchestration |
| engines (3) | models, integrations | services, detectors, agents, orchestration |
| services (3) | models, integrations, config, exceptions | engines, detectors, agents, orchestration |
| detectors (3) | models ONLY | integrations, engines, services, agents, orchestration |
| integrations (2) | models | ALL except models |
| models (1) | exceptions | ALL except exceptions |
| exceptions (0) | Nothing | ALL |

**Important Notes:**
1. Layer 3 components (engines, services, detectors) cannot import from each other
2. Data flows between Layer 3 components via orchestration layer
3. Services can import other services sparingly (minimize coupling)
4. Agents at Layer 4 can use engines and services as utilities
