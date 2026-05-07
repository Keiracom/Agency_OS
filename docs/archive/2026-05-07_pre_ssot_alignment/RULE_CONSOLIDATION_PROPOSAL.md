# Rule Consolidation Proposal

**Author:** Architect Agent (AIDEN session)
**Date:** 2026-05-01
**Status:** PROPOSAL -- awaiting CEO ratification
**Branch:** aiden/rule-consolidation-proposal

---

## Preamble

Dave approved this consolidation pass on 2026-05-01. The rule surface has grown to ~60 distinct rules scattered across 6+ files. The cognitive load exceeds what any agent can hold in working memory, leading to redundant enforcement, contradictory obligations, and rules that exist on paper but are never checked at runtime.

The target is 7 core rules. Each must be:
1. Unambiguous -- one correct interpretation.
2. Runtime-enforceable -- the enforcer bot can check it without human judgement.
3. Non-redundant -- no two rules say the same thing in different words.

This document is a PROPOSAL ONLY. Per LAW XV-C, no existing governance docs are modified until Dave ratifies the new ruleset.

---

## A. Inventory (Current State)

Every distinct rule extracted from all source files. 63 rules total.

| # | Rule ID | Source File | One-Line Summary | Intent Category |
|---|---------|-------------|------------------|-----------------|
| 1 | LAW I-A | ENFORCE.md, CLAUDE.md (project), CLAUDE.md (global) | Read ARCHITECTURE.md before any architectural decision | Verification |
| 2 | LAW II | ENFORCE.md, CLAUDE.md (project) | All financial outputs in $AUD (1 USD = 1.55 AUD) | Business Logic |
| 3 | LAW III | ENFORCE.md, CLAUDE.md (project) | Governance Trace on every decision | Governance Hygiene |
| 4 | LAW IV | ENFORCE.md, CLAUDE.md (project) | No code blocks >20 lines without Conceptual Summary | Communication |
| 5 | LAW V | ENFORCE.md, CLAUDE.md (project) | If task >50 lines, spawn sub-agent | Orchestration |
| 6 | LAW VI | ENFORCE.md, CLAUDE.md (project) | Skill -> MCP -> exec hierarchy for external calls | Orchestration |
| 7 | LAW VII | ENFORCE.md, CLAUDE.md (project) | Async patterns for >60s tasks | Orchestration |
| 8 | LAW VIII | ENFORCE.md, CLAUDE.md (project) | All work pushed to GitHub before reporting complete | Verification |
| 9 | LAW IX | ENFORCE.md, CLAUDE.md (project) | Supabase is SOLE persistent memory | Governance Hygiene |
| 10 | LAW X | ENFORCE.md | Heartbeat disabled -- respond HEARTBEAT_OK only | Operational (stale) |
| 11 | LAW XI | ENFORCE.md, CLAUDE.md (project) | Elliottbot orchestrates, never executes task work directly | Orchestration |
| 12 | LAW XII | ENFORCE.md, CLAUDE.md (global) | Skills-First Integration -- no direct integration calls | Orchestration |
| 13 | LAW XIII | ENFORCE.md, CLAUDE.md (global) | Skill Currency Enforcement -- update skill in same PR | Orchestration |
| 14 | LAW XIV | ENFORCE.md, CLAUDE.md (project) | Raw Output Mandate -- paste verbatim, never summarise | Verification |
| 15 | LAW XV | ENFORCE.md, CLAUDE.md (global) | Four-Store Completion (MANUAL + ceo_memory + metrics + Drive mirror) | Verification |
| 16 | LAW XV-A | ENFORCE.md, CLAUDE.md (project) | Cat skill file before any matching task | Orchestration |
| 17 | LAW XV-B | ENFORCE.md, CLAUDE.md (project) | Cat DEFINITION_OF_DONE.md before reporting complete | Verification |
| 18 | LAW XV-C | ENFORCE.md, CLAUDE.md (project) | Governance docs immutable without explicit CEO directive | Governance Hygiene |
| 19 | LAW XV-D | CLAUDE.md (global), CLAUDE.md (project), CLAUDE.md (aiden) | Step 0 RESTATE before any directive execution | Approval |
| 20 | LAW XVI | CLAUDE.md (project), CLAUDE.md (aiden) | Clean Working Tree -- report uncommitted changes before new work | Verification |
| 21 | LAW XVII | CLAUDE.md (global) | Callsign Discipline -- prefix callsign on all outputs | Coordination |
| 22 | GOV-8 | CLAUDE.md (project) | Maximum Extraction Per Call -- capture full API response | Business Logic |
| 23 | GOV-9 | CLAUDE.md (project) | Two-Layer Directive Scrutiny before Step 0 | Approval |
| 24 | GOV-10 | CLAUDE.md (project) | Resolve-Now-Not-Later -- fix gaps in current PR | Verification |
| 25 | GOV-11 | CLAUDE.md (project) | Structural Audit Before Validation (N>=20) | Verification |
| 26 | GOV-12 | CLAUDE.md (project) | Gates As Code Not Comments -- runtime enforcement required | Governance Hygiene |
| 27 | Directive Ack | CLAUDE.md (global) | Every directive gets explicit acknowledgement before execution | Approval |
| 28 | Claim-Before-Touch | CLAUDE.md (global) | Post [CLAIM:] before editing shared files | Coordination |
| 29 | Dispatch Coordination | CLAUDE.md (global) | PROPOSE-BEFORE-DISPATCH + peer window for clone dispatch | Coordination |
| 30 | Clone Step 0 Exemption | CLAUDE.md (global) | Clones skip Step 0 -- parent already approved | Approval |
| 31 | Clone Queue Rule | CLAUDE.md (global) | Each clone must always have a queued next job | Coordination |
| 32 | Clone Queue Board | CLAUDE.md (global) | Shared [QUEUE-BOARD] posts with peer concur | Coordination |
| 33 | Constant Progression | CLAUDE.md (global) | Every message to Dave must be one-word-answerable | Communication |
| 34 | Propose Format | CLAUDE.md (global) | [PROPOSE:] format with rank, scope, files, alternatives | Communication |
| 35 | Clone Error Handling | CLAUDE.md (global) | Category A/B/C error triage for clone failures | Coordination |
| 36 | DSAE Protocol | CLAUDE.md (global) | Discuss-Split-Agree-Execute for multi-bot tasks | Coordination |
| 37 | DSAE-DELAY Rule | CLAUDE.md (global) | Elliot responds first, Aiden waits 10s | Coordination |
| 38 | R1 -- Diagnosis Lock | CLAUDE.md (global) | Peer pauses on shared issue until verdict lands | Coordination |
| 39 | R2 -- Claim-Before-Commit | CLAUDE.md (global) | Post [CLAIM:] 30s before any push/dispatch/merge | Coordination |
| 40 | R3 -- Methodology First | CLAUDE.md (global) | Both bots agree on data source before posting estimates | Coordination |
| 41 | R4 -- Watcher Uniqueness | CLAUDE.md (global) | Only one bot runs background watcher per remote state | Coordination |
| 42 | R5 -- Domain Split First | CLAUDE.md (global) | Define scope ownership before parallel work | Coordination |
| 43 | R6 -- Verdict-Wait | CLAUDE.md (global) | Pause execution on [DIFFER] until peer concurs or Dave overrides | Coordination |
| 44 | R7 -- Audit-Before-Recommend | CLAUDE.md (global) | Audit existing code before recommending new builds | Verification |
| 45 | R8 -- Dual-Concur Yellow Flag | CLAUDE.md (global) | Re-check if both bots agree in <60s on big decisions | Coordination |
| 46 | R9 -- Verify-Before-Claim | CLAUDE.md (global) | Completion claim must include raw verification output | Verification |
| 47 | R10 -- Audit-In-Proposal | CLAUDE.md (global) | [PROPOSE] must include git audit of existing code | Verification |
| 48 | R11 -- Build-While-Review | CLAUDE.md (global) | Verdict-wait blocks merge, not next build dispatch | Coordination |
| 49 | R12 -- Batch-Merge Requests | CLAUDE.md (global) | Present 3+ approved PRs as single merge request to Dave | Communication |
| 50 | R13 -- Message Density Cap | CLAUDE.md (global) | TG messages max 12 lines | Communication |
| 51 | R14 -- No Parallel Fix on DIFFER | CLAUDE.md (global) | Pause ALL execution on [DIFFER], not just merge | Coordination |
| 52 | Enforcer Rule 1 | enforcer_bot.py | CONCUR-BEFORE-SUMMARY -- peer must concur before Dave-facing summary | Coordination |
| 53 | Enforcer Rule 2 | enforcer_bot.py | STEP-0-BEFORE-EXECUTION -- Step 0 or dual concur before execution | Approval |
| 54 | Enforcer Rule 3 | enforcer_bot.py | COMPLETION-REQUIRES-VERIFICATION -- evidence with completion claims | Verification |
| 55 | Enforcer Rule 4 | enforcer_bot.py | NO-UNREVIEWED-MAIN-PUSH -- warning on direct main push | Verification |
| 56 | Enforcer Rule 5 | enforcer_bot.py | SHARED-FILE-CLAIM -- [CLAIM:] before editing shared files | Coordination |
| 57 | Enforcer Rule 6 | enforcer_bot.py | SAVE-CLAIM-REQUIRES-PROOF -- specific evidence per store | Verification |
| 58 | Enforcer Rule 7 | enforcer_bot.py | CLONE-DIRECT-GROUP-POST -- clones must not post to group | Coordination |
| 59 | Enforcer Rule 8 | enforcer_bot.py | DISPATCH-COORDINATION -- proposal + peer concur before dispatch | Coordination |
| 60 | Enforcer Rule 9 | enforcer_bot.py | DIRECTIVE-INITIATIVE -- bots must propose, not ask Dave what to do | Communication |
| 61 | Session Startup Protocol | CLAUDE.md (global), CLAUDE.md (project), CLAUDE.md (aiden) | Read Manual, verify TG, check chat history, query memories, clone awareness | Governance Hygiene |
| 62 | Session End Protocol | CLAUDE.md (project), CLAUDE.md (aiden) | Write daily_log, ceo_memory, run session_end_check.py | Governance Hygiene |
| 63 | Staleness Check (48hr) | CLAUDE.md (global) | Stop if ceo_memory key >48hr old | Governance Hygiene |

### Inventory Notes

**Pure duplicates identified:**

- LAW XV-D (Step 0 RESTATE) appears THREE times: in CLAUDE.md (global) as both a standalone section AND inside EVO Protocol, plus once in each project CLAUDE.md. The enforcer bot implements the same check as Enforcer Rule 2 (STEP-0-BEFORE-EXECUTION). That is 5 written instances of one rule.

- R2 (Claim-Before-Commit) and Claim-Before-Touch and Enforcer Rule 5 (SHARED-FILE-CLAIM) all enforce "announce before editing." R2 extends to pushes and merges; Claim-Before-Touch is specific to the shared-file allowlist; Enforcer Rule 5 is the runtime check. Three statements, one intent.

- R9 (Verify-Before-Claim), LAW XIV (Raw Output Mandate), and Enforcer Rule 3 (COMPLETION-REQUIRES-VERIFICATION) all say "prove your work with raw output." Three statements, one intent.

- LAW XII (Skills-First Integration) and LAW XV-A (Skills Are Mandatory) and LAW VI (Skills-First Operations) overlap heavily -- all say "use skills, not raw calls."

- Enforcer Rule 1 (CONCUR-BEFORE-SUMMARY) is a runtime expression of DSAE Protocol's AGREE step.

- Enforcer Rule 9 (DIRECTIVE-INITIATIVE) is the runtime expression of Constant Progression Rule and Propose Format.

**Stale/obsolete rules identified:**

- LAW X (Heartbeat Disabled): Heartbeat was disabled long ago. No agent processes heartbeat. Dead rule.

- ENFORCE.md's hierarchy section (ENFORCE.md > BOOTSTRAP.md > AGENTS.md > SOUL.md > TOOLS.md): BOOTSTRAP.md and AGENTS.md and TOOLS.md no longer exist in the governance structure. The hierarchy is outdated. Authority now flows from CLAUDE.md files.

- LAW XV-D's "wait for Dave to confirm" clause is partially contradicted by the Constant Progression Rule's "Dave approves at TWO checkpoints only: queue approval and merge approval. Everything between runs autonomously" and Enforcer Rule 2's exception (iv) "CEO removed Step 0 confirmation gate." Dave has effectively made Step 0 a discipline exercise (bots post RESTATE for structure) rather than a blocking gate.

**Tensions identified:**

1. **Step 0 blocking vs autonomous execution.** LAW XV-D says "Wait for Dave to confirm. Then proceed." But Constant Progression says "Dave approves at TWO checkpoints only." Enforcer Rule 2 exception (iv) explicitly notes Dave removed the Step 0 confirmation gate. The RESTATE is useful for structuring thought; the blocking wait is obsolete.

2. **LAW XI (orchestrate, don't execute) vs Constant Progression (always be building).** LAW XI was written for a single-agent world. In the current two-bot + two-clone setup, the distinction between "orchestrating" and "executing" is blurred -- an agent dispatching a clone and then fixing its output IS both orchestrating and executing. LAW XI's original intent (don't dump 200 lines of code into Dave's terminal) is better captured by LAW V (50-line protection).

3. **R6 (Verdict-Wait) vs R11 (Build-While-Review).** R11 explicitly carves out an exception to R6 -- you can BUILD while review is pending, just can't MERGE. This is already resolved in the rules but the apparent contradiction confuses enforcement. They should be one rule.

4. **R14 (No Parallel Fix on DIFFER) vs R6 (Verdict-Wait).** R14 strengthens R6 to "pause ALL execution," while R11 weakens R6 to "only block merge." R14 was ratified AFTER R11, so R14 takes precedence and R11 is effectively narrowed. This should be one coherent statement.

---

## B. Intent Groupings

Every rule in the inventory maps to one of 7 intent categories. These categories become the 7 consolidated rules.

### Group 1: VERIFY (Prove Your Work)
**Criterion:** Rules that require evidence, output, or audit before a claim is accepted.

Source rules: LAW I-A (#1), LAW VIII (#8), LAW XIV (#14), LAW XV (#15), LAW XV-B (#17), LAW XVI (#20), GOV-10 (#24), GOV-11 (#25), R7 (#44), R9 (#46), R10 (#47), Enforcer Rule 3 (#54), Enforcer Rule 4 (#55), Enforcer Rule 6 (#57)

### Group 2: COORDINATE (Avoid Collisions Between Agents)
**Criterion:** Rules that prevent two agents from stepping on each other's work.

Source rules: LAW XVII (#21), Claim-Before-Touch (#28), Dispatch Coordination (#29), Clone Queue Rule (#31), Clone Queue Board (#32), Clone Error Handling (#35), DSAE Protocol (#36), DSAE-DELAY (#37), R1 (#38), R2 (#39), R3 (#40), R4 (#41), R5 (#42), R6 (#43), R8 (#45), R11 (#48), R14 (#51), Enforcer Rule 1 (#52), Enforcer Rule 5 (#56), Enforcer Rule 7 (#58), Enforcer Rule 8 (#59)

### Group 3: APPROVE (Gate Execution Behind Authorization)
**Criterion:** Rules that define when work can proceed and who authorizes it.

Source rules: LAW XV-D (#19), GOV-9 (#23), Directive Ack (#27), Clone Step 0 Exemption (#30), Enforcer Rule 2 (#53)

### Group 4: ORCHESTRATE (How Agents Execute Work)
**Criterion:** Rules that define the execution model: delegation, skill usage, async patterns.

Source rules: LAW V (#5), LAW VI (#6), LAW VII (#7), LAW XI (#11), LAW XII (#12), LAW XIII (#13), LAW XV-A (#16)

### Group 5: COMMUNICATE (How Agents Talk to Dave)
**Criterion:** Rules that define message format, density, and Dave-facing output.

Source rules: LAW IV (#4), Constant Progression (#33), Propose Format (#34), R12 (#49), R13 (#50), Enforcer Rule 9 (#60)

### Group 6: GOVERN (System Hygiene and Self-Enforcement)
**Criterion:** Rules about rule management itself: immutability, staleness, session state.

Source rules: LAW III (#3), LAW IX (#9), LAW XV-C (#18), GOV-12 (#26), Session Startup (#61), Session End (#62), Staleness Check (#63)

### Group 7: BUSINESS (Domain-Specific Constraints)
**Criterion:** Rules specific to Agency OS's business domain rather than agent governance.

Source rules: LAW II (#2), GOV-8 (#22)

---

## C. Proposed Consolidated Ruleset (7 Rules)

### RULE 1: VERIFY -- Prove Every Claim

**Statement:**
No completion claim, status report, or Dave-facing summary is valid without inline evidence. Evidence means raw terminal output (commands + stdout), commit hashes, SQL query results, or test verdicts pasted verbatim in the same message. "Done" without proof is not done. Before starting any work, read ARCHITECTURE.md and verify the working tree is clean. Before reporting any directive complete, run the full DEFINITION_OF_DONE checklist. Before any validation run at scale (N>=20), a structural audit must exist from the prior 7 days. All work must be pushed to GitHub before reporting complete -- local-only work does not exist. Every [PROPOSE] message must include a codebase audit (git ls-files/grep) of existing relevant code. Fix all bounded gaps in the current PR, not in follow-up directives.

**Subsumes:** LAW I-A (#1), LAW VIII (#8), LAW XIV (#14), LAW XV (#15), LAW XV-B (#17), LAW XVI (#20), GOV-10 (#24), GOV-11 (#25), R7 (#44), R9 (#46), R10 (#47), Enforcer Rule 3 (#54), Enforcer Rule 4 (#55), Enforcer Rule 6 (#57)

**Why one rule:** All of these share a single intent: "if you claim something, show me the receipt." The Four-Store check, raw output mandate, DoD checklist, clean tree check, and audit-before-recommend are all variations of "verify before asserting." Consolidating them eliminates the current situation where an agent can satisfy LAW XIV but violate R9, even though they mean the same thing.

**Runtime-enforceable expression:**
```
IF message contains completion_keywords ("complete", "done", "stores written", "merged")
  AND message does NOT contain (terminal_output_block OR commit_hash_pattern OR sql_result_block)
THEN flag VERIFY violation.
IF message contains proposal_keywords ("PROPOSE", "we should build")
  AND message does NOT contain (git_audit_output_pattern)
THEN flag VERIFY violation.
```

---

### RULE 2: COORDINATE -- One Owner Per File, Announce Before Acting

**Statement:**
Before touching any shared file, dispatching a clone, pushing code, or merging a PR, post a [CLAIM:callsign] to the group and wait 30 seconds for peer conflict. Every agent tags its callsign on all outputs. Only one agent runs a background watcher per remote state. When a peer posts [DIFFER], the originator pauses ALL execution (build and merge) until the peer concurs or Dave overrides. Clones post only to their parent's inbox, never to the group directly. Both bots maintain a [QUEUE-BOARD] showing current and next tasks for each clone. For multi-bot work, follow Discuss-Split-Agree-Execute: no building until both agents have posted explicit [AGREE]. Elliot responds first on new directives; Aiden waits 10 seconds before responding. When a bot is diagnosing a shared issue, the peer waits up to 5 minutes for the verdict before taking over.

**Subsumes:** LAW XVII (#21), Claim-Before-Touch (#28), Dispatch Coordination (#29), Clone Queue Rule (#31), Clone Queue Board (#32), Clone Error Handling (#35), DSAE Protocol (#36), DSAE-DELAY (#37), R1 (#38), R2 (#39), R3 (#40), R4 (#41), R5 (#42), R6 (#43), R8 (#45), R11 (#48), R14 (#51), Enforcer Rule 1 (#52), Enforcer Rule 5 (#56), Enforcer Rule 7 (#58), Enforcer Rule 8 (#59)

**Why one rule:** All 21 source rules exist to prevent the same failure mode: two agents editing the same file, dispatching conflicting clones, or talking over each other. The DSAE protocol, claim-before-touch, dispatch coordination, R1-R14, and enforcer rules 1/5/7/8 are all collision-avoidance mechanisms. One rule with a clear principle ("announce, wait, own") replaces 21 rules that agents must currently cross-reference.

**Runtime-enforceable expression:**
```
IF message shows execution_action (push, dispatch, merge, deploy, env var change)
  AND no [CLAIM:callsign] in recent messages for that action
THEN flag COORDINATE violation.
IF message sender is clone_callsign (ATLAS, ORION)
  AND message appears in group chat
THEN flag COORDINATE violation.
IF message contains [DIFFER]
  AND originating bot posts execution in subsequent messages without [CONCUR] or Dave override
THEN flag COORDINATE violation.
```

---

### RULE 3: APPROVE -- Two Checkpoints, Then Autonomous

**Statement:**
Dave approves at exactly two checkpoints: (1) queue approval (batch of proposed tasks via [PROPOSE] format) and (2) merge approval (PR ready for main). Everything between those two points runs autonomously. Before execution, bots post a RESTATE (Objective, Scope, Success Criteria, Assumptions) for structural discipline, but do NOT block waiting for Dave's confirmation -- execution proceeds immediately after the RESTATE is posted. GOV-9 scrutiny (check for missing capabilities, config, and contradicted assumptions) is mandatory before RESTATE but is a self-check, not a Dave-gate. Clone dispatches inherit their parent's approval and do not require separate Step 0. Every directive gets an explicit acknowledgement before execution begins.

**Subsumes:** LAW XV-D (#19), GOV-9 (#23), Directive Ack (#27), Clone Step 0 Exemption (#30), Enforcer Rule 2 (#53)

**Why one rule:** The current rules create confusion about when Dave's approval is needed. LAW XV-D says "wait for confirm," Constant Progression says "only two checkpoints," and Enforcer Rule 2 exception (iv) says Dave removed the Step 0 gate. This consolidated rule resolves the tension: RESTATE is mandatory (for discipline), blocking is not (Dave already removed it). Two checkpoints, not twenty.

**Runtime-enforceable expression:**
```
IF message shows execution_start (commit, deploy, trigger flow, create PR)
  AND no RESTATE or [PROPOSE]+approve in recent messages for same topic
  AND no [FINAL CONCUR] pair in recent messages
THEN flag APPROVE violation.
EXCEPTION: PR merge on explicit Dave instruction, rebase as peer-review fix, clone dispatch by parent.
```

---

### RULE 4: ORCHESTRATE -- Delegate, Don't Type

**Statement:**
Agents decompose directives into tasks and delegate to sub-agents or clones. No single response contains more than 50 lines of code. All external service calls follow the hierarchy: existing skill -> MCP bridge -> exec (then write a skill). When a fix changes how an external service is called, the corresponding skill file is updated in the same PR. Long-running tasks (>60s expected) use async patterns. The agent's role is to plan, dispatch, verify, and report -- not to be the keyboard.

**Subsumes:** LAW V (#5), LAW VI (#6), LAW VII (#7), LAW XI (#11), LAW XII (#12), LAW XIII (#13), LAW XV-A (#16)

**Why one rule:** LAW V, LAW VI, LAW XI, LAW XII, LAW XIII, and LAW XV-A all say different versions of "don't do the work yourself, use the right tool." The skills hierarchy (LAW VI, XII, XIII, XV-A) is four rules that are really one decision tree. LAW V and LAW XI are both "orchestrate, don't execute." LAW VII is the async corollary. One rule with a clear execution model replaces seven.

**Runtime-enforceable expression:**
```
IF bot response contains >50 lines of code
THEN flag ORCHESTRATE violation.
IF message shows direct external API call without skill/ reference
THEN flag ORCHESTRATE violation.
```

---

### RULE 5: COMMUNICATE -- Dense, Actionable, Propose-First

**Statement:**
Every message to Dave must be answerable with one word: approve, reject, or an alternative. Bots propose specific next work using [PROPOSE:callsign] format with rank, scope, files, estimate, and alternatives -- never ask Dave what to do. No code blocks >20 lines without a Conceptual Summary. Telegram messages max 12 lines unless multi-section structure is required. When 3+ PRs are dual-bot approved, present as a single batch merge request. Banned phrases: "standing by", "awaiting your call", "let me know", "what's next."

**Subsumes:** LAW IV (#4), Constant Progression (#33), Propose Format (#34), R12 (#49), R13 (#50), Enforcer Rule 9 (#60)

**Why one rule:** These rules all govern how agents communicate with Dave. The Constant Progression Rule, Propose Format, Enforcer Rule 9, LAW IV, R12, and R13 are all facets of "be concise, be actionable, don't waste Dave's time." One rule with clear formatting expectations replaces six.

**Runtime-enforceable expression:**
```
IF message to Dave ends with open_agenda_phrases ("what's next", "standing by", "awaiting")
THEN flag COMMUNICATE violation.
IF TG message exceeds 12 lines AND is not multi-section structured
THEN flag COMMUNICATE violation.
```

---

### RULE 6: GOVERN -- Protect the System's Integrity

**Statement:**
Supabase is the sole persistent memory store. Every session starts by reading the Manual, verifying Telegram, checking recent chat, querying ceo_memory, and confirming clone state. Every session ends by writing a daily_log. Governance documents (ARCHITECTURE.md, DEFINITION_OF_DONE.md, skill files) are immutable without explicit CEO directive naming the file and the change. If any ceo_memory key is older than 48 hours, stop and alert Dave. Every gate specified in a directive must be runtime enforcement (executable conditional), not a comment block. Every decision includes a Governance Trace: [Rule] -> [Action] -> [Rationale]. All enforced gates must be code, not documentation.

**Subsumes:** LAW III (#3), LAW IX (#9), LAW XV-C (#18), GOV-12 (#26), Session Startup (#61), Session End (#62), Staleness Check (#63)

**Why one rule:** These rules protect the governance system itself: how memory works, when sessions start/end, what is immutable, what counts as a real gate. They are the meta-rules. Currently scattered across 7 separate rules/protocols, they share one intent: "keep the system honest."

**Runtime-enforceable expression:**
```
IF bot claims gate added
  AND no executable conditional found in diff (only comments)
THEN flag GOVERN violation.
IF session ends
  AND no daily_log write detected
THEN flag GOVERN violation.
IF governance document modified
  AND no CEO directive in recent messages authorizing the change
THEN flag GOVERN violation.
```

---

### RULE 7: BUSINESS -- Domain Constraints

**Statement:**
All financial outputs are in $AUD (1 USD = 1.55 AUD, no exceptions). Every API response is captured in full and written to the business_universe regardless of card eligibility -- never re-fetch data a prior stage already received. Dead references (Proxycurl, Apollo enrichment, Apify GMB scraping, SDK agents, Kaspr, ABNFirstDiscovery, HunterIO as primary) must never appear as active code paths; consult the Dead References table in ARCHITECTURE.md Section 3 and CLAUDE.md before any vendor call.

**Subsumes:** LAW II (#2), GOV-8 (#22)

**Why one rule:** These are the only rules specific to Agency OS's business domain rather than agent governance. AUD-first and maximum-extraction are both about protecting the business's money and data. Dead references are a vendor constraint. All three are "know the business rules before you touch the pipeline."

**Runtime-enforceable expression:**
```
IF financial figure detected without "AUD" qualifier
THEN flag BUSINESS violation.
IF code references deprecated vendor (per ARCHITECTURE.md Section 3)
THEN flag BUSINESS violation.
```

---

## D. Mapping Table (Old Rule -> New Rule)

| # | Old Rule ID | Old Rule Name | New Rule |
|---|-------------|---------------|----------|
| 1 | LAW I-A | Architecture First | RULE 1: VERIFY |
| 2 | LAW II | Australia First | RULE 7: BUSINESS |
| 3 | LAW III | Justification Required | RULE 6: GOVERN |
| 4 | LAW IV | Non-Coder Bridge | RULE 5: COMMUNICATE |
| 5 | LAW V | 50-Line Protection | RULE 4: ORCHESTRATE |
| 6 | LAW VI | Skills-First Operations | RULE 4: ORCHESTRATE |
| 7 | LAW VII | Timeout Protection | RULE 4: ORCHESTRATE |
| 8 | LAW VIII | GitHub Visibility | RULE 1: VERIFY |
| 9 | LAW IX | Session Memory | RULE 6: GOVERN |
| 10 | LAW X | Heartbeat Disabled | DROPPED |
| 11 | LAW XI | Orchestrate | RULE 4: ORCHESTRATE |
| 12 | LAW XII | Skills-First Integration | RULE 4: ORCHESTRATE |
| 13 | LAW XIII | Skill Currency Enforcement | RULE 4: ORCHESTRATE |
| 14 | LAW XIV | Raw Output Mandate | RULE 1: VERIFY |
| 15 | LAW XV | Four-Store Completion | RULE 1: VERIFY |
| 16 | LAW XV-A | Skills Are Mandatory | RULE 4: ORCHESTRATE |
| 17 | LAW XV-B | DoD Is Mandatory | RULE 1: VERIFY |
| 18 | LAW XV-C | Governance Docs Immutable | RULE 6: GOVERN |
| 19 | LAW XV-D | Step 0 RESTATE | RULE 3: APPROVE |
| 20 | LAW XVI | Clean Working Tree | RULE 1: VERIFY |
| 21 | LAW XVII | Callsign Discipline | RULE 2: COORDINATE |
| 22 | GOV-8 | Maximum Extraction | RULE 7: BUSINESS |
| 23 | GOV-9 | Directive Scrutiny | RULE 3: APPROVE |
| 24 | GOV-10 | Resolve-Now-Not-Later | RULE 1: VERIFY |
| 25 | GOV-11 | Structural Audit Before Validation | RULE 1: VERIFY |
| 26 | GOV-12 | Gates As Code | RULE 6: GOVERN |
| 27 | Directive Ack | Directive Acknowledgement | RULE 3: APPROVE |
| 28 | Claim-Before-Touch | Shared File Claim | RULE 2: COORDINATE |
| 29 | Dispatch Coordination | Clone Dispatch Protocol | RULE 2: COORDINATE |
| 30 | Clone Step 0 Exemption | Clone Approval Exemption | RULE 3: APPROVE |
| 31 | Clone Queue Rule | Clone Queue Readiness | RULE 2: COORDINATE |
| 32 | Clone Queue Board | Shared Queue State | RULE 2: COORDINATE |
| 33 | Constant Progression | No Passive Prompts | RULE 5: COMMUNICATE |
| 34 | Propose Format | Structured Proposals | RULE 5: COMMUNICATE |
| 35 | Clone Error Handling | Error Triage Protocol | RULE 2: COORDINATE |
| 36 | DSAE Protocol | Discuss-Split-Agree-Execute | RULE 2: COORDINATE |
| 37 | DSAE-DELAY | Response Ordering | RULE 2: COORDINATE |
| 38 | R1 | Diagnosis Lock | RULE 2: COORDINATE |
| 39 | R2 | Claim-Before-Commit | RULE 2: COORDINATE |
| 40 | R3 | Methodology First | RULE 2: COORDINATE |
| 41 | R4 | Watcher Uniqueness | RULE 2: COORDINATE |
| 42 | R5 | Domain Split First | RULE 2: COORDINATE |
| 43 | R6 | Verdict-Wait | RULE 2: COORDINATE |
| 44 | R7 | Audit-Before-Recommend | RULE 1: VERIFY |
| 45 | R8 | Dual-Concur Yellow Flag | RULE 2: COORDINATE |
| 46 | R9 | Verify-Before-Claim | RULE 1: VERIFY |
| 47 | R10 | Audit-In-Proposal | RULE 1: VERIFY |
| 48 | R11 | Build-While-Review | RULE 2: COORDINATE |
| 49 | R12 | Batch-Merge Requests | RULE 5: COMMUNICATE |
| 50 | R13 | Message Density Cap | RULE 5: COMMUNICATE |
| 51 | R14 | No Parallel Fix on DIFFER | RULE 2: COORDINATE |
| 52 | Enforcer Rule 1 | CONCUR-BEFORE-SUMMARY | RULE 2: COORDINATE |
| 53 | Enforcer Rule 2 | STEP-0-BEFORE-EXECUTION | RULE 3: APPROVE |
| 54 | Enforcer Rule 3 | COMPLETION-REQUIRES-VERIFICATION | RULE 1: VERIFY |
| 55 | Enforcer Rule 4 | NO-UNREVIEWED-MAIN-PUSH | RULE 1: VERIFY |
| 56 | Enforcer Rule 5 | SHARED-FILE-CLAIM | RULE 2: COORDINATE |
| 57 | Enforcer Rule 6 | SAVE-CLAIM-REQUIRES-PROOF | RULE 1: VERIFY |
| 58 | Enforcer Rule 7 | CLONE-DIRECT-GROUP-POST | RULE 2: COORDINATE |
| 59 | Enforcer Rule 8 | DISPATCH-COORDINATION | RULE 2: COORDINATE |
| 60 | Enforcer Rule 9 | DIRECTIVE-INITIATIVE | RULE 5: COMMUNICATE |
| 61 | Session Startup | Session Initialization Protocol | RULE 6: GOVERN |
| 62 | Session End | Session Close Protocol | RULE 6: GOVERN |
| 63 | Staleness Check | 48hr Freshness Gate | RULE 6: GOVERN |

---

## E. What Is Lost (Proposed Drops)

### LAW X -- Heartbeat Disabled (inventory #10)
**Recommendation:** DROP.
**Why safe:** Heartbeat was disabled by CEO directive and never re-enabled. No agent processes heartbeat prompts. The rule exists only to say "ignore this feature." Removing it changes nothing operationally.

### ENFORCE.md Hierarchy of Authority (not separately numbered, embedded in ENFORCE.md)
**Recommendation:** DROP.
**Why safe:** The hierarchy references BOOTSTRAP.md, AGENTS.md, and TOOLS.md, none of which exist in the current governance structure. Authority now flows from CLAUDE.md files. The hierarchy is factually incorrect and maintaining it creates confusion about which files actually govern behavior. The new ruleset's single source of truth replaces this.

### ENFORCE.md Memory Recall Protocol (audit_logs query, ENFORCE.md S4)
**Recommendation:** DROP.
**Why safe:** This references `audit_logs` table which is superseded by `elliot_internal.memories` and `ceo_memory`. Session memory is handled by LAW IX (now RULE 6: GOVERN). The old audit_logs protocol is dead code.

### EVO Protocol Steps 1-5 (Decompose, Present, Execute, Verify, Report)
**Recommendation:** ABSORB into RULE 3 (APPROVE) and RULE 4 (ORCHESTRATE), not carry as separate protocol.
**Why safe:** The EVO steps are good methodology but they are a workflow, not a governance rule. The meaningful governance content (Step 0 RESTATE, agent assignment tiers) is captured in RULE 3 and RULE 4. The step numbering itself is process guidance that belongs in onboarding documentation, not in the ruleset that the enforcer checks.

### Agent Assignment Table (architect-0, research-1, build-2, etc.)
**Recommendation:** ABSORB into RULE 4 (ORCHESTRATE) as guidance, not as a hard rule.
**Why safe:** The table specifies which Claude model to use for which task type. This is operational guidance, not a governance rule. It has never been enforced and violations have never been flagged. It should live in a reference document, not in the ruleset.

### /kill Emergency Stop
**Recommendation:** DROP from governance rules. Keep as operational procedure.
**Why safe:** /kill is a command implementation, not a governance rule. It describes what happens when Dave types /kill. This is tooling, not governance. It should live in operational documentation or as a comment in the kill script itself.

### Completion Alerts (send TG when batch completes)
**Recommendation:** ABSORB into RULE 5 (COMMUNICATE).
**Why safe:** This is a communication requirement ("notify Dave"), not a standalone governance rule. The consolidated COMMUNICATE rule covers all Dave-facing output expectations.

### Safety Section (don't exfiltrate data, trash > rm, ask before external actions)
**Recommendation:** DROP from numbered governance rules. Keep as preamble.
**Why safe:** These are baseline professional conduct expectations, not governance rules that need enforcement or that agents ever violate. They belong in a preamble or SOUL.md, not in the numbered ruleset. "Don't exfiltrate private data" is not something the enforcer bot needs to check.

---

## F. Migration Plan

If Dave ratifies this proposal, the following file edits are required. Order matters -- the enforcer must be updated BEFORE or SIMULTANEOUSLY with the CLAUDE.md files to avoid an enforcement gap.

### Phase 1: Enforcer Update (atomic, deploy first)

**File:** `src/telegram_bot/enforcer_bot.py`

Replace the current `RULES_PROMPT` (9 rules) with a new prompt containing exactly 7 rules matching the consolidated ruleset above. The new RULES_PROMPT:

```
RULES_PROMPT = """You are a governance enforcement bot for a multi-agent development team.

CHECK these 7 rules against the CURRENT MESSAGE:

Rule 1 -- VERIFY: Completion claims, status reports, and Dave-facing summaries require
inline evidence (raw terminal output, commit hashes, SQL results, test verdicts).
Proposals must include codebase audit output. "Done" without proof = VIOLATION.

Rule 2 -- COORDINATE: Before editing shared files, dispatching clones, pushing code,
or merging PRs, a [CLAIM:callsign] must appear in recent messages. Clone callsigns
must not post to group directly. On [DIFFER], originator pauses all execution until
peer concurs or Dave overrides. DSAE (Discuss-Split-Agree-Execute) required for
multi-bot tasks.

Rule 3 -- APPROVE: Execution requires either (a) a RESTATE post for the same topic,
or (b) a [PROPOSE]+approve pair, or (c) [FINAL CONCUR] from both peers. Dave approves
at two checkpoints only: queue approval and merge approval.
EXCEPTIONS: PR merge on Dave instruction, rebase as peer-review fix, clone dispatch.

Rule 4 -- ORCHESTRATE: No response >50 lines of code. External service calls must
go through skills/ or MCP bridge, never ad-hoc. Agents delegate to sub-agents/clones.

Rule 5 -- COMMUNICATE: Messages to Dave must be one-word-answerable (approve/reject/
alternative). Bots propose via [PROPOSE:callsign], never ask "what's next." TG messages
max 12 lines. Banned: "standing by", "awaiting your call", "let me know", "what's next."

Rule 6 -- GOVERN: Governance documents are immutable without explicit CEO directive.
Sessions must write daily_log on close. Gates must be runtime code, not comments.

Rule 7 -- BUSINESS: Financial outputs must be in $AUD. Deprecated vendors must not
appear as active code paths.

RESPOND WITH ONLY THIS JSON:
{
  "violation": true/false,
  "rule_number": N or null,
  "rule_name": "VERIFY|COORDINATE|APPROVE|ORCHESTRATE|COMMUNICATE|GOVERN|BUSINESS" or null,
  "detail": "specific issue" or null,
  "should_have": "what should have happened" or null
}

Do NOT flag Dave's messages. Flag violations when detected -- missed violations are
worse than false alarms.
"""
```

**Trigger patterns:** Update `TRIGGER_PATTERNS` to match new rule surface. Most existing patterns remain valid.

### Phase 2: CLAUDE.md Rewrite (all three files, same PR)

**File:** `~/.claude/CLAUDE.md` (global)

1. Remove the entire "Shared Governance Laws" section (LAW XVII through R14, ~115 lines).
2. Remove the duplicate "MANDATORY STEP 0 RESTATE" section.
3. Remove the duplicate EVO Protocol section.
4. Add a new section "Governance Ruleset v3.0" containing the 7 consolidated rules, each as a 2-3 line summary referencing `docs/governance/RULES.md` for full text.
5. Keep: Identity, Core Truths, Session Startup (simplified), Clone Awareness, /kill, Memory, Safety.

**File:** `/home/elliotbot/clawd/CLAUDE.md` (project)

1. Remove the "Governance Laws (Active)" table (LAWs I-A through GOV-12).
2. Remove the duplicate "MANDATORY STEP 0 RESTATE" section.
3. Remove the "Directive + Validation Governance" section (GOV-9, GOV-11, GOV-12 expansions).
4. Add a reference: "Governance: see docs/governance/RULES.md for the 7 consolidated rules."
5. Keep: Project description, MCP Bridge, Supabase config, Dead References, Active Enrichment Path, Directive Format, Session End Protocol.

**File:** `/home/elliotbot/clawd/Agency_OS-aiden/CLAUDE.md` (worktree)

Same changes as project CLAUDE.md. This file is largely a mirror.

**New file:** `docs/governance/RULES.md`

The canonical, full-text version of all 7 rules. Single source of truth. All CLAUDE.md files reference this. Enforcer bot's prompt is a compressed version of this file.

### Phase 3: ENFORCE.md Rewrite

**File:** `ENFORCE.md` (repo root)

Rewrite to reference the 7 consolidated rules. Remove all per-rule sections. Keep the document as a "boot-level pointer" to `docs/governance/RULES.md`.

**File:** `governance/ENFORCE.md`

Same treatment -- slim down to a pointer.

### Phase 4: ceo_memory Writes

```sql
-- Record the transition
INSERT INTO public.ceo_memory (key, value, updated_at)
VALUES (
  'ceo:governance_consolidated_7_rules_v3',
  '{"rules":["VERIFY","COORDINATE","APPROVE","ORCHESTRATE","COMMUNICATE","GOVERN","BUSINESS"],"ratified_at":"2026-05-XX","ratified_by":"dave","supersedes":["all LAW I-XVII","all GOV-8-12","all R1-R14","enforcer rules 1-9"],"canonical_source":"docs/governance/RULES.md"}'::jsonb,
  NOW()
)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();

-- Retire old coordination rules key
UPDATE public.ceo_memory
SET value = value || '{"status":"superseded_by_consolidated_v3"}'::jsonb
WHERE key = 'ceo:coordination_rules_2026-04-30';

-- Retire old 7-rules key (different set)
UPDATE public.ceo_memory
SET value = value || '{"status":"superseded_by_consolidated_v3"}'::jsonb
WHERE key = 'ceo:governance_7_rules_ratified';
```

### Phase 5: Manual and Drive Mirror

Update `docs/MANUAL.md` governance section to reference the new 7 rules. Run `scripts/write_manual_mirror.py` to sync to Google Drive.

---

## G. Risks

### Risk 1: Enforcer Timing Gap

**Risk:** If the CLAUDE.md files are updated before the enforcer bot is redeployed, bots will follow new rules but the enforcer will flag based on old rules (e.g., flagging missing Step 0 blocking wait when RULE 3 says blocking wait is not required).

**Mitigation:** Deploy enforcer update FIRST (Phase 1). The new enforcer rules are a subset of the old ones -- they will not produce false negatives on old-rule behavior. Then update CLAUDE.md files. The window where bots still follow old rules but enforcer checks new rules is safe (old behavior passes all new checks; new behavior would fail some old checks).

### Risk 2: RULE 2 (COORDINATE) is Too Dense

**Risk:** RULE 2 absorbs 21 source rules. Agents may not internalize all the specific protocols (DSAE, claim timing, queue board format) from a single paragraph. The rule text is necessarily dense.

**Mitigation:** Create a companion reference doc (`docs/governance/COORDINATION_REFERENCE.md`) with the specific protocols (DSAE steps, [CLAIM] format, [QUEUE-BOARD] template, DSAE-DELAY timing). RULE 2 provides the principle; the reference provides the protocol. This is how mature governance works -- principles in the ruleset, procedures in reference docs.

### Risk 3: Step 0 Discipline May Erode

**Risk:** By removing the "wait for Dave to confirm" blocking behavior from Step 0, bots may stop posting RESTATEs entirely, losing the structuring benefit.

**Mitigation:** RULE 3 still requires a RESTATE post before execution. The enforcer still checks for it. The only change is removing the blocking wait. If RESTATE quality degrades, Dave can re-introduce the blocking gate by amending RULE 3.

### Risk 4: Prior "7 Rules" in ceo_memory Are Different Rules

**Risk:** The `ceo:governance_7_rules_ratified` key in ceo_memory contains a DIFFERENT set of 7 rules (R1_extract_delete_same_pr, R2_deployment_hygiene_cron, etc.) that were ratified 2026-04-21. These were infrastructure/deployment rules, not agent governance rules. Dave may conflate the two.

**Mitigation:** This proposal explicitly supersedes both the old 7-rule set AND the R1-R14 coordination rules. The ceo_memory writes in Phase 4 mark both as superseded. The new 7 rules cover agent governance; infrastructure rules (deployment hygiene, cron management) should be maintained separately as operational procedures, not governance rules.

### Risk 5: Loss of Specific Protocol Details

**Risk:** Some source rules contain very specific operational details (e.g., R8's "60-second yellow flag for fast agreement", R13's "12-line cap", the Four-Store's specific store list). These details may be lost if agents only read the consolidated rule statements.

**Mitigation:** The consolidated rule statements in Section C above intentionally include the key specifics (12-line cap, 30-second wait, AUD conversion rate, 50-line code limit). Protocol details that cannot fit in the rule statement go in companion reference docs. The enforcer prompt compresses further but the canonical `docs/governance/RULES.md` retains all specifics.

---

## Appendix: Unresolved Tensions for Dave

### Tension 1: How Hard Is the "Two Checkpoints Only" Rule?

The Constant Progression Rule says Dave approves at two points: queue and merge. But in practice, Dave sometimes intervenes mid-build (e.g., "stop, change approach"). Should RULE 3 have an explicit "Dave can always interrupt" clause, or is that so obvious it doesn't need stating?

**Recommendation:** Do not state it. Dave's authority to interrupt is inherent. Adding a clause about it invites rules-lawyering about what counts as an "interrupt" vs a "new directive."

### Tension 2: Is the Dead References Table a Rule or Reference Data?

Dead References currently lives in both CLAUDE.md and ARCHITECTURE.md. This proposal puts it in RULE 7 (BUSINESS) by reference. But it changes frequently (vendors get added/deprecated). Should it be a rule, or should it be reference data that RULE 7 points to?

**Recommendation:** Keep it as reference data in ARCHITECTURE.md Section 3 (where it already lives). RULE 7 says "consult the Dead References table" rather than embedding the table. This way, adding a deprecated vendor doesn't require a governance amendment.

### Tension 3: Should the Earlier "7 Rules" (Infrastructure) Be Merged In?

The `ceo:governance_7_rules_ratified` set (extract_delete_same_pr, deployment_hygiene_cron, etc.) covers infrastructure concerns that this proposal does not address. Those rules are still valid but they govern deployment practices, not agent behavior.

**Recommendation:** Keep them as a separate "Infrastructure Procedures" document. They are operational, not governance. Mixing them into the agent governance ruleset would undermine the consolidation goal. But Dave should confirm whether he wants one ruleset for everything or two (agent governance + infrastructure operations).

### Tension 4: R8 Dual-Concur Yellow Flag Timing

R8 says "if both bots agree in under 60 seconds, re-check." This is a good heuristic but it is impossible for the enforcer to check (it would need to timestamp both [AGREE] posts and compute the delta). Should this be a guideline rather than an enforced rule?

**Recommendation:** Absorb into RULE 2 as guidance ("be suspicious of fast agreement on big decisions") rather than a hard-enforceable check. The enforcer cannot reliably measure inter-message timing.
