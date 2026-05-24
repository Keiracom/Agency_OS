# bd Routing Policy — 3-Repo Topology

**Phase 1.2.5 bundle artefact 3** (Aiden R3).
Authored 2026-05-24. Takes effect at Phase 2.0 (repo carve).
Implements consolidated gate **"bd routing policy: central bd with --repo tag on product issues"** from `ceo:agency_os_keiracom_separation_v1`.

---

## TL;DR

| Repo | `--repo` tag | Linear team | bd database |
| --- | --- | --- | --- |
| Internal fleet (`keiracom-fleet`) | omit (default) | `Keiracom` | central Dolt store, lives in fleet repo |
| Product (`keiracom-product`) | `--repo=product` | `Keiracom-Product` | same central Dolt store |
| Archive (Agency OS, retired) | `--repo=archive` | `Keiracom-Archive` | same central Dolt store |

**One bd database. Three logical repos. Cross-repo dependencies are first-class.**

---

## Notes — canonical key value (per audit-dispatch checklist, `_orchestrator.md`)

`ceo:agency_os_keiracom_separation_v1` queried 2026-05-24 ahead of authoring (updated 2026-05-24T11:04Z).

> Status: **RATIFIED**. 3-repo topology:
> - **Internal fleet repo** (working name `keiracom-fleet`) — Dave internal agent team configs, NOT customer-facing.
> - **Product repo** (working name TBD, rename-ready) — V1.0 AI workforce code shipped to customers; Memory Abstraction Layer + Hindsight self-hosted + Go sidecar + MCP server + tenant onboarding + install script + CLI.
> - **Archive repo** (existing URL preserved) — 1100 prior pull requests + dead BDR product code; marked inactive in README.
>
> Sequencing (relevant subset): Phase 1.2.5 (INSERT) — pre-migration artefact bundle includes **bd-routing policy** ← this artefact. Phase 2.0 — repo creation: carve fleet repo, create fresh product repo, confirm archive state, namespace ceo_memory + Weaviate.
>
> Relevant consolidated gates:
> - **"bd routing policy: central bd with --repo tag on product issues"** ← this artefact
> - "Phase 1.2.5 architecture doc bundle BEFORE first product-migration PR"
> - "Loop-nudge classifier extended to N-repo before separation goes live"
> - "Cross-repo dependency sync: shared constraints file; CI fails on lockfile drift"
> - "Migration runner scope spans 3 repos + shared Supabase"

The directive is unambiguous: **one bd database**, **tag-based routing**. No per-repo bd databases (would lose cross-repo dependency tracking — see §Anti-patterns below).

---

## Where the bd database lives

The bd Dolt store lives in the **fleet repo** (`.beads/issues.jsonl` passive export + Dolt remote at `refs/dolt/data`). The product and archive repos do **not** carry their own bd instances; agents working in product or archive worktrees still issue bd commands against the fleet-repo store.

**Mechanism.** `bd` resolves the workspace by walking up from `$PWD` for `.beads/*.db` by default. For non-fleet worktrees, point bd at the fleet store via the `--db` flag — wrapped in a per-callsign shell alias so the convention is invisible at the call site:

```bash
# In each non-fleet callsign's IDENTITY.md bootstrap (or shell rc):
alias bd='bd --db /home/elliotbot/clawd/keiracom-fleet/.beads/issues.db'
```

This is set in each agent's `IDENTITY.md` workspace bootstrap so worker sessions (Atlas/Orion/Scout/Nova) and deliberator sessions (Elliot/Aiden/Max) all reach the same store regardless of which repo's worktree they happen to be in.

Empirical: `bd --help` exposes `--db string` ("Database path (default: auto-discover .beads/*.db)") — this is the supported override; there is no env-var equivalent today. A native env var would be a small bd feature request — out of scope for this artefact.

---

## Tagging convention

| `--repo` value | Meaning | Linear sync target |
| --- | --- | --- |
| *(omitted)* | Fleet default | `Keiracom` team |
| `product` | Product repo work | `Keiracom-Product` team |
| `archive` | Archive repo work | `Keiracom-Archive` team |
| `both` | Spans fleet + product (rare; explicit cross-cut) | Both teams; primary = `Keiracom` |

**Hard rule.** Every `bd create` in the product or archive worktree MUST carry an explicit `--repo` tag. Omitting it routes to fleet, which is wrong-but-silent — exactly the divergence class we are trying to prevent.

**Enforcement (Phase 2.0 follow-up KEI).** A `pre-bd-create` hook reads the worktree's `IDENTITY.md` for a `repo:` field; if the worktree is product/archive and the `bd create` command lacks `--repo`, the hook rejects. Out of scope for this artefact (which is the policy doc); filed as `Agency_OS-j6dy` for Phase 2.0.

---

## Cross-repo dependency semantics

bd dependencies (`blocked-by`, `blocks`, `discovered-from`, `child-of`, `parent-of`, `related-to`) are **repo-agnostic** in the central store. A fleet KEI can block a product KEI; a product KEI can be discovered-from an archive KEI.

| Relationship | Semantics |
| --- | --- |
| `blocked-by` | The blocked issue cannot land until the blocker is closed. Crosses repos freely. |
| `blocks` | Inverse of blocked-by. |
| `discovered-from` | "This issue was surfaced while working on X." Use for migration artefacts that point back to archive KEIs. |
| `child-of` / `parent-of` | Epic/sub-task. Use sparingly across repos — usually a sub-task belongs in the same repo as its parent. |
| `related-to` | Soft signal; no scheduling impact. |

`bd ready` honours cross-repo blockers by default: a product KEI blocked by an open fleet KEI does not surface as ready until the fleet KEI closes, even if the agent is running in the product worktree.

---

## Linear sync convention

| `--repo` tag | Linear team | Linear label auto-applied |
| --- | --- | --- |
| *(omitted, fleet)* | `Keiracom` | `repo:fleet` |
| `product` | `Keiracom-Product` | `repo:product` |
| `archive` | `Keiracom-Archive` | `repo:archive` |
| `both` | `Keiracom` (primary), `Keiracom-Product` (mirror) | `repo:both` |

Linear is **read-only** per the existing LAW (`feedback_linear_read_only`); the sync direction is bd → Linear (push), never Linear → bd (pull writes are blocked). The `--repo` tag is stamped on every Linear issue at create time so reviewers can query a single label `repo:product` to see only product KEIs.

**Failure mode handled.** If a `--repo` value is unknown (e.g. a typo `--repo=produkt`), the bd → Linear sync rejects the push and the bd issue is marked `sync_blocked` with the reason. Surfaces in `bd doctor`. No silent mis-route.

---

## Worked examples

### Example 1 — fleet KEI blocking product KEI

A migration runner upgrade lives in the fleet repo; the first product PR cannot land until it ships.

```bash
# In fleet worktree
bd create --title="Migration runner: dual-rollback support" \
          --type=feature --priority=1 \
          --description="Adds rollback-per-tenant before product launch."
# -> creates KEI-FOO (fleet default, no --repo tag)

# In product worktree
bd create --title="First product PR — tenant onboarding" \
          --type=task --priority=1 --repo=product \
          --deps=blocked-by:KEI-FOO \
          --description="Cannot land before migration runner dual-rollback."
# -> creates KEI-BAR with repo=product, blocked-by KEI-FOO

bd ready --repo=product  # KEI-BAR NOT in queue until KEI-FOO closes
bd close KEI-FOO         # KEI-FOO -> done in fleet repo
bd ready --repo=product  # KEI-BAR now surfaces
```

### Example 2 — product fix referencing archive KEI

A product-repo bug is the same shape as an archive KEI from the BDR era. Cross-reference but do not block.

```bash
# In product worktree
bd create --title="Lead-enrichment retry race fixed for Hindsight ingest" \
          --type=bug --priority=2 --repo=product \
          --deps=discovered-from:KEI-archive-789 \
          --description="Same shape as KEI-archive-789 (Cognee era); fix differs because Hindsight is per-tenant."
```

The `discovered-from` link preserves the historical context without making the archive KEI a blocker (it is already closed-and-frozen by repo state).

### Example 3 — archive issue spawning fleet follow-up

While auditing archive code for the migration manifest, an issue is found that affects the fleet's internal scheduling (not product). The archive issue is filed, then a fleet follow-up is spawned.

```bash
# In archive worktree (Phase 2.2 read-only audit)
bd create --title="audit-finding: Salesforge timeout retry leaks token" \
          --type=bug --priority=3 --repo=archive \
          --labels=audit-finding,phase-2.2 \
          --description="Salesforge handshake leaks bearer token to log if first retry times out."
# -> creates KEI-arch-NNN with repo=archive

# Fleet follow-up
bd create --title="Internal Salesforge skill: scrub token on timeout retry" \
          --type=task --priority=2 \
          --deps=discovered-from:KEI-arch-NNN \
          --description="Same code path is still live in fleet (internal Salesforge usage). Patch + redact logs."
# -> creates KEI-fleet-MMM, discovered-from KEI-arch-NNN
```

### Example 4 — `--repo=both` cross-cut

A shared lib (e.g. a small util in `scripts/` that ships to both fleet and product) needs a version bump.

```bash
bd create --title="Bump shared constraints file to fastembed 0.4.1" \
          --type=task --priority=2 --repo=both \
          --description="Both fleet + product pull from shared-constraints.txt; CI in both repos fails on lockfile drift."
```

`--repo=both` produces one bd issue, one bd → Linear sync per team (so the Linear board for `Keiracom-Product` shows the issue under `repo:both`). The primary team is `Keiracom` (fleet) for the canonical thread; the product mirror is informational so the product team sees the cross-cut on their board.

Use **sparingly**: most issues belong to one repo. `both` is the explicit signal for an actual cross-cut (shared constraints, shared MCP server, shared Supabase schema).

### Example 5 — peer-coordination on a shared file in two repos

If Atlas and Orion are both touching a file that exists in both fleet and product worktrees (e.g. a synced skill file), the `claim-before-touch` discipline still applies, scoped per repo. Atlas claims the fleet copy; Orion claims the product copy. The bd issues are siblings with `related-to`:

```bash
# Atlas in fleet worktree
bd create --title="Update skills/mcp-bridge SKILL.md — fleet copy" \
          --type=task --repo=fleet --assignee=atlas
# -> KEI-flt-AAA

# Orion in product worktree
bd create --title="Update skills/mcp-bridge SKILL.md — product copy" \
          --type=task --repo=product --assignee=orion \
          --deps=related-to:KEI-flt-AAA
# -> KEI-prd-BBB
```

Both close independently; the `related-to` link helps a future auditor see the parallel update.

---

## Anti-patterns

| Anti-pattern | Why it breaks | Correct pattern |
| --- | --- | --- |
| One bd database per repo | Loses cross-repo `blocked-by` chains. `bd ready` in product wouldn't see a blocking fleet KEI. Schedule drift inevitable. | One central bd, `--repo` tag for routing. |
| Omit `--repo` in product/archive worktrees | Routes silently to fleet team in Linear; deliberator board misses the issue. | Always set `--repo=product` or `--repo=archive` outside the fleet worktree. |
| Per-repo Linear teams + per-repo bd | Same issue ends up in two stores. Cross-cuts (shared schema) get filed twice with no link. | Single bd; Linear team is determined by `--repo` tag at sync. |
| Use bd labels (`--labels=product`) instead of `--repo` | `bd ready --repo` filter ignores labels. Linear sync team-routing breaks. | `--repo` is reserved metadata; labels stay for thematic tagging. |
| Cross-repo `child-of`/`parent-of` | Linear sub-task semantics don't follow across teams cleanly. | Use `discovered-from` or `related-to` for cross-repo provenance. |

---

## All-callsign command-flag uniformity

Every callsign — workers (Atlas/Orion/Scout/Nova) and deliberators (Elliot/Aiden/Max) — uses the same `bd` flags. No per-callsign aliases.

```bash
# All callsigns, every repo, same five commands:
bd ready [--repo=<tag>]              # find unblocked work, optionally filtered by repo
bd create --repo=<tag> ...           # always tag in non-fleet worktrees
bd show <id>                         # cross-repo lookup; tag is in the issue body
bd update <id> --claim               # claim regardless of which repo issued the work
bd close <id> --evidence=<path>      # close with structured evidence
```

The Phase 2.0 `pre-bd-create` hook checks `IDENTITY.md` for `repo:` to enforce the convention; agents do not have to remember which worktree they are in beyond knowing their `IDENTITY.md` is current.

---

## Operator runbook — Phase 2.0 first-product-issue flow

```bash
# 1. Worker (e.g. Orion) opens the product worktree
cd /home/elliotbot/clawd/keiracom-product

# 2. Verify bd workspace resolves to fleet repo's Dolt store
bd doctor   # MUST show workspace=/path/to/keiracom-fleet/.beads

# 3. Create the first product KEI with --repo
bd create --title="[ORION] Hindsight engine: in-tenant deployment script" \
          --type=feature --priority=1 --repo=product --assignee=orion \
          --description="..." --acceptance="..."
# -> KEI-prd-001, synced to Linear team Keiracom-Product

# 4. Claim + build per usual
bd update KEI-prd-001 --claim
# ... build ...
bd close KEI-prd-001 --evidence=/tmp/kei-prd-001-evidence.json
```

---

## Open follow-ups (out of scope for this artefact)

Filed at Phase 2.0 sequencing. All filed as bd issues 2026-05-24 ahead of merge so the policy doc cites real KEIs, not aspirational TODOs:

- **Pre-bd-create hook** (`Agency_OS-j6dy`, P2 feature) — enforces `--repo` requirement in non-fleet worktrees, reading `IDENTITY.md`.
- **`bd ready --repo` filter** (`Agency_OS-v2nm`, P3 task) — verify composition with the implicit unblocked-only behaviour of `bd ready` under the 3-repo dependency graph.
- **Linear team auto-create** (`Agency_OS-rg79`, P2 task) — `Keiracom-Product` and `Keiracom-Archive` teams need to exist in Linear before the first sync attempt. Manual one-shot by an admin OR scripted via Linear API.
- **`bd doctor --convention=cross-repo`** (`Agency_OS-42dm`, P3 feature) — extension of `bd doctor` to surface issues where the `--repo` tag and the synced Linear team disagree (drift detection).
- **Shared-constraints CI gate** (`Agency_OS-6xm3`, P2 feature) — implements consolidated gate "Cross-repo dependency sync: shared constraints file; CI fails on lockfile drift" from `ceo:agency_os_keiracom_separation_v1`. Both fleet and product repos pull from shared-constraints.txt; CI in each repo fails on lockfile divergence.
