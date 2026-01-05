# Phase 21: Landing Page + UI Overhaul

**Status:** 🔴 Not Started (High Priority)  
**Tasks:** 18 total (4 complete from existing Vercel)  
**Depends On:** Phase 17 (v0 API key)  
**Skills Required:**
- `skills/frontend/V0_SKILL.md` — v0.dev integration
- `skills/frontend/PHASE_21_UI_SKILL.md` — Design system + components

---

## Overview

Overhaul the Agency OS frontend with a "Bloomberg Terminal" aesthetic:
- High information density
- Dark theme default
- Professional SaaS appearance
- Landing page with animations
- Dashboard with bento grid layout

**Tool:** v0.dev Platform API for component generation

---

## Task Summary

| Section | Tasks | Status |
|---------|-------|--------|
| 21A: Content Merges (from V2) | 5 | 🔴 |
| 21B: Keep from Vercel | 4 | ✅ |
| 21C: Consistency Fixes | 3 | 🔴 |
| 21D: v0.dev Integration | 4 | 🔴 |
| 21E: Optional Enhancements | 2 | 🔴 |
| **TOTAL** | **18** | **4/18** |

---

## 21A: Content Merges from V2 → Vercel (5 tasks)

| Task | Description | Priority |
|------|-------------|----------|
| LP-001 | Replace headline: "Stop chasing clients. Let them find you." | P0 |
| LP-002 | Add live activity feed animation (rotating notifications) | P0 |
| LP-003 | Add AI email typing animation (typewriter effect) | P1 |
| LP-004 | Replace static How It Works with interactive tabs (auto-rotate) | P1 |
| LP-005 | Use hardcoded stats (55%+, 12%+, <14 days) instead of "0" | P0 |

---

## 21B: Keep/Enhance from Vercel (4 tasks) ✅

| Task | Description | Status |
|------|-------------|--------|
| LP-006 | ROI comparison section (strongest differentiator) | ✅ |
| LP-007 | Meeting estimates on pricing cards | ✅ |
| LP-008 | Dashboard preview in hero | ✅ |
| LP-009 | Features comparison table | ✅ |

---

## 21C: Consistency Fixes (3 tasks)

| Task | Description | Priority |
|------|-------------|----------|
| LP-010 | Fix ALS tier display: Hot = 85+ (not 80-100) | P0 |
| LP-011 | Make spots remaining dynamic (query waitlist count) | P1 |
| LP-012 | Sync tier thresholds: Hot (85+), Warm (60-84), Cool (35-59), Cold (20-34) | P0 |

---

## 21D: v0.dev Integration (4 tasks)

| Task | Description | Priority |
|------|-------------|----------|
| V0-001 | Install v0-sdk and configure API key | P0 |
| V0-002 | Create `scripts/v0-generate.ts` helper script | P0 |
| V0-003 | Generate landing page components via v0 API | P0 |
| V0-004 | Generate dashboard components via v0 API | P0 |

---

## 21E: Optional Enhancements (2 tasks)

| Task | Description | Priority |
|------|-------------|----------|
| LP-013 | Add dark mode toggle | P2 |
| LP-014 | A/B test headline variants | P2 |

---

## Design System (Summary)

Full details in `skills/frontend/PHASE_21_UI_SKILL.md`

### Colors

```css
--bg-primary: #0a0a0f;
--bg-secondary: #0f0f13;
--glass-bg: rgba(255, 255, 255, 0.05);
--glass-border: rgba(255, 255, 255, 0.1);
--gradient-primary: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
```

### ALS Tiers (CRITICAL)

| Tier | Score | Color |
|------|-------|-------|
| Hot | 85-100 | Orange/Red gradient |
| Warm | 60-84 | Yellow/Orange gradient |
| Cool | 35-59 | Blue |
| Cold | 20-34 | Gray |
| Dead | <20 | Dark gray |

---

## v0 Prompts

See `PROGRESS.md` Phase 21 section for ready-to-use prompts:
1. Landing Page Hero + Activity Feed
2. AI Email Typing Demo
3. Interactive How It Works Tabs
4. User Dashboard (Bloomberg Style)
5. Admin Dashboard

---

## Files to Create

```
frontend/components/
├── landing/
│   ├── HeroSection.tsx
│   ├── ActivityFeed.tsx
│   ├── TypingDemo.tsx
│   └── HowItWorksTabs.tsx
├── dashboard/
│   ├── BentoGrid.tsx
│   ├── StatsCard.tsx
│   ├── ActivityFeed.tsx
│   └── ALSDistribution.tsx
└── admin/
    ├── AdminGrid.tsx
    ├── ClientTable.tsx
    └── RevenueChart.tsx
```

---

## Files to Modify

- `frontend/app/page.tsx` — Landing page
- `frontend/app/dashboard/page.tsx` — User dashboard
- `frontend/app/admin/page.tsx` — Admin dashboard
- `frontend/tailwind.config.ts` — Design tokens
- `frontend/app/globals.css` — Animation keyframes

---

## Success Criteria

- [ ] v0-sdk installed and helper script working
- [ ] Landing page has dark theme with animations
- [ ] Headline: "Stop chasing clients. Let them find you."
- [ ] Activity feed rotates notifications
- [ ] AI email typing demo works
- [ ] How It Works tabs auto-rotate
- [ ] Stats show 55%+, 12%+, <14 days
- [ ] User dashboard uses bento grid
- [ ] Admin dashboard has command center design
- [ ] All ALS displays show correct tiers (85+ = Hot)
- [ ] Spots remaining is dynamic
- [ ] Mobile responsive
- [ ] No console errors
- [ ] Lighthouse performance >80

---

## Claude Code Kickoff

See `prompts/PHASE_21_KICKOFF.md` for ready-to-use prompt.
