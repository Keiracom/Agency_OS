# SKILL.md — Phase 21: Landing Page + UI Overhaul

**Skill:** Phase 21 UI Design System & Implementation  
**Author:** Dave + Claude  
**Version:** 1.0  
**Created:** January 5, 2026  
**Phase:** 21  
**Specification:** `PROGRESS.md` (Phase 21 section)

---

## Purpose

Overhaul the Agency OS frontend with a "Bloomberg Terminal" aesthetic - high information density, dark theme, professional SaaS appearance. This includes:
1. Landing page with animations and social proof
2. User dashboard with bento grid layout
3. Admin dashboard with command center design

**Core Philosophy:** Dense, data-rich interfaces that convey professionalism and capability.

---

## Prerequisites

- Phase 17-19 tasks in progress
- v0-sdk installed (see `skills/frontend/V0_SKILL.md`)
- V0_API_KEY configured in `config/.env`
- Existing frontend at `frontend/`
- Shadcn/ui initialized
- Tremor available for charts

---

## Design System

### Color Palette

```css
/* Backgrounds */
--bg-primary: #0a0a0f;        /* Main background */
--bg-secondary: #0f0f13;      /* Card backgrounds */
--bg-tertiary: #1a1a1f;       /* Elevated elements */

/* Glass morphism */
--glass-bg: rgba(255, 255, 255, 0.05);
--glass-border: rgba(255, 255, 255, 0.1);
--glass-blur: 20px;

/* Text */
--text-primary: #ffffff;
--text-secondary: rgba(255, 255, 255, 0.7);
--text-tertiary: rgba(255, 255, 255, 0.5);
--text-muted: rgba(255, 255, 255, 0.3);

/* Accent gradients */
--gradient-primary: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
--gradient-cta: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #a855f7 100%);

/* Status colors */
--status-success: #22c55e;
--status-warning: #f59e0b;
--status-error: #ef4444;
--status-info: #3b82f6;

/* ALS Score colors */
--als-hot: linear-gradient(90deg, #f97316, #ef4444);      /* 85-100 */
--als-warm: linear-gradient(90deg, #eab308, #f97316);     /* 60-84 */
--als-cool: #3b82f6;                                       /* 35-59 */
--als-cold: #6b7280;                                       /* 20-34 */
--als-dead: #374151;                                       /* <20 */
```

### Typography

```css
/* Font family */
font-family: 'Inter', system-ui, -apple-system, sans-serif;

/* Scale */
--text-xs: 0.75rem;      /* 12px - Labels, badges */
--text-sm: 0.875rem;     /* 14px - Body small, table cells */
--text-base: 1rem;       /* 16px - Body default */
--text-lg: 1.125rem;     /* 18px - Subheadings */
--text-xl: 1.25rem;      /* 20px - Card titles */
--text-2xl: 1.5rem;      /* 24px - Section headings */
--text-3xl: 1.875rem;    /* 30px - Page titles */
--text-4xl: 2.25rem;     /* 36px - Hero subheading */
--text-5xl: 3rem;        /* 48px - Hero heading mobile */
--text-6xl: 3.75rem;     /* 60px - Hero heading tablet */
--text-7xl: 4.5rem;      /* 72px - Hero heading desktop */

/* Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### Spacing (Compact Mode)

```css
/* Base unit: 4px */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */

/* Card padding */
--card-padding: var(--space-4);           /* Standard: 16px */
--card-padding-compact: var(--space-3);   /* Compact: 12px */

/* Table row padding */
--table-row-padding: var(--space-2) var(--space-3);  /* py-2 px-3 */
```

### Border Radius

```css
/* Maximum border radius: 8px (no pills except badges) */
--radius-sm: 4px;     /* Small elements */
--radius-md: 6px;     /* Buttons, inputs */
--radius-lg: 8px;     /* Cards, modals */
--radius-full: 9999px; /* Badges, pills only */
```

### Shadows & Effects

```css
/* Glass morphism card */
.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
}

/* Elevated card */
.elevated-card {
  background: #0f0f13;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
}

/* Glow effect for CTAs */
.glow-primary {
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
}

/* Gradient border */
.gradient-border {
  position: relative;
  background: linear-gradient(#0a0a0f, #0a0a0f) padding-box,
              linear-gradient(135deg, #3b82f6, #8b5cf6) border-box;
  border: 1px solid transparent;
}
```

### Animations

```css
/* Fade up on load */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Pulse for live indicators */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Slide in for activity items */
@keyframes slideIn {
  from { opacity: 0; transform: translateX(-10px); }
  to { opacity: 1; transform: translateX(0); }
}

/* Typing cursor blink */
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* Stagger delays */
.fade-up { animation: fadeUp 0.6s ease-out forwards; }
.fade-up-delay-1 { animation: fadeUp 0.6s ease-out 0.1s forwards; opacity: 0; }
.fade-up-delay-2 { animation: fadeUp 0.6s ease-out 0.2s forwards; opacity: 0; }
.fade-up-delay-3 { animation: fadeUp 0.6s ease-out 0.3s forwards; opacity: 0; }
```

---

## Component Specifications

### 1. Stats Card

```typescript
interface StatsCardProps {
  title: string;
  value: string | number;
  change?: {
    value: string;
    trend: 'up' | 'down' | 'neutral';
  };
  icon?: React.ReactNode;
  color?: 'blue' | 'green' | 'purple' | 'orange';
}

// Usage
<StatsCard
  title="Pipeline Value"
  value="$284K"
  change={{ value: "+23% this month", trend: "up" }}
  icon={<DollarSign />}
  color="green"
/>
```

**Visual spec:**
- Background: glass-card
- Padding: 16px
- Title: text-xs, text-tertiary, uppercase, tracking-wider
- Value: text-2xl or text-3xl, font-bold, text-primary
- Change: text-xs, color based on trend (green up, red down)
- Icon: 20x20, positioned top-right, color-matched

### 2. Activity Feed

```typescript
interface ActivityItem {
  id: string;
  channel: 'email' | 'linkedin' | 'sms' | 'voice' | 'mail';
  action: string;
  name: string;
  timestamp: Date;
  status?: 'success' | 'pending' | 'failed';
}

interface ActivityFeedProps {
  items: ActivityItem[];
  maxVisible?: number;      // Default 5
  autoRotate?: boolean;     // Default true
  rotateInterval?: number;  // Default 3000ms
}
```

**Visual spec:**
- Container: glass-card, no padding (items have padding)
- Header: "Live Activity" with pulsing green dot
- Items: py-3 px-4, border-b border-white/5
- Icon: Channel icon, color-coded (email=blue, linkedin=blue, sms=purple, voice=green, mail=orange)
- Text: action text truncated, name bold
- Time: text-xs, text-muted, relative ("2s ago")
- Animation: New items slide in from top, old items fade out

### 3. ALS Distribution

```typescript
interface ALSDistributionProps {
  data: {
    hot: number;    // 85-100
    warm: number;   // 60-84
    cool: number;   // 35-59
    cold: number;   // 20-34
    dead?: number;  // <20 (optional)
  };
  showLabels?: boolean;
}
```

**Visual spec:**
- Title: "ALS Score™ Distribution"
- Each tier row:
  - Label left (tier name + range)
  - Count right
  - Progress bar below, gradient fill
- Progress bar heights: 8px
- Colors: Use --als-* variables
- **CRITICAL:** Tiers must match codebase:
  - Hot: 85-100 (NOT 80-100)
  - Warm: 60-84
  - Cool: 35-59
  - Cold: 20-34
  - Dead: <20

### 4. Bento Grid Layout

```typescript
interface BentoGridProps {
  children: React.ReactNode;
  columns?: 2 | 3 | 4;
  gap?: 'sm' | 'md' | 'lg';
}

// Usage
<BentoGrid columns={4} gap="md">
  <StatsCard ... />  {/* Spans 1 */}
  <StatsCard ... />  {/* Spans 1 */}
  <StatsCard ... />  {/* Spans 1 */}
  <StatsCard ... />  {/* Spans 1 */}
  <ActivityFeed className="col-span-2 row-span-2" />
  <ALSDistribution className="col-span-2" />
</BentoGrid>
```

**CSS Grid spec:**
```css
.bento-grid {
  display: grid;
  gap: var(--space-4);
}

.bento-grid-4 {
  grid-template-columns: repeat(4, 1fr);
}

/* Responsive */
@media (max-width: 1024px) {
  .bento-grid-4 { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 640px) {
  .bento-grid-4 { grid-template-columns: 1fr; }
}
```

### 5. Interactive Tabs (How It Works)

```typescript
interface TabItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}

interface HowItWorksTabsProps {
  tabs: TabItem[];
  autoRotate?: boolean;
  rotateInterval?: number;  // Default 6000ms
}
```

**Visual spec:**
- Tab bar: horizontal, glass background, gradient indicator on active
- Tab buttons: px-4 py-2, text-sm, inactive=text-tertiary, active=text-primary
- Content area: fade transition between tabs
- Step number: Badge with "01", "02", etc.
- Auto-rotate: Pause on hover/click, resume after 10s inactivity

### 6. Typing Demo

```typescript
interface TypingDemoProps {
  email: {
    to: string;
    subject: string;
    body: string;
  };
  typingSpeed?: number;     // Base ms per char, default 30
  pauseOnPunctuation?: boolean;  // Default true
  restartDelay?: number;    // Ms before restart, default 5000
}
```

**Visual spec:**
- Container: glass-card, email compose UI style
- Header: To/Subject fields (static)
- Body: Typewriter effect with blinking cursor
- Indicator: "AI is writing..." with pulsing dot
- Variable speed: Pause 150ms at periods, 100ms at commas

---

## Page Specifications

### Landing Page (`frontend/app/page.tsx`)

**Sections:**
1. **Hero**
   - Headline: "Stop chasing clients. Let them find you." (gradient text)
   - Subheadline: "Five channels. Fully automated. One platform."
   - Badge: "Only {remaining} of 20 founding spots remaining" (pulsing dot)
   - CTAs: "See It In Action" (primary), "How it works →" (secondary)
   - Background: Gradient orbs, subtle animation

2. **Social Proof Bar**
   - Stats: "55%+ open rate", "12%+ reply rate", "<14 days to first meeting", "5 channels"
   - Horizontal layout, separator dots

3. **Live Demo Section**
   - Activity Feed (left)
   - AI Email Typing Demo (right)

4. **How It Works**
   - Interactive tabs: Discover → Find → Score → Reach → Convert
   - Auto-rotate every 6 seconds

5. **Features Comparison**
   - Keep existing "Generic AI SDRs vs Agency OS" table
   - 3 feature cards: Australian-First, Conversion Intelligence, ALS Score™

6. **ROI Comparison**
   - Keep existing "Agency OS vs Junior SDR" section
   - Year 1 comparison boxes
   - Savings highlight: "$54K + 2.2x meetings"

7. **Pricing**
   - 3 tier cards with meeting estimates
   - Keep existing structure, ensure ALS tiers correct

8. **CTA Section**
   - Waitlist form: Email + Agency Name
   - Dynamic spots remaining

### User Dashboard (`frontend/app/dashboard/page.tsx`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar  │  Header with search + notifications             │
│           ├─────────────────────────────────────────────────│
│           │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
│           │  │Pipeline│ │Meetings│ │ Reply  │ │ Active │   │
│           │  │ $284K  │ │   47   │ │ 12.4%  │ │ 2,847  │   │
│           │  └────────┘ └────────┘ └────────┘ └────────┘   │
│           │                                                 │
│           │  ┌─────────────────────┐ ┌──────────────────┐  │
│           │  │   Activity Feed     │ │ ALS Distribution │  │
│           │  │   (live updates)    │ │   Hot: 127       │  │
│           │  │                     │ │   Warm: 892      │  │
│           │  │                     │ │   Cool: 456      │  │
│           │  └─────────────────────┘ └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Data connections:**
- Pipeline: Sum of opportunities × probability
- Meetings: Count of `meetings` where `status = 'booked'`
- Reply Rate: (Replied leads / Contacted leads) × 100
- Active Leads: Count of leads in active campaigns
- Activity Feed: Real-time from `activities` table
- ALS Distribution: Group by `als_tier`

### Admin Dashboard (`frontend/app/admin/page.tsx`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar  │  COMMAND CENTER                    System: ●●●● │
│           ├─────────────────────────────────────────────────│
│           │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
│           │  │Clients │ │  MRR   │ │ Emails │ │ Health │   │
│           │  │   47   │ │$58,750 │ │124,847 │ │  All ● │   │
│           │  └────────┘ └────────┘ └────────┘ └────────┘   │
│           │                                                 │
│           │  ┌─────────────────────┐ ┌──────────────────┐  │
│           │  │   Client Table      │ │ Revenue by Tier  │  │
│           │  │   (compact rows)    │ │   [Donut Chart]  │  │
│           │  │                     │ ├──────────────────┤  │
│           │  │                     │ │ Platform Activity│  │
│           │  └─────────────────────┘ └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Data connections:**
- Total Clients: Count of `clients` where `status = 'active'`
- MRR: Sum of `clients.mrr`
- Platform Emails: Sum of `activities` where `type = 'email_sent'`
- System Health: From `/api/v1/health` endpoint
- Client Table: From `/api/v1/admin/clients`
- Revenue Chart: Group by `clients.tier`, sum `mrr`

---

## Required Files

### New Components

| File | Purpose |
|------|---------|
| `frontend/components/landing/HeroSection.tsx` | Landing hero with animations |
| `frontend/components/landing/ActivityFeed.tsx` | Animated activity feed |
| `frontend/components/landing/TypingDemo.tsx` | AI email typing animation |
| `frontend/components/landing/HowItWorksTabs.tsx` | Interactive process tabs |
| `frontend/components/landing/SocialProofBar.tsx` | Stats bar |
| `frontend/components/dashboard/BentoGrid.tsx` | Grid layout component |
| `frontend/components/dashboard/StatsCard.tsx` | Metric card |
| `frontend/components/dashboard/ActivityFeed.tsx` | Dashboard activity feed |
| `frontend/components/dashboard/ALSDistribution.tsx` | Score distribution chart |
| `frontend/components/admin/AdminGrid.tsx` | Admin bento layout |
| `frontend/components/admin/ClientTable.tsx` | Compact client list |
| `frontend/components/admin/RevenueChart.tsx` | Tier revenue donut |

### Modified Files

| File | Changes |
|------|---------|
| `frontend/app/page.tsx` | Replace with new landing page |
| `frontend/app/dashboard/page.tsx` | Replace with bento grid layout |
| `frontend/app/admin/page.tsx` | Replace with command center |
| `frontend/tailwind.config.ts` | Add design system tokens |
| `frontend/app/globals.css` | Add animation keyframes |

---

## Implementation Order

### Phase 21A: Setup (V0-001, V0-002)
1. Install v0-sdk
2. Create helper script
3. Add design system tokens to Tailwind config
4. Add animation keyframes to globals.css

### Phase 21B: Landing Page (V0-003, LP-001 to LP-005)
1. Generate HeroSection via v0
2. Generate ActivityFeed via v0
3. Generate TypingDemo via v0
4. Generate HowItWorksTabs via v0
5. Integrate into page.tsx
6. Update stats to hardcoded values (55%+, 12%+, <14 days)
7. Test animations and responsive behavior

### Phase 21C: User Dashboard (V0-004, LP-010, LP-012)
1. Generate dashboard components via v0
2. Integrate into dashboard/page.tsx
3. Fix ALS tier displays (85+ = Hot)
4. Wire up real data connections
5. Test data refresh and loading states

### Phase 21D: Admin Dashboard (V0-004)
1. Generate admin components via v0
2. Integrate into admin/page.tsx
3. Wire up admin API endpoints
4. Test with real client data

### Phase 21E: Polish (LP-011)
1. Make spots remaining dynamic
2. Add loading skeletons
3. Test mobile responsiveness
4. Verify no console errors
5. Performance audit (Lighthouse)

---

## ALS Tier Reference (CRITICAL)

**Always use these thresholds:**

| Tier | Score Range | Color | Display |
|------|-------------|-------|---------|
| Hot | 85-100 | Orange/Red gradient | "Hot (85-100)" |
| Warm | 60-84 | Yellow/Orange gradient | "Warm (60-84)" |
| Cool | 35-59 | Blue | "Cool (35-59)" |
| Cold | 20-34 | Gray | "Cold (20-34)" |
| Dead | <20 | Dark gray | "Dead (<20)" |

**Source:** `src/models/lead.py` lines 183-195

**Search and replace if wrong:**
- ❌ "Hot (80-100)" → ✅ "Hot (85-100)"
- ❌ "Warm (50-79)" → ✅ "Warm (60-84)"
- ❌ "Nurture (0-49)" → ✅ Split into Cool/Cold/Dead

---

## Success Criteria

Phase 21 is complete when:

- [ ] v0-sdk installed and helper script working
- [ ] Landing page has dark theme with animations
- [ ] Headline is "Stop chasing clients. Let them find you."
- [ ] Activity feed shows rotating notifications
- [ ] AI email typing demo works
- [ ] How It Works tabs auto-rotate
- [ ] Stats show 55%+, 12%+, <14 days
- [ ] User dashboard uses bento grid layout
- [ ] Admin dashboard has command center design
- [ ] All ALS displays show correct tiers (85+ = Hot)
- [ ] Spots remaining is dynamic or consistent
- [ ] Mobile responsive (stack on small screens)
- [ ] No console errors
- [ ] Lighthouse performance score >80

---

## QA Checklist

### Visual QA
- [ ] Dark theme applied consistently
- [ ] No white/light backgrounds leaking through
- [ ] Gradients render correctly
- [ ] Glass morphism blur effect visible
- [ ] Animations smooth (60fps)
- [ ] No layout shifts on load

### Functional QA
- [ ] Activity feed rotates correctly
- [ ] Typing demo types and restarts
- [ ] Tabs switch on click and auto-rotate
- [ ] Tabs pause on hover/interaction
- [ ] Waitlist form submits
- [ ] Dashboard data loads
- [ ] Admin data loads

### Responsive QA
- [ ] Desktop (1920px): Full layout
- [ ] Laptop (1440px): Full layout, smaller text
- [ ] Tablet (1024px): 2-column grid
- [ ] Mobile (375px): Single column, stacked

### Accessibility QA
- [ ] Focus states visible
- [ ] Color contrast passes WCAG AA
- [ ] Animations respect prefers-reduced-motion
- [ ] Screen reader text for icons

---
