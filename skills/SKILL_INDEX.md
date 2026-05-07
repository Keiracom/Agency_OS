# SKILL INDEX — Agency OS

**Last Updated:** 2026-05-07 (post-cleanup: PR-A dead code, PR-B renames, PR-C folder reorg)

## Canonical Skills (active, live code path)

| Skill | File | Live Code | Notes |
|-------|------|-----------|-------|
| austender | `skills/austender/SKILL.md` | `src/integrations/austender_client.py` | F2.2 discovery, public OCDS API |
| asic-new-co | `skills/asic-new-co/SKILL.md` | pending | Blocked on ASIC DSP API key |
| callback-poller | `skills/callback-poller/SKILL.md` | Prefect callback polling | |
| dataforseo | `skills/dataforseo/SKILL.md` | `src/integrations/dataforseo.py` | SERP + keyword signals |
| decomposer | `skills/decomposer/SKILL.md` | Task decomposition protocol | |
| drive-manual | `skills/drive-manual/SKILL.md` | Google Drive mirror | |
| hubspot | `skills/hubspot/SKILL.md` | pending | Blocked on per-tenant token |
| leadmagic | `skills/leadmagic/SKILL.md` | `src/integrations/leadmagic.py` | T3 email + T5 mobile |
| mcp-bridge | `skills/mcp-bridge/SKILL.md` | `skills/mcp-bridge/scripts/mcp-bridge.js` | 12 MCP servers |
| pipedrive | `skills/pipedrive/SKILL.md` | `src/integrations/pipedrive_client.py` | First CRM integration |
| pr-tool | `skills/pr-tool/SKILL.md` | GitHub PR creation | |
| seek | `skills/seek/SKILL.md` | pending | Blocked on Apify token |
| smartlead | `skills/smartlead/SKILL.md` | MCP bridge dispatch (116 tools) | Replaces Salesforge |
| superpowers | `skills/superpowers/SKILL.md` | Agent capability extensions | |
| three-store-save | `skills/three-store-save/SKILL.md` | Session persistence | |

## Legacy Skills (non-standard naming, kept as reference)

| Dir | Files | Notes |
|-----|-------|-------|
| agents/ | 4 .md files | Agent role definitions (Builder/QA/Fixer/Coordination) |
| campaign/ | CAMPAIGN_SKILL.md | Campaign management reference |
| conversion/ | CONVERSION_SKILL.md | Conversion tracking reference |
| crm/ | CRM_INTEGRATION_SKILL.md | Generic CRM — superseded by pipedrive + hubspot |
| frontend/ | 5 .md files | Frontend build guides |
| linkedin/ | LINKEDIN_CONNECTION_SKILL.md | LinkedIn automation reference |
| testing/ | 2 .md files | Test methodology (E2E + Live UX) |

## Deleted (empty dirs removed in this PR)

- `skills/email/` — empty, no content
- `skills/enrichment/` — empty, no content
