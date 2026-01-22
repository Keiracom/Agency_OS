# Architecture Index — Agency OS

**Purpose:** Master navigation for all architecture documentation.
**Principle:** Architecture docs are the SINGLE SOURCE OF TRUTH.
**Last Updated:** 2026-01-22

---

## Folder Index

| Folder | Purpose | Index |
|--------|---------|-------|
| **foundation/** | Core rules, API, database (LOCKED) | [INDEX](foundation/INDEX.md) |
| **business/** | Tiers, scoring, campaigns, CIS | [INDEX](business/INDEX.md) |
| **distribution/** | Channel specs (email, SMS, voice, LinkedIn) | [INDEX](distribution/INDEX.md) |
| **flows/** | Data flows (onboarding → outreach → CRM) | [INDEX](flows/INDEX.md) |
| **content/** | SDK, Smart Prompts, AI content | [INDEX](content/INDEX.md) |
| **process/** | Dev workflow, review process | [INDEX](process/INDEX.md) |
| **frontend/** | UI architecture aligned with backend | [INDEX](frontend/INDEX.md) |

---

## Quick Links

| Need | Go To |
|------|-------|
| Tech stack decisions | [foundation/DECISIONS.md](foundation/DECISIONS.md) |
| Import rules | [foundation/IMPORT_HIERARCHY.md](foundation/IMPORT_HIERARCHY.md) |
| ALS scoring | [business/SCORING.md](business/SCORING.md) |
| Campaign lifecycle | [business/CAMPAIGNS.md](business/CAMPAIGNS.md) |
| Onboarding flow | [flows/ONBOARDING.md](flows/ONBOARDING.md) |
| Multi-channel outreach | [flows/OUTREACH.md](flows/OUTREACH.md) |
| Frontend patterns | [frontend/TECHNICAL.md](frontend/TECHNICAL.md) |

---

## Support Files

| File | Purpose |
|------|---------|
| [TODO.md](TODO.md) | Gaps, priorities, pending decisions |
| [ARCHITECTURE_DOC_SKILL.md](ARCHITECTURE_DOC_SKILL.md) | Templates for creating docs |

---

## How to Use

1. **Find a topic** — Check folder index above
2. **Go to folder INDEX** — See all docs in that area
3. **Read the spec** — Understand what should exist
4. **Check TODO.md** — See if there are known gaps
5. **Implement** — Code must match the spec

---

## Doc Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete and verified |
| 🟡 | Partial / In progress |
| 🔴 | Not created / Not implemented |
