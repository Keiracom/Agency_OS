---
name: Fix 10 - Campaign Auto-Inherit FK
description: Adds client_resource_id FK to campaign_resources table
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 10: Campaign Auto-Inherit FK Missing

## Gap Reference
- **TODO.md Item:** #10
- **Priority:** P2 High
- **Location:** `src/models/` and Supabase migrations
- **Issue:** client_resource_id not in campaign_resources table

## Pre-Flight Checks

1. Find campaign_resources model:
   ```bash
   grep -rn "campaign_resources\|CampaignResource" src/models/
   ```

2. Check current columns:
   ```bash
   grep -A 20 "class CampaignResource" src/models/*.py
   ```

3. Check RESOURCE_POOL.md for expected schema:
   ```bash
   grep -n "client_resource_id" docs/architecture/business/RESOURCE_POOL.md
   ```

## Implementation Steps

1. **Update CampaignResource model:**
   ```python
   # In src/models/campaign_resource.py (or equivalent)
   class CampaignResource(Base):
       __tablename__ = "campaign_resources"

       # Existing columns...

       # ADD: Foreign key to client_resources for inheritance tracking
       client_resource_id = Column(
           UUID(as_uuid=True),
           ForeignKey("client_resources.id", ondelete="SET NULL"),
           nullable=True,
           comment="Source client resource if auto-inherited"
       )

       # Relationship
       client_resource = relationship("ClientResource", back_populates="campaign_resources")
   ```

2. **Create migration:**
   ```bash
   # Create migration file
   # supabase/migrations/XXX_add_campaign_resource_fk.sql
   ```

   ```sql
   -- Add client_resource_id to campaign_resources
   ALTER TABLE campaign_resources
   ADD COLUMN client_resource_id UUID REFERENCES client_resources(id) ON DELETE SET NULL;

   -- Add index for lookups
   CREATE INDEX idx_campaign_resources_client_resource_id
   ON campaign_resources(client_resource_id);

   -- Add comment
   COMMENT ON COLUMN campaign_resources.client_resource_id IS 'Source client resource if auto-inherited';
   ```

3. **Update ClientResource model** (add back_populates if needed)

4. **Update any allocation logic** that creates campaign_resources to set the FK

## Acceptance Criteria

- [ ] client_resource_id column added to CampaignResource model
- [ ] Foreign key constraint to client_resources.id
- [ ] ON DELETE SET NULL behavior
- [ ] Migration file created
- [ ] Index added for performance
- [ ] Relationship defined in both models

## Validation

```bash
# Check model has column
grep -n "client_resource_id" src/models/*.py

# Check migration exists
ls -la supabase/migrations/*campaign_resource*

# Verify model syntax
python -m py_compile src/models/campaign_resource.py

# Type check
mypy src/models/campaign_resource.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #10
2. Report: "Fixed #10. campaign_resources now has client_resource_id FK with migration."
