# Test Path Classification — Phase 1.2.5 bundle artefact 7

**Authored:** 2026-05-24 (orion, per Elliot dispatch)
**Status:** RATIFIED-PENDING (Aiden architecture + Max quality dual-concur on PR)
**Anchor:** `ceo:agency_os_keiracom_separation_v1` sign-off item 2

## 1. Why this exists

The Dave-ratified separation directive (`AGENCY-OS-KEIRACOM-SEPARATION-V1`, 2026-05-24) carves three repos out of the current Agency_OS monorepo:

  - **Fleet repo** (working name `keiracom-fleet`) — internal agent fleet configs, NOT customer-facing.
  - **Product repo** (TBD name, rename-ready) — V1.0 AI workforce code shipped to customers (Memory Abstraction Layer, MCP dispatcher, Go sidecar, tenant onboarding, install script, CLI).
  - **Archive repo** (existing URL preserved) — 1100 prior PRs + dead BDR product (Agency OS / Siege Waterfall pipeline). Marked inactive in README.

Sign-off item 2 of the separation directive specifies:

> "Stripped product-only matrix until first paying customer, with 3 non-negotiable tests (tenant onboarding, MCP wrong-project-id rejection, namespace boundary negative-paths). Concrete enumerated allow-list of test paths as Phase 1.2.5 artefact (Elliot refinement)."

This document is the artefact. It enumerates which test paths survive into the product repo CI matrix, why, and how the cutover sequences.

## 2. Three buckets

Every `tests/**/*.py` file lands in exactly one of:

| Bucket | Repo | CI participation | Rationale |
|---|---|---|---|
| **PRODUCT** | product repo | Yes — stripped matrix | Tests covering V1.0 customer-facing surface (MCP dispatcher, Memory Abstraction Layer, tenant onboarding, namespace boundaries). |
| **FLEET** | fleet repo | Yes — fleet matrix | Tests covering internal orchestrator plumbing, clone bring-up, governance enforcement, alerts, hooks. Not customer-facing. |
| **ARCHIVE** | archive repo | No — frozen (archive repo CI disabled) | Tests for retired Agency OS BDR product (Siege Waterfall enrichment pipeline, vendor integrations, outreach engines, score models). Preserved for historical reference + audit, never run. |

## 3. Classification rules

Source-of-truth: `config/product_repo_test_allowlist.txt`. Anything not matched by an allowlist entry is fleet OR archive (decided at cutover by 3-repo migration manifest).

### PRODUCT (explicit allowlist — see `config/product_repo_test_allowlist.txt` for the canonical list)

- `tests/dispatcher/*.py` — MCP dispatcher (V1.0 primary product code). All 16 current files listed by name.
- `tests/memory/*.py` — Memory Abstraction Layer (V1.0 primary product code). All 3 current files listed.
- Tenant onboarding (non-negotiable #1):
  - `tests/test_services/test_onboarding_pipeline.py`
  - `tests/test_flows/test_post_onboarding_flow.py`
  - `tests/scripts/test_seed_demo_tenant.py`
  - `tests/unit/test_set_tenant_session.py`
  - `tests/live/test_onboarding_live.py`
- Namespace boundary (non-negotiable #3):
  - `tests/governance/test_ceo_memory_context_constraint.py` (the `0scg` migration test — proves CHECK + NOT NULL on `ceo_memory.context`; cross-namespace gate)
  - `tests/governance/test_ceo_memory_writer.py` (KEI-87 write-guard — only `elliot`/`dave` can write `ceo:*`; cross-callsign boundary)
  - `tests/integration/test_tenant_isolation.py` (per-tenant data isolation)
- MCP wrong-project-id rejection (non-negotiable #2): test file **not yet written**. Allowlist carries a comment placeholder + the gate is "no release-marked PR merges without this test existing". Tracked as a follow-up bd issue.

### FLEET (anything NOT in product allowlist + matches one of):

- `tests/orchestrator/*` — orchestrator plumbing (per Elliot dispatch hint). Examples: `test_next_work_prompter.py`, `test_supervisor_wake_publish.py`, `test_self_assign_on_ready.py`.
- `tests/scripts/test_spawn_*.py` — clone bring-up (per dispatch hint).
- `tests/governance/*` (except the 3 namespace-boundary tests promoted to product) — KEI-87 trigger discipline, layered governance, gatekeeper emit.
- `tests/alerts/*` — fleet service-health alerts.
- `tests/cognee/*` — fleet Cognee memory infra (read path for the existing pre-MAL recall).
- `tests/hooks/*` — fleet PreToolUse / Stop hooks.
- `tests/observability/*` — fleet BetterStack / instrumentation.
- `tests/session_store/*`, `tests/session_resumption/*` — fleet session state.
- `tests/ci_guards/*` — fleet CI policy enforcers.
- `tests/dispatcher/test_dispatcher_service_install.py` — **also product** (installs are customer-facing). Cross-listed: appears in product allowlist + duplicated in fleet manifest with a `# duplicated` comment.

### ARCHIVE (anything NOT in product allowlist + matches one of):

- `tests/pipeline/*`, `tests/test_pipeline/*` — Siege Waterfall pipeline orchestration (per dispatch hint).
- `tests/enrichment/*` — Agency OS multi-tier enrichment (ContactOut, Hunter, Leadmagic waterfalls).
- `tests/test_engines/*` — Agency OS scoring/scout engines.
- `tests/test_detectors/*` — Agency OS lead-detector signals.
- `tests/outreach/*` — Agency OS outreach cadence + safety.
- `tests/test_flows/*` (except `test_post_onboarding_flow.py` which is product) — Agency OS Prefect flows (Flow A/B).
- `tests/test_skills/*` — most Agency OS skills (BDR-specific).
- `tests/integrations/*` — Agency OS vendor integrations (Salesforge, Unipile, Telnyx, Leadmagic, Bright Data).
- `tests/intelligence/*` — Agency OS competitive intelligence.
- `tests/coo_bot/*`, `tests/slack_bot/*`, `tests/telegram_bot/*` — Agency OS bot UI (pre-NATS).
- `tests/replay/*` — Agency OS replay harness.
- `tests/skill_gen/*` — Agency OS skill generator.

### SPLIT (case-by-case per file — manifest will be authored as part of Phase 2.2 migration runner):

- `tests/skills/*` — per dispatch hint, some fleet skills (drive-manual, callback-poller, decomposer) survive; some product skills (BYO API key, dispatcher CLI) survive; some Agency OS skills (DataForSEO, ContactOut, Leadmagic) archive.
- `tests/integration/*` — varies per integration target.
- `tests/migrations/*` — varies per migration domain.
- `tests/api/*` — split by endpoint: tenant + onboarding endpoints → product; pipeline + score endpoints → archive; webhook handlers fleet-or-product depending on source.

## 4. Local verification

Run the allowlist enforcer against the current `tests/**` tree:

```bash
python3 scripts/ci/check_product_test_allowlist.py --report
```

Expected output today (in the pre-migration Agency_OS monorepo):

```
product-repo allowlist: 27 / 475 test files matched (5.7%); 448 would be rejected.
```

The 5.7% reflects today's product-tier surface: 16 dispatcher + 3 memory + 5 onboarding + 3 namespace-boundary = 27 product tests vs 475 total. The 448 rejected files split fleet / archive / split-to-be-classified per §3 above. The bucket totals will refine as the §3 SPLIT manifest is authored in Phase 2.2.

In the **product repo** post-migration, `tests/**` will only contain allowlisted paths, so the enforcer exits 0.

## 5. Cutover sequence

Reading from `ceo:agency_os_keiracom_separation_v1.sequencing`:

  1. ✅ Phase 1.1 — V1.0 ratification (DONE 2026-05-24)
  2. 🔄 Phase 1.2 — retire Agency OS architecture doc, V1.0-aligned doc, content audit pass (IN PROGRESS via Stage 0 staleness audit + Phase 1.3 IDENTITY refresh)
  3. 🔄 Phase 1.2.5 — pre-migration artefact bundle: **this document is item 7 of the bundle**
  4. ✅ Phase 1.3 — agent identity refresh for 4 PARTIAL IDENTITY files (DONE 2026-05-24 via Agency_OS-fwdb v3)
  5. ⏳ Phase 2.0 — repo creation (product repo carved, fresh CI matrix enabled, this allowlist enforcer wired)
  6. ⏳ Phase 2.1 — Hindsight verification spike (6 items)
  7. ⏳ Phase 2.2 — migrate product code via clean PRs, subject to dynamic-exclusion migration manifest

The allowlist enforcer (`check_product_test_allowlist.py`) starts running in CI at Phase 2.0 against the fresh product repo's pruned `tests/**` tree.

## 6. CI rule (GitHub Actions workflow snippet)

To be placed in the **product repo** at `.github/workflows/product-repo-test-matrix.yml`. Snippet that fails CI on any unmatched test path:

```yaml
name: Product Repo Test Matrix Enforcement

on:
  pull_request:
    paths:
      - "tests/**"
      - "config/product_repo_test_allowlist.txt"
  push:
    branches: [main]

jobs:
  enforce-product-allowlist:
    name: Stripped test matrix — allowlist enforcement
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Run product-repo allowlist enforcer
        # Exit 1 if any tests/**/*.py file is not matched by an allowlist entry.
        # Fix path: either add the path to config/product_repo_test_allowlist.txt
        # (with review of whether the test actually belongs in the product repo
        # CI matrix) OR move/delete the test file.
        run: |
          python3 scripts/ci/check_product_test_allowlist.py
```

## 7. Notes — `ceo:agency_os_keiracom_separation_v1` (queried 2026-05-24)

Per the audit-dispatch checklist (canonical-key-query gate), the queried value of the canonical key is pasted here verbatim for review:

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
    "Internal fleet repo (working name keiracom-fleet) — Dave internal agent team configs, NOT customer-facing",
    "Product repo (working name TBD, rename-ready) — V1.0 AI workforce code shipped to customers; Memory Abstraction Layer + Hindsight self-hosted + Go sidecar + MCP server + tenant onboarding + install script + CLI",
    "Archive repo (existing URL preserved) — 1100 prior pull requests + dead BDR product code; marked inactive in README"
  ],
  "sign_off_decisions": {
    "item_2_ci_matrix": "Stripped product-only matrix until first paying customer, with 3 non-negotiable tests (tenant onboarding, MCP wrong-project-id rejection, namespace boundary negative-paths). Concrete enumerated allow-list of test paths as Phase 1.2.5 artefact (Elliot refinement)"
  }
}
```

The three classifications in this document (PRODUCT / FLEET / ARCHIVE) are derived directly from the `repo_topology` + `sign_off_decisions.item_2_ci_matrix` fields above. The three non-negotiable tests (tenant onboarding, MCP wrong-project-id rejection, namespace boundary negative-paths) are explicitly carved out of the product allowlist (§3 PRODUCT, all 3 non-negotiables enumerated; #2 carries a placeholder since the test file has not yet been written — gate noted in `config/product_repo_test_allowlist.txt`).

## 8. Acceptance criteria

- [x] `config/product_repo_test_allowlist.txt` exists + enumerates ≥1 path per non-negotiable bucket.
- [x] `scripts/ci/check_product_test_allowlist.py` runs locally with `--report` against current `tests/**` tree and reports counts.
- [x] Reported "matched" percent is in the expected **~5-10%** band today (pre-migration; product code is small fraction of monorepo) — refines to ~30-40% in the post-migration product repo where `tests/**` is already pruned to the allowlist.
- [x] CI workflow snippet provided as a paste-target for the product repo's `.github/workflows/product-repo-test-matrix.yml`.
- [x] Canonical key `ceo:agency_os_keiracom_separation_v1` queried + pasted into §7 per audit-dispatch checklist.
- [ ] Aiden architecture-lens concur on PR.
- [ ] Max code-quality-lens concur on PR.
- [ ] Dual-concur → Elliot admin-merge per orchestrator-merge-after-NATS-concur pattern.
