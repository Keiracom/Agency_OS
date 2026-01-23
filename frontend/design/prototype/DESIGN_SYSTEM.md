# Dashboard Prototype Design System

**Purpose:** Design tokens and patterns for the Agency OS dashboard prototype.
**Based on:** Mockups in `frontend/design/dashboard/mockups/`

---

## Color Palette

### Primary Colors
```css
--sidebar-bg: #1E3A5F;           /* Dark navy sidebar */
--sidebar-border: #2D4A6F;       /* Sidebar borders */
--sidebar-active: #2563EB;       /* Active nav item */
--sidebar-text: #94A3B8;         /* Inactive nav text */
--sidebar-text-active: #FFFFFF;  /* Active nav text */
```

### Content Colors
```css
--content-bg: #F8FAFC;           /* Page background */
--card-bg: #FFFFFF;              /* Card background */
--card-border: #E2E8F0;          /* Card borders */
--card-shadow: 0 1px 3px rgba(0,0,0,0.1);
```

### Text Colors
```css
--text-primary: #1E293B;         /* Headings, values */
--text-secondary: #64748B;       /* Labels, descriptions */
--text-muted: #94A3B8;           /* Timestamps, hints */
```

### Accent Colors
```css
--accent-blue: #3B82F6;          /* Primary actions */
--accent-blue-hover: #2563EB;    /* Hover state */
--accent-green: #10B981;         /* Success, positive */
--accent-orange: #F97316;        /* Warning, warm */
--accent-red: #EF4444;           /* Error, hot */
--accent-purple: #8B5CF6;        /* AI suggested */
```

### ALS Tier Colors
```css
--tier-hot: #EF4444;             /* 85-100 */
--tier-warm: #F97316;            /* 60-84 */
--tier-cool: #3B82F6;            /* 35-59 */
--tier-cold: #6B7280;            /* 20-34 */
--tier-dead: #D1D5DB;            /* <20 */
```

### Channel Colors
```css
--channel-email: #3B82F6;        /* Blue */
--channel-sms: #10B981;          /* Green */
--channel-linkedin: #0077B5;     /* LinkedIn blue */
--channel-voice: #8B5CF6;        /* Purple */
--channel-mail: #F59E0B;         /* Amber */
```

---

## Typography

### Font Family
```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
```

### Font Sizes
```css
--text-xs: 0.75rem;    /* 12px - timestamps, badges */
--text-sm: 0.875rem;   /* 14px - labels, body small */
--text-base: 1rem;     /* 16px - body */
--text-lg: 1.125rem;   /* 18px - card titles */
--text-xl: 1.25rem;    /* 20px - section headers */
--text-2xl: 1.5rem;    /* 24px - page titles */
--text-3xl: 1.875rem;  /* 30px - large metrics */
--text-4xl: 2.25rem;   /* 36px - hero metrics */
```

### Font Weights
```css
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

---

## Spacing

```css
--space-1: 0.25rem;    /* 4px */
--space-2: 0.5rem;     /* 8px */
--space-3: 0.75rem;    /* 12px */
--space-4: 1rem;       /* 16px */
--space-5: 1.25rem;    /* 20px */
--space-6: 1.5rem;     /* 24px */
--space-8: 2rem;       /* 32px */
--space-10: 2.5rem;    /* 40px */
--space-12: 3rem;      /* 48px */
```

---

## Border Radius

```css
--radius-sm: 0.375rem;  /* 6px - small elements */
--radius-md: 0.5rem;    /* 8px - buttons, inputs */
--radius-lg: 0.75rem;   /* 12px - cards */
--radius-xl: 1rem;      /* 16px - large cards */
--radius-full: 9999px;  /* Pills, avatars */
```

---

## Shadows

```css
--shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
--shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1);
--shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1);
--shadow-blue: 0 4px 14px rgba(59,130,246,0.25);
```

---

## Component Patterns

### Card
```tsx
<div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
  <div className="px-6 py-4 border-b border-[#E2E8F0]">
    <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
      Section Title
    </h2>
  </div>
  <div className="p-6">
    {/* Content */}
  </div>
</div>
```

### KPI Card
```tsx
<div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-6">
  <div className="flex items-center justify-between mb-2">
    <span className="text-sm font-medium text-[#64748B]">Label</span>
    <Icon className="h-5 w-5 text-[#94A3B8]" />
  </div>
  <div className="text-3xl font-bold text-[#1E293B]">Value</div>
  <div className="flex items-center gap-1 mt-1 text-sm text-[#10B981]">
    <TrendingUp className="h-4 w-4" />
    <span>+5%</span>
  </div>
</div>
```

### Button Primary
```tsx
<button className="px-4 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white font-medium rounded-lg transition-colors shadow-lg shadow-blue-500/25">
  Button Text
</button>
```

### Badge
```tsx
<span className="px-2 py-0.5 rounded-full text-xs font-medium bg-[#DBEAFE] text-[#1D4ED8]">
  Badge
</span>
```

### Nav Item
```tsx
<a className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
  isActive
    ? "bg-[#2563EB] text-white shadow-lg shadow-blue-500/25"
    : "text-[#94A3B8] hover:text-white hover:bg-[#2D4A6F]"
}`}>
  <Icon className="h-5 w-5" />
  <span>Label</span>
</a>
```

---

## Layout Grid

### Sidebar Width
```css
--sidebar-width: 256px;  /* 16rem */
```

### Content Grid
```css
/* Dashboard home */
.hero-kpis { grid-template-columns: repeat(2, 1fr); }
.campaigns-section { grid-template-columns: 1fr; }
.activity-meetings { grid-template-columns: 2fr 1fr; }

/* Responsive */
@media (max-width: 1024px) {
  .activity-meetings { grid-template-columns: 1fr; }
}
```

---

## File Structure

```
frontend/design/prototype/
├── DESIGN_SYSTEM.md          <- This file
├── components/
│   ├── layout/
│   │   ├── DashboardShell.tsx
│   │   ├── Sidebar.tsx
│   │   └── Header.tsx
│   ├── dashboard/
│   │   ├── KPICard.tsx
│   │   ├── CampaignPriorityCard.tsx
│   │   ├── ActivityFeed.tsx
│   │   ├── MeetingsWidget.tsx
│   │   ├── ALSDistribution.tsx
│   │   └── OnTrackIndicator.tsx
│   ├── campaigns/
│   │   ├── CampaignList.tsx
│   │   ├── CampaignDetail.tsx
│   │   ├── CampaignNew.tsx
│   │   ├── PrioritySlider.tsx
│   │   ├── SequenceBuilder.tsx
│   │   └── CampaignMetrics.tsx
│   ├── leads/
│   │   ├── LeadList.tsx
│   │   ├── LeadDetail.tsx
│   │   ├── ALSScorecard.tsx
│   │   ├── LeadTimeline.tsx
│   │   └── LeadEnrichment.tsx
│   ├── replies/
│   │   └── ReplyInbox.tsx
│   ├── reports/
│   │   ├── ReportsPage.tsx
│   │   └── Charts.tsx
│   └── settings/
│       ├── SettingsHub.tsx
│       ├── ICPSettings.tsx
│       ├── LinkedInSettings.tsx
│       ├── ProfileSettings.tsx
│       └── NotificationSettings.tsx
└── pages/
    ├── DashboardHome.tsx
    ├── CampaignsPage.tsx
    ├── LeadsPage.tsx
    ├── RepliesPage.tsx
    ├── ReportsPage.tsx
    └── SettingsPage.tsx
```

---

## Features from Architecture

### Dashboard Home (`DASHBOARD.md`)
- [ ] Hero KPIs: Meetings Booked, Show Rate
- [ ] On Track indicator
- [ ] Campaign priority sliders (sum to 100%)
- [ ] Confirm & Activate button
- [ ] Live activity feed
- [ ] Upcoming meetings widget
- [ ] ALS distribution chart

### Campaigns (`CAMPAIGNS.md`)
- [ ] Campaign list with priority sliders
- [ ] AI Suggested badge
- [ ] Status badges (Active, Paused, Draft)
- [ ] Channel indicators
- [ ] Metrics: meetings, reply rate, show rate
- [ ] Campaign detail with tabs
- [ ] Sequence builder
- [ ] New campaign form

### Leads (`LEADS.md`)
- [ ] Lead list with tier filters
- [ ] ALS tier badges (Hot/Warm/Cool/Cold/Dead)
- [ ] Lead detail with contact/company info
- [ ] ALS breakdown chart
- [ ] Activity timeline
- [ ] Deep research card (Hot leads)
- [ ] Bulk actions

### Settings (`SETTINGS.md`)
- [ ] Settings hub with navigation cards
- [ ] ICP configuration form
- [ ] LinkedIn connection status
- [ ] Profile settings
- [ ] Notification preferences
- [ ] Emergency pause button

---

## Demo Data

All prototype components use static demo data. See individual component files for data structures.
