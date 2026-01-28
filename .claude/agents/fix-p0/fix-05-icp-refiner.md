---
name: Fix 05 - ICP Refiner Service
description: Implements ICP Refiner to apply WHO patterns to sourcing
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 05: ICP Refiner Service Not Implemented

## Gap Reference
- **TODO.md Item:** #5
- **Priority:** P0/P1 Critical
- **Location:** `src/orchestration/monthly_replenishment_flow.py`
- **Issue:** WHO patterns learned but not applied to sourcing

## Pre-Flight Checks

1. Find where WHO patterns are stored/learned:
   ```bash
   grep -rn "WHO\|pattern\|icp.*refin" src/
   ```

2. Read monthly_replenishment_flow.py to understand current flow

3. Check if ICP refinement logic exists anywhere:
   ```bash
   find src/ -name "*icp*refin*" -o -name "*refin*icp*"
   ```

## Implementation Steps

1. **Create ICP Refiner service** (if not exists):
   ```python
   # src/services/icp_refiner.py
   """
   Contract: src/services/icp_refiner.py
   Purpose: Apply learned WHO patterns to improve lead sourcing criteria
   Layer: 3 - services
   Imports: models, integrations
   Consumers: orchestration flows
   """

   from typing import Dict, List, Optional
   from sqlalchemy.orm import Session
   from uuid import UUID

   class ICPRefiner:
       """Refines ICP criteria based on conversion patterns."""

       async def get_learned_patterns(
           self,
           db: Session,
           client_id: UUID
       ) -> Dict:
           """Retrieve WHO patterns from successful conversions."""
           # Query converted leads
           # Extract common attributes (title, industry, company size, etc.)
           # Return pattern dict
           pass

       async def apply_to_sourcing(
           self,
           db: Session,
           client_id: UUID,
           base_criteria: Dict,
           patterns: Dict
       ) -> Dict:
           """Apply learned patterns to sourcing criteria."""
           refined = base_criteria.copy()

           # Boost criteria that match conversion patterns
           # Example: if 80% of conversions are "VP" titles, weight VP higher

           return refined

       async def refine_icp(
           self,
           db: Session,
           client_id: UUID,
           base_criteria: Dict
       ) -> Dict:
           """Main entry point: get patterns and apply to criteria."""
           patterns = await self.get_learned_patterns(db, client_id)
           if not patterns:
               return base_criteria
           return await self.apply_to_sourcing(db, client_id, base_criteria, patterns)
   ```

2. **Integrate into monthly_replenishment_flow.py:**
   ```python
   from src.services.icp_refiner import ICPRefiner

   icp_refiner = ICPRefiner()

   # In replenishment task:
   async def replenish_leads_task(db, client_id, base_criteria):
       # Apply ICP refinement before sourcing
       refined_criteria = await icp_refiner.refine_icp(
           db, client_id, base_criteria
       )

       # Use refined_criteria for lead sourcing
       leads = await source_leads(db, client_id, refined_criteria)
   ```

3. **Pattern learning input** (verify these exist):
   - Conversion outcomes stored with lead attributes
   - Minimum conversion threshold (20 per DECISIONS.md)

## Acceptance Criteria

- [ ] ICPRefiner class exists with get_learned_patterns()
- [ ] ICPRefiner class has apply_to_sourcing()
- [ ] monthly_replenishment_flow.py imports and uses ICPRefiner
- [ ] Refined criteria used for lead sourcing
- [ ] Respects minimum 20 conversions threshold (DECISIONS.md)

## Validation

```bash
# Check ICP refiner exists
ls -la src/services/icp_refiner.py

# Check integration in flow
grep -n "icp_refiner\|ICPRefiner" src/orchestration/monthly_replenishment_flow.py

# Verify no syntax errors
python -m py_compile src/services/icp_refiner.py
python -m py_compile src/orchestration/monthly_replenishment_flow.py

# Type check
mypy src/services/icp_refiner.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #5
2. Report: "Fixed #5. ICP Refiner service implemented and integrated into monthly replenishment."
