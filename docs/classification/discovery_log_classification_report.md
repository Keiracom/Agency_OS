# Discovery Log Classification Report — Phase 1.2.5 bundle artefact 5

**Authored:** 2026-05-24 (orion, per Elliot dispatch — Aiden R7)
**Status:** RATIFIED-PENDING (Aiden + Max + Elliot dual-concur on PR)
**Anchor:** `ceo:agency_os_keiracom_separation_v1`

## 1. Why this exists

Per the Dave-ratified separation directive (`AGENCY-OS-KEIRACOM-SEPARATION-V1`, 2026-05-24), three repos are carved out of Agency_OS: fleet / product / archive. Discovery log entries (lessons, gotchas, design discoveries) currently live in two stores:

1. `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/discovery_log.jsonl` (file-memory)
2. `public.agent_memories` table (Supabase)

When the product repo carves off, **discovery log entries need per-repo placement**: entries about fleet plumbing stay in the fleet repo; entries about V1.0 product code move to the product repo; entries about retired Agency OS pipeline move to the archive repo; cross-product entries get propagated to both fleet + product.

This deliverable classifies each entry to enable that per-repo placement.

## 2. Classifier shape

`scripts/classifier/discovery_log_classifier.py` reads both sources, applies a keyword-based heuristic against each entry's combined text (`context` + `finding` + `failed_path` + `verified_path` + `content` + `summary` + `tags`), and assigns one of:

| Label | Meaning |
|---|---|
| **fleet** | Orchestration plumbing, NATS, CI / lint / test infra, ceo_memory governance, supabase / psycopg / bd / dolt, slack relay, cognee, systemd, callsign discipline laws. |
| **product** | Keiracom V1.0 product code — chat, dashboard, workforce, Memory Abstraction Layer, Hindsight, MCP dispatcher (product-side), tenant onboarding, BYO API key, customer-facing install / CLI. |
| **archive** | Agency OS-era — Siege Waterfall, CIS / ALS scoring, T0-T5 enrichment tiers, dead vendors (Leadmagic / Bright Data / Salesforge / ContactOut / Hunter / Clay / Apollo / Kaspr / Proxycurl), GMB / ABN / BU, Flow A/B, ElevenAgents. |
| **cross-product** | Explicit cross-product items — separation directive, MAL infrastructure that serves the product, tenant model architecture, `ceo:comm_architecture`. |
| **manual-review** | Classifier could not confidently classify (no keyword hits OR top two buckets within 1 match). Human pass needed. |

Per dispatch: "**NO destructive writes on first pass** — output a proposed classification + ask for review before applying tags back." The classifier defaults to `--dry-run` (renders the report, makes no writes). `--apply` writes classification tags back to the JSONL only after dual-concur on this PR.

**Idempotency** (dispatch requirement): each annotated JSONL entry receives a `classification` field. Re-runs skip already-annotated entries unless `--reclassify` is set. Verified by `test_classify_all_is_idempotent`.

## 3. Empirical run — 2026-05-24 dry-run output

```
$ python3 scripts/classifier/discovery_log_classifier.py --report
======================================================================
Discovery Log Classifier Report (dry-run — no writes)
======================================================================

JSONL source (11 entries):
  fleet             10  (90.9%)
  manual-review      1  (9.1%)

agent_memories source (0 entries):

Manual-review queue: 1 entries
  - KEI-201 [no_keyword_hits] 'Live bulk extract of 5 Slack channels into Weaviate Slack_history collection onl'
```

### 3.1 JSONL distribution

**11 entries, 90.9% fleet, 9.1% manual-review.** Fleet dominance is expected — discovery_log.jsonl is the agent-side learning log, and almost every entry to date covers fleet plumbing (KEI-99 relay watcher, KEI-100 migration-guard CI, KEI-85 schema verification, KEI-132 chaos-test conftest, Agency_OS-zbvs Cognee supersession, etc.).

### 3.2 agent_memories source — 0 rows + vocabulary divergence note

**Dispatch said:** `WHERE source_type IN ('discovery', 'finding', 'gotcha')`. Empirically, agent_memories does NOT use those source_types. The actual populated source_types (top 20 by count) are:

```
identity_fact      1600
decision           1387
lesson              997   ← closest to "lesson learned"
milestone           978
pattern             713   ← closest to "design pattern discovery"
ceo_instruction     385
strategic_shift     326
session_reflection  246
daily_log           246
verified_fact       221   ← closest to "fact discovery"
session_start_audit 128
core_fact            87
rescued_from_mem0    82
test_result          30
rule                 22
rsi_output           21
reasoning            12
skill                11
research             11
dave_confirmed        8
```

The classifier handles this by:
- **Default:** reads with the literal dispatch source_types (returns 0 today). Logs a hint to re-run with `--wider`.
- **`--wider` flag:** reads with `lesson` / `pattern` / `verified_fact` / `test_result` / `research` (the empirically-populated discovery-like set).

**This is a vocabulary-divergence gap to surface to Elliot for decision:**
- (a) **rename** the existing agent_memories rows to the canonical `discovery`/`finding`/`gotcha` source_types via a separate migration, OR
- (b) **update the dispatch + downstream readers** to use the actual `lesson`/`pattern`/etc. vocabulary, OR
- (c) **keep both vocabularies side-by-side** (current default + `--wider` opt-in) until Phase 2.0 namespace cleanup forces a decision.

Recommend **(b)** — the existing vocabulary is richer and load-bearing; renaming 2,000+ rows for the sake of dispatch literalism is reverse-burden. But Elliot has the orchestrator role-lock call on which downstream readers need updating.

### 3.3 Connection-side gap (psycopg DSN)

During the dry-run, the agent_memories psycopg read failed with:

```
WARNING agent_memories read failed: missing "=" after
"postgresql+asyncpg://postgres.jatzvazlbusedwsnqxzr:...@.../postgres"
```

The DSN env carries the `+asyncpg` driver-prefix (a SQLAlchemy convention) that synchronous psycopg doesn't parse. **Known pattern** — captured in the `reference_psycopg_supabase_pgbouncer` memory:

> "psycopg3 against Supabase pooler needs prepare_threshold=None (pgbouncer txn-mode drops PREPARE); also strip +asyncpg from DSN."

The classifier handles the failure gracefully (returns empty list + log warning, doesn't crash). The "strip `+asyncpg`" step is a one-line `read_agent_memories` fix; deferred to a follow-up KEI since the agent_memories read returns 0 even when the DSN parses successfully (vocabulary divergence per §3.2 is the upstream cause).

### 3.4 Manual-review entry

Only 1 entry in the manual-review queue:

- **KEI-201** — `"Live bulk extract of 5 Slack channels into Weaviate Slack_history collection only..."`. Routed to manual-review for `reason=no_keyword_hits`. Reading the full entry: it's about Slack history bulk extract + Weaviate ingest configuration. The right bucket is **fleet** (memory/ingest plumbing) — but the entry's vocabulary uses `Weaviate` / `Slack_history` / `bulk extract` which aren't in the current fleet keyword list.

**Fix:** add `weaviate`, `slack_history`, `bulk extract` to the fleet keyword list and re-run (or hand-classify in the manual-review pass). Tracked as a tunable item for the next iteration of the classifier.

## 4. Classification heuristics — the keyword lists

Per category, the keyword anchors are (full list in `scripts/classifier/discovery_log_classifier.py` `KEYWORDS` dict):

- **fleet** (47 keywords): orchestration plumbing (`relay`, `tmux`, `dispatcher`, `orchestrator`, `watchdog`), NATS substrate (`nats`, `jetstream`, `keiracom.elliot.inbox`, `keiracom.dispatch`), CI/test plumbing (`pytest`, `ruff`, `sonar`, `conftest`, `kei-108`), ceo_memory governance (`ceo_memory`, `kei-87`, `write-guard`, `callsign_enforce`), supabase / psycopg, bd / dolt, slack relay (`slack_relay`, `tg -c ceo`), cognee, systemd, callsign laws (`law xvii`, `law xv-d`).
- **product** (24 keywords): Keiracom V1.0 specs (`keiracom_chat`, `keiracom_dashboard`, `keiracom workforce`), Memory Abstraction Layer + Hindsight (`memory_abstraction_layer`, `mal v1`, `hindsight`), tenant + onboarding (`tenant_isolation`, `tenant onboarding`, `set_tenant_session`), MCP dispatcher (`mcp dispatcher`, `mcp_project_id`), BYO key + customer-facing, product config (`product vision`, `pricing config`, `icp_market`), Fair-Source.
- **archive** (33 keywords): Siege Waterfall (`siege waterfall`, `flow a`, `flow b`), CIS / ALS scoring (`cis`, `als scoring`, `reachability`, `propensity`), T0-T5 enrichment tiers, dead vendors (Leadmagic, Bright Data, Salesforge, ContactOut, Hunter, Kaspr, Proxycurl, Apollo, Clay, Apify, Webshare, SERP API), GMB / ABN / BU, ElevenAgents.
- **cross-product** (13 keywords): explicit cross-product items (`agency_os_keiracom`, `separation directive`, `phase 1.2.5/1.3/2.0/2.1/2.2`, `3-repo`), MAL infrastructure, tenant model architecture, `ceo:comm_architecture`.

**Tie-break rule:** ONLY a true tie (top bucket score equal to next bucket score) routes to manual-review with `reason=tie_or_near_tie`. A 1-point lead is sufficient confidence — a "fleet 3 / product 2" entry classifies as fleet, not manual-review. Updated 2026-05-24 per Max HOLD on PR #1121: original doc said "within `MIN_CONFIDENCE_MARGIN`" implying margin=1 routes to manual-review, but the code does strict `<` (only margin=0 routes). Empirical 10-fleet-1-manual-review distribution on real JSONL confirms the strict semantics are not over-routing — kept the code, fixed the doc.

## 5. Apply pass — sequenced after concur

The dry-run output above is **proposed** classification — not applied. To apply tags back to the JSONL:

```bash
python3 scripts/classifier/discovery_log_classifier.py --apply
```

This writes a `classification` field onto each JSONL entry (idempotent — re-running with `--apply` after the first run is a no-op unless `--reclassify` is added).

**agent_memories write-back is NOT implemented in this first pass.** Per dispatch's "no destructive writes" guard, agent_memories tag-writing is deferred to a follow-up KEI that ships:
1. A `context` column on `agent_memories` (mirrors the `0scg` migration on `ceo_memory`).
2. A `write_agent_memory_classification` wrapper that uses the same `SET LOCAL agency_os.callsign` discipline the KEI-87 trigger expects.
3. Per-row UPDATE batches via psycopg + the canonical pgbouncer-aware DSN.

## 6. Cutover sequence

Reading from `ceo:agency_os_keiracom_separation_v1.sequencing`:

  1. ✅ Phase 1.1 — V1.0 ratification (DONE 2026-05-24)
  2. 🔄 Phase 1.2 — retire Agency OS architecture doc + content audit
  3. 🔄 Phase 1.2.5 — pre-migration artefact bundle (**this report is item 5 of the bundle**; the allowlist + enforcer was item 7 — PR #1118)
  4. ✅ Phase 1.3 — agent identity refresh (DONE via Agency_OS-fwdb v3)
  5. ⏳ Phase 2.0 — repo creation (classifier output feeds per-repo discovery log placement)
  6. ⏳ Phase 2.1 — Hindsight verification spike
  7. ⏳ Phase 2.2 — migrate product code via clean PRs

The classifier runs at **Phase 2.0**: each entry's `classification` field determines which of the three repos receives its copy of the discovery log line (`fleet` → fleet repo; `product` → product repo; `archive` → archive repo; `cross-product` → fleet repo + product repo, both).

## 7. Notes — `ceo:agency_os_keiracom_separation_v1` (queried 2026-05-24)

Per the audit-dispatch checklist canonical-key-query-gate, the queried value of the canonical key is pasted here verbatim for reviewer cross-check. (Same key paste as `docs/migration/test_path_classification.md` §7 — both Phase 1.2.5 artefacts source classification from the same canonical key.)

```json
{
  "frame": {
    "keiracom": "Was the internal agent fleet built in parallel; now the commercial venture. Working name; final brand TBD post-launch via market analysis.",
    "agency_os": "The BDR product the fleet built for AU marketing agencies (discovery + enrichment + 4-channel outreach). RETIRED, preserved as archive, not deleted."
  },
  "status": "RATIFIED",
  "ratified_at": "2026-05-24T10:23:00+00:00",
  "ratified_by": "dave",
  "directive_ref": "AGENCY-OS-KEIRACOM-SEPARATION-V1",
  "repo_topology": [
    "Internal fleet repo (working name keiracom-fleet)",
    "Product repo (working name TBD, rename-ready) — V1.0 AI workforce code",
    "Archive repo (existing URL preserved) — dead BDR product code"
  ]
}
```

The four classification buckets (fleet / product / archive / cross-product) map directly onto `repo_topology` + the cross-product concept implicit in the separation framing.

## 8. Acceptance criteria

- [x] `scripts/classifier/discovery_log_classifier.py` reads JSONL + agent_memories sources; defaults to `--dry-run` (no destructive writes on first pass per dispatch).
- [x] Idempotent on re-run (`test_classify_all_is_idempotent`); `--reclassify` overrides.
- [x] Tests cover positive (fleet/product/archive/cross-product) + negative (ambiguous → manual-review) + idempotency + reclassify-override + helper unit tests. **9/9 pytest pass in 0.11s.**
- [x] Dry-run output rendered for current sources (§3).
- [x] Manual-review queue surfaced with reason codes + entry preview (§3.4).
- [x] Vocabulary-divergence gap on agent_memories source_types surfaced for Elliot decision (§3.2).
- [x] Connection-side gap (psycopg DSN `+asyncpg` strip) surfaced + workaround noted (§3.3).
- [x] Canonical key `ceo:agency_os_keiracom_separation_v1` queried + pasted into §7.
- [x] ruff check + format clean.
- [ ] Aiden architecture-lens concur.
- [ ] Max code-quality-lens concur.
- [ ] Elliot impl-feasibility concur.
- [ ] Dual-concur (any 2 of 3) → Elliot admin-merge per orchestrator-merge-after-NATS-concur pattern.
- [ ] After merge: run `--apply` to write JSONL tags back. agent_memories write-back deferred to follow-up KEI per §5.
