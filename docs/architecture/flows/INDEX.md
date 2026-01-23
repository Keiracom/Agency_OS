# Data Flows — Agency OS

**Purpose:** End-to-end data flows from onboarding through outreach to conversion.

---

## Documents

| Doc | Purpose | Status |
|-----|---------|--------|
| [ONBOARDING.md](ONBOARDING.md) | ICP extraction, resource assignment | ✅ Complete |
| [ENRICHMENT.md](ENRICHMENT.md) | Apollo → Apify → Clay waterfall | ✅ Complete |
| [OUTREACH.md](OUTREACH.md) | Multi-channel execution, JIT validation | ✅ Complete |
| [MEETINGS_CRM.md](MEETINGS_CRM.md) | Meeting lifecycle, CRM push | ✅ Complete |
| [MONTHLY_LIFECYCLE.md](MONTHLY_LIFECYCLE.md) | Month 2+ operations, replenishment | ✅ Complete |
| [AUTOMATION_DEFAULTS.md](AUTOMATION_DEFAULTS.md) | Default sequences, timing | ✅ Complete |
| [REPLY_HANDLING.md](REPLY_HANDLING.md) | Intent classification, responses | 🟡 Spec only |

### Client Transparency (Phase H)

| Feature | Purpose | Status |
|---------|---------|--------|
| Daily Digest | Email summary of outreach activity | ✅ Implemented |
| Live Activity Feed | Real-time outreach stream | 🔴 Pending |
| Content Archive | Searchable sent content | 🔴 Pending |
| Best Of Showcase | High-performing examples | 🔴 Pending |

---

## Flow Sequence

```
ONBOARDING
    ↓
ICP Extraction → Resource Assignment → Campaign Suggestions
    ↓
ENRICHMENT
    ↓
Apollo → Apify → Clay → Score (ALS) → Allocate Channels
    ↓
OUTREACH
    ↓
Email → Voice → LinkedIn → SMS (per sequence)
    ↓
REPLY HANDLING
    ↓
Intent → Response → Sequence Control
    ↓
MEETINGS & CRM
    ↓
Booking → Outcome → Deal → CRM Push
    ↓
MONTHLY LIFECYCLE (Month 2+)
    ↓
Credit Reset → Replenishment → CIS Refinement
```

---

## Cross-References

- [Master Index](../ARCHITECTURE_INDEX.md)
- [TODO.md](../TODO.md) — Gaps and priorities
