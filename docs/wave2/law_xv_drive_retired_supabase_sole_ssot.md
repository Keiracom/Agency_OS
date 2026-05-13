# LAW XV — Drive Manual archived, Supabase ceo_memory sole SSOT

**Author:** Aiden (design only — per Dave verbatim ts ~1778668100)
**Implementer:** Elliot (post-compact ratification + execute, bundled with pre-restart governance refresh)
**Beads:** Agency_OS-uik — P1
**Self-referential:** bd issue filed + claimed BEFORE branch + commit per `ceo:rule:no_build_without_linear_issue` (Linear KEI sync gated on KEI-22 D1/D3 per Agency_OS-8lz precedent).

## Dave verbatim (canonical source — ts ~1778668100)

> Drive Manual (Doc ID 1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho) RETIRED. 6 strategic sections migrated to ceo_memory keys:
> - ceo:product_vision
> - ceo:pricing_config
> - ceo:icp_market
> - ceo:provider_stack_active
> - ceo:competitive_intelligence
> - ceo:team_roster
>
> LAW XV three-store updated:
> 1. Supabase ceo_memory (primary SSOT, specific key per decision type)
> 2. cis_directive_metrics (execution metrics)
> 3. Linear issue comment (build task decisions)
> Drive Manual write REMOVED.
>
> CEO new-session protocol: Supabase direct query, no Drive read.
>
> KEI-37 scope add: ceo:boot_state_current includes refs to all active ceo:* strategic keys.
>
> GOVERNANCE.md + CLAUDE.md update across 6 worktrees for LAW XV change.

**ceo_memory anchor (per `ceo:rule:ceo_operational_directives_recorded`):** `ceo:rule:supabase_sole_ssot` (Elliot to backfill per the new auto-record protocol; KEI-22 D7 ships the mechanism that future-proofs this).

## Why this change matters

The Drive Manual was a single Google Doc 5+ months old that the CEO read at session start. Three failure modes today:

1. **Read latency** — fetching the Doc adds 2-5s to every CEO boot; sometimes unreachable behind Google auth.
2. **Stale narrative** — Drive sections drifted from on-main reality (KEI-22 state-mismatch class — same symptom).
3. **Write fragmentation** — LAW XV required write to Drive, ceo_memory, and cis_directive_metrics. Drive write often skipped or failed silently. Per session_end_check.py audit logs from prior sessions, Drive mirror failure was the #1 most-frequently-bypassed LAW XV gate.

Supabase ceo_memory key-per-decision-type fixes all three. Sub-second query, structured data, single source of truth.

## Migration map

| Drive Manual section | New ceo_memory key | Content shape |
|---|---|---|
| Product Vision | `ceo:product_vision` | Mission statement + 3-year roadmap + non-goals |
| Pricing Config | `ceo:pricing_config` | Tier prices ($AUD), bundle composition, AUD/USD rate |
| ICP Market | `ceo:icp_market` | Target ICPs, exclusions, market sizing |
| Provider Stack Active | `ceo:provider_stack_active` | Email/LinkedIn/Voice/SMS/Vector/Graph providers + tier/cost |
| Competitive Intelligence | `ceo:competitive_intelligence` | Competitor list, positioning, win/loss notes |
| Team Roster | `ceo:team_roster` | Callsign list + roles + reporting chain |

Each key value is a structured JSON object. Schema versioned via a `schema_version: 1` integer field.

## LAW XV three-store update (verbatim handoff for CLAUDE.md)

### Before (deprecated)

```
LAW XV — Four-Store Completion (HARD BLOCK): A directive is NOT complete until ALL FOUR are written:
1. docs/MANUAL.md in repo
2. Supabase ceo_memory — directive counter + state
3. cis_directive_metrics — execution metrics row
4. Google Drive mirror (best-effort via write_manual_mirror.py — failure logged, non-blocking)
```

### After (ratified ts ~1778668100)

```
LAW XV — Three-Store Completion (HARD BLOCK): A directive is NOT complete until ALL THREE are written:
1. Supabase ceo_memory — primary SSOT, specific key per decision type (ceo:rule:* for rules; ceo:product_vision/pricing_config/icp_market/provider_stack_active/competitive_intelligence/team_roster for strategic; ceo:directive_NNN for directive completion; ceo:session_end_YYYY-MM-DD for session boundaries)
2. cis_directive_metrics — execution metrics row (input/output tokens, cost_aud, exit_status)
3. Linear issue comment — build task decisions appended to the matching KEI's discussion thread
Drive Manual write REMOVED.
```

Files affected (Elliot's lane post-compact):

- `CLAUDE.md` (root + global + per-worktree per-callsign instance × 6 worktrees) — replace LAW XV section verbatim.
- `~/.claude/CLAUDE.md` (global private) — replace LAW XV section verbatim.
- `GOVERNANCE.md` — replace four-store with three-store + ratification note.
- `scripts/session_end_check.py` — drop the Drive-mirror check, add the Linear-issue-comment writer.
- `scripts/write_manual_mirror.py` — deprecate (not delete — flag with `__deprecated__ = True` module header for one cycle, remove next session).
- 6 worktree CLAUDE.md instances (aiden/atlas/orion/scout/elliot/max).

## CEO new-session boot protocol

Old path:

1. Read Drive Manual (latency + reachability risk).
2. Query 30+ ceo_memory keys to reconstruct state.
3. Reconcile Drive narrative vs ceo_memory state.

New path (post-merge of this design's implementation):

1. Query `ceo:boot_state_current` (one key, sub-100ms).
2. Branch on `needs_dave`.
3. Query specific `ceo:product_vision` / `ceo:pricing_config` / `ceo:provider_stack_active` etc. keys ON DEMAND when CEO needs them for context.

Drive Manual is no longer in the boot path. Read-only fallback: the Doc remains accessible at the old ID for historical archive lookups, but no agent should read it for current-state queries.

## KEI-37 schema addition

Extend `ceo:boot_state_current` (already designed in `docs/wave2/kei37_boot_state_design.md`) with a `strategic_keys_ref` array:

```json
{
  ...
  "strategic_keys_ref": [
    "ceo:product_vision",
    "ceo:pricing_config",
    "ceo:icp_market",
    "ceo:provider_stack_active",
    "ceo:competitive_intelligence",
    "ceo:team_roster"
  ],
  "rules_ref": [
    "ceo:rule:linear_only_source_of_work",
    "ceo:rule:beads_layer3_enforcement",
    "ceo:rule:no_build_without_linear_issue",
    "ceo:rule:check_existing_before_building",
    "ceo:rule:agent_session_recovery_internal",
    "ceo:rule:ceo_operational_directives_recorded",
    "ceo:rule:pre_execution_claim_protocol",
    "ceo:rule:supabase_sole_ssot"
  ],
  ...
}
```

`rules_ref` already in the KEI-37 design from PR #834 (per Dave ts ~1778667300). `strategic_keys_ref` is new in THIS change.

CEO new-session reads `ceo:boot_state_current` → sees both arrays → can fetch any rule or strategic key on demand. No 30-key fan-out.

## GOVERNANCE.md / CLAUDE.md change matrix

| File | Section | Change |
|---|---|---|
| `~/.claude/CLAUDE.md` | §Memory bullet "docs/MANUAL.md — Primary human-readable SSOT (mirror to Google Doc on save)" | Delete |
| `~/.claude/CLAUDE.md` | §Four-Store Completion Rule (LAW XV) | Replace with three-store version |
| `~/.claude/CLAUDE.md` | §Session Startup step 0 ("READ THE MANUAL FIRST") | Replace with "Query `ceo:boot_state_current` FIRST" |
| `GOVERNANCE.md` | §LAW XV | Replace four-store with three-store |
| `GOVERNANCE.md` | §STANDING RULES list | Add `ceo:rule:supabase_sole_ssot` (Dave ts ~1778668100) |
| `Agency_OS/.claude/modules/_session_start.md` | "Manual (LAZY-LOAD)" bullet | Replace with `ceo:boot_state_current` query |
| `Agency_OS/.claude/modules/_session_end.md` | session-end 3-store check reference | Update to Linear-issue-comment third store |
| 6× worktree `CLAUDE.md` per-callsign | Inherited via `@.claude/modules/` includes | No direct edit if module-based; verify each |

Estimated total edit: 30-40 lines across 8 files × 6 worktrees ≈ 200 LoC text. Mechanical.

## ceo:rule:* anchor (per the new auto-record protocol)

| Key | Content (Elliot writes post-compact) |
|---|---|
| `ceo:rule:supabase_sole_ssot` | Dave verbatim ts ~1778668100 + LAW XV before/after diff + the 6 strategic keys list. |

Auto-record mechanism (KEI-22 D7 — Orion's lane) ships the Slack-relay governance-trigger-phrase detection. Until D7 ships, Elliot writes manually as Dave issues rules.

## session_end_check.py change

Old check (paraphrased from the script's structure):

```python
stores = ["ceo_memory", "cis_directive_metrics", "drive_mirror"]
for store in stores:
    assert_written(store, directive_id)
```

New check:

```python
stores = ["ceo_memory", "cis_directive_metrics", "linear_issue_comment"]
for store in stores:
    assert_written(store, directive_id)
```

`write_manual_mirror.py` deprecated (one-cycle warning then removed); replaced by `write_linear_issue_comment.py` (Elliot's lane post-compact — new utility script that finds the matching KEI via the directive_id + appends a comment to its Linear discussion via the linear-server MCP).

## Sequencing

Elliot's post-compact governance refresh cascade absorbs this change alongside:

- KEI-37 boot_state schema (this PR's `strategic_keys_ref` addition).
- KEI-38 concur-gate regex narrowing (+ Rule 2).
- KEI-39 pre-execution claim protocol.
- Linear-KEI-before-build standing rule (Agency_OS-8lz design doc merged in PR #836 + PR #837 ceo:rule:* anchor).
- ceo_memory hygiene sweep.

This LAW XV change is the LARGEST single piece in the cascade because it touches CLAUDE.md across 6 worktrees + GOVERNANCE.md + 2 utility scripts. Recommend Elliot batches it as a SEPARATE PR within the cascade (not bundled with the smaller governance edits) for atomic rollback ability.

## Implementation handoff for Elliot

Files to touch:

1. `~/.claude/CLAUDE.md` — LAW XV + Memory + Session Startup sections (verbatim text in §LAW-XV-three-store-update above).
2. `GOVERNANCE.md` — same LAW XV update + add `ceo:rule:supabase_sole_ssot` to standing rules list.
3. `Agency_OS/.claude/modules/_session_start.md` — replace Manual lazy-load with `ceo:boot_state_current` query.
4. `Agency_OS/.claude/modules/_session_end.md` — update three-store check reference.
5. `scripts/session_end_check.py` — drop Drive-mirror check; add Linear-issue-comment writer.
6. `scripts/write_manual_mirror.py` — flag deprecated for one cycle.
7. `scripts/write_linear_issue_comment.py` (NEW) — utility that finds matching KEI for directive_id + appends Linear comment via linear-server MCP.
8. Per-worktree CLAUDE.md instances × 6 — verify module-inheritance picks up changes; direct-edit any that don't.

Estimated total LoC: ~250 text + ~80 LoC new write_linear_issue_comment.py + ~30 LoC session_end_check.py delta.

## Rollback

If Supabase ceo_memory becomes unreachable for >2h during a critical session, fallback path:

1. Read the 6 strategic keys from a JSONL backup at `docs/archive/ceo_memory_strategic_backup_2026-05-13.jsonl` (Elliot to seed at migration time).
2. Treat the JSONL as a read-only Drive-Manual-equivalent for the outage duration.

Recovery: `INSERT ... SELECT FROM jsonb_populate_recordset(...)` once Supabase returns.

## Acceptance criteria

- All 8 files updated per the change matrix.
- `ceo:rule:supabase_sole_ssot` written to ceo_memory.
- session_end_check.py passes for a test directive that writes only to ceo_memory + cis_directive_metrics + Linear issue comment (no Drive write).
- CEO new-session boot reads `ceo:boot_state_current` first, no Drive read on the boot path.
- 6 strategic ceo_memory keys exist (`ceo:product_vision`, `ceo:pricing_config`, `ceo:icp_market`, `ceo:provider_stack_active`, `ceo:competitive_intelligence`, `ceo:team_roster`) with `schema_version: 1` envelope and content migrated from the Drive Doc sections.
- JSONL backup committed BEFORE retirement.
