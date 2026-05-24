# Migrated Manifest Seed — Phase 1.2.5 Artefact 6

**KEI:** `Agency_OS-fi4u`. **Author:** max (deliberator-tier governance per role-lock exception — my own G4 gate from MAL V1 deliberation).
**Status:** seed authored 2026-05-24. **Blocks:** Phase 2.2 first product-migration PR.
**Companion deliverable:** `docs/migration/migrated_manifest_seed.json` (machine-readable manifest).
**Companion enforcer:** `scripts/ci/check_migration_manifest.py`.
**CI workflow:** `.github/workflows/migration-manifest-gate.yml`.

---

## 1. Notes — canonical key paste (per audit-dispatch checklist `_orchestrator.md`)

`ceo:agency_os_keiracom_separation_v1` queried 2026-05-24 ahead of authoring. The consolidated gate served by this artefact:

> "Migration manifest with dynamic exclusion (paths with active PR/KEI work excluded)"

Plus the sequencing entry:

> "Phase 1.2.5 (INSERT) pre-migration artefact bundle: 3-repo architecture doc + per-repo CLAUDE.md split decision + bd-routing policy + Weaviate cutover plan + discovery log classifier + migrated-manifest seed"

This artefact is the migrated-manifest-seed entry of that bundle (artefact 6 of 7).

`ceo:memory_abstraction_layer_v1` queried for the `src/memory/*` rationale text — the MAL V1 spec is the authority that says these files are product-tier.

`ceo:comm_architecture` does not classify any files (the substrate is fleet-only) — referenced for completeness; no manifest entries derived from it.

---

## 2. What this artefact is

A **seed manifest** enumerating every file currently on `origin/main` that is classified **product (P)** per the just-merged `docs/architecture/three_repo_carveout_execution.md` (PR #1122). Each entry conforms to the schema from PR #1122 §6.

**Seed semantics:**
- The manifest is **forward-looking input** for the Phase 2.0 migration runner. It does not move any files itself.
- Entries are **explicit enumerations** (no globs) following the same discipline as Orion's `config/product_repo_test_allowlist.txt` (PR #1118).
- `active_pr_block` annotations are **dynamically refreshed** (see §4) so a file with in-flight PR work isn't moved while the work is pending.
- The seed will **grow** as Keiracom V1.0 product code is authored (Hindsight wrappers, tenant onboarding, install script — all forward-looking placeholders today).

**What this artefact is NOT:**
- Not the migration runner itself (Phase 2.0 build per MAL V1 Gate F, P0 critical-path).
- Not the actual file movement (Phase 2.2).
- Not the repo carve operation (Phase 2.0 separate dispatch).
- Not a full classification — it enumerates **only P** entries that exist on `origin/main`. Fleet/archive entries are derivable from the classification rules in PR #1122 §3 and §4 but not enumerated here (their tree stays in `keiracom-fleet`/`keiracom/agency-os` and doesn't need a move manifest).

---

## 3. Seed contents — 60 entries

Per-category breakdown (verifiable via `jq` on the JSON):

| Category | Count | Source rule |
|---|---|---|
| `src/dispatcher/*.py` | 17 | PR #1122 §4.8 — "V1.0 MCP dispatcher per PR #1118 allowlist" |
| `src/memory/*.py` | 10 | PR #1122 §4.8 — "Memory Abstraction Layer V1" + `ceo:memory_abstraction_layer_v1` |
| `mcp-servers/memory-mcp/*` | 4 | Memory MCP server (Hindsight integration) |
| `scripts/ci/check_product_test_allowlist.py` | 1 | PR #1122 §4.6 — moves with the test enforcer |
| `config/product_repo_test_allowlist.txt` | 1 | PR #1122 §4.2 — PR #1118 allowlist |
| Test paths from PR #1118 allowlist | 27 | PR #1122 §4.10 — verbatim PR #1118 enumeration |
| **Total** | **60** | |

### Known classification gaps (deferred to follow-up)

PR #1122 §3.1 classifies the whole `mcp-servers/` directory as P, but the directory contains **48 files across 13 MCP servers**, of which only a subset is genuinely product-tier:

- **Product (in this seed):** `mcp-servers/memory-mcp/*` (4 files) — Hindsight memory integration.
- **Likely archive (NOT in this seed):** `mcp-servers/{dataforseo, prospeo, resend, salesforge, telnyx, unipile, vapi}-mcp/*` — these wrap dead Agency OS vendors per `ARCHITECTURE.md §3`. Including them as P contradicts the dead-vendor lock; excluding them per per-MCP refinement.
- **Likely fleet (NOT in this seed):** `mcp-servers/{gmail, telegram}/*` — fleet operator/relay integrations.
- **Cross-product infra (NOT in this seed):** `mcp-servers/{prefect, railway, vercel}-mcp/*` — could be F or P depending on Phase 2.0 deployment model.

**Recommend follow-up KEI:** refine PR #1122 §3.1 `mcp-servers/` row from `P` to `SPLIT` and add a §4 subsection with per-MCP classification. Filed as the open follow-up for this artefact (see §7).

---

## 4. Dynamic-exclusion contract — `active_pr_block` field

Per PR #1122 §6 schema, every entry has an `active_pr_block` field:
- `null` — no in-flight work; eligible for the next migration cycle.
- `"PR #N"` or `"PR #N; PR #M"` or `"Agency_OS-XXXX"` — work is in-flight; **excluded from migration cycle** until the blocker closes.

The enforcer's `--refresh-exclusions` flag queries:

1. **Open GitHub PRs** via `gh pr list --state=open --json number,files` — any PR whose `files[].path` matches a manifest `source_path` (exact match or single-level glob — same fnmatch shape as Orion's allowlist enforcer).
2. **Open bd KEIs** via `bd list --status=open --json` — heuristic substring match on the issue's `description + notes` body for the source_path.

Annotations are written back via atomic `tmp.replace()` (same shape as PR #1119 Weaviate cutover snapshot — idempotent re-runs).

**Why dynamic, not static:**
- A static manifest breaks on the first in-flight PR conflict — file gets migrated mid-work, leaves the open PR with a missing path. Author has to rebase against the migrated path; cascade failures across the bundle.
- Dynamic exclusion lets the Phase 2.0 migration runner re-evaluate the manifest each cycle. Entries become eligible automatically once their blocking PR merges.

**Refresh cadence (Phase 2.0+):** the migration runner calls `--refresh-exclusions` immediately before each migration cycle. Phase 1.2.5 (this PR) refreshes manually via CLI or CI `workflow_dispatch`.

---

## 5. Enforcer — `scripts/ci/check_migration_manifest.py`

**Three-tier exit codes** (same shape as PR #1118 `check_product_test_allowlist.py`):

- `0` — all entries pass schema + path-existence + enumeration discipline.
- `1` — enforcement violation: schema missing field, target_repo enum invalid, operation enum invalid, path contains glob, path doesn't exist on disk.
- `2` — config error: manifest file missing, malformed JSON.

**Validations enforced** (runtime CODE per GOV-12, not doc-claim):

1. Top-level required fields present (`manifest_version`, `entries`).
2. Each entry has all required fields (`source_path`, `target_repo`, `target_path`, `operation`, `rationale`, `active_pr_block`).
3. `target_repo` in `{fleet, product, archive, both}`.
4. `operation` in `{move, copy, archive}`.
5. `source_path` has no glob characters (`*`, `?`, `[`, `]`) — enumeration discipline.
6. `source_path` exists on disk (catches path-rot from removed files).

**Why these and not more:**
- Hash discipline (per PR #1122 §6 `source_sha256`/`target_sha256`) belongs to the migration runner, not the pre-migration manifest gate. Filed as Phase 2.0 follow-up.
- `target_path` semantics (collision detection, parent-dir creation) belong to the runner.
- `active_pr_block` annotation correctness is checked at refresh time, not enforced — the runner uses the annotation, the gate doesn't reject on it.

---

## 6. CI workflow integration — `migration-manifest-gate.yml`

**Trigger paths:** the manifest itself + the enforcer script + every P-classified path (so any PR touching a product-bound path runs the gate).

**Mode:** `continue-on-error: true` in Phase 1.2.5 (warn-only — failures surface in CI output but don't block merge). Flip to hard-gate post-Phase-2.0 carve by removing the line.

**Why warn-only initially:** the seed manifest is forward-looking; entries reference paths that exist on `origin/main` today but will move during Phase 2.0. A hard gate now would block legitimate PRs that edit product-bound paths. Hard gate becomes meaningful once those paths live in `keiracom-product` and edits to them are migration violations.

---

## 7. Open follow-ups (Phase 2.0 sequencing)

Filed as bd KEIs (or to be filed; some already exist):

- **Per-MCP `mcp-servers/` classification refinement** — split the §3.1 P-blanket into per-server classification (memory→P, dead vendor→A, fleet relay→F, cross-product infra→F-or-P).
- **Migration runner implementation** — consumes this manifest. Per MAL V1 Gate F, P0 critical-path, ships before launch.
- **Hash-discipline checker** — runner-side SHA-256 source/target match (PR #1122 §6).
- **Hard-gate flip** — remove `continue-on-error: true` from `.github/workflows/migration-manifest-gate.yml` once Phase 2.0 carve completes.
- **Manifest growth as V1.0 lands** — add entries for `infra/hindsight/`, product-side prompts, tenant schemas, install script when those paths are authored.
- **bd KEI body-match precision** — current `--refresh-exclusions` does substring match on bd issue body for source_path; replace with a structured `--touches-path <path>` field on bd issues when bd grows that affordance.

---

## 8. Acceptance criteria

- [x] Canonical key queried + paste in §1 per audit-dispatch checklist.
- [x] Explicit enumeration (no globs) — 60 entries individually listed.
- [x] Schema conforms to PR #1122 §6 with all 6 required fields per entry.
- [x] Dynamic-exclusion mechanism named + implemented in enforcer (`--refresh-exclusions`).
- [x] CI gate config (`.github/workflows/migration-manifest-gate.yml`) — runtime enforcement per GOV-12.
- [x] Negative-path tests on synthetic offenders per `feedback_negative_path_test_before_approve` (12 tests covering all 3 exit tiers + each validation rule + report mode).
- [x] Seed manifest self-validates via `scripts/ci/check_migration_manifest.py` (test `test_seed_manifest_on_disk_validates`).
- [ ] Elliot impl-feasibility lens concur (per author-exclusion: Max authored, eligible reviewers are Elliot + Aiden).
- [ ] Aiden architecture/governance lens concur.
- [ ] 2-of-2 author-excluded NATS concur → Elliot admin-merge per `_orchestrator.md §Orchestrator-merge-after-NATS-concur`.

---

_End artefact. Section additions or material revisions require an explicit dispatch naming this file._
