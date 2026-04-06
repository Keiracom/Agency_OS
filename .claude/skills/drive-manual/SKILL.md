---
name: drive-manual
description: "Update the Agency OS Manual Google Doc. Use when: architecture changes, stack decisions, directive milestones, blocker updates, test baseline changes. NOT for: bug fixes, lint, routine PRs."
---

# Drive Manual Skill

Maintains the **Agency OS Manual** in Google Drive — the CEO's SSOT for project state.

## Credentials
- Service account: `elliottbot@gen-lang-client-0442027069.iam.gserviceaccount.com`
- Key file: `/home/elliotbot/google-service-account.json`
- **Limitation:** Service account cannot CREATE docs (Drive quota = 0). Can only WRITE to existing shared docs.

## Doc Setup
Dave must:
1. Create a Google Doc called "Agency OS Manual" in the "Agency Os" Drive folder
2. Share it with `elliottbot@gen-lang-client-0442027069.iam.gserviceaccount.com` as **Editor**
3. Paste the Doc ID here (from the URL: `docs.google.com/document/d/<DOC_ID>/edit`)

Once Doc ID is known, store it in `~/.config/agency-os/.env` as `GOOGLE_MANUAL_DOC_ID=<id>`.

## Usage

```bash
cd /home/elliotbot/clawd
source venv/bin/activate

# Write full manual skeleton (first time or full reset)
python skills/drive-manual/write_manual.py --doc-id <DOC_ID> --full

# Update a specific section (appends with timestamp)
python skills/drive-manual/write_manual.py --doc-id <DOC_ID> \
  --section "Active Decisions" \
  --content "ALS floor raised to 40 (CEO Directive #172)"
```

## When to Update

| Trigger | Section to update |
|---------|------------------|
| New directive with arch decision | Active Decisions |
| Stack change | Architecture |
| Test baseline change | Current State |
| Blocker resolved or added | Blockers |
| Infra change (model, server, etc.) | Current State |
| Milestone (e.g. Waterfall v3 complete) | Current State + Active Decisions |

## Save Trigger Rule
**Save to manual** when: architecture decisions, stack changes, strategic decisions, infra changes, test baseline changes, milestones.
**Skip**: bug fixes, lint, routine PRs.

## Notes
- CEO reads via Google Drive search ("Agency OS Manual")
- Elliottbot writes via Docs API batchUpdate
- Both Supabase (`elliot_internal.memories`) and this doc updated in same directive cycle
