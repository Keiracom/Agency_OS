# #317.2 Status

## Script Fix
- PipelineConfig: removed (class does not exist in orchestrator)
- Intelligence: wired — `src.pipeline.intelligence` module passed as `intelligence=` kwarg to PipelineOrchestrator
- Dry-run: PASS (0 import errors, 0 crashes, 4.6s, output written)

## Changes made to scripts/317_live_validation.py
Replaced the dead `PipelineConfig` pattern with real dependency injection:
- `Layer2Discovery(conn=pool, dfs=dfs_client)` — discovery
- `FreeEnrichment(conn=pool)` — scraping + ABN
- `ProspectScorer()` — affordability + intent gates
- `DMIdentification(bd_client=..., dfs_client=...)` — DM waterfall
- `dfs_client` as `gmb_client` (DFSLabsClient has `maps_search_gmb`)
- `intelligence module` passed for Sonnet/Haiku stages
- `orchestrator.run(category_codes=category_codes, location=location, target_count=domains)`

## Live Run
- Status: READY — awaiting Dave's go
- Blocker: none (script is clean; dry-run confirmed)
- Estimated cost: ~$66 AUD for 250 domains (per script header)
  - Per 10 domains: ~$1.40 AUD
  - Per 50 domains: ~$7.00 AUD
- Pipeline runs locally via asyncio — NO Prefect deployment required

## Command to execute live run
```bash
cd /home/elliotbot/clawd/Agency_OS
python3 scripts/317_live_validation.py --domains 10 --category dentist --location australia
```
For full 50-domain validation:
```bash
python3 scripts/317_live_validation.py --domains 50 --category dentist --location australia
```

## Commit
a7ffda9 pushed to feat/317-contactout-live-validation

## Next Step
Dave confirms go → main session runs the live command above (10 or 50 domains as approved).
