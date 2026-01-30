# 🔬 CODEBASE DEEP DIVE — Agency OS Commit Analysis

**Author:** Elliot (CTO)  
**Date:** 2025-07-24  
**Commit:** `cd040cc` — "feat: Add UI components, prototypes, and update gitignore"  
**Scale:** 281 files changed, 47,605 insertions, 995 deletions  

---

## 1. Executive Summary

This commit represents **Dave's most ambitious push to date** — a full-spectrum effort that simultaneously:

1. **Created an entire agent-based fix/audit framework** (50+ spec files) to systematically close every gap identified in a prior TODO.md audit
2. **Built 3 frontend prototypes** exploring the product's visual identity — from information-dense dashboards to premium glassmorphism to a 3D component showroom
3. **Assembled a massive UI component library** — 148 components in `components/ui/` + 48 in `src/components/ui/` + a custom library with 3D, Sci-Fi, Spline, and Rive integrations (196+ total components)
4. **Committed real Xero financial data** (bills/accounts payable) into the repo
5. **Added 69 production dependencies** including Three.js, Framer Motion, Spline, Rive, Plasmic, and the full Radix UI primitives suite

**In plain terms:** Dave mapped every known bug/gap into actionable Claude agent specs, explored 3 different visual directions for the frontend, and stockpiled an enormous UI arsenal. This is strategic groundwork — not shipping code, but laying the rails for rapid execution.

---

## 2. Fix Backlog — All 34 Gaps

The fix framework lives in `.claude/agents/fix-*` directories, organized by priority tier. Each spec is a fully detailed agent instruction with pre-flight checks, implementation steps, acceptance criteria, and validation commands.

### Fix Master Orchestration

**File:** `.claude/agents/fix-master.md`

The Fix Master is a meta-agent that deploys fix agents in 4 phases with **mandatory CEO approval gates** between phases. It uses parallel execution within tiers, sequential execution between tiers, and maintains a status tracker. This is a well-designed orchestration pattern.

### P0/P1 — Critical (5 fixes)

| # | Fix | Description | Files Affected | Complexity | Risk |
|---|-----|-------------|----------------|------------|------|
| 1 | **FILE_STRUCTURE.md** | 199 actual files, only 135 documented (~50% gap) | `docs/architecture/foundation/FILE_STRUCTURE.md`, all `src/` | **Medium** — scanning + documenting | Low |
| 2 | **Funnel Detector** | Detector exists but NOT called in `run_all_detectors_task()` | `src/orchestration/pattern_learning_flow.py` | **Low** — add import + function call | **High** — dead code means no funnel learning |
| 3 | **Voice Retry Logic** | No busy/no_answer retry (spec says busy=2hr, no_answer=next day) | `src/engines/voice.py` | **Medium** — new function + scheduling | **High** — losing warm leads |
| 4 | **LinkedIn Weekend** | Sat 50% / Sun 0% rule not enforced | `src/engines/linkedin.py` | **Low** — multiplier function | **High** — account ban risk |
| 5 | **ICP Refiner** | WHO patterns learned but never applied to sourcing | `src/orchestration/monthly_replenishment_flow.py`, `src/services/icp_refiner.py` | **High** — new service class + integration | **High** — core intelligence loop broken |

**CTO Assessment:** Fixes 2, 4, and 5 are genuinely critical. The funnel detector being disconnected means the Conversion Intelligence System is running on 5 of 6 cylinders. LinkedIn weekend enforcement is a compliance/safety issue. The ICP refiner gap means the system learns WHO converts but never uses that knowledge — the intelligence loop is open.

### P2 — High Priority (7 fixes)

| # | Fix | Description | Files Affected | Complexity |
|---|-----|-------------|----------------|------------|
| 6 | **Database Models** | 6 models undocumented in DATABASE.md (CampaignSuggestion, DigestLog, IcpRefinementLog, LinkedInCredential, ClientIntelligence, SDKUsageLog) | `docs/architecture/foundation/DATABASE.md` | Low |
| 7 | **Database Enums** | 5 enums undocumented (ResourceType, ResourceStatus, HealthStatus, SuggestionType, SuggestionStatus) | `docs/architecture/foundation/DATABASE.md` | Low |
| 8 | **Digest Routes** | 4 endpoints undocumented (GET/PATCH /digest/settings, GET /preview, GET /history) | `docs/architecture/foundation/API_LAYER.md` | Low |
| 9 | **Camoufox Wiring** | Tier 3 scraper code exists but not called in waterfall | `src/engines/scout.py` | **Medium** — integration + error handling |
| 10 | **Campaign FK** | `client_resource_id` missing from campaign_resources table | `src/models/`, Supabase migrations | **Medium** — model change + migration |
| 11 | **getCampaignPerformance** | Frontend stub returns empty array, needs real backend endpoint | `frontend/lib/api/reports.ts`, `src/api/routes/` | **High** — full endpoint + schema |
| 12 | **Resend Reply Handler** | No "replied" event handler in webhook processing | `src/api/routes/webhooks.py` | **Medium** — new handler + lead status updates |

**CTO Assessment:** Fix 9 (Camoufox wiring) is another "built but disconnected" pattern — same issue as the funnel detector. Fix 12 (Resend reply) means email replies may not be tracked, which would break the reply handling flow. Fix 11 is a frontend-backend contract gap.

### P3 — Medium Priority (21 fixes across 5 subcategories)

#### P3 Voice Engine (4 fixes)

| # | Fix | Description | Complexity |
|---|-----|-------------|------------|
| 13 | **Phone Provisioning** | No automated number provisioning via Twilio | High — new service class |
| 14 | **Recording Cleanup** | 90-day recording deletion not implemented | Medium — Prefect task + Twilio API |
| 15 | **Business Hours** | No check before placing calls | Medium — timezone-aware validation |
| 16 | **DNCR Check** | Voice calls not checking Do Not Call Register | Medium — integration + caching |

**CTO Assessment:** Fix 16 (DNCR) is **arguably P0 for Australian compliance**. Calling numbers on the DNCR is illegal. Fix 15 (business hours) is also a compliance concern — calling outside hours could generate complaints.

#### P3 LinkedIn Engine (3 fixes)

| # | Fix | Description | Complexity |
|---|-----|-------------|------------|
| 17 | **Stale Withdrawal** | 30-day stale connection requests not withdrawn | Medium — query + API calls |
| 18 | **Shared Quota** | Manual + automated activity not combined in quota tracking | High — unified tracking system |
| 19 | **Profile View Delay** | No 10-30 min delay before connect request (anti-detection) | High — scheduling system |

**CTO Assessment:** Fix 18 is important — if manual LinkedIn usage isn't counted against the automated quota, accounts could exceed daily limits and get banned. Fix 19 is smart anti-detection hygiene.

#### P3 Email Engine (2 fixes)

| # | Fix | Description | Complexity |
|---|-----|-------------|------------|
| 20 | **Signature Generation** | Dynamic email signature not implemented | Medium — templates + sender lookup |
| 21 | **Display Name Format** | "First Last \| Company" format not enforced | Low — formatter function |

#### P3 Documentation (4 fixes)

| # | Fix | Description | Complexity |
|---|-----|-------------|------------|
| 22 | **Import Hierarchy** | Agents, services, detectors layers undocumented | Low — documentation |
| 23 | **Contract Comments** | ~50% compliance on contract comments (should be >90%) | High — touch many files |
| 24 | **TECHNICAL.md** | Component count outdated (61→70+), missing /dashboard/archive | Low |
| 25 | **ADMIN.md** | Overstated endpoint count | Low |

#### P3 Frontend (8 fixes)

| # | Fix | Description | Complexity |
|---|-----|-------------|------------|
| 26 | **LeadEnrichmentCard** | Component planned but not created | Medium |
| 27 | **LeadActivityTimeline** | Timeline component missing | Medium |
| 28 | **LeadQuickActions** | Quick action dropdown missing | Medium |
| 29 | **LeadStatusProgress** | Funnel position progress bar missing | Medium |
| 30 | **LeadBulkActions** | Multi-lead batch operations missing | High |
| 31 | **Profile Settings Page** | /settings/profile page missing | Medium |
| 32 | **Notifications Page** | /settings/notifications page missing | Medium |
| 33 | **Onboarding Progress** | Onboarding progress indicators missing | Medium |

**CTO Assessment:** All 8 frontend specs include complete TypeScript code in the spec itself. These are essentially "paste and adjust" implementations — Dave wrote the code in the specs. Execution should be fast.

### P5 — Future (1 fix)

| # | Fix | Description | Complexity |
|---|-----|-------------|------------|
| 34 | **SECURITY.md** | Auth, RBAC, API keys, encryption, audit logging undocumented | High — requires full security audit |

**CTO Assessment:** The spec for fix-34 is itself a near-complete SECURITY.md document. Dave wrote the entire doc inside the agent spec. Just needs validation against actual code.

---

## 3. Audit Framework

**16 audit agents** organized into a comprehensive domain coverage matrix, orchestrated by an Audit Master.

### Audit Master (`.claude/agents/audit-master.md`)

Deploys all 15 domain auditors in parallel, then compiles a CEO summary report. Output goes to `docs/audits/FULL_AUDIT_[DATE].md`.

### Domain Auditors

| Auditor | Scope | Key Checks |
|---------|-------|------------|
| **audit-foundation** | API routes, database, config, imports | Route coverage, schema alignment, env vars |
| **audit-integrations** | All 21 third-party integrations | Error handling, rate limiting, retry logic, auth, timeouts |
| **audit-engines** | 16 engine modules | Doc alignment, error handling, typing, async patterns |
| **audit-services** | 27 service modules | Single responsibility, DI, error handling, tests |
| **audit-models** | 22+ data models | Schema match, type correctness, validators, relationships |
| **audit-flows** | Prefect orchestration flows | Doc alignment, error handling, idempotency, schedules |
| **audit-agents** | AI agents (7+) | Prompts, constitutions, tool usage, token management |
| **audit-business** | CIS, scoring, campaigns, tiers, billing | Detector implementation, ALS formula, allocation logic |
| **audit-distribution** | Email, SMS, Voice, LinkedIn, Mail | Warmup, compliance, send limits, fallback chains |
| **audit-frontend-core** | App router, hooks, lib, types | Route structure, hook rules, type safety, config |
| **audit-frontend-pages** | All page components | Doc alignment, state management, loading/error states, a11y |
| **audit-docs** | All documentation | Completeness, currency, accuracy, structure |
| **audit-tests** | Test coverage and quality | Coverage by module, test quality, CI integration |
| **audit-config** | Env vars, Docker, deployment, CI/CD | Secret management, Docker builds, Railway/Vercel config |
| **audit-security** | Security vulnerabilities | Auth, API security, secrets, data protection, Australian compliance |

**CTO Assessment:** This is a rigorous audit framework. Each auditor has detailed checklists, expected inventories, and standardized output formats. The integration auditor alone maps 21 services (Anthropic, Apollo, Apify, Camoufox, Clay, ClickSend, DataForSEO, DNCR, ElevenLabs, HeyReach, Postmark, Redis, Resend, Salesforge, SDK Brain, Sentry, Serper, Supabase, Twilio, Unipile, Vapi). The services auditor knows about 27 services by name. **Dave has deeply internalized the codebase architecture.**

---

## 4. Frontend Direction

### Three Prototype Directions

#### Prototype 1: Information-Dense Dashboard (`/prototype`)
- **Aesthetic:** Clean, professional, light theme (slate-900 sidebar, white content area)
- **Navigation:** 6-page SPA (Dashboard, Campaigns, Leads, Replies, Reports, Settings)
- **Design Language:** Tailwind utilities, Lucide icons, subtle shadows, blue accent color
- **Key Feature:** Click animations on nav items (scale-95 on press, icon rotation)
- **Agency:** "Acme Agency" on "Velocity Plan"
- **Verdict:** Production-ready SaaS look. Conventional but solid.

#### Prototype 2: Premium Glassmorphism (`/prototype-premium`)
- **Aesthetic:** Dark glassmorphism (`bg-white/[0.03] backdrop-blur-xl`), cyan/blue accent gradients
- **Components Used:** NumberTicker, MagicCard, BorderBeam, MovingBorder, ShineBorder
- **Design Language:** Aurora glow backgrounds, glass cards with `border-white/[0.08]`, glow shadows
- **Key Feature:** GlassCard component with configurable glow colors (cyan, purple, emerald, orange)
- **Badge:** "PREMIUM" font-mono label next to logo
- **Verdict:** High-end feel, EqtyLab-inspired. Impressive visually but may sacrifice readability.

#### Prototype 3: Component Showroom (`/showroom`)
- **Purpose:** Exhibition of every premium component in the library
- **3D Components:** FloatingCrystal, GlassOrb, ParticleField, FloatingText3D, WaveGrid, NeonTunnel
- **Sci-Fi:** HoloCard
- **External:** SplineScene, SplineRobot, SplineAbstract, RiveButton, RiveLoader, RiveCharacter
- **Pattern:** Dynamic imports with SSR disabled (correct for canvas/WebGL), graceful fallback placeholders
- **Verdict:** This is a design exploration lab, not a product page. Shows the range of what's possible.

### Design Mockups (`frontend/design/dashboard/mockups/`)

Two polished mockup components:

1. **PremiumHeroCard** — Meetings booked hero metric with aurora glow background, SVG wave line, on-track/ahead/behind status indicators. Uses emerald/cyan/amber color coding.

2. **PremiumActivityCard** — Glassmorphism activity feed with channel-colored icons (email=blue, SMS=green, LinkedIn=sky, voice=purple). Mock data shows realistic interactions.

Also includes 4 HTML preview files (default, Apple XP style, cyberpunk, light) and screenshots from January 2026.

### SPEC_REFERENCE.md — Design Bible

**This is gold.** A compiled reference from architecture docs covering:

- **Banned terms** (never say "credits remaining", "lead count", "hot leads")
- **Approved terms** ("meetings booked", "prospects in pipeline", "show rate")
- **ALS tier mapping** — internal labels (Hot/Warm/Cool/Cold/Dead) vs client-facing labels (High Priority/Engaged/Nurturing/Low Activity/Inactive)
- **Metric visibility tiers** — T1 Hero (always visible), T2 Campaign, T3 Activity, T4 Hidden (INTERNAL ONLY)
- **Permission modes** — autopilot (Sparkles icon), co-pilot (Eye icon), manual (MousePointer icon)
- **Campaign slots by tier** — Ignition (5), Velocity (10), Dominance (20)
- **Reply intent classifications** — 8 types from meeting_interest to angry_or_complaint
- **What clients should NEVER see** — raw ALS scores, enrichment costs, source waterfall, credit usage

**CTO Assessment:** This spec reference prevents the #1 mistake SaaS companies make — exposing internal metrics to clients. The term ban list and visibility tiers show mature product thinking.

---

## 5. Financial Data (Xero)

### File Details
- **File:** `CAI\uf03aAgency_OSxerodatabills_accpay.json` (Unicode character in filename — path artifact)
- **Size:** 8,654 bytes
- **Provider:** ClaudeCode-DavidS-2026
- **Type:** Accounts Payable (ACCPAY) bills

### Financial Summary

| Metric | Value |
|--------|-------|
| Total Bills | 6 |
| Total Value | $3,166.58 |
| Total Paid | $2,630.58 |
| Total Outstanding | $533.00 |
| Statuses | 3 PAID, 2 DRAFT, 1 DELETED |

### Vendors

| Vendor | Bills | Notes |
|--------|-------|-------|
| **Australian Taxation Office** | $27.00 (paid), $530.00 (draft), $3.00 (deleted) | Tax obligations — BAS/GST |
| **N2N Australia Pty Ltd** | $1,264.43 (paid), $1,339.15 (paid) | Likely a contractor/service provider |

### ⚠️ CONCERN: Financial Data in Git

**This Xero data is committed to the repository.** While it's accounts payable (not revenue/client data), it contains:
- Real business entity names
- Payment amounts and dates  
- Tax office interaction history
- PaymentIDs and InvoiceIDs

**Recommendation:** Add `*xero*`, `*accpay*` patterns to `.gitignore` and remove from tracking. Financial data should not live in source control.

---

## 6. UI Component Library Inventory

### Scale
| Location | Count | Source |
|----------|-------|--------|
| `frontend/components/ui/` | **148** components | shadcn/ui + Magic UI + Aceternity |
| `frontend/src/components/ui/` | **48** components | Aceternity UI (additional) |
| `frontend/src/components/library/` | **17** components | Custom 3D, Sci-Fi, Spline, Rive |
| **Total** | **213** UI components | |

### Category Breakdown (components/ui/ — 148 files)

| Category | Count | Examples |
|----------|-------|---------|
| **3D/Spatial** | 4 | 3d-card, 3d-pin, globe, world-map |
| **Animation/Motion** | 17 | animated-beam, blur-fade, flip-words, morphing-text, typing-animation, smooth-cursor |
| **Background/Effects** | 19 | aurora-background, meteors, particles, shooting-stars, sparkles, wavy-background, vortex |
| **Cards/Containers** | 10 | card, card-hover-effect, card-stack, evervault-card, magic-card, neon-gradient-card, wobble-card |
| **Form/Input** | 10 | button, input, textarea, select, slider, switch, file-upload |
| **Layout/Navigation** | 10 | sidebar, sheet, tabs, table, dropdown-menu, navbar-menu, scroll-area |
| **Premium/Special** | 15 | shine-border, shimmer-button, rainbow-button, moving-border, border-beam, number-ticker, lamp |
| **Text Effects** | 12 | text-animate, text-generate-effect, text-hover-effect, text-reveal, colourful-text, sparkles-text |
| **Display/Content** | 15 | timeline, terminal, safari, macbook-scroll, hero-video-dialog, parallax-scroll, compare |
| **Other/Utility** | 36 | Various supporting components (toast, tooltip, skeleton, loading-skeleton, etc.) |

### Custom Library Components (`frontend/src/components/library/`)

| Subdirectory | Components | Technology |
|--------------|-----------|------------|
| **3d/** | FloatingCrystal, GlassOrb, ParticleField, FloatingText3D, WaveGrid, NeonTunnel | React Three Fiber + Drei |
| **scifi/** | HoloCard | Custom CSS/animation |
| **external/** | SplineScene, SplineRobot, SplineAbstract, RiveButton, RiveLoader, RiveCharacter | Spline + Rive |

### Application Component Directories

Beyond UI primitives, the app has domain-specific component directories:

| Directory | Purpose |
|-----------|---------|
| `components/admin/` | Admin dashboard components |
| `components/campaigns/` | Campaign management UI |
| `components/communication/` | Messaging/comms UI |
| `components/dashboard/` | Dashboard v1 |
| `components/dashboard-v2/` | Dashboard redesign |
| `components/generated/` | Auto-generated (hero, tabs, typing) |
| `components/landing/` | Landing page components |
| `components/layout/` | Layout wrappers |
| `components/leads/` | Lead management UI |
| `components/magicui/` | Magic UI specific |
| `components/marketing/` | Marketing page components |
| `components/onboarding/` | Onboarding flow |
| `components/plasmic/` | Plasmic integration |

---

## 7. Dependency & Config Changes

### Package.json — 69 Production Dependencies

**Core Framework:**
- Next.js 14.0.4, React 18.2, TypeScript 5.9.3

**UI Primitives (Radix):** 20 packages
- Full Radix UI suite: accordion, alert-dialog, avatar, checkbox, collapsible, dialog, dropdown-menu, hover-card, icons, label, popover, progress, radio-group, scroll-area, select, separator, slider, slot, switch, tabs, toast, tooltip

**3D/Graphics:**
- `three` ^0.182.0 + `@react-three/fiber` ^8.15.19 + `@react-three/drei` ^9.96.5
- `three-globe` ^2.45.0, `cobe` ^0.6.5 (globe rendering)

**Animation:**
- `framer-motion` ^12.29.0 + `motion` ^12.29.0
- `canvas-confetti` ^1.9.4

**External Platforms:**
- `@rive-app/react-canvas` ^4.26.1 (Rive animations)
- `@plasmicapp/loader-nextjs` ^1.0.451 + `@plasmicapp/react-web` ^0.2.415 (Plasmic CMS)
- `@arwes/react` ^1.0.0 (Sci-fi UI framework)
- `v0-sdk` ^0.15.3 (Vercel v0 components)

**Data/Charts:**
- `@tanstack/react-query` ^5.17.0, `@tanstack/react-table` ^8.11.0
- `@tremor/react` ^3.18.7 (dashboards)
- `recharts` ^2.15.4

**Particles:**
- `@tsparticles/engine`, `@tsparticles/react`, `@tsparticles/slim` ^3.9.1

**Other Notable:**
- `@sentry/nextjs` ^10.36.0 (error tracking)
- `@supabase/auth-helpers-nextjs` + `@supabase/supabase-js` (auth/DB)
- `react-hook-form`, `zod` (forms/validation)
- `shiki` + `@shikijs/transformers` (code highlighting)
- `rough-notation` ^0.5.1 (hand-drawn annotation effects)
- `simplex-noise` ^4.0.3 (procedural noise)

### Tailwind Config

- **Custom colors:** `hot` (red), `warm` (orange), `cool` (blue), `cold` (gray) — maps to ALS tier colors
- **5 chart colors** via CSS custom properties
- **Standard shadcn/ui setup** with CSS variable-based theming
- **108 lines** total — clean and focused

### .gitignore

Standard Python + Node gitignore. **Notable absence:** No patterns for financial data files (Xero exports).

---

## 8. Key Observations & Recommendations

### 🟢 What Dave Did Well

1. **Systematic gap analysis** — The 34 fix specs are thorough, well-structured, and actionable. Each one has pre-flight checks, implementation steps, acceptance criteria, and validation commands. This is production-grade engineering planning.

2. **Audit framework depth** — The 16 auditors cover every domain with detailed checklists. The audit-master orchestration pattern is clean.

3. **SPEC_REFERENCE.md** — This design bible prevents product mistakes. The term bans, visibility tiers, and client-facing vs internal label mapping show Dave deeply understands the product's information architecture.

4. **Code-in-specs** — Several fix specs (especially frontend #26-33 and security #34) include nearly complete implementations. This dramatically reduces execution time.

5. **Three-direction exploration** — Testing information-dense, premium glassmorphism, and component showroom simultaneously was smart. Now we can converge.

### 🟡 Concerns

1. **Component library bloat** — 213 UI components is excessive. Many will never be used in the actual product. The Aceternity/Magic UI components are impressive demos but most are presentation effects (meteors, shooting stars, aurora backgrounds) not suitable for a SaaS dashboard.

2. **Dependency weight** — 69 production deps is heavy. Three.js alone adds ~600KB gzipped. Rive, Spline, tsparticles, and the full Radix suite compound this. **Bundle size will be a problem.**

3. **Xero data in git** — Financial data should never be in source control. Remove and gitignore.

4. **Priority misranking** — Fix #16 (DNCR check) is labeled P3 but is actually a **legal compliance requirement** in Australia. Should be P0. Fix #15 (business hours) is similar.

5. **"Built but disconnected" pattern** — Fixes #2 (funnel detector) and #9 (Camoufox) are both code that exists but isn't wired in. This suggests a pattern where Dave builds components but doesn't always integrate them into the orchestration layer. Worth watching for.

6. **No CI/CD visible** — The audit framework mentions GitHub Actions but the commit itself doesn't include workflow files. Test infrastructure remains unclear.

### 🔴 Recommended Priority Reordering

| Original | Fix | Recommended Priority | Reason |
|----------|-----|---------------------|--------|
| P3 | #16 DNCR Check | **P0** | Legal compliance — calling DNCR numbers is illegal in Australia |
| P3 | #15 Business Hours | **P1** | Compliance — calling outside hours generates complaints |
| P3 | #18 Shared Quota | **P1** | Account safety — untracked manual activity risks LinkedIn bans |
| P0 | #1 File Structure | **P3** | Documentation — important but not blocking anything |

### 📋 Recommended Next Steps

1. **Immediately:** Remove Xero data from git, add to `.gitignore`
2. **This week:** Execute P0 fixes (#2, #3, #4, #5 + promoted #16, #15)
3. **This week:** Choose one frontend direction (recommend: prototype-1 base with selective premium elements from prototype-2)
4. **Next week:** Execute P2 fixes (#6-12)
5. **Audit bundle size:** Run `next build` and measure. Likely need to tree-shake unused components
6. **Prune component library:** Tag which of the 213 components will actually ship. Archive the rest.

### 💡 Architecture Note

The fix/audit agent framework Dave built is essentially a **Claude-native project management system**. Instead of Jira tickets, each fix is a Claude agent spec. Instead of a sprint board, the fix-master.md is the orchestrator. This is novel and potentially very efficient — each "ticket" is immediately executable by Claude with zero translation overhead. Worth preserving this pattern.

---

*End of Deep Dive. Total files analyzed: 50+ agent specs, 3 prototype pages, 2 mockup components, 1 design spec, 1 financial data file, 213+ UI components cataloged, package.json, tailwind.config.js, .gitignore.*
