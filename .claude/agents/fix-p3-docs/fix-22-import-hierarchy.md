---
name: Fix 22 - Import Hierarchy Documentation
description: Completes IMPORT_HIERARCHY.md with agents, services, detectors
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
  - Glob
---

# Fix 22: IMPORT_HIERARCHY.md Incomplete

## Gap Reference
- **TODO.md Item:** #22
- **Priority:** P3 Medium (Documentation)
- **Location:** `docs/architecture/foundation/IMPORT_HIERARCHY.md`
- **Issue:** Agents, services, detectors layers not documented

## Pre-Flight Checks

1. Read current IMPORT_HIERARCHY.md:
   ```bash
   cat docs/architecture/foundation/IMPORT_HIERARCHY.md
   ```

2. Inventory actual directories:
   ```bash
   ls -la src/agents/
   ls -la src/services/
   ls -la src/detectors/
   ```

3. Check existing layer definitions:
   ```bash
   grep -n "Layer\|layer" docs/architecture/foundation/IMPORT_HIERARCHY.md
   ```

## Implementation Steps

1. **Map actual import relationships:**
   ```bash
   # Check what agents import
   grep -rn "^from src\.\|^import src\." src/agents/*.py | head -50

   # Check what services import
   grep -rn "^from src\.\|^import src\." src/services/*.py | head -50

   # Check what detectors import
   grep -rn "^from src\.\|^import src\." src/detectors/*.py | head -50
   ```

2. **Update layer diagram** to include all layers:
   ```markdown
   ## Import Hierarchy

   ```
   Layer 5: src/orchestration/    → Can import ALL below
   Layer 4: src/agents/           → models, integrations, engines, services
   Layer 3: src/engines/          → models, integrations
   Layer 3: src/services/         → models, integrations
   Layer 3: src/detectors/        → models, integrations
   Layer 2: src/integrations/     → models ONLY
   Layer 1: src/models/           → exceptions ONLY
   Layer 0: src/exceptions/       → Nothing (base)
   ```
   ```

3. **Document each new layer:**
   ```markdown
   ### Layer 4: Agents (`src/agents/`)

   **Purpose:** AI agents for specialized tasks (SDK, enrichment, ICP)
   **Can Import:** models, integrations, engines, services
   **Cannot Import:** orchestration
   **Consumers:** orchestration flows only

   | Agent | Purpose | Key Imports |
   |-------|---------|-------------|
   | enrichment_agent.py | Deep lead research | scout, claude SDK |
   | email_agent.py | Personalized email | content, smart_prompts |
   | voice_kb_agent.py | Voice knowledge base | claude SDK |
   | icp_agent.py | ICP extraction | claude SDK |

   ### Layer 3: Services (`src/services/`)

   **Purpose:** Business logic services (import, suppression, etc.)
   **Can Import:** models, integrations
   **Cannot Import:** engines, agents, orchestration
   **Consumers:** engines, orchestration

   | Service | Purpose | Key Imports |
   |---------|---------|-------------|
   | customer_import_service.py | CSV import logic | models |
   | suppression_service.py | Lead suppression | models |
   | icp_refiner.py | ICP refinement | models |

   ### Layer 3: Detectors (`src/detectors/`)

   **Purpose:** Pattern detection and learning
   **Can Import:** models, integrations
   **Cannot Import:** engines, agents, orchestration
   **Consumers:** orchestration flows

   | Detector | Purpose | Key Imports |
   |----------|---------|-------------|
   | funnel_detector.py | Funnel pattern detection | models |
   | timing_detector.py | Optimal timing detection | models |
   | response_detector.py | Response pattern detection | models |
   ```

4. **Add cross-reference rules:**
   ```markdown
   ## Cross-Layer Rules

   | From Layer | Can Import | Cannot Import |
   |------------|------------|---------------|
   | orchestration | ALL | - |
   | agents | models, integrations, engines, services | orchestration |
   | engines | models, integrations | services, agents, orchestration |
   | services | models, integrations | engines, agents, orchestration |
   | detectors | models, integrations | engines, agents, orchestration |
   | integrations | models | ALL except models |
   | models | exceptions | ALL except exceptions |
   ```

## Acceptance Criteria

- [ ] Agents layer documented with purpose and imports
- [ ] Services layer documented with purpose and imports
- [ ] Detectors layer documented with purpose and imports
- [ ] Layer diagram updated to show all layers
- [ ] Each layer has table of files with purpose
- [ ] Cross-layer import rules clearly defined
- [ ] No circular dependencies documented

## Validation

```bash
# Check all layers are documented
grep -n "Layer.*agents\|Layer.*services\|Layer.*detectors" docs/architecture/foundation/IMPORT_HIERARCHY.md

# Check tables exist for new layers
grep -n "Agents\|Services\|Detectors" docs/architecture/foundation/IMPORT_HIERARCHY.md

# Verify doc still valid markdown
# (visual inspection)
```

## Post-Fix

1. Update TODO.md — delete gap row #22
2. Report: "Fixed #22. IMPORT_HIERARCHY.md now documents agents, services, detectors layers."
