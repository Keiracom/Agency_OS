# Design: `vault-envwrap` launcher — Vault-resolved service boot (vault_secrets Phase 2)

**Status:** DRAFT FOR REVIEW — no build, no service changes. Awaiting Aiden architecture
review + Dave approach sign-off.
**Author:** NOVA · 2026-06-03 · **Gate:** `vault_secrets` (00770e74)
**Risk class:** boot-path-structural (a bad launcher = fleet-wide startup crash-loop).
Execution requires an attended window, NOT swap-100% / unattended.

---

## 1. Problem

`vault_secrets` requires every secret to resolve from Vault at spawn with zero `.env`
carve-outs (allowlist: `VAULT_ADDR`/`VAULT_TOKEN` only). Coverage audit
(`vault_secrets_allowlist.md`) found:

- **80 of 107** systemd units read secrets via `EnvironmentFile=…/agency-os/.env` and
  do **not** call `resolve_into_env`. Only the agent-spawn path is Vault-covered.
- Removing the 62 migrate carve-outs from `.env` today would crash-loop those 80 units.

## 2. Why a launcher (the single lever)

`src/config/settings.py` (pydantic `BaseSettings`) is imported by **91 files** and reads
`os.environ`; `config/.env` does not exist, so **`os.environ` is the sole secret source**.
Therefore a launcher that populates `os.environ` from Vault *before* the service process
reads config makes the entire fleet Vault-backed **without editing settings.py or any of
the 91 consumers**. This is a launch-boundary change, not a code migration.

**Precedent:** `resolve_into_env()` is already PROVEN on the agent-spawn cold-start path
(#1289 / #1443, `agent_cold_start.py`, `env -i` no-`.env`). This launcher **generalizes
that proven pattern** to the host-service fleet — it is not a new mechanism.

Alternatives rejected:
- *Per-entrypoint `resolve_into_env()` calls* — ~58 edits, easy to miss one, no single
  rollback point.
- *Render `.env` from Vault at boot* — keeps plaintext secrets on disk; defeats the gate.

## 3. Proposed approach

A thin wrapper invoked as the systemd `ExecStart`:

```
ExecStart=/…/vault-envwrap -- /…/.venv/bin/python /…/script.py
```

`vault-envwrap` (proposed `scripts/vault_envwrap.py`):
1. Reads `VAULT_ADDR` + `VAULT_TOKEN` from the (now minimal) environment.
2. Calls `kv_resolver.resolve_into_env()` → pulls all manifest secrets + aliases into
   `os.environ`.
3. Asserts completeness (configurable required-set); logs `resolved/missing/errors`.
4. `os.execvp(cmd[0], cmd)` — replaces the process image, so the service inherits the
   Vault-populated environment with no `.env` dependency.

Modes:
- `--verify` — resolve + report, do NOT exec (memory-safe dry-run for the pilot).
- default — resolve, assert, exec.

## 4. The key architecture decision (for Aiden)

**This makes Vault a hard boot dependency for the whole fleet.** Today `.env` is a local
file — always available. After cutover, if Vault is sealed/unreachable/the token is
expired, **every wrapped service fails to start**. Trade-off to ratify:

| Fail-mode | Behaviour if Vault unreachable | Gate-honest? | Availability |
|-----------|--------------------------------|--------------|--------------|
| **Fail-closed** | service refuses to boot | ✅ (no `.env`) | ⚠️ Vault is now SPOF on boot |
| **Graceful fallback** | fall back to inherited `.env` | ❌ (carve-outs remain) | ✅ resilient |

**Proposed staged stance:** graceful fallback *during* rollout (keep `EnvironmentFile=.env`
alongside the wrapper so nothing breaks), flip to fail-closed + remove carve-outs only
after (a) all batches green, (b) Vault HA/auto-unseal confirmed, (c) token-renewal story
ratified. This sequences availability risk behind the gate flip rather than ahead of it.

**Dependencies this surfaces (need Aiden/Dave ruling):**
- Vault availability/HA on the boot path (`keiracom-vault-unseal.service` is the host
  unseal unit — is its RTO sufficient as a boot gate?).
- `VAULT_TOKEN` lifecycle — TTL, renewal, what happens on expiry at boot.
- Secret caching — should the launcher cache last-good resolution to survive a transient
  Vault blip during boot?

## 4b. Boot-ordering & cold-boot (systemd) — Aiden axis 1

A wrapped unit MUST NOT start before Vault is up + unsealed, or it fails closed at boot.
**Machine-derived finding: of the 80 `.env`-dependent units, only 1 has a Vault ordering
dep today — 79 have none.** Conversion therefore adds, to each unit (via a drop-in, not
the base unit, so rollback is a file delete):

```
[Unit]
After=network-online.target keiracom-vault-unseal.service
Requires=keiracom-vault-unseal.service
Wants=network-online.target
```

- `Requires=` (not just `Wants=`) so a failed/sealed Vault propagates as a clear unit
  failure rather than a silent partial boot.
- **Cold-boot-during-Vault-outage:** with `Requires=`, wrapped units stay in
  `activating`/`failed` until Vault unseals; systemd retries on `keiracom-vault-unseal`
  recovery. The fleet does NOT silently run with stale/absent secrets. During rollout the
  retained `EnvironmentFile=.env` (graceful mode, §4) means even a hard Vault outage
  degrades to baseline `.env` boot, not an outage — this is why fail-closed is the LAST
  step, gated on Vault HA sign-off.
- **Blast radius if fail-closed prematurely:** a Vault outage would block boot of up to 80
  units simultaneously. Unacceptable until Vault HA/unseal RTO is ratified — hence the
  staged stance.

## 5. Boot-path inventory it touches — Aiden axis 4

**Exhaustive machine-derived inventory: `vault_envwrap_boot_inventory.md`** (every
`.env`-dependent unit, its `ExecStart`, and whether it has a Vault ordering dep).

**Count reconciliation (80 vs 102):** the conversion target is the **80 `.service`
units** that carry `EnvironmentFile=…/.env`. Timers (`.timer`) carry no `EnvironmentFile`
— they *activate* a backing `.service`, so wrapping the service covers the timer-driven
run; converting a timer is a no-op. Aiden's 102 = 71 services + 31 timers across the
fleet; filtered to actual `.env` secret readers it is 80 services + 0 timers. No unit is
missed — timers inherit their service's conversion. (Host total seen: 105 services + 36
timers; 80 services are `.env`-dependent.)

Risk-bucketed (detail in `vault_secrets_allowlist.md`):

| Risk | Count | Rollout |
|------|------:|---------|
| LOW (periodic alerts/monitors) | 11 | batch 1 — pilot |
| MED (indexers, sync workers, per-agent) | 49 | batches 2–N |
| HIGH (slack/NATS listeners, dispatcher, fleet-supervisor, coo/enforcer bots) | 20 | last, one at a time |

The agent-spawn path (dispatcher → `agent_cold_start`) already resolves from Vault and is
**out of scope** — not wrapped.

## 6. Single-unit pilot plan

**Pilot unit:** `agency-os-alert-budget-threshold.service` — periodic (timer-driven),
observability-only, no downstream dependency, failure self-heals next tick.

1. Author `scripts/vault_envwrap.py` (+ `vault-envwrap` shim). No unit changes yet.
2. `vault-envwrap --verify -- <pilot cmd>` — confirm resolve from Vault, report.
3. In the attended window: edit ONLY the pilot unit's `ExecStart` to use the wrapper
   (keep `EnvironmentFile=.env` as fallback — graceful mode). `systemctl --user
   daemon-reload && restart`.
4. Observe one full timer cycle: unit runs green, logs show Vault resolution, behaviour
   identical to baseline.
5. Hold ≥24h. If clean → proceed to the rest of LOW. If not → rollback (§7).

**Pilot success criteria:** unit active/green, journal shows `resolved=N missing=…`, the
alert fires identically, zero new errors, memory flat.

**Tranche plan + per-tranche go/no-go (Aiden axis 2 — no big-bang across 80):**
| Tranche | Units | Go/no-go gate before next tranche |
|---------|-------|-----------------------------------|
| 0 (pilot) | 1 (`alert-budget-threshold`) | green + identical behaviour + 24h soak + rollback rehearsed |
| 1 | rest of LOW (10) | all active, one full timer cycle each, zero regressions, 24h |
| 2…N | MED (49) in ~10-unit tranches | each tranche green + soak before the next |
| final | HIGH (20), **one unit at a time** | per-unit green + watch; never two HIGH concurrently |
**No-go on any tranche → halt rollout, rollback that tranche (§7), reassess. No tranche
proceeds on a partial pass.**

## 7. Rollback

- **Per-unit:** revert the one `ExecStart` line to the original `python …`; the retained
  `EnvironmentFile=.env` means the service is back to baseline on `daemon-reload`+restart.
  Sub-minute, no data risk.
- **Fleet-wide:** units are converted in batches; each batch's prior `ExecStart` is
  captured (git-tracked unit drops + a recorded `systemctl cat` snapshot) before edit.
  Mass-revert = restore the snapshot + `daemon-reload`.
- **Hard stop:** because graceful-fallback keeps `.env` present throughout rollout, a
  wrapper failure degrades to baseline behaviour rather than an outage.

**⛔ Sequencing guarantee (Aiden axis 3 — load-bearing):** `.env` IS the rollback target.
The vault_secrets Phase-2 `.env` prune (removing the 62 carve-outs) MUST NOT run until the
launcher is proven across the **full 80-unit inventory**. Order is strict and one-way:

```
pilot (1) → LOW → MED → HIGH (all 80 green + soaked)
  → THEN flip fail-closed (gated on Vault HA sign-off)
  → THEN prune .env carve-outs
```

Pruning `.env` early removes the rollback target and converts any later wrapper failure
into an outage. Phase-1 (#1443) deliberately keeps the secrets in `.env`; this guarantee
holds them there until rollback is no longer needed.

## 8. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Fleet-wide crash-loop from a launcher bug | attended window only; pilot + batched verify-green; graceful fallback keeps `.env` |
| Vault SPOF on boot | stay graceful until HA/auto-unseal RTO ratified; fail-closed is the LAST step |
| Token expiry at boot | renewal story ratified before fail-closed flip; launcher logs token TTL |
| Missed reader (a service reads env in a way the audit didn't catch) | `--verify` per unit before cutover; pilot 24h hold |
| `STRIPE_SECRET_KEY` missing | out-of-band: provision or drop from manifest before fail-closed |

## 9. Gate-complete definition

`vault_secrets` flips proven when: all 80 units boot via `vault-envwrap` (or retire), the
62 carve-outs are removed from `.env`, `.env` = `VAULT_ADDR`/`VAULT_TOKEN` only (+
documented frontend vars en route to Vercel), `git grep` clean in `src/`, and a live
proof_bar asserts a wrapped service resolves a secret from Vault with `.env` absent.

## 10. Open questions for review

1. **Aiden:** fail-closed vs graceful-during-rollout — endorse the staged stance (§4)?
2. **Aiden:** Vault HA/auto-unseal sufficiency for a boot-path dependency; token renewal.
3. **Dave:** approach sign-off + when the attended rollout window can be scheduled.
4. Should the launcher cache last-good resolution to ride out a transient Vault blip?
