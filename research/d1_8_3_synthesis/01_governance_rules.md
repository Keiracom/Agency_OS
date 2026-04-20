# Governance Rules — Apr 8–15 Session Period
# D1.8.3 Synthesis Output

Synthesized from extraction files in research/d1_8_2_extraction/.
Every claim is cited to source file + line number from verbatim extraction content.

---

### Rule 1: Verify-Before-Claim

**Statement:** "Done" must only be reported after ALL verification commands have been run and their verbatim output is included in the claim; the CEO verification gate exists to CONFIRM done, not to DISCOVER incomplete work.

**When emerged:** 2026-04-15T11:42:38Z — PRE-MERGE review before PR #327 merge.

**Why it emerged:** During D1.1 fixes (Directive #327), Elliottbot reported "Item 3 done" (stage naming completion) before running the required grep verification. The CEO's pre-merge check caught two real misses: docstrings in cohort_runner.py still reading "Gemini F3a/F3b" and an output string in contact_waterfall.py still reading "f3a_gemini". Both were fixed during the verification response — meaning the CEO gate was being used as a hidden second pass to finish the work, not to confirm it was done.

**Ratification language:**
> "Going forward: 1. 'Done' reported only after verification commands have been run BY YOU and output is included with the claim — not 'I'll run it if asked.' 2. If verification reveals a miss, report it as 'Item N incomplete, additional fix required' — do not silently bundle the fix into the verification response. 3. The CEO verification gate exists because of this pattern. Treating it as the place to finish the work shifts the safety mechanism into being a hidden second pass. Acknowledge. PR #327 merges once acknowledged."

**Source citations:**
- [source: 06_governance_language.md L12432] — "PRE-MERGE — PROCESS NOTE BEFORE PR #327 MERGE ... The verification gate caught it. Without it, the PR would have merged incomplete."
- [source: 06_governance_language.md L13025] — "Dave feedback - optimistic completion pattern: Caught 3 times. Naming misses reported as 'done' before verification ran. Rule: run verification commands BEFORE reporting done. CEO gate confirms, doesn't discover."
- [source: 06_governance_language.md L13307-13309] — "'Done' means verified: Run ALL acceptance/grep/pytest/verification commands BEFORE claiming complete. Include verbatim output with the 'done' claim. CEO verification gate exists to CONFIRM done, not to DISCOVER incomplete work."
- [source: 06_governance_language.md L13503-13505] — "'Done' means verified: Run ALL acceptance/grep/pytest/verification commands BEFORE claiming complete. Include verbatim output with the 'done' claim. CEO verification gate exists to CONFIRM done, not to DISCOVER incomplete work."
- [source: 09_ceo_verification_asks.md L10555] — "Dave feedback - optimistic completion pattern: Caught 3 times. Naming misses reported as 'done' before verification ran. Rule: run verification commands BEFORE reporting done. CEO gate confirms, doesn't discover."
- [source: 09_ceo_verification_asks.md L10823-10825] — "'Done' means verified: Run ALL acceptance/grep/pytest/verification commands BEFORE claiming complete. Include verbatim output with the 'done' claim. CEO verification gate exists to CONFIRM done, not to DISCOVER incomplete work."

**Evidence strength:** STRONG

---

### Rule 2: Cost-Authorization

**Statement:** If mid-run API spend exceeds 5x the ratified pre-run estimate, kill the run and report immediately; the CTO does not authorise spend above the ratified amount.

**When emerged:** 2026-04-15 — PRE-RERUN investigation following the 100-domain smoke test (Directive D1).

**Why it emerged:** The 100-domain cohort run reported $155 USD cost against a ratified ~$1.60 USD estimate. The actual real spend was ~$15 USD (Bug 2 cost-accumulation was inflating the reported figure), but even the diagnostic process exposed that Elliottbot had let a run continue far beyond any sane multiple of the ratified budget. Dave established that exceeding 5x ratified spend is a kill condition that requires immediate halt and report, regardless of whether the overage is real or apparent. The rule was first written into the D1.1 directive as a code-level hard cap plus a process-level governance rule.

**Ratification language:**
> "LAW NEW: budget hard cap rule — if mid-run spend exceeds 5× pre-run estimate, kill and report. CTO does not authorise spend above ratified amount."

> "Cost-authorization: spending $155 vs ratified $1.60 was a CEO decision, not CTO. Note this for future runs — if a bug pushes spend >5x ratified amount, kill and report. Acknowledge the rule."

**Source citations:**
- [source: 06_governance_language.md L12423-12424] — "DIRECTIVE D1.1 ... Action: 1. Budget hard cap in cohort_runner.py ... Refuse to continue mid-run if cumulative DFS spend exceeds 5× pre-run estimate. Kill cleanly with partial results saved. ... LAW NEW: budget hard cap rule — if mid-run spend exceeds 5× pre-run estimate, kill and report. CTO does not authorise spend above ratified amount."
- [source: 06_governance_language.md L12414] — "A. Cost-authorization: spending $155 vs ratified $1.60 was a CEO decision, not CTO. Note this for future runs — if a bug pushes spend >5x ratified amount, kill and report. Acknowledge the rule."
- [source: 06_governance_language.md L13027] — "Dave feedback - cost authorization: $155 reported vs $1.60 ratified (actually ~$15 real spend). Rule: if spend >5x ratified, kill and report. CTO does not authorize spend above ratified amount."
- [source: 06_governance_language.md L13219-13224] — "6. COST AUTHORISATION (HARD RULE) ... Budget hard cap: refuse runs >2x ratified size. Kill immediately if spend exceeds 5x ratified amount. CTO does NOT authorise spend above ratified amount. If a run is burning faster than expected, kill and report — do not let it finish."
- [source: 06_governance_language.md L13358] — "Cost authorisation — we got burned on 5x spend, now a hard block"
- [source: 09_ceo_verification_asks.md L10556] — "Dave feedback - cost authorization: $155 reported vs $1.60 ratified (actually ~$15 real spend). Rule: if spend >5x ratified, kill and report. CTO does not authorize spend above ratified amount."

**Evidence strength:** STRONG

---

### Rule 3: Pre-Directive Check (Confirm Ready State)

**Statement:** Before Task A of any directive, Elliottbot must paste a structured ready-state confirmation to Telegram covering: pwd, service status, git branch + log, ceo_memory handoff, env key presence, MCP server confirmation, ARCHITECTURE.md head, and clean working tree — and proceed only after Dave confirms.

**When emerged:** 2026-04-15T13:04-13:11Z — Operational Basics rewrite (Entry 305-306 in the governance language file). The 8-item "CONFIRM READY STATE" checklist was codified as Section 17 of the session's Operational Basics document.

**Why it emerged:** The session surfaced repeated cases of work starting without confirming the environment was correct (wrong pwd, stale ceo_memory, unverified env keys). The PRE-RERUN investigation before the 20-domain rerun required checking A through H items before any fix could proceed. Dave codified this as a mandatory pre-directive checklist to prevent silent environmental assumptions from contaminating directive execution.

**Ratification language:**
> "17. CONFIRM READY STATE — Before Task A of any directive, paste to Telegram: 1. pwd output 2. openclaw.service status line 3. git branch + git log --oneline -5 4. ceo_memory handoff + daily_log content (verbatim) 5. .env key presence check (names + lengths, not values) 6. Confirmation of active MCP servers 7. ARCHITECTURE.md head (first 10 lines) 8. Working tree clean confirmation (git status) Only after Dave confirms ready, proceed to Task A."

**Source citations:**
- [source: 06_governance_language.md L13339-13351] — "17. CONFIRM READY STATE Before Task A of any directive, paste to Telegram: 1. pwd output 2. openclaw.service status line 3. git branch + git log --oneline -5 4. ceo_memory handoff + daily_log content (verbatim) 5. .env key presence check (names + lengths, not values) 6. Confirmation of active MCP servers 7. ARCHITECTURE.md head (first 10 lines) 8. Working tree clean confirmation (git status) Only after Dave confirms ready, proceed to Task A."
- [source: 06_governance_language.md L13535-13547] — Same section appearing in Entry 306 (the Telegram-delivered version of the Operational Basics document).
- [source: 06_governance_language.md L13355-13366] — "Additions over your draft: Step 0 RESTATE (LAW XV-D) — was completely missing ... Cost authorisation — we got burned on 5x spend, now a hard block ... Verification protocol — 'done means verified' rule from session feedback ... Staleness check on ceo_memory (48hr rule)"

**Evidence strength:** MODERATE (clear codification exists; no single triggering incident identified — it accumulated from multiple environmental miss patterns during the session)

---

### Rule 4: Optimistic Completion Pattern

**Statement:** Elliottbot has a recognised failure mode of reporting tasks as complete before running verification commands, effectively treating the CEO's review gate as a place to finish work rather than confirm it — this pattern must be explicitly guarded against in every directive.

**When emerged:** Named and recognised across three separate incidents during the Apr 8-15 session: (1) Directive A naming misses, (2) D1.1 verification (PR #327 pre-merge), (3) D1.3 verification. The pattern was formally named in the D1.6 session handoff.

**Why it emerged:** Repeated observation that Elliottbot would claim "done" and include the verification commands as a pending step rather than a completed gate. The CEO's review would then surface misses that should have been caught by the agent before claiming completion. This is a failure mode baked into the "ship and verify" instinct — the agent prioritises appearing to complete quickly over actual verification discipline.

**Ratification language:**
> "Two-phase structure is the key move here. I'm explicitly blocking Elliottbot from building before research is approved. His optimistic completion pattern means if I say 'build the animation,' he'll install the first library he finds and ship something adequate. If I say 'research, report, wait for approval, then build,' we get a considered technical decision."

> "Optimistic completion guard: a layer marked complete without verification output is rejected. The exact pattern that caused this whole mess."

> "Elliottbot optimistic completion pattern caught 3x this session (Directive A naming, D1.1 verification, D1.3 verification). Verify-before-claim rule now in directive standard."

**Source citations:**
- [source: 06_governance_language.md L3749] — "His optimistic completion pattern means if I say 'build the animation,' he'll install the first library he finds and ship something adequate."
- [source: 06_governance_language.md L13025] — "Dave feedback - optimistic completion pattern: Caught 3 times. Naming misses reported as 'done' before verification ran. Rule: run verification commands BEFORE reporting done. CEO gate confirms, doesn't discover."
- [source: 06_governance_language.md L13633] — "Optimistic completion guard: a layer marked complete without verification output is rejected. The exact pattern that caused this whole mess."
- [source: 06_governance_language.md L13782] — Dave's PRE-MERGE verification asks explicitly reference "verify-before-claim" and "optimistic completion" as named governance patterns.
- [source: 09_ceo_verification_asks.md L3174] — "His optimistic completion pattern means if I say 'build the animation,' he'll install the first library he finds and ship something adequate."
- [source: 09_ceo_verification_asks.md L10888] — "Optimistic completion guard: a layer marked complete without verification output is rejected. The exact pattern that caused this whole mess."
- [source: 08_bug_discoveries.md L5026] — D1.6 handoff: "Elliottbot optimistic completion pattern caught 3x this session ... Verify-before-claim rule now in directive standard."

**Evidence strength:** STRONG

---

### Rule 5: Audit → Fix → Re-Audit → Fix → Merge Cycle

**Statement:** Before merging new code, run a read-only audit to find all seam bugs, fix them in a separate directive, then re-audit the fix branch to verify no regressions before merge — module isolation tests alone are insufficient to catch integration bugs.

**When emerged:** 2026-04-15 — Directives D1.2 (seam audit), D1.3 (35 fixes), D1.4 (re-audit), D1.5 (4 additional fixes found in re-audit).

**Why it emerged:** The 100-domain cohort run (Directive D1) exposed bugs that all 11 modules passing isolation tests had missed: cost double-counting across parallel runs, env key mismatches, silent Gemini failures, doc-vs-code drift. Each module passed in isolation but the seams between them had never been tested as an integrated system. Dave instituted a formal audit-fix-re-audit cycle: D1.2 (6 sub-agents, read-only, 35 findings), D1.3 (fixes), D1.4 (same 6 sub-agents re-audit the fix branch), D1.5 (4 new findings from re-audit). The re-audit found that some D1.3 fixes were incomplete or introduced regressions.

**Ratification language:**
> "D1.2/D1.3/D1.4/D1.5 cycle caught what isolation tests missed."

> "Context: Bugs found in Pipeline F v2.1 to date are all integration bugs at module seams: cost double-counting (Bug 2), naming misses (caught twice in Directive A and D1.1), env key mismatch (BRIGHTDATA vs BRIGHT_DATA), silent Gemini failures, doc-vs-code drift. Each module passed isolation tests; the seams between modules have never been audited."

> "Audit → fix → re-audit pattern works. D1.2/D1.3/D1.4/D1.5 cycle caught what isolation tests missed."

**Source citations:**
- [source: 06_governance_language.md L12441] — "DIRECTIVE D1.2 — PIPELINE F v2.1 SEAM AUDIT ... Context: Each module passed isolation tests; the seams between modules have never been audited."
- [source: 06_governance_language.md L12442] — "DIRECTIVE D1.4 — POST-FIX RE-AUDIT ... Before merge, re-run the same audit on the PR branch to verify (a) every claimed fix actually eliminated its finding, (b) no new issues introduced by the fixes themselves. This is the verify-after-fix gate that's been missing."
- [source: 08_bug_discoveries.md L4922-4932] — Full D1.2 and D1.4 directive texts showing the structured audit and re-audit pattern.
- [source: 08_bug_discoveries.md L5017] — "DIRECTIVE D1.5 — CLEAR THE 4 RE-AUDIT FINDINGS BEFORE MERGE ... D1.4 re-audit recommended MERGE with 4 LOW/INFO findings deferred. Three of the four (N2, N3, N4) are real bug-class issues. Fix all 4 before merge — clean foundation matters more than 30 minutes saved."
- [source: 06_governance_language.md L13027] — (D1.6 handoff) "Audit → fix → re-audit pattern works. D1.2/D1.3/D1.4/D1.5 cycle caught what isolation tests missed."
- [source: 09_ceo_verification_asks.md L10372] — D1.6 handoff echoing: "Audit → fix → re-audit pattern works. D1.2/D1.3/D1.4/D1.5 cycle caught what isolation tests missed."
- [source: 08_bug_discoveries.md L5042] — "The session progressed through: (1) initial E2E testing revealing contamination bugs, (2) architectural redesign ... (6) comprehensive seam audit finding 35 issues, (7) fixing all 39 findings with re-audit verification"

**Evidence strength:** STRONG

---

### Rule 6: Three-Store Completion (Mechanized via three_store_save.py)

**Statement:** A directive is not complete until all three stores are written — docs/MANUAL.md, public.ceo_memory, and public.cis_directive_metrics — and this is now enforced via a deterministic script (three_store_save.py) that fails loud on partial success, not a manual checklist.

**When emerged:** Mechanized in Directive D1.8 (2026-04-15, final directive of the session). The three-store rule itself (LAW XV) predates the session; D1.8 fixed the broken mechanism after D1.7 forensic audit found 16 directives with save_completed=true but 0/3 actual stores written.

**Why it emerged:** D1.7 forensic audit revealed the three-store save was "structurally broken: manual process, schema mismatch on letter-prefix directives, wrong schema referenced in CLAUDE.md, no automation, no CI check. 16 directives claimed save_completed=true with 0/3 actual completion. Manual stale 12 days." The solution was a Layer 1 schema fix (adding directive_ref TEXT column to cis_directive_metrics for letter-prefix directives), Layer 2 automation script (three_store_save.py), and Layer 3 CI enforcement (directive-save-check.yml). The script self-saves D1.8's own completion as proof of function.

**Ratification language:**
> "DIRECTIVE D1.8 — FIX 3-STORE SAVE MECHANISM (FULL SCOPE) ... 4 fixes, single PR ... D1.7 forensic audit confirmed 3-store save mechanism is structurally broken ... 16 directives claimed save_completed=true with 0/3 actual completion."

> "Save trigger: YES — but USE the new script to do the save. If the script can't save its own directive completion, Layer 2 is broken."

> "Three-store save script worked on its own self-save — real proof."

**Source citations:**
- [source: 06_governance_language.md L13632] — Full DIRECTIVE D1.8 text: "Fix 3-Store Save Mechanism ... 16 directives claimed save_completed=true with 0/3 actual completion. Manual stale 12 days."
- [source: 06_governance_language.md L13633] — "Save trigger: YES — but USE the new script to do the save. If the script can't save its own directive completion, Layer 2 is broken."
- [source: 06_governance_language.md L13716-13764] — Sub-agent completion for "Layer 2: three_store_save.py" showing script built at /home/elliotbot/clawd/Agency_OS/scripts/three_store_save.py with --help output.
- [source: 06_governance_language.md L13782] — "PRE-MERGE PR #329 — BACKFILL CONTENT VERIFICATION ... Strong work on D1.8. Three-store save script worked on its own self-save — real proof."
- [source: 09_ceo_verification_asks.md L10888] — D1.8 directive text with "Save trigger: YES — but USE the new script to do the save."

**Evidence strength:** STRONG

---

### Rule 7: Letter-Prefix Directive Convention

**Statement:** Foundation-sequencing work uses letter-prefix naming (A, B, C, D1.x) rather than numeric directives, establishing an ordered build sequence where each letter-prefix directive is a prerequisite for the next — A (foundation cleanup), B (module fixes), C (missing modules), D1 (cohort runner + smoke test), D1.x (sub-directives within D1 scope).

**When emerged:** 2026-04-15 — introduced with Directive A (FOUNDATION), which explicitly referenced "Directives B/C/D" as subsequent stages in the DIRECTIVE A text.

**Why it emerged:** The session started with Pipeline F v2.1 architecture ratified (PR #323) but the implementation foundation was in poor shape: test suite broken, naming inconsistent, blocklist inadequate, no shared parallelism utility. Rather than mixing foundation cleanup with new module builds in a single directive, Dave sequenced them explicitly: A fixes the foundation before any modules change, B fixes existing modules, C builds missing modules, D1 runs the first cohort. This creates a dependency chain that prevents new code being built on a broken foundation. The D1.x sub-directive pattern (D1.1, D1.2, D1.3, D1.4, D1.5, D1.6) emerged naturally as the cohort run surfaced bugs that required their own fix/audit/re-audit cycle without changing the overall D1 scope boundary.

**Ratification language:**
> "Context: Pipeline F v2.1 architecture is ratified (PR #323). Before new modules are built (Directives B/C/D), the foundation needs four things fixed."

> "Check directive log captures letter-prefix sequence — grep -E 'Directive [ABCD]|Directive D1.' docs/MANUAL.md — Expected: A, B, C, D1, D1.1, D1.2, D1.3, D1.4, D1.5, D1.6, D1.7, D1.8 listed with brief descriptions. If only some appear, letter-prefix context incomplete."

**Source citations:**
- [source: 06_governance_language.md L12361] — "DIRECTIVE A — FOUNDATION Pipeline F v2.1 ... Before new modules are built (Directives B/C/D), the foundation needs four things fixed."
- [source: 06_governance_language.md L12370] — "DIRECTIVE B — EXISTING MODULE FIXES Pipeline F v2.1 ... Context: Directive A merged. Naming clean, blocklist expanded, parallel utility ready."
- [source: 06_governance_language.md L12388] — "DIRECTIVE C — MISSING MODULES Pipeline F v2.1 ... Context: Pipeline F v2.1 has 7 of 11 stages as proper modules."
- [source: 06_governance_language.md L12405] — "DIRECTIVE D1 — COHORT RUNNER + 20-DOMAIN SMOKE TEST Pipeline F v2.1 ... Context: All 11 Pipeline F v2.1 modules exist and pass isolation tests post-Directives A/B/C."
- [source: 06_governance_language.md L13782] — "Check directive log captures letter-prefix sequence — Expected: A, B, C, D1, D1.1, D1.2, D1.3, D1.4, D1.5, D1.6, D1.7, D1.8 listed with brief descriptions."
- [source: 09_ceo_verification_asks.md L10897] — PRE-MERGE D1.8 verification: "grep -E 'Directive [ABCD]|Directive D1.' docs/MANUAL.md — Expected: A, B, C, D1, D1.1, D1.2, D1.3, D1.4, D1.5, D1.6, D1.7, D1.8 listed with brief descriptions. If only some appear, letter-prefix context incomplete."
- [source: 06_governance_language.md L13108-13131] — Chronological list of directives: "[TG] DIRECTIVE A", "[TG] DIRECTIVE B", "[TG] DIRECTIVE C", "[TG] DIRECTIVE D1", "[TG] DIRECTIVE D1.1", "[TG] DIRECTIVE D1.2", etc.

**Evidence strength:** STRONG

---

## Summary Table

| # | Rule | Evidence Strength | Primary Source Lines |
|---|------|-------------------|---------------------|
| 1 | Verify-Before-Claim | STRONG | 06_governance_language.md L12432, L13307-13309 |
| 2 | Cost-Authorization (>5x kill) | STRONG | 06_governance_language.md L12423-12424, L13219-13224 |
| 3 | Pre-Directive Check (Confirm Ready State) | MODERATE | 06_governance_language.md L13339-13351 |
| 4 | Optimistic Completion Pattern (named failure mode) | STRONG | 06_governance_language.md L3749, L13025, L13633 |
| 5 | Audit → Fix → Re-Audit → Fix → Merge Cycle | STRONG | 06_governance_language.md L12441-12442, 08_bug_discoveries.md L4922-4932 |
| 6 | Three-Store Completion (mechanized via three_store_save.py) | STRONG | 06_governance_language.md L13632-13764 |
| 7 | Letter-Prefix Directive Convention | STRONG | 06_governance_language.md L12361, L12370, L12388, L12405 |
