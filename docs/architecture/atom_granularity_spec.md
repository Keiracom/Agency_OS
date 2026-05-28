# Atom Granularity Spec v1

**Owner:** Aiden (architecture lens) + Scout (initial draft, dispatched by Elliot 2026-05-27)
**Status:** RATIFIED — Dave + Aiden + Viktor 2026-05-27 retrieval-design ratify
**bd:** `Agency_OS-3g9t` — CUTOVER GATE (Wave 1 foundation, Aiden push-forward)
**Filed under:** `docs/architecture/atom_granularity_spec.md`
**Companion module:** `src/keiracom_system/memory/atom_granularity.py`
**CI gate:** `scripts/ci/check_atom_granularity.py`

## Canonical anchor (verbatim per audit-dispatch checklist)

`ceo:cutover_plan_v1` — `full_retrieval_tier_ratify_2026_05_27_22Z.waves.wave_1_foundation`:

> "Hindsight primitives complete (synthesize+trace+delete with source-atom pointers) + atom granularity spec + tenant scoping per-callsite + bounded-spawn dispatcher-kill + Go sidecar deploy + real-time invalidation"

`ceo:memory_abstraction_layer_v1` — `eleven_agreed_positions #3`:

> "Six query primitives: Ingest, Recall, Synthesize, Supersede, Trace, Delete"

The retrieval primitives (PR #1228 / #1230 / #1234) are necessary but not sufficient. The DESIGN-2026-05-27 ratify also names atom granularity as a cutover-gating concern: "atom granularity matters as much as the retrieval pipeline". Too coarse and recall is noisy + reranker has to do too much work; too fine and one user query generates a fan-out of recall round-trips to reconstruct context.

## §1 Scope

**In scope:** programmatic granularity rules that every atom written to Hindsight (any wrapper — Decision / Artifact / TaskContext / AntiPattern) MUST satisfy before ingest. Cross-cuts the four MAL node types — applies uniformly to all of them.

**Out of scope:**
- Atom **schema** (field shape) — owned by `ceo:atomization_architecture_v1` + `docs/architecture/design/atomization_pilot_schema_lock_proposal.md` (Orion's atom-store schema).
- LLM-driven atomization quality (Gemini Flash atomizer service) — Phase 2 atomization pilot scope.
- Per-tenant override of granularity rules — Phase 2 follow-up; V1 is one rule-set fleet-wide.

## §2 Granularity rules (RATIFIED V1)

Every atom must satisfy ALL of the following or the validator returns `ok=False`. The CI gate fails the PR if any committed atom fixture (JSON/JSONL in scanned locations) violates the spec.

### R1 — Content size bounds

- **Min:** 50 characters of substantive content (after stripping whitespace).
- **Max:** 2000 characters of substantive content.
- **Why:** below 50 chars an atom carries less than one full thought (e.g. "yes", "Paris", a bare URL) — recall returns it without context. Above 2000 chars an atom usually contains multiple concepts and should be atomised further (R2). Token-equivalent at ~4 chars/token: roughly 12–500 tokens.

### R2 — Single-concept rule

Each atom should describe **one** fact, decision, observation, or anti-pattern. Heuristic checks (the validator is conservative — false negatives fine, false positives must be near-zero):

- **R2.a:** content contains at most **5 sentences** (period-terminated). 6+ sentences is a strong "multi-concept" signal.
- **R2.b:** content does not contain **more than one** of these multi-concept connectors at sentence boundaries: `". Additionally"`, `". Furthermore"`, `". Separately"`, `". On a different topic"`. One is fine — it's transitional; two or more flags as multi-concept.
- **R2.c:** content does not contain **more than 3** distinct H2/H3 markdown headings (`## ...` / `### ...`). Document-shaped content is not atom-shaped.

R2 is heuristic, not formal. The escape valve is the `single_concept_override: true` field — atoms tagged with that bypass R2 checks (audit-logged at validation site; reviewer must justify).

### R3 — Source-pointer requirement

Every atom must carry a non-empty `source_ref` (alias: `provenance.source`). Format is free-text but must be present + non-trivial (min 7 chars — accommodates `pr:NNNN`, `commit:7sha`, longer keys). Examples that satisfy:

- `"pr:1228"` (GitHub PR)
- `"commit:5c8c54e3e"` (git SHA)
- `"slack:#ceo:2026-05-27T14:30Z"` (Slack channel + timestamp)
- `"drive:1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho:p3"` (Drive doc + page)
- `"ceo:memory_abstraction_layer_v1"` (canonical ceo_memory key)

Why: synthesize (`SynthesisResult.source_atom_ids`, PR #1228) only works if atoms themselves can be traced. An atom without a source pointer is a floating claim; the synthesis drift guard at the primitives layer catches the synthesis-level case, but the granularity layer must catch it earlier — at ingest.

### R4 — Field-name canonicalisation

The validator accepts both `source_ref` and `provenance.source` (nested dict). It does NOT accept ad-hoc field names (`origin`, `from`, `cited_from`, etc.) — canonical names only, so retrieval at the engine layer doesn't fan out on aliases.

## §3 Validator API (Python)

```python
from src.keiracom_system.memory.atom_granularity import (
    validate_atom,
    GranularityViolation,
    GranularityRules,
)

outcome = validate_atom(
    {"content": "...", "source_ref": "pr:1228", "single_concept_override": False},
    rules=GranularityRules(),  # defaults to V1 ratified
)
if not outcome.ok:
    for v in outcome.violations:
        log.error("atom %s violates %s: %s", outcome.atom_id, v.rule_id, v.detail)
```

`GranularityRules` is the policy object — same `dataclass(frozen=True)` pattern as `RecencyDecayConfig` (PR #1234). Fields:

- `min_content_chars: int = 50`
- `max_content_chars: int = 2000`
- `max_sentences: int = 5`
- `max_multi_concept_connectors: int = 1`
- `max_h2_h3_headings: int = 3`
- `min_source_ref_chars: int = 7`
- `accepted_source_ref_keys: frozenset[str] = {"source_ref", "provenance.source"}`

Tuning is Phase 2 empirical work (running the spec against the existing fleet corpus + measuring false-positive rate). V1 values are starting points.

## §4 CI gate — `scripts/ci/check_atom_granularity.py`

Scans configurable locations for atom-shaped JSON / JSONL files and validates each row. Exit codes mirror the existing CI gate pattern (`check_migration_manifest.py`):

- **0** — all atoms pass OR no atoms found (no-op acceptable at V1; ramps up as atom-shaped fixtures are committed).
- **1** — at least one atom violates the spec; gate FAILS.
- **2** — config error (malformed JSON, scan location wrong).

Default scan locations (override via env var `KEIRACOM_ATOM_SCAN_PATHS`):

- `tests/keiracom_system/memory/fixtures/atoms/*.json` (none yet — placeholder for future test fixtures)
- `tests/keiracom_system/memory/fixtures/atoms/*.jsonl`
- `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/discovery_log.jsonl` (when present; per `CLAUDE.md` standing practice)

The gate is **runtime executable**, not documentation-only (per **GOV-12 — Gates As Code**).

## §5 Out-of-spec atoms — escape valves

Two:

1. **`single_concept_override: true`** on the atom — bypasses R2 only. R1 (size) and R3 (source) still enforced. Use case: an atom that genuinely is bigger than 5 sentences because the underlying fact is irreducible (e.g. a multi-step protocol). Reviewer must justify in the atom's metadata.
2. **`granularity_exempt: true`** on the atom — bypasses R1, R2, R3 entirely. RARE — reserved for legacy backfill where atomising would destroy context. Reviewer + Aiden gate D approval required. Validator logs the exemption + emits a `keiracom.atom.granularity.exempt` metric.

## §6 Definition of done

- [x] Spec doc landed (this file).
- [x] Programmatic validator in `src/keiracom_system/memory/atom_granularity.py`.
- [x] CI gate in `scripts/ci/check_atom_granularity.py` — runtime executable (GOV-12).
- [x] Test suite >=4 negatives per rule (Aiden gate-validator discipline).
- [x] No live atom corpus required to run the validator (V1 ramps up; gate is no-op until atom-shaped fixtures land).

## §7 Open questions (Phase 2)

- **Tokeniser-based size bound** (use TEI BGE tokeniser instead of char count) — needs tokeniser plumbing in the validator. Phase 2.
- **Per-topology granularity overrides** — codebase atoms (code excerpts) legitimately exceed 2000 chars; decisions are usually shorter. Phase 2 follows the same `topology->config` pattern as `recency_decay.DEFAULT_HALF_LIVES`.
- **LLM-driven splitter** for atoms that violate R1.max — the Gemini Flash atomizer (atomization pilot Week 1) might be wired here. Phase 2.
