# Distribution Channel Architecture Index

**Purpose:** Single source of truth for all distribution channel specifications.
**Principle:** Code/flows/engines must match these specs exactly.

---

## Architecture Files

| File | Channel | Status | Code Status |
|------|---------|--------|-------------|
| `RESOURCE_POOL.md` | Domain/Resource Pool | ✅ Spec done | ❌ Not implemented |
| `EMAIL_DISTRIBUTION.md` | Email | ✅ Spec done | 🟡 Partial |
| `SMS_DISTRIBUTION.md` | SMS | ✅ Spec done | 🟡 Partial |
| `VOICE_DISTRIBUTION.md` | Voice | ✅ Spec done | 🟡 Partial |
| `LINKEDIN_DISTRIBUTION.md` | LinkedIn | ✅ Spec done | 🟡 Partial |
| `MAIL_DISTRIBUTION.md` | Direct Mail | ✅ Spec done | ❌ Not implemented |

---

## Shared Concepts

### Rolling Billing Cycle

Each client's "month" starts on their signup day:
```
Client A signs up Jan 5  → Month 1: Jan 5 - Feb 4
Client B signs up Jan 22 → Month 1: Jan 22 - Feb 21
```

### Resource Ownership Model

```
Platform Level:
├── resource_pool (domains, phone numbers, LinkedIn seats)
│   └── Unassigned resources available for new clients

Client Level:
├── client_resources (assigned from pool on signup)
│   └── Dedicated resources for this client's lifetime

Campaign Level:
├── campaign_resources (inherited from client_resources)
│   └── Used by allocator for round-robin distribution
```

### Default Sequence (System-Controlled)

| Step | Day | Channel | Fallback |
|------|-----|---------|----------|
| 1 | 0 | Email | — |
| 2 | 3 | Voice | Email |
| 3 | 5 | LinkedIn | Skip |
| 4 | 8 | Email | — |
| 5 | 12 | SMS | Email |

---

## Verification Protocol

For each channel, verify:

1. **Tables exist** — Schema matches spec
2. **Service exists** — Integration client implemented
3. **Engine wired** — Engine uses service correctly
4. **Flow wired** — Prefect flow triggers engine
5. **Rate limits enforced** — Per-resource limits work
6. **Warmup logic** — Gradual ramp implemented (if applicable)
7. **Timezone handling** — Recipient timezone used

---

## Related Documentation

| Doc | Purpose |
|-----|---------|
| `../AUTOMATED_DISTRIBUTION_DEFAULTS.md` | Timing, sequences, warmup schedule |
| `../DECISIONS.md` | Technology stack decisions |
| `../../specs/engines/ALLOCATOR_ENGINE.md` | Allocator engine spec |
| `../../specs/engines/TIMING_ENGINE.md` | Timing engine spec |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| 🔴 | Not implemented / Spec needed |
| 🟡 | Partially implemented |
| ✅ | Fully implemented and verified |
