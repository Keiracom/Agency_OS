---
name: Fix 06 - Database Models Documentation
description: Documents 6 missing models in DATABASE.md
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 06: Undocumented Database Models

## Gap Reference
- **TODO.md Item:** #6
- **Priority:** P2 High
- **Location:** `docs/architecture/foundation/DATABASE.md`
- **Issue:** 6 undocumented models: CampaignSuggestion, DigestLog, IcpRefinementLog, LinkedInCredential, ClientIntelligence, SDKUsageLog

## Pre-Flight Checks

1. Find model definitions:
   ```bash
   grep -rn "class CampaignSuggestion\|class DigestLog\|class IcpRefinementLog\|class LinkedInCredential\|class ClientIntelligence\|class SDKUsageLog" src/models/
   ```

2. Read DATABASE.md to understand documentation format

3. Verify these models aren't already documented:
   ```bash
   grep -n "CampaignSuggestion\|DigestLog\|IcpRefinementLog\|LinkedInCredential\|ClientIntelligence\|SDKUsageLog" docs/architecture/foundation/DATABASE.md
   ```

## Implementation Steps

1. **Read each model file** to extract:
   - Table name
   - All columns with types
   - Primary key
   - Foreign keys
   - Indexes
   - Relationships

2. **Document each model** in DATABASE.md format:
   ```markdown
   ### CampaignSuggestion
   **Table:** `campaign_suggestions`
   **Purpose:** [one-line description]

   | Column | Type | Constraints | Description |
   |--------|------|-------------|-------------|
   | id | UUID | PK | ... |
   | ... | ... | ... | ... |

   **Relationships:**
   - belongs_to: Campaign
   - ...

   **Indexes:**
   - idx_campaign_suggestion_client_id
   ```

3. **Add to appropriate section** in DATABASE.md (maintain alphabetical or logical grouping)

4. **Update model count** in DATABASE.md summary

## Models to Document

| Model | Expected Location |
|-------|-------------------|
| CampaignSuggestion | src/models/campaign_suggestion.py |
| DigestLog | src/models/digest_log.py |
| IcpRefinementLog | src/models/icp_refinement_log.py |
| LinkedInCredential | src/models/linkedin_credential.py |
| ClientIntelligence | src/models/client_intelligence.py |
| SDKUsageLog | src/models/sdk_usage_log.py |

## Acceptance Criteria

- [ ] CampaignSuggestion fully documented
- [ ] DigestLog fully documented
- [ ] IcpRefinementLog fully documented
- [ ] LinkedInCredential fully documented
- [ ] ClientIntelligence fully documented
- [ ] SDKUsageLog fully documented
- [ ] Each includes: table name, columns, types, constraints, relationships
- [ ] Model count updated in DATABASE.md

## Validation

```bash
# Check all 6 models are documented
for model in CampaignSuggestion DigestLog IcpRefinementLog LinkedInCredential ClientIntelligence SDKUsageLog; do
  grep -c "$model" docs/architecture/foundation/DATABASE.md
done

# Should output 6 lines, each with count > 0
```

## Post-Fix

1. Update TODO.md — delete gap row #6
2. Report: "Fixed #6. DATABASE.md now documents all 6 missing models."
