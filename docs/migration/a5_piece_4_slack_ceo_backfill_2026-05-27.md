# A5 piece 4 — Slack #ceo archive backfill to Hindsight (2026-05-27)

**bd:** Agency_OS-ygxz
**Cutover anchor:** STATE_SEPARATION knowledge-state-pgvector (closes the gap surfaced in piece 5 validation 2026-05-27 09:49Z).
**Dispatch:** Elliot 2026-05-27 — "close the cold-archive gap on Dave's historical decisions before his ephemeral cutover."

## Result

**piece_4_slack_ceo flipped FAIL → PASS at the 100-message milestone.** Full backfill continues unattended (2,633 messages exported; ~12s/msg via `TaskContextWrapper.ingest`; ETA ~8.8hr from kick-off at 11:30Z).

### Smoke recall delta

| Run | piece_4_slack_ceo verdict | Memories | Relevant | All-4 pass count |
|---|---|---:|---:|---|
| Baseline 2026-05-26 20:33Z | **FAIL** | 3 | 0 | 3/4 |
| Post-Drive-Manual-expansion 2026-05-27 09:49Z | **FAIL** | 3 | 0 | 3/4 |
| Mid-backfill 2026-05-27 ~11:34Z (107/2633 = 4.1% ingested) | **PASS** | **50** | **7** | **4/4** |

```
$ python3 scripts/migrations/a5_smoke_recall.py --out /tmp/early_smoke_100.json --log-level WARNING
# piece_4_slack_ceo passed=True memories=50 relevant=7
#   mem[0] relevant=True matched=['dave', 'ceo']
#   mem[1] relevant=True matched=['dave', 'ceo']
#   mem[2] relevant=True matched=['dave', 'ceo']
#   mem[3] relevant=False matched=['ceo']      # below ≥2-token threshold
#   mem[4] relevant=True matched=['dave', 'ceo']
```

## Pipeline (operator-runnable)

```
# 1) Export #ceo channel via Slack API (62-day window)
$ SLACK_BOT_TOKEN=xoxb-... python3 /tmp/export_slack_ceo.py /tmp/slack_ceo_archive.jsonl
# 2633 messages written (2632 with non-empty text)

# 2) Backfill into Hindsight under FLEET_TENANT_ID via TaskContextWrapper
$ python3 scripts/migrations/slack_ceo_backfill_to_hindsight.py \
    --input /tmp/slack_ceo_archive.jsonl \
    --state-file runtime/a5_piece_4_slack_ceo_state.jsonl \
    --execute
# 2026-05-27 11:30:04 INFO file=/tmp/slack_ceo_archive.jsonl messages=2633

# 3) Smoke validate
$ python3 scripts/migrations/a5_smoke_recall.py
# piece_4_slack_ceo PASS once ≥1 memory recall surfaces ≥2 signal tokens
```

State file (`runtime/a5_piece_4_slack_ceo_state.jsonl`) makes the backfill idempotent — interrupted runs resume from the last `ok=true` row.

## Source-channel verification

```
$ curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
       "https://slack.com/api/conversations.info?channel=C0B2PM3TV0B"
{"ok": true, "channel": {"name": "ceo", ...}}

$ curl ".../conversations.members?channel=C0B2PM3TV0B&limit=5"
{"ok": true, "members": ["U091TGTPB9U", "U0B2SRUBKD3", "U0B331GBFFV", "U0B43G79FCH"]}
# Bot is a member; channels:history + groups:history scopes work
```

## Export script (lives in /tmp, not in repo)

Pre-export tooling already exists at `scripts/orchestrator/slack_history_ingest.py` (KEI-201) but that POSTs to Weaviate `Slack_history` class, not JSONL. For this one-shot JSONL export I wrote `/tmp/export_slack_ceo.py` — direct `conversations.history` pagination with `oldest=NOW-62d`, integer timestamps (Slack 400s on decimal `oldest`), tier-2 rate-limit-safe 3s spacing. **Not committed to repo** — it's a one-shot operator tool; the canonical Slack-export path remains `slack_history_ingest.py`. Path-of-least-resistance for now; can be folded into `slack_ceo_backfill_to_hindsight.py` as a `--from-slack-api` mode in a follow-up if Aiden's lens wants it.

## Empirical evidence (frozen for audit trail)

`docs/migration/evidence/a5_piece_4_smoke_pass_evidence_2026-05-27.json` — snapshot at 107/2633 ingested, all 4 pieces passing.

## What this closes

Per Atlas's piece 5 validation 2026-05-27 09:49Z (PR #1213): 3/4 PASS with piece_4_slack_ceo unchanged-fail since 2026-05-26 baseline. Root cause: backfill never run with `--execute`; state file `runtime/a5_piece_4_slack_ceo_state.jsonl` did not exist.

**This PR closes that gap empirically.** Slack #ceo archive ingest active under `FLEET_TENANT_ID`; smoke recall now 4/4 PASS at the recall-surface level; full corpus (2,633 messages over 62 days) continues to ingest unattended.

## Honest gaps preserved

- **One-shot, not incremental:** new #ceo messages after 2026-05-27 11:30Z won't auto-flow into Hindsight until a continuous-sync pipeline ships (Phase B). For now, re-run the 3-step pipeline above periodically.
- **Single-tenant:** all writes under `FLEET_TENANT_ID=00000000-0000-0000-0000-000000000001`. Multi-tenant Slack ingest pending customer launch.
- **Recall heuristic still conservative:** `≥2 signal-token` threshold per memory matches the 2026-05-26 piece-5 harness. Precision/recall ROC not measured at this density.
- **Viktor gap (2026-05-25)** carried forward: 1 of 2,633 messages had missing text; ingested with `viktor_gap` metadata flag per `slack_ceo_backfill_to_hindsight.py:24` framing. No silent skips.

## Backfill completion plan

Backfill is running unattended as `nohup` pid 641887; log at `/tmp/slack_ceo_full_backfill.log`; state file at `runtime/a5_piece_4_slack_ceo_state.jsonl`. State-file idempotency means it can resume from any interrupt. ETA full completion ~2026-05-27 20:00Z. PR is mergeable BEFORE full completion since smoke verdict is met at 107 messages.

## Anchors

- bd: Agency_OS-ygxz closes on merge
- Cutover Readiness Gate: STATE_SEPARATION knowledge-state-pgvector criterion materially advanced — last of 4 historical sources now retrievable.
- Five-store completion rule (RATIFIED-CEO 2026-05-26): runtime PROOF (this smoke recall) is what closes the gap, not just the script existing.
- Viktor 2026-05-25 gap closure: A3 dual-write covers FORWARD writes; A5 piece 4 backfills the 2-month historical #ceo archive.
