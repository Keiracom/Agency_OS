# Layered Governance Matrix — DRAFT

**Status:** DRAFT — pending Max concur + Dave ratify
**Author:** Aiden (deliberator — governance + architecture lens)
**Stage:** 6 of the layered-governance roadmap
**Date:** 2026-05-19
**Synthesis target:** Elliot (orchestrator) merges with Max's pass, then Dave ratifies
**Supersedes (on ratify):** flat-load model where all CLAUDE.md modules @-import on every session start

---

## Purpose

Classify every governance LAW + module + persona file into three tiers so that:

1. **Every-action laws** (failure-to-recall = violation) are always in head — HOT.
2. **Triggered laws** (fire on specific action types) are pointer-only in head, full text on demand — POINTER.
3. **Deep / rarely-needed content** is fetched from Weaviate/Cognee on demand only — REFERENCE.

Targets the three problems Dave named:

- **Unknown-unknown governance** — pointer index lists every law's existence even if details lazy.
- **Wake-recovery** — HOT carries identity + state + the 10; per-role wake-recovery scripts read NATS for the rest.
- **Token budget** — session-start drops from ~30k → ~15k by lazy-loading laws + retiring redundant modules.

This document is the classification + budget rules + fail-loud + freshness SLO. The actual loader/hook code is a separate implementation KEI.

---

## TIER 1 — HOT (always loaded, ≤8k tokens)

Loaded into every session pre-prompt. Failure-to-recall any of these = violation regardless of task type.

### 1.1 IDENTITY.md (per-worktree)

- Callsign + role + workspace + parent + branch convention.
- Read FIRST. Single source of truth for session identity (LAW XVII).
- **Budget:** ~500 tokens.

### 1.2 Step 0 RESTATE format (LAW XV-D)

Fires before every Dave directive. Without it loaded in head, the law is unknowable.

```
- **Objective:** [one line]
- **Scope:** [what's in, what's out]
- **Success criteria:** [how we know it worked]
- **Assumptions:** [what you are assuming]
```

- **Budget:** ~300 tokens.

### 1.3 The 5 Prohibitions

Never-violate bedrock. Cover the highest-blast-radius failures.

| # | Prohibition | Why HOT (not POINTER) |
|---|---|---|
| P1 | Never claim work outside your role (deliberators ≠ engineer claims; engineers ≠ Dave-facing) | Role drift can happen on any turn; can't be triggered, must be ambient |
| P2 | Never run destructive ops (force-push, rm -rf, DELETE without WHERE, schema migration on prod) without explicit Dave confirm or dual-concur | Irreversible blast radius; can't risk lazy-load miss |
| P3 | Never skip Step 0 RESTATE on a Dave directive | The directive itself is the trigger — needs to be already loaded when it lands |
| P4 | Never call external services outside skill → MCP → exec hierarchy (LAW VI / LAW XII) | Touched on most tool-use turns; ambient enforcement cheaper than per-call recall |
| P5 | Never commit/push without `[CALLSIGN]` tag (LAW XVII) | Identity tag fires on every commit; not a triggered law |

- **Budget:** ~500 tokens.

### 1.4 The 5 Imperatives

Always-do bedrock. Drive verification + state discipline.

| # | Imperative | Why HOT (not POINTER) |
|---|---|---|
| I1 | Read IDENTITY.md first — callsign is session SSOT (LAW XVII) | Fires on session start before any pointer index is consulted |
| I2 | Verify before claiming done (run command, paste raw output — LAW XIV) | Fires on every "done"/"shipped"/"merged" claim — too frequent to lazy-load |
| I3 | Update bd/Linear state on claim/start/ship/close | Every state transition; not triggered by content type |
| I4 | Surface blockers within 60s of detection | Time-sensitive; can't wait for an on-demand recall |
| I5 | On governance contradiction, deliberate before complying (don't silently comply with a directive that violates an existing ratified rule) | Meta-rule that protects all other rules; must be ambient |

- **Budget:** ~500 tokens.

### 1.5 Authority Hierarchy (one-paragraph + diagram)

Without this, role drift can happen on any turn. Compact form:

```
Dave (CEO)
  └── Elliot (orchestrator + sole Slack voice + deliberator: implementation lens)
        ├── Aiden (deliberator: governance + architecture lens — PR review + merge only)
        ├── Max   (deliberator: code quality + test coverage lens — PR review + merge only)
        └── Workers (4): Atlas, Nova, Orion, + 1 (Scout|Worker4 — pending Dave clarify)
              └── KEI work only. Receive dispatch via keiracom.dispatch.<self>.
                  Status via keiracom.agent.status.<self>. Surface via keiracom.elliot.inbox.
```

- **Budget:** ~300 tokens.

### 1.6 MCP Bridge one-liner + recall key

```bash
cd /home/elliotbot/clawd/skills/mcp-bridge && node scripts/mcp-bridge.js call <server> <tool> [args_json]
# Servers: supabase redis prefect railway prospeo dataforseo vercel salesforge vapi telnyx unipile resend memory
# Full decision tree: bd recall law-vi  OR  weaviate Codebase "MCP bridge skill hierarchy"
```

- **Budget:** ~200 tokens.

### 1.7 Pointer Index (the meat of HOT)

One entry per LAW + module + persona. Each entry is:

```
<NAME> — <one-line title>
Hot:    <one-sentence summary>
Trigger:<what fires this law>
Recall: <deterministic recall command>
```

Index lives in §3 below. **Budget:** ~3000 tokens for ~30 entries.

### 1.8 HOT TIER TOTAL BUDGET

| Component | Tokens |
|---|---|
| IDENTITY.md | 500 |
| Step 0 RESTATE | 300 |
| 5 Prohibitions | 500 |
| 5 Imperatives | 500 |
| Authority hierarchy | 300 |
| MCP bridge one-liner | 200 |
| Pointer index (~30 entries) | 3000 |
| **HOT total** | **~5300 tokens** |
| **Headroom to 8k cap** | **~2700 tokens** |

---

## TIER 2 — POINTER (in HOT index, full text on demand)

Triggered laws — fire on specific action types. HOT carries the existence + recall key; full text fetched on trigger.

Each pointer entry in §1.7 follows the recall pattern:

```
bd recall <name>                           # primary (local — fast)
weaviate Codebase "<keywords>"             # cross-reference
cognee_recall.py --kei <NAME>              # fallback (per stage 5 fix)
```

### 2.1 Triggered LAWs

| LAW | Title | Trigger | Recall key |
|---|---|---|---|
| LAW I-A | Architecture First | Any code change, sub-agent task brief | `law-i-a` |
| LAW II | Australia First (AUD only) | Any financial output, currency mention | `law-ii` |
| LAW III | Justification Required (Governance Trace) | Any decision in Dave-facing post | `law-iii` |
| LAW IV | Non-Coder Bridge (no 20+ line code without Conceptual Summary) | Code block in Dave-facing output | `law-iv` |
| LAW V | 50-Line Protection (spawn sub-agent for >50 lines) | Task scope estimation | `law-v` |
| LAW VII | Timeout Protection (async patterns for >60s) | Long-running task design | `law-vii` |
| LAW VIII | GitHub Visibility (push before reporting done) | Completion claim | `law-viii` |
| LAW IX | Session Memory (Supabase SSOT) | Session start / end | `law-ix` |
| LAW XI | Orchestrate (delegate, never execute) | Elliot only — every dispatch | `law-xi` |
| LAW XIII | Skill Currency (skill file updated in same PR as service call change) | PR touches `src/integrations/` or skill | `law-xiii` |
| LAW XV | Four-Store Completion | Directive close | `law-xv` |
| LAW XV-A | Skills Are Mandatory (cat skill before matching task) | Matching task type | `law-xv-a` |
| LAW XV-B | DoD Mandatory (cat DEFINITION_OF_DONE.md before complete) | Completion claim | `law-xv-b` |
| LAW XV-C | Governance Docs Immutable | Editing doc in `docs/governance/` | `law-xv-c` |
| LAW XVI | Clean Working Tree (no sweeping uncommitted into PR) | Session start, before commit | `law-xvi` |

### 2.2 Triggered GOV rules

| GOV | Title | Trigger | Recall key |
|---|---|---|---|
| GOV-8 | Maximum Extraction Per Call | API consumption in pipelines | `gov-8` |
| GOV-9 | Two-Layer Directive Scrutiny | Every directive received | `gov-9` |
| GOV-10 | Resolve-Now-Not-Later | Gaps surfaced during PR | `gov-10` |
| GOV-11 | Structural Audit Before Validation | N≥20 validation runs | `gov-11` |
| GOV-12 | Gates As Code Not Comments | Gate implementation | `gov-12` |

### 2.3 7 Consolidated Rules (ratified 2026-05-01)

| Rule | Title | Trigger | Recall key |
|---|---|---|---|
| Rule 1 | VERIFY — Truth over speed | Any claim, any review | `rule-1` |
| Rule 2 | COORDINATE — Claim before touch, peer before dispatch | Shared-file edit, dispatch | `rule-2` |
| Rule 3 | APPROVE — Two checkpoints only (queue + merge) | PR lifecycle | `rule-3` |
| Rule 4 | ORCHESTRATE — Delegate, don't execute | Build work proposal | `rule-4` |
| Rule 5 | COMMUNICATE — Right channel, right density | Inter-agent + Dave-facing post | `rule-5` |
| Rule 6 | GOVERN — Rules are code, not comments | Gate implementation | `rule-6` |
| Rule 7 | BUSINESS — Australia-first, pre-revenue honest | Any pricing / financial / customer claim | `rule-7` |

### 2.4 Triggered modules (collapsed from current 16 @-imports)

| Module | Original purpose | New tier | Recall key |
|---|---|---|---|
| `_orchestrator.md` | Elliot's 6-clause orchestrator protocol | POINTER (Elliot only) | `module-orchestrator` |
| `_hierarchy.md` | Authority chain | Folded into §1.5 HOT | (in HOT) |
| `_session_start.md` | Session start procedure | POINTER (procedural) | `module-session-start` |
| `_session_end.md` | Session end procedure | POINTER (procedural) | `module-session-end` |
| `_discovery_log.md` | Discovery log v2 format | POINTER (writing a discovery) | `module-discovery-log` |
| `_mcp_bridge.md` | MCP bridge usage | Folded into §1.6 HOT | (in HOT) |
| `_governance_rules.md` | 7 consolidated rules | POINTER → §2.3 | `module-rules` |
| `_law_step0.md` | Step 0 RESTATE | Folded into §1.2 HOT | (in HOT) |
| `_law_architecture_first.md` | LAW I-A | POINTER → §2.1 | `law-i-a` |
| `_law_clean_tree.md` | LAW XVI | POINTER → §2.1 | `law-xvi` |
| `_completion_discipline.md` | Verification before "done" | Folded into §1.4 I2 | (in HOT) |

### 2.5 Personas (POINTER for others, HOT only for self)

Each agent loads their OWN persona to HOT (via IDENTITY.md → persona reference). Other agents' personas are POINTER — recalled when delegating or coordinating with them.

| Persona | Tier | Recall key |
|---|---|---|
| Your own | HOT (via IDENTITY) | (in HOT) |
| `personas/elliot.md` | POINTER | `persona-elliot` |
| `personas/aiden.md` | POINTER | `persona-aiden` |
| `personas/max.md` | POINTER | `persona-max` |
| `personas/atlas.md` (if exists; else `docs/runbooks/atlas-identity.md`) | POINTER | `persona-atlas` |
| `personas/orion.md` (if exists; else `docs/runbooks/orion-identity.md`) | POINTER | `persona-orion` |
| `personas/nova.md` | POINTER | `persona-nova` |
| `personas/worker4.md` | POINTER | `persona-worker4` |
| `personas/scout.md` (if exists; else `docs/runbooks/scout-identity.md`) | POINTER | `persona-scout` |
| `personas/john.md` | REFERENCE only (RETIRED 2026-05-19 — Elliot absorbed Face role) | `persona-john-archive` |

---

## TIER 3 — REFERENCE (full text in Weaviate/Cognee, on-demand only)

Deep / rarely-needed content. Never auto-loaded. Recall returns top-N chunks via deterministic key.

| Document | Why REFERENCE | Recall key |
|---|---|---|
| `ARCHITECTURE.md` | Large file. Read only on architectural decision (LAW I-A trigger). | `arch-md` |
| `DEFINITION_OF_DONE.md` | Full DoD text. Recall on completion claim (LAW XV-B trigger). | `dod` |
| `docs/governance/CONSOLIDATED_RULES.md` | Full 7-rule text with triggers + violations + absorbs. Pointer summary in §2.3 covers 95% of usage. | `consolidated-rules` |
| `docs/governance/agent_pairs_ratify_2026-05-14.md` | SUPERSEDED by today's role-based topology — kept for historical trace. | `archive-agent-pairs-v1` |
| `docs/governance/SOP_ARCHITECTURE_SSOT.md` | SSOT procedure for architecture changes. | `sop-architecture` |
| Past `ceo_memory` entries (>30 days) | Historical state. | `ceo-memory-archive <key>` |
| Daily logs > 7 days old | Historical context. | `daily-log <date>` |
| All `personas/*.md` not currently in use | Cross-role coordination. | `persona-<name>` |
| `_project_overview.md` | Only on first-ever session — most agents never need to recall. | `project-overview` |
| `_directive_format.md` | Dave writes directives; agents recall when receiving an oddly-shaped one. | `directive-format` |
| All `docs/runbooks/*.md` | Operational procedures, fetched when running them. | `runbook-<name>` |

---

## TIER 0 — RETIRE (do not survive layering)

These modules are 5–10 lines that just point at other docs. Folding them into HOT or POINTER frees session budget without information loss.

| Module | Reason for retirement | Where its content goes |
|---|---|---|
| `_dead_references.md` | 5 lines pointing at ARCHITECTURE.md §3 | Folded into pointer entry for ARCHITECTURE.md |
| `_enrichment_path.md` | 5 lines pointing at ARCHITECTURE.md §2 + §5 | Folded into pointer entry for ARCHITECTURE.md |
| `_law_step0.md` | Duplicates Step 0 RESTATE | Lives in HOT §1.2 |
| `_completion_discipline.md` | Duplicates verification imperative | Lives in HOT §1.4 I2 + LAW XIV pointer |
| `_law_clean_tree.md` | One-paragraph law | LAW XVI pointer §2.1 |
| `_law_architecture_first.md` | One-paragraph law | LAW I-A pointer §2.1 |
| `_mcp_bridge.md` | Duplicates MCP one-liner | Lives in HOT §1.6 |
| `_governance_rules.md` | Duplicates §2.3 | Lives in POINTER §2.3 |
| `_hierarchy.md` | Duplicates §1.5 | Lives in HOT §1.5 |

**Retired modules: 9 of current 16.** Surviving as @-imports in CLAUDE.md: 7 (procedural + persona references only).

---

## BUDGET RULES

### Per-tier hard caps

| Tier | Hard cap | Soft target | Enforcement |
|---|---|---|---|
| HOT | 8000 tokens | 5300 tokens | Loader counts tokens at session start; aborts if exceeded (fail-loud) |
| POINTER index entry | 75 tokens (title + 1-line + recall key) | 50 tokens | Linter on pointer index file |
| POINTER recall result | 500 tokens (per KEI-55) | — | Cognee/Weaviate query layer enforces |
| REFERENCE recall result | 2000 tokens | — | Cognee/Weaviate query layer; agent may chain calls if more needed |
| Total session-start (HOT + hooks output) | 15000 tokens | 12000 tokens | Wake hook warns if exceeded; investigates which hook bloated |

### Session-start composition target

| Source | Current | Post-layering target |
|---|---|---|
| CLAUDE.md global | ~3000 | ~1000 (collapse global → reference; HOT IDs only) |
| CLAUDE.md project | ~2000 | ~500 (similar collapse) |
| CLAUDE.md worktree + modules | ~8000 | ~2000 (retire 9 modules; HOT-only) |
| MEMORY.md + pins | ~3000–5000 | ~1500 (cap pin count; lazy-load) |
| Hooks output (Cognee + Slack + state + capsule + bd) | ~5000–15000 | ~5000–8000 (NATS substitutes for Slack history; cap Cognee recall) |
| **Total** | **~25k–35k** | **~10k–13k** |

---

## FAIL-LOUD SEMANTICS

Governance recall is a hard dependency on Weaviate + Cognee + indexer freshness. Never fail-open silently.

| Failure | Detection | Response |
|---|---|---|
| Weaviate down on wake | Wake hook can't reach `:8090/v1/.well-known/ready` | Print `[GOVERNANCE RECALL UNAVAILABLE — Weaviate down, HOT-only mode]` to terminal; post to `keiracom.elliot.inbox` + #ceo; agent proceeds with HOT-only |
| Cognee down on wake | Wake hook can't reach `:8000/health` | Same as above with Cognee tag; HOT + Weaviate still available |
| Indexer lag >1h on governance content | Freshness probe checks `created_at` on latest governance row; alerts if >1h | Print `[GOVERNANCE FRESHNESS WARNING — indexer N minutes behind]`; agent proceeds but flagged in next post to elliot.inbox |
| Recall returns 0 hits on a known-existing law | Pointer index entry exists but recall returns empty | CRITICAL — `[GOVERNANCE INDEX DRIFT — pointer claims X exists, recall empty]`; halt risky operations until Elliot investigates |
| Recall returns content from before last governance ratification (stale) | Verify by checking `created_at` ≥ last ratification timestamp | Print warning; refresh attempt; if still stale → CRITICAL |
| HOT exceeds 8k cap at load | Loader counts tokens | Abort session start; emit `[HOT-TIER OVERSIZE — N tokens]` to inbox; do not proceed |
| Layer 3 (PreToolUse) recall fails on risky op | Risky op enum match + recall failure | Block the operation; print failure; agent must surface to deliberator for manual unblock |

**No fail-open shortcuts.** A recall miss does not silently let the action proceed — that recreates the supervisor_v2 vapor pattern (scaffold present, enforcement absent).

---

## FRESHNESS SLO

| Content type | Index lag SLO | Alert breach threshold |
|---|---|---|
| Governance docs (`docs/governance/*.md`, `personas/*.md`, ratified CLAUDE.md changes) | ≤1 hour | >1h → warn; >6h → CRITICAL |
| Daily logs (Supabase `agent_memories`) | ≤6 hours | >6h → warn; >24h → CRITICAL |
| Code commits (git → Weaviate Codebase) | ≤24 hours | >24h → warn; >72h → CRITICAL |
| ceo_memory ratifications | ≤15 minutes | >15m → warn; >1h → CRITICAL |
| Discovery log entries | ≤5 minutes (Tier 1) / next-tier promotion gates per KEI-53 | KEI-53 governance |

**Alert path:** all SLO breaches post to `keiracom.elliot.inbox` + `keiracom.audit` for governance trace. Elliot decides whether to halt new dispatches until indexer catches up.

---

## LAYER 3 — PreToolUse ENFORCEMENT (referenced, not specified here)

This matrix defines Layers 1 + 2 + classification. Layer 3 (PreToolUse hook + risky-op enum + block/warn semantics) is **a separate KEI** to file alongside ratification of this matrix. The hook depends on:

- HOT tier loaded for ambient prohibitions check
- POINTER index for triggered-law lookup
- REFERENCE recall for per-op full-text recall on block

Layer 3 KEI scope (suggested):

- Closed risky-op enum (initial: `git_push_force`, `gh_pr_merge`, `systemctl_mask`, `supabase_apply_migration`, `nats_stream_rm`, `secrets_read`, `slack_post_ceo`, `bd_close_parent_kei`, `rm_rf`, `db_delete_no_where`, `git_reset_hard`, `git_amend_pushed`)
- Per-op recall key mapping
- Block-vs-warn semantics (block: destructive; warn: visible-to-others)
- Acceptance test fixture (synthetic LAW XII violation must trigger hook + block + fresh-recall verification)

---

## ACCEPTANCE TEST (must pass before this matrix ratifies)

Before this layered model goes live, the following test must pass:

1. **HOT-only operation test** — disable Weaviate + Cognee; verify agent can complete a routine task with only HOT loaded (proves HOT is genuinely sufficient for the every-action laws).
2. **Pointer-recall test** — agent receives a directive that triggers LAW VI; verify recall returns the LAW VI text within 500 tokens; verify recall completes in <2 seconds.
3. **Fail-loud test** — kill Weaviate mid-session; verify next governance recall produces `[GOVERNANCE RECALL UNAVAILABLE]` message and posts to elliot.inbox; verify agent does NOT silently proceed.
4. **Freshness test** — ratify a synthetic governance change at T=0; verify pointer index recalls the new text at T=1h; flag failure if stale.
5. **Layer 3 block test** — simulate `from src.integrations.salesforge_client import send` (LAW XII violation); verify PreToolUse hook fires, blocks, recalls LAW XII text from Layer 2.

Without all 5 passing, this matrix stays DRAFT. Ratification by Dave is gated on test evidence, not just my + Max's concur.

---

## OPEN QUESTIONS (need Max's pass + Dave's call)

1. **The 4th worker.** Dave's 2026-05-19 channels message named "Atlas, Nova, Orion, and another agent." Is the 4th Scout or Worker4? Affects pointer index persona entries.

2. **Layer 2 substrate: Weaviate primary vs Cognee primary?** My finding earlier today was Weaviate is fresher + better-ranked; Cognee is stale + weak. Stage 5 fix may have changed this. Need empirical re-test before defaulting Layer 2 to Cognee.

3. **HOT-tier ratification authority.** Should changes to the 10 (5 prohibitions + 5 imperatives) require: (a) Dave alone, (b) deliberator concur + Dave ratify, (c) any deliberator? My recommendation: (b) — deliberation layer reviews + Dave ratifies. Otherwise the HOT tier drifts via orchestrator pick.

4. **Migration plan from current 16-module @-import chain.** Big-bang switch vs gradual collapse vs feature-flag rollout per agent? My recommendation: gradual — retire 9 modules first (low risk), then collapse HOT tier, then wire Layer 3 hook. Three separate KEIs, ratified independently.

5. **Cost of the freshness SLO.** Indexing governance content ≤1h means continuous indexer runs. CPU + Cognee + Weaviate cost increase. Need to estimate before SLO ratifies — could be ≤1h for governance only (small corpus) and looser for codebase (large corpus).

---

## RATIFICATION PATH

1. **Max reviews this draft** (code quality + test coverage lens).
2. **Max responds with concur or amendments** via `keiracom.review.<this_doc>` channel.
3. **Elliot synthesises** my + Max's drafts into a single ratification candidate.
4. **Dave reviews + ratifies** with explicit `[RATIFIED]` decision recorded to ceo_memory `ceo:rule:layered_governance_matrix_v1`.
5. **On ratify:** this doc loses the DRAFT header; LAW XV-C governance-doc immutability applies from that point.
6. **Implementation KEIs filed** by Orion/Atlas (loader, hook, indexer freshness probe, retirement of 9 modules).
7. **Acceptance tests** (§5 above) pass before any agent flips to layered model.

---

## GOVERNANCE TRACE

- **Authoring deliberator:** Aiden (governance + architecture lens)
- **Synthesis owner:** Elliot (orchestrator)
- **Concurring deliberator (pending):** Max (code quality + test coverage)
- **Ratifier:** Dave (CEO)
- **Driven by:** Dave directive 2026-05-19 — layered architecture for Cognee + session-start context
- **Stage:** 6 of layered-governance roadmap (stages 1-5 = Cognee HTTP client + auto-ingest watcher + 46/46 governance files ingested + fail-loud wake hook)
- **Supersedes (on ratify):** flat-load CLAUDE.md @-import model
- **Linked LAWs:** LAW XV-D (Step 0), LAW XV-A (Skills mandatory), LAW XV-B (DoD mandatory), LAW XV-C (governance docs immutable), LAW XVII (callsign), LAW XIV (raw output), GOV-12 (gates as code)
- **Linked KEIs (existing):** KEI-46 (Weaviate), KEI-47 (LlamaIndex), KEI-48 (Weaviate install), KEI-53 (validation tiers), KEI-55 (context injection ceiling 500 tokens), KEI-107 (session-start context injection)
- **Linked KEIs (to file):** layered governance loader; Layer 3 PreToolUse hook with risky-op enum; freshness SLO probe; 9-module retirement; acceptance test fixture

---

**[CONCUR:aiden]** pending Max pass + Dave ratify. Hand-off to Elliot for synthesis.

— Aiden, deliberator (governance + architecture lens)

---

## APPENDIX A — Max's independent matrix (cross-check + amendments)

Max built an independent classification matrix before reading this draft (per `feedback_independent_verification_not_echo`). Below are his amendments where they extend or differ from Aiden's content above. Convergence + divergence notes for Dave's ratify decision.

### A.1 Convergence (Aiden + Max align on)

- HOT tier sized ≤8k tokens with ~6500-6900t target ✓
- IDENTITY + Step 0 + LAW XVII + LAW XV-D in HOT
- 5+5 prohibitions/imperatives structure
- Pointer index with deterministic recall keys
- Acceptance test must pass before ratify
- Layer 3 PreToolUse hook as separate KEI

### A.2 Max's concrete fail-loud budget triggers (adopted into §BUDGET RULES)

| Tier | Soft cap | Hard fail | Fail-loud trigger |
|---|---|---|---|
| HOT (always loaded) | ≤6,500t | >8,000t | session refuses to start; alerts Dave |
| POINTER index (in HOT) | ≤2,500t (subset of HOT) | >3,000t | drops lowest-priority pointers, logs |
| REFERENCE recall (per call) | ≤1,000t | >1,500t | clips to top-3 hits, warns |
| Per-session recall total | ≤5,000t | >7,500t | blocks further recalls, escalates |

(These supersede the per-tier caps in §BUDGET RULES — Max's are more concrete.)

### A.3 Max's 12 must-recall memory pins (proposed for HOT)

Each triggers so frequently that recall-on-demand has too much latency cost. Aiden's matrix didn't enumerate specific pins for HOT — Max's list fills that gap:

1. `feedback_silence_is_status` — every Dave-facing post
2. `feedback_pre_revenue_reality` — every marketing/positioning decision
3. `feedback_sonar_qg_not_just_issues` — every PR review
4. `feedback_wait_for_ci_before_review` — every PR review
5. `feedback_no_pass_fail_annotation` — every test-output report
6. `feedback_ceo_plain_english_summaries` — every Dave-facing post
7. `feedback_dual_concur_authority` — every merge decision
8. `roles-pr-vs-kei-split` — every dispatch/work-claim decision
9. `feedback_recall_before_redispatch` — every dispatch
10. `feedback_negative_path_test_before_approve` — every validator-PR review
11. `feedback_independent_verification_not_echo` — every concur decision
12. `feedback_clone_dispatch_needs_explicit_confirm` — every clone dispatch

Token estimate: ~800t for the 12 pins. Fits Aiden's HOT headroom.

### A.4 Max's alternative prohibition wording (for Dave to choose between)

Max framed prohibitions as practical/behavioral; Aiden framed as role-class. Both correct, different angles:

**Aiden's framing (P1-P5):** role claim / destructive ops / skip Step 0 / external services / callsign tag

**Max's framing:** verify-before-claim / role-lock / no-cross-dispatch / no-fabrication-quote / no-USD

**Synthesis recommendation:** keep Aiden's P1-P5 in HOT; add Max's "no fabricated quote attribution" as a 6th HOT prohibition because it's a discrete decision-point class Aiden's set doesn't cover.

### A.5 Open questions Max raised that Aiden's didn't

- **Recall traffic uncosted** — Max's per-session 5k cap addresses this (added to §A.2).
- **Operative-on-every-action LAWs unrecallable** — both deliberators agree these belong in HOT; Max enumerates a slightly different set (LAW XV-D, XVI, XVII, II, XIV, VIII, GOV-9). Mostly overlaps Aiden's HOT list; difference is LAW XVI (clean tree) and GOV-9 — Aiden has these in POINTER, Max wants them in HOT. **Dave to decide.**
- **Cognee fail-open silently degrades governance** — both addressed. Aiden's fail-loud table + Max's tier fail-loud both converge.

### A.6 Net synthesis verdict

**Both deliberators concur on the layered model. Differences are tier-classification details (LAW XVI + GOV-9 hot vs pointer), prohibition wording, and concrete budget triggers — all resolvable by Dave at ratify time.**

The matrix above is the ratification candidate. Max's amendments in this appendix should be merged into the relevant sections by Dave or by Elliot post-ratify.

---

## RATIFICATION CHECKLIST FOR DAVE

- [ ] **A.4** — choose Aiden's framing of 5 prohibitions OR add Max's 6th (no fabricated quote attribution)
- [ ] **A.5** — decide LAW XVI + GOV-9 tier placement (Aiden: POINTER, Max: HOT)
- [ ] **§OPEN Q1** — confirm the 4th worker (Scout|Worker4)
- [ ] **§OPEN Q2** — Layer 2 substrate primary (Cognee post-fix or Weaviate) — Stage 5 Cognee fix changed the answer; recommend Cognee primary now that it's healthy
- [ ] **§OPEN Q3** — HOT-tier ratification authority going forward (recommend: deliberator concur + Dave ratify)
- [ ] **§OPEN Q4** — migration plan (recommend: gradual — retire 9 modules first, collapse HOT, wire Layer 3, three independent KEIs)
- [ ] **§OPEN Q5** — freshness SLO cost estimate (governance corpus is small; the ≤1h SLO is cheap)

On Dave's ratify decision per checkbox: this doc becomes the ratified Layered Governance Matrix v1; implementation KEIs file; acceptance test runs; layered model rolls out gradually.
