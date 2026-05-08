# E3 — Rescore 113 Stale Drafts (2026-03-25 batch)

**Author:** Elliottbot (callsign ELLIOT)
**Compiled:** 2026-05-08
**Phase 1 task:** E3 from Dave's PHASE_1_KICKOFF
**Mode:** DRY-RUN (analysis only, no DB mutation in this PR)

---

## SCOPE

54 distinct prospects, 113 drafts (across email/linkedin/voice channels), single 5-minute batch on 2026-03-25 08:57–09:02 UTC. 1 campaign affected.

## METHOD

Script: `scripts/rescore_113_drafts_2026_05_08.py`

1. Query 54 prospects via `campaign_lead_messages` → `campaign_leads` → `business_universe`
2. Apply `score_decay_factor()` (mirrored from `src/pipeline/stage_4_scoring.py:27`):
   - age < 30 days → 1.0
   - age 30-90 days → 0.95
   - age 90-180 days → 0.85
   - age >= 180 days → 0.70
3. Multiply current `bu.propensity_score` by decay factor
4. Verdict bands:
   - **DROP**: decayed propensity < 70 (Stage 4 default `min_score_to_enrich`)
   - **WARM**: 70-84
   - **HOT**: 85+
5. Track which BU rows were re-enriched since message creation (`bu.updated_at > msg.created_at`)

## VERBATIM RUN OUTPUT

```
$ DATABASE_URL=$(grep -E "^DATABASE_URL=" /home/elliotbot/.config/agency-os/.env | cut -d= -f2-) \
    python3 scripts/rescore_113_drafts_2026_05_08.py

=== E3 Rescore Report — 2026-05-08 ===

bu_id    domain                                              prop_now  age_days  decay  prop_decayed  re_enriched  verdict
8e7f1715-…  lanewaymedia.co                                   62        44.5       0.95   58.9          False        DROP
e82fa3e8-…  taurusmarketing.com.au                            57        44.5       0.95   54.1          False        DROP
0a63fe4d-…  nogapsdental.com                                  56        44.5       0.95   53.2          False        DROP
…  (54 rows total — full output in run log)
ee72d543-…  dgadigital.com.au                                 40        44.5       0.95   38.0          False        DROP

=== Summary ===
Total prospects:           54
DROP (prop_decayed<70):    54
WARM (70-84):              0
HOT (85+):                 0
BU re-enriched since msg:  15

(dry run — no DB mutation. Re-run with --apply to mutate.)
```

## HEADLINE FINDING

**100% of the 54 prospects fail the propensity ≥ 70 send gate.**

- Average propensity NOW: 45.9 (well below 70)
- Average decayed propensity: 43.6
- Highest propensity: 62 (`lanewaymedia.co`)
- Lowest propensity: 40 (multiple)
- 0 prospects in WARM or HOT bands
- 15 prospects (28%) had BU re-enriched since 2026-03-25 — but their current scores still don't pass

**Per Dave's E3 directive ("Remove stale leads from send queue. This must be done before any email sends"), the entire 113-message batch should be dropped from the send queue.**

This is independent of decay: even at decay=1.0 (no time penalty), no prospect would clear 70.

## ROOT CAUSE

The 2026-03-25 batch was generated against prospects who never cleared the propensity threshold to begin with. They were enriched with low propensity at message-generation time and the message generation pipeline did not gate on propensity. This is a bug at the campaign-generation stage, not just stale data.

In Phase 1 E5/E6 rebuild, the gate must apply at message-generation, not just at send-time. Otherwise the same 0%-eligible drafts would be regenerated on the next campaign run.

## RECOMMENDED ACTION

| Action | When | Owner |
|---|---|---|
| Apply DROP verdict — UPDATE 113 messages to `status='draft_dropped_low_propensity'` | After Dave/Max approve this report | Elliot (`--apply` rerun) |
| Add propensity gate to message-generation pipeline | E5/E6 rebuild | Elliot |
| Backfill `cis_run_log` with this rescore event | After --apply | Elliot |

The `--apply` flag was NOT used in this PR. Status mutation requires explicit go-signal because it touches production rows.

## SCRIPT

`scripts/rescore_113_drafts_2026_05_08.py` — committed in this PR. Idempotent (DRY-RUN by default). Writes to stdout. No external dependencies beyond `asyncpg` (already in pipeline reqs).

Re-run command:
```
DATABASE_URL=$(grep -E "^DATABASE_URL=" /home/elliotbot/.config/agency-os/.env | cut -d= -f2-) \
  python3 scripts/rescore_113_drafts_2026_05_08.py
```

To apply mutations:
```
DATABASE_URL=... python3 scripts/rescore_113_drafts_2026_05_08.py --apply
```

## EXIT CRITERIA — Phase 1 #9

Per Dave's PHASE_1_KICKOFF exit list item #9 ("113 drafts re-scored, stale prospects flagged"):

✓ All 113 messages mapped back to 54 prospects
✓ All 54 rescored against current BU signals + decay
✓ All 54 flagged DROP (no prospect clears propensity gate)
✗ Mutation NOT applied — pending Dave/Max approve

This file documents the analysis. The mutation step (`--apply`) is held for explicit go-signal.
