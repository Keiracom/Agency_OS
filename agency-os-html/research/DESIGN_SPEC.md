# Agency OS Premium Dashboard Design Specification
## Version 2.0 — "Command Center"

**Created:** 2026-02-03  
**Design Philosophy:** "Bloomberg Terminal meets Linear"  
**Target Emotion:** Power, Control, Sophistication

---

## Executive Summary

This specification transforms Agency OS from a standard SaaS dashboard into a **premium command center** that justifies $2,500-$7,500/month pricing. The design emphasizes our 6 competitive moats through deliberate visual storytelling.

**Core Principles:**
1. **Dark mode default** — Professional, focused, data-forward
2. **Information density with clarity** — Show more without overwhelming
3. **Power user first** — Keyboard shortcuts, command palette
4. **Moat visualization** — Make unique capabilities impossible to miss
5. **Kitchen vs Table** — Outcomes only, never internals

---

## 1. Visual Identity System

### 1.1 Color Palette — Dark Mode (Default)

```css
/* ═══════════════════════════════════════════════════════════════
   AGENCY OS DARK THEME — "Obsidian"
   ═══════════════════════════════════════════════════════════════ */

/* Base Layers */
--bg-void:          #05050A;    /* Deepest background, page level */
--bg-base:          #0A0A12;    /* Primary background */
--bg-surface:       #12121D;    /* Cards, elevated surfaces */
--bg-surface-hover: #1A1A28;    /* Hover state for surfaces */
--bg-elevated:      #222233;    /* Modals, dropdowns */

/* Borders & Dividers */
--border-subtle:    #1E1E2E;    /* Subtle card borders */
--border-default:   #2A2A3D;    /* Default borders */
--border-strong:    #3A3A50;    /* Emphasized borders */

/* Text Hierarchy */
--text-primary:     #F8F8FC;    /* Primary text, headings */
--text-secondary:   #B4B4C4;    /* Body text, descriptions */
--text-muted:       #6E6E82;    /* Captions, timestamps */
--text-disabled:    #4A4A5C;    /* Disabled states */

/* Brand & Accent */
--accent-primary:   #7C3AED;    /* Purple — premium, innovation */
--accent-primary-hover: #9061F9;
--accent-primary-muted: rgba(124, 58, 237, 0.15);

--accent-teal:      #14B8A6;    /* Growth, positive trends */
--accent-teal-muted: rgba(20, 184, 166, 0.15);

--accent-blue:      #3B82F6;    /* Trust, information */
--accent-blue-muted: rgba(59, 130, 246, 0.15);

/* Status Colors */
--status-success:   #22C55E;    /* Green — positive, complete */
--status-success-muted: rgba(34, 197, 94, 0.15);

--status-warning:   #F59E0B;    /* Amber — attention needed */
--status-warning-muted: rgba(245, 158, 11, 0.15);

--status-error:     #EF4444;    /* Red — error, critical */
--status-error-muted: rgba(239, 68, 68, 0.15);

/* Data Visualization Palette */
--data-1:           #7C3AED;    /* Primary series */
--data-2:           #3B82F6;    /* Secondary series */
--data-3:           #14B8A6;    /* Tertiary series */
--data-4:           #F59E0B;    /* Quaternary series */
--data-5:           #EC4899;    /* Pink for contrast */

/* Tier Colors */
--tier-hot:         #EF4444;    /* 85-100 */
--tier-hot-bg:      rgba(239, 68, 68, 0.1);
--tier-warm:        #F59E0B;    /* 60-84 */
--tier-warm-bg:     rgba(245, 158, 11, 0.1);
--tier-cool:        #3B82F6;    /* 35-59 */
--tier-cool-bg:     rgba(59, 130, 246, 0.1);
--tier-cold:        #6B7280;    /* 20-34 */
--tier-cold-bg:     rgba(107, 114, 128, 0.1);

/* Gradients */
--gradient-premium: linear-gradient(135deg, #7C3AED 0%, #3B82F6 100%);
--gradient-success: linear-gradient(135deg, #14B8A6 0%, #22C55E 100%);
--gradient-surface: linear-gradient(180deg, #12121D 0%, #0A0A12 100%);
```

### 1.2 Color Palette — Light Mode (Optional)

```css
/* ═══════════════════════════════════════════════════════════════
   AGENCY OS LIGHT THEME — "Pearl"
   ═══════════════════════════════════════════════════════════════ */

--bg-void:          #F4F4F8;
--bg-base:          #FAFAFC;
--bg-surface:       #FFFFFF;
--bg-surface-hover: #F8F8FC;
--bg-elevated:      #FFFFFF;

--border-subtle:    #F0F0F4;
--border-default:   #E5E5EB;
--border-strong:    #D1D1DB;

--text-primary:     #111827;
--text-secondary:   #4B5563;
--text-muted:       #9CA3AF;
--text-disabled:    #D1D5DB;

/* Accents remain the same */
```

---

## 2. Typography System

### 2.1 Font Stack

```css
/* Primary UI Font */
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

/* Data & Monospace */
--font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', 'Consolas', monospace;

/* Display (Optional - for hero numbers) */
--font-display: 'Inter', var(--font-sans);
```

### 2.2 Typography Scale

| Token | Size | Weight | Line Height | Use Case |
|-------|------|--------|-------------|----------|
| `--text-display` | 56px | 800 | 1.0 | Hero metrics |
| `--text-h1` | 32px | 700 | 1.2 | Page titles |
| `--text-h2` | 24px | 600 | 1.25 | Section headers |
| `--text-h3` | 18px | 600 | 1.3 | Card titles |
| `--text-body` | 14px | 400 | 1.5 | Body text |
| `--text-body-sm` | 13px | 400 | 1.5 | Dense content |
| `--text-caption` | 12px | 500 | 1.4 | Labels, captions |
| `--text-micro` | 11px | 500 | 1.3 | Tags, badges |
| `--text-data` | 13px | 400 | 1.4 | Tables, numbers (mono) |

### 2.3 Typography Classes

```css
/* Display — Hero metrics */
.text-display {
  font: 800 56px/1.0 var(--font-display);
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

/* Numbers should always use tabular figures */
.text-number {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* Uppercase labels */
.text-label {
  font: 500 11px/1.3 var(--font-sans);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
```

---

## 3. Spacing System

### 3.1 Base Scale (4px increments)

```css
--space-0:  0;
--space-1:  4px;     /* Micro spacing */
--space-2:  8px;     /* Tight spacing */
--space-3:  12px;    /* Default padding */
--space-4:  16px;    /* Card padding */
--space-5:  20px;    /* Section padding */
--space-6:  24px;    /* Component gaps */
--space-8:  32px;    /* Section gaps */
--space-10: 40px;    /* Major sections */
--space-12: 48px;    /* Page margins */
--space-16: 64px;    /* Hero spacing */
```

### 3.2 Container Widths

```css
--container-sm:  640px;
--container-md:  768px;
--container-lg:  1024px;
--container-xl:  1280px;
--container-2xl: 1536px;
```

---

## 4. Shadow & Depth System

### 4.1 Elevation Layers

```css
/* Level 0 — Flat */
--shadow-none: none;

/* Level 1 — Subtle lift */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3),
             0 1px 3px rgba(0, 0, 0, 0.2);

/* Level 2 — Cards */
--shadow-md: 0 2px 4px rgba(0, 0, 0, 0.3),
             0 4px 8px rgba(0, 0, 0, 0.2);

/* Level 3 — Hover/Focus */
--shadow-lg: 0 4px 8px rgba(0, 0, 0, 0.3),
             0 8px 16px rgba(0, 0, 0, 0.2);

/* Level 4 — Modals, Dropdowns */
--shadow-xl: 0 8px 16px rgba(0, 0, 0, 0.4),
             0 16px 32px rgba(0, 0, 0, 0.3);

/* Glow effects for accents */
--glow-purple: 0 0 20px rgba(124, 58, 237, 0.4);
--glow-teal:   0 0 20px rgba(20, 184, 166, 0.4);
--glow-success: 0 0 20px rgba(34, 197, 94, 0.4);
```

### 4.2 Border Radius

```css
--radius-sm:   4px;   /* Buttons, inputs */
--radius-md:   8px;   /* Cards */
--radius-lg:   12px;  /* Large cards */
--radius-xl:   16px;  /* Hero elements */
--radius-2xl:  24px;  /* Featured cards */
--radius-full: 9999px; /* Pills, avatars */
```

---

## 5. Layout Architecture

### 5.1 Grid System

**Desktop (≥1280px):**
- 12-column grid
- 24px gutters
- 48px page margins
- Sidebar: 72px collapsed, 260px expanded

**Tablet (768px - 1279px):**
- 8-column grid
- 16px gutters
- 24px page margins
- Sidebar: collapsed by default

**Mobile (< 768px):**
- 4-column grid
- 16px gutters
- 16px page margins
- Bottom navigation

### 5.2 Information Density Zones

```
┌─────────────────────────────────────────────────────────────────────────┐
│ HEADER — Low density, navigation focused                                │
├──────┬──────────────────────────────────────────────────────────────────┤
│      │                                                                  │
│  S   │  HERO ZONE — Medium density, key metrics                        │
│  I   │  (Meetings booked, pipeline value, conversion rates)            │
│  D   │                                                                  │
│  E   ├──────────────────────────────────────────────────────────────────┤
│  B   │                                                                  │
│  A   │  PRIMARY ZONE — High density, actionable data                    │
│  R   │  (Hot leads, upcoming meetings, recent activity)                │
│      │                                                                  │
│  L   ├──────────────────────────────────────────────────────────────────┤
│  O   │                                                                  │
│  W   │  INSIGHTS ZONE — Medium density, intelligence                    │
│      │  (What's working, channel performance, AI discoveries)          │
│  D   │                                                                  │
│  E   ├──────────────────────────────────────────────────────────────────┤
│  N   │                                                                  │
│  S   │  SECONDARY ZONE — Variable density, detailed analytics           │
│  I   │  (Voice AI performance, SMS threads, infrastructure health)     │
│  T   │                                                                  │
│  Y   │                                                                  │
└──────┴──────────────────────────────────────────────────────────────────┘
```

### 5.3 Responsive Breakpoints

```css
/* Mobile First */
@media (min-width: 640px)  { /* sm - Tablet portrait */ }
@media (min-width: 768px)  { /* md - Tablet landscape */ }
@media (min-width: 1024px) { /* lg - Desktop small */ }
@media (min-width: 1280px) { /* xl - Desktop */ }
@media (min-width: 1536px) { /* 2xl - Desktop large */ }
```

---

## 6. Hero Components — "WOW" Elements

### 6.1 Main Metric Hero Card

**Purpose:** Immediately communicate success (meetings booked)

**Design:**
```
┌────────────────────────────────────────────────────────────────────────┐
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │ ← Gradient top accent
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   MEETINGS THIS MONTH                                                  │
│                                                                        │
│   ██╗██████╗                    ┌─────────────────────────┐           │
│   ██║╚════██╗                   │       RADIAL GAUGE      │           │
│   ██║ █████╔╝                   │         120%            │           │
│   ██║██╔═══╝                    │    Target Exceeded      │           │
│   ██║███████╗                   └─────────────────────────┘           │
│   ╚═╝╚══════╝                                                         │
│                                                                        │
│   Goal: 10 • Target hit 3 days early ✓                                │
│                                                                        │
│   ─────────────────────────────────────────────────────────────────── │
│   📈 ↑ 25% vs last month • Strong momentum                            │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

**Specifications:**
- Hero number: 72px, font-weight 800, tabular-nums
- Gradient accent bar: 3px, `--gradient-premium`
- Gauge: SVG radial, animated on load
- Card background: `--bg-surface` with subtle gradient
- Shadow: `--shadow-md`

### 6.2 Lead Scoring Radar Chart — "Lead DNA"

**Purpose:** Visualize WHY a lead is hot (our unique 7-signal scoring)

**Design:**
```
┌─────────────────────────────────────────────────────────────────────┐
│ 🧬 Lead Intelligence                                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│         Data Quality                                                │
│              ████ 18/20                                             │
│             ╱    ╲                                                   │
│    Risk    ╱      ╲   Authority                                      │
│    ███    ╱ RADAR  ╲  █████ 25/25                                    │
│   12/15  ╱  CHART   ╲                                                │
│          ╲          ╱                                                │
│           ╲        ╱   Company Fit                                   │
│            ╲      ╱    █████ 22/25                                   │
│             ╲    ╱                                                   │
│              Timing                                                 │
│              ████ 15/15                                              │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  🚀 SCORE BOOSTERS:                                                 │
│  [👑 Executive]  [🆕 New Role]  [📈 Company Hiring]                 │
│  [🔗 LinkedIn Active]  [💰 Buyer Signal]                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Specifications:**
- SVG radar chart with animated fill
- 5 axes: Data Quality, Authority, Company Fit, Timing, Risk
- Booster badges: pill-shaped, icon + text
- Colors: `--accent-primary` for filled area, `--border-default` for axes

### 6.3 Channel Orchestration Wheel

**Purpose:** Show multi-channel sophistication (our 5-channel moat)

**Design:**
```
┌─────────────────────────────────────────────────────────────────────┐
│ ⚡ Channel Orchestration                         Active: 5/5        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                      📮 Direct Mail                                 │
│                           │                                         │
│                    ╭──────┴──────╮                                  │
│                    │             │                                  │
│              📞    │             │    💬                            │
│             Voice  │    🎯 92    │   SMS                            │
│                    │    LEAD     │                                  │
│                    │             │                                  │
│                    ╰──────┬──────╯                                  │
│                           │                                         │
│               🔗 ─────────┴───────── 📧                             │
│            LinkedIn              Email                              │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Channel Status:                                                    │
│  📧 Email   ████████████████████ 1,247 touches                     │
│  🔗 LinkedIn ██████████████░░░░░░ 423 touches                       │
│  📞 Voice   ████████░░░░░░░░░░░░ 47 calls                          │
│  💬 SMS     ██████░░░░░░░░░░░░░░ 127 messages                       │
│  📮 Mail    ██░░░░░░░░░░░░░░░░░░ 23 sent                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Specifications:**
- Circular diagram: SVG with animated segments
- Center score: large, bold, colored by tier
- Channel icons: emit/receive state animations
- Progress bars: colored by channel type

### 6.4 Voice AI Performance Card

**Purpose:** Showcase autonomous Voice AI (unique differentiator)

**Design:**
```
┌─────────────────────────────────────────────────────────────────────┐
│ 📞 Voice Outreach                                        Live 🟢    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐               │
│  │   47    │  │   31    │  │    8    │  │   26%   │               │
│  │  Calls  │  │ Connect │  │ Booked  │  │  Rate   │               │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘               │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Latest Calls:                                                      │
│                                                                     │
│  ✅ Sarah Chen — MEETING BOOKED                         3:12       │
│     "Interested in learning more about lead generation"            │
│     [▶ Listen] [📄 Transcript]                                     │
│                                                                     │
│  🔄 Mike Ross — FOLLOW-UP SCHEDULED                     1:45       │
│     "Not the right time, call back in Q2"                          │
│     [▶ Listen] [⏰ Feb 10]                                         │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  🧠 Common Objections Handled:                                      │
│  • "Using another agency" — 12 calls (8 recovered)                 │
│  • "Not the right time" — 8 calls (5 scheduled)                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Specifications:**
- Stats grid: 4 columns, large numbers
- Call list: outcome badges, duration, quick actions
- Objection stats: shows AI sophistication
- "Live" indicator: pulsing green dot

### 6.5 Conversion Intelligence Panel — "What's Working"

**Purpose:** Show self-learning AI (our 4-detector system)

**Design:**
```
┌─────────────────────────────────────────────────────────────────────┐
│ 🧠 What's Working                                     Updated: 2h   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────┐  ┌─────────────────────────┐          │
│  │ WHO CONVERTS BEST       │  │ WHAT MESSAGING WORKS    │          │
│  │                         │  │                         │          │
│  │ CEO/Founder    2.3x ↑   │  │ Pain Question   3.1x ↑  │          │
│  │ Marketing Dir  1.8x ↑   │  │ Case Study CTA  2.4x ↑  │          │
│  │ Head of Growth 1.5x ↑   │  │ Short Subject   1.9x ↑  │          │
│  └─────────────────────────┘  └─────────────────────────┘          │
│                                                                     │
│  ┌─────────────────────────┐  ┌─────────────────────────┐          │
│  │ WHEN TO REACH OUT       │  │ CHANNEL MIX THAT WINS   │          │
│  │                         │  │                         │          │
│  │ Best Day:  Tuesday      │  │ Email → LinkedIn  68%   │          │
│  │ Best Hour: 10am local   │  │ +SMS = +23% reply       │          │
│  │ Worst: Monday morning   │  │ +Voice = +41% book      │          │
│  └─────────────────────────┘  └─────────────────────────┘          │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  🔥 THIS WEEK'S DISCOVERY:                                          │
│  "Leads with 'Growth' in title convert 2.1x better.                │
│   System adjusting targeting automatically."                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Specifications:**
- 2x2 grid of insight cards
- Lift metrics: green with up arrows
- Discovery banner: highlight background, bold text
- "Updated" timestamp: shows freshness

---

## 7. Micro-interactions & Animation

### 7.1 Timing Guidelines

```css
--duration-instant: 100ms;   /* Micro-feedback */
--duration-fast:    150ms;   /* Button states */
--duration-normal:  200ms;   /* Default transitions */
--duration-slow:    300ms;   /* Complex animations */
--duration-slower:  500ms;   /* Page transitions */

--ease-out:    cubic-bezier(0.33, 1, 0.68, 1);      /* Decelerate */
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);     /* Smooth */
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);  /* Bounce */
```

### 7.2 Hover States

**Cards:**
```css
.card {
  transition: transform var(--duration-fast) var(--ease-out),
              box-shadow var(--duration-fast) var(--ease-out);
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}
```

**Buttons:**
```css
.btn {
  transition: all var(--duration-fast) var(--ease-out);
}
.btn:hover {
  background: var(--accent-primary-hover);
  transform: translateY(-1px);
}
.btn:active {
  transform: translateY(0);
}
```

### 7.3 Loading States

**Skeleton Screens:**
```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--bg-surface) 0%,
    var(--bg-surface-hover) 50%,
    var(--bg-surface) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

**Number Count-up:**
- Duration: 1000ms
- Easing: ease-out
- Start from 0, animate to final value

### 7.4 Celebration Moments

**Meeting Booked:**
```css
@keyframes celebrate {
  0% { transform: scale(1); }
  50% { transform: scale(1.1); }
  100% { transform: scale(1); }
}

.celebration {
  animation: celebrate 500ms var(--ease-spring);
}
```

**Confetti:** Trigger on goal achievement
- Particle count: 50-100
- Duration: 2000ms
- Colors: `--accent-primary`, `--accent-teal`, `--status-success`

### 7.5 Real-time Updates

**Pulse Animation (Live Indicator):**
```css
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.5); }
}

.live-dot {
  animation: pulse 2s infinite;
}
```

**Data Refresh:**
- Subtle flash on updated values
- Number transition: animate from old to new

---

## 8. Data Visualization Standards

### 8.1 Chart Styles

**General Principles:**
- Minimal gridlines (max 4-5 horizontal)
- No chart borders
- Data-ink ratio > 0.8
- Always include zero baseline for bar charts
- Smooth curves for line charts (tension: 0.4)

**Colors:**
```css
/* Sequential Data */
.chart-series-1 { color: var(--data-1); }  /* Purple */
.chart-series-2 { color: var(--data-2); }  /* Blue */
.chart-series-3 { color: var(--data-3); }  /* Teal */
.chart-series-4 { color: var(--data-4); }  /* Amber */

/* Status Data */
.chart-positive { color: var(--status-success); }
.chart-negative { color: var(--status-error); }
```

### 8.2 Number Formatting

```javascript
// Large numbers
1234 → "1,234"
12345 → "12.3K"
1234567 → "1.2M"

// Percentages
0.6834 → "68%"
0.0523 → "5.2%"

// Currency
4700 → "$4.7K"
47000 → "$47K"
470000 → "$470K"

// Durations
127 seconds → "2:07"
3672 seconds → "1h 1m"
```

### 8.3 Trend Indicators

**Up Trend:**
```html
<span class="trend trend-up">
  <svg>↑</svg> 23%
</span>
```
Color: `--status-success`

**Down Trend:**
```html
<span class="trend trend-down">
  <svg>↓</svg> 12%
</span>
```
Color: `--status-error`

**Neutral:**
```html
<span class="trend trend-neutral">
  — stable
</span>
```
Color: `--text-muted`

### 8.4 Sparklines

**Specifications:**
- Height: 32px
- Width: 80-120px
- Stroke width: 2px
- Fill: gradient from line color to transparent
- No axes or labels

---

## 9. Component Library

### 9.1 Cards

**Base Card:**
```css
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.card-header {
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-body {
  padding: var(--space-5);
}
```

**Stat Card:**
```html
<div class="stat-card">
  <div class="stat-value">68%</div>
  <div class="stat-label">Show Rate</div>
  <div class="stat-trend trend-up">↑ 5%</div>
</div>
```

### 9.2 Badges & Pills

**Tier Badge:**
```html
<span class="badge badge-hot">Hot</span>
<span class="badge badge-warm">Warm</span>
<span class="badge badge-cool">Cool</span>
<span class="badge badge-cold">Cold</span>
```

**Signal Badge:**
```html
<span class="signal-badge">
  <span class="signal-icon">👑</span>
  <span class="signal-text">Executive</span>
</span>
```

### 9.3 Buttons

**Primary:**
```html
<button class="btn btn-primary">Book Meeting</button>
```

**Ghost:**
```html
<button class="btn btn-ghost">View All →</button>
```

**Icon Button:**
```html
<button class="btn-icon" aria-label="Settings">
  <svg>...</svg>
</button>
```

### 9.4 Lists

**Lead List Item:**
```html
<div class="lead-item lead-item--hot">
  <div class="lead-avatar">SC</div>
  <div class="lead-info">
    <div class="lead-name">Sarah Chen</div>
    <div class="lead-company">Bloom Digital • Marketing Director</div>
    <div class="lead-signal">Opened 5 emails in 2 hours</div>
  </div>
  <div class="lead-score">
    <span class="score-value">94</span>
    <span class="score-label">Score</span>
  </div>
</div>
```

---

## 10. Accessibility Standards

### 10.1 Color Contrast

| Element | Minimum Ratio | Target Ratio |
|---------|---------------|--------------|
| Body text | 4.5:1 | 7:1 (AAA) |
| Large text | 3:1 | 4.5:1 |
| UI components | 3:1 | 4.5:1 |
| Focus indicators | 3:1 | 4.5:1 |

### 10.2 Focus States

All interactive elements must have visible focus:
```css
:focus-visible {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}
```

### 10.3 Keyboard Navigation

- Tab order follows visual hierarchy
- Escape closes modals/dropdowns
- Arrow keys navigate within components
- Enter/Space activate buttons

---

## 11. Implementation Checklist

### Phase 1: Core Visual System
- [ ] Dark mode color palette
- [ ] Typography scale
- [ ] Spacing system
- [ ] Shadow system
- [ ] Border radius tokens

### Phase 2: Layout
- [ ] Grid system
- [ ] Responsive breakpoints
- [ ] Sidebar navigation
- [ ] Header component

### Phase 3: Hero Components
- [ ] Main metric hero card
- [ ] Lead DNA radar chart
- [ ] Channel orchestration wheel
- [ ] Voice AI performance card
- [ ] What's Working panel

### Phase 4: Data Visualization
- [ ] Sparklines
- [ ] Radial gauges
- [ ] Trend indicators
- [ ] Number animations

### Phase 5: Micro-interactions
- [ ] Hover states
- [ ] Loading skeletons
- [ ] Celebration moments
- [ ] Real-time updates

### Phase 6: Polish
- [ ] Accessibility audit
- [ ] Performance optimization
- [ ] Browser testing
- [ ] Mobile responsive

---

*This design specification ensures Agency OS dashboard conveys premium value and showcases our unique competitive moats.*
