# Business Logic — Agency OS

**Purpose:** Business model, pricing, scoring, and campaign architecture.

---

## Documents

| Doc | Purpose | Status |
|-----|---------|--------|
| [TIERS_AND_BILLING.md](TIERS_AND_BILLING.md) | Subscription tiers, credits, monthly reset | ✅ Complete |
| [SCORING.md](SCORING.md) | ALS formula, tier thresholds, channel access | ✅ Complete |
| [CIS.md](CIS.md) | Conversion Intelligence System, 5 detectors | ✅ Complete |
| [CAMPAIGNS.md](CAMPAIGNS.md) | Campaign lifecycle, AI suggestions, sequences | ✅ Complete |

---

## Key Concepts

### Subscription Tiers
| Tier | Leads/Month | Price |
|------|-------------|-------|
| Ignition | 1,250 | $X |
| Velocity | 2,250 | $Y |
| Dominance | 4,500 | $Z |

### ALS Tiers
| Tier | Score | Channel Access |
|------|-------|----------------|
| Hot | 85-100 | All + SDK |
| Warm | 60-84 | Email, Voice, LinkedIn |
| Cool | 35-59 | Email, LinkedIn |
| Cold | 20-34 | Email only |
| Dead | <20 | None |

---

## Cross-References

- [Master Index](../ARCHITECTURE_INDEX.md)
- [TODO.md](../TODO.md) — Gaps and priorities
