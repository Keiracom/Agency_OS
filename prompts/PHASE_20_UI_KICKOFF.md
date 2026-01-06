# Phase 21 Kickoff Prompt for Claude Code

Copy and paste this entire prompt into Claude Code to begin Phase 21.

---

Act as Sr. Frontend Engineer with expertise in React, Next.js, Tailwind, and UI/UX design systems.

## Context

Agency OS is a multi-channel client acquisition SaaS for Australian marketing agencies. The platform is functionally complete (174/174 tasks) but the UI needs a visual overhaul to a "Bloomberg Terminal" aesthetic - high information density, dark theme, professional SaaS appearance.

We're using v0.dev Platform API to generate high-quality components, then integrating them into the existing Next.js frontend.

## CRITICAL: Read Skills First

Before writing ANY code, read these skill files in order:

```bash
# 1. v0.dev integration patterns
cat skills/frontend/V0_SKILL.md

# 2. Phase 21 design system and component specs
cat skills/frontend/PHASE_21_UI_SKILL.md

# 3. Check progress tracker for task list
cat PROGRESS.md | grep -A 200 "PHASE 21"
```

These skills contain:
- Exact color palette and design tokens
- Component specifications with TypeScript interfaces
- ALS tier thresholds (CRITICAL: Hot = 85+, not 80+)
- v0 prompt engineering patterns
- File organization standards
- Success criteria and QA checklist

## Reference Files

```
config/.env                           # Contains V0_API_KEY
skills/frontend/V0_SKILL.md           # v0 SDK usage guide
skills/frontend/PHASE_21_UI_SKILL.md  # Design system + specs
PROGRESS.md                           # Phase 21 task list with v0 prompts
frontend/app/page.tsx                 # Current landing page (replace)
frontend/app/dashboard/page.tsx       # Current user dashboard (overhaul)
frontend/app/admin/page.tsx           # Current admin dashboard (overhaul)
landing-page-v2.html                  # Reference for animations
```

## Task Execution Order

### V0-001: Install v0-sdk and configure
```bash
cd frontend
pnpm add v0-sdk
```
- Verify V0_API_KEY loads from config/.env
- Test SDK connection with simple generate call

### V0-002: Create helper script
Create `scripts/v0-generate.ts` following the template in V0_SKILL.md:
- Loads V0_API_KEY from config/.env
- Accepts prompt file path as argument
- Writes generated files to `frontend/components/generated/`
- Supports iteration with follow-up prompts

### V0-003: Generate landing page components
Use the v0 prompts from PROGRESS.md (Phase 21 section):
1. PROMPT 1: Landing Page Hero + Activity Feed
2. PROMPT 2: AI Email Typing Demo
3. PROMPT 3: Interactive How It Works Tabs

For each prompt:
1. Save prompt to `prompts/landing-*.txt`
2. Run helper script
3. Review generated code
4. Iterate if needed ("make spacing more compact", "fix colors to match design system")
5. Move refined components to `frontend/components/landing/`

Target files:
- `frontend/components/landing/HeroSection.tsx`
- `frontend/components/landing/ActivityFeed.tsx`
- `frontend/components/landing/TypingDemo.tsx`
- `frontend/components/landing/HowItWorksTabs.tsx`

### V0-004: Generate dashboard components
Use prompts from PROGRESS.md:
1. PROMPT 4: User Dashboard (Bloomberg Terminal Style)
2. PROMPT 5: Admin Dashboard

Target files:
- `frontend/components/dashboard/BentoGrid.tsx`
- `frontend/components/dashboard/StatsCard.tsx`
- `frontend/components/dashboard/ActivityFeed.tsx`
- `frontend/components/dashboard/ALSDistribution.tsx`
- `frontend/components/admin/AdminGrid.tsx`
- `frontend/components/admin/ClientTable.tsx`
- `frontend/components/admin/RevenueChart.tsx`

### LP-001: Update headline
Replace current headline with: "Stop chasing clients. Let them find you."
Apply gradient text effect per design system.

### LP-002: Integrate ActivityFeed
Add the generated ActivityFeed component to landing page.
Configure with sample activities from PROGRESS.md prompts.

### LP-003: Integrate TypingDemo
Add AI email typing demo to landing page.
Use the email content from PROGRESS.md PROMPT 2.

### LP-004: Integrate HowItWorksTabs
Replace static "How It Works" section with interactive tabs.
Configure 6-second auto-rotate, pause on interaction.

### LP-005: Update stats
Replace placeholder "0" values with:
- "55%+" open rate
- "12%+" reply rate
- "<14 days" to first meeting
- "5 channels" unified

### LP-010 & LP-012: Fix ALS tiers
Search entire frontend for incorrect ALS tier displays:
```bash
grep -r "80-100\|80 - 100\|Hot (80" frontend/
grep -r "50-79\|50 - 79\|Warm (50" frontend/
grep -r "Nurture" frontend/
```

Replace with correct thresholds from PHASE_21_UI_SKILL.md:
- Hot: 85-100 (NOT 80-100)
- Warm: 60-84 (NOT 50-79)
- Cool: 35-59
- Cold: 20-34
- Dead: <20

### LP-011: Dynamic spots remaining
Option A (Simple): Query Supabase waitlist table count
Option B (API): Create endpoint `/api/v1/waitlist/count`

Display: "Only {20 - count} of 20 founding spots remaining"
Fallback to hardcoded "17" if query fails.

### Dashboard Integration
1. Update `frontend/app/dashboard/page.tsx` with BentoGrid layout
2. Wire StatsCard components to real API data
3. Wire ActivityFeed to real-time activities
4. Wire ALSDistribution to lead tier counts

### Admin Integration
1. Update `frontend/app/admin/page.tsx` with AdminGrid layout
2. Wire ClientTable to `/api/v1/admin/clients`
3. Wire RevenueChart to aggregated tier data
4. Add system health indicators

## Design Requirements (from PHASE_21_UI_SKILL.md)

- Background: #0a0a0f (primary), #0f0f13 (cards)
- Glass morphism: backdrop-blur-[20px], border-white/10
- Max border-radius: 8px
- Gradients: from-blue-500 to-purple-600
- Text: white (primary), white/70 (secondary), white/50 (muted)
- Compact spacing: p-3 to p-4 on cards
- Table rows: py-2 px-3

## Constraints

- Preserve all existing functionality and data connections
- Keep Shadcn/ui primitives where already used
- Use Tremor for charts (install if needed: `pnpm add @tremor/react`)
- Ensure mobile responsiveness (stack on <640px)
- Test dark mode appearance
- Do not break authentication or protected routes

## Validation After Each Task

```bash
# Check for build errors
pnpm build

# Start dev server and visually verify
pnpm dev

# Check for console errors in browser
# Test on mobile viewport (375px width)
```

## Output

After completing all tasks:

1. Update PROGRESS.md - mark completed tasks:
```
V0-001 | Install v0-sdk | ✅
V0-002 | Create helper script | ✅
...
```

2. Add any blockers to the Blockers Log section

3. Run final QA checklist from PHASE_21_UI_SKILL.md

4. Commit with message: `feat(ui): Phase 21 - Landing page and dashboard overhaul`

## Begin

Start by reading the skill files:
```bash
cat skills/frontend/V0_SKILL.md
```

Then proceed with V0-001. Report status after each task.


## Deployment

After all tasks complete and QA passes:
```bash
# Push to GitHub
git add .
git commit -m "feat(ui): Phase 21 - Landing page and dashboard overhaul"
git push origin main

# Vercel auto-deploys from main branch
# Verify at: https://agency-os-liart.vercel.app
```

Confirm deployment succeeded before marking Phase 21 complete.