# Plasmic Dashboard Audit

**Purpose:** Complete audit of all dashboard features to build in Plasmic Studio
**Project ID:** sTVtoZDhkmD2Edyr9vqjyS
**Last Updated:** 2026-01-23

---

## Color Palette (From Mockups)

### Primary Colors
| Name | Hex | Usage |
|------|-----|-------|
| **Navy Sidebar** | `#1a2744` | Sidebar background |
| **Dark Card BG** | `#1a1a1f` | Dark mode cards |
| **Card White** | `#FFFFFF` | Light mode cards |
| **Page Background** | `#F5F7FA` | Light mode page bg |

### Accent Colors
| Name | Hex | Usage |
|------|-----|-------|
| **Primary Blue** | `#2196F3` | Links, buttons, active states |
| **Success Green** | `#4CAF50` | Positive metrics, +trends |
| **Warning Orange** | `#FF9800` | Warnings, attention |
| **Error Red** | `#F44336` | Negative metrics, errors |
| **Emerald Accent** | `#10B981` | Deals, conversions |

### Text Colors
| Name | Hex | Usage |
|------|-----|-------|
| **Heading Dark** | `#1F2937` | Main headings |
| **Body Text** | `#4B5563` | Body copy |
| **Muted Text** | `#9CA3AF` | Secondary info |
| **White Text** | `#FFFFFF` | On dark backgrounds |
| **White/60** | `rgba(255,255,255,0.6)` | Dark mode muted |

### ALS Tier Colors
| Tier | Hex | Background |
|------|-----|------------|
| **Hot** | `#EF4444` | `bg-red-500` |
| **Warm** | `#F97316` | `bg-orange-500` |
| **Cool** | `#3B82F6` | `bg-blue-500` |
| **Cold** | `#9CA3AF` | `bg-gray-400` |
| **Dead** | `#E5E7EB` | `bg-gray-200` |

---

## Component Inventory

### Status: BUILT (9 components)
These exist in codebase - import/sync to Plasmic:

| Component | File | Description |
|-----------|------|-------------|
| HeroMetricsCard | `components/dashboard/HeroMetricsCard.tsx` | Meetings + Show Rate cards |
| OnTrackIndicator | `components/dashboard/OnTrackIndicator.tsx` | Ahead/On Track/Behind badge |
| LiveActivityFeed | `components/dashboard/LiveActivityFeed.tsx` | Real-time activity list |
| EmergencyPauseButton | `components/dashboard/EmergencyPauseButton.tsx` | Pause all outreach |
| BestOfShowcase | `components/dashboard/BestOfShowcase.tsx` | Top performing content |
| MeetingsWidget | `components/dashboard/meetings-widget.tsx` | Upcoming meetings |
| ActivityTicker | `components/dashboard/ActivityTicker.tsx` | Bloomberg-style ticker |
| CapacityGauge | `components/dashboard/CapacityGauge.tsx` | Monthly usage gauge |
| CoPilotView | `components/dashboard/CoPilotView.tsx` | AI email assistant |

### Status: BUILT (8 campaign components)
| Component | File | Description |
|-----------|------|-------------|
| PrioritySlider | `components/campaigns/PrioritySlider.tsx` | Priority % slider |
| CampaignPriorityPanel | `components/campaigns/CampaignPriorityPanel.tsx` | Panel with all sliders |
| CampaignPriorityCard | `components/campaigns/CampaignPriorityCard.tsx` | Single campaign card |
| CampaignAllocationManager | `components/campaigns/CampaignAllocationManager.tsx` | Full allocation UI |
| SequenceBuilder | `components/campaigns/SequenceBuilder.tsx` | Edit sequences |
| CampaignMetricsPanel | `components/campaigns/CampaignMetricsPanel.tsx` | Campaign performance |
| CampaignTabs | `components/campaigns/CampaignTabs.tsx` | Tab navigation |
| PermissionModeSelector | `components/campaigns/permission-mode-selector.tsx` | Permission settings |

---

## Pages to Build in Plasmic

### Page 1: Dashboard Home (`/dashboard`)

**Layout:**
```
+------------------------------------------------------------------+
| HEADER: Logo | Search | Client Dropdown | Settings | Profile     |
+------------------------------------------------------------------+
|        |                                                          |
| SIDEBAR|  DASHBOARD                                               |
|        |  +-----------------------+  +-----------------------+   |
| [Home] |  | 12 Meetings Booked    |  | 85% Show Rate         |   |
| [Camp] |  | On track for 15-25    |  | +3 vs last month      |   |
| [Leads]|  | [Green: Ahead badge]  |  | 10 showed, 8 deals    |   |
| [Reply]|  +-----------------------+  +-----------------------+   |
| [Reprt]|                                                          |
| [Setng]|  +--------------------------------------------------+   |
|        |  | YOUR CAMPAIGNS                    [+ Add Campaign]|   |
|        |  |                                                   |   |
|        |  | Tech Decision Makers (AI)     ●━━━━━━━○──  40%   |   |
|        |  | 6 meetings | 3.8% reply                          |   |
|        |  |                                                   |   |
|        |  | Series A Startups (AI)        ○━━━━━●────  35%   |   |
|        |  | 4 meetings | 2.9% reply                          |   |
|        |  |                                                   |   |
|        |  | Total: 100%           [ Confirm & Activate ]     |   |
|        |  +--------------------------------------------------+   |
|        |                                                          |
|        |  +------------------------+  +------------------------+ |
|        |  | RECENT ACTIVITY   Live |  | UPCOMING MEETINGS      | |
|        |  | [Email] Sarah Chen..   |  | Today 2:00 PM          | |
|        |  | [Reply] Mike Johnson.. |  | Sarah Chen (Discovery) | |
|        |  | [Meeting] Lisa Park..  |  | Tomorrow 10 AM         | |
|        |  +------------------------+  +------------------------+ |
|        |                                                          |
|        |  +--------------------------------------------------+   |
|        |  | ALS DISTRIBUTION                                  |   |
|        |  | Hot [████] 15%  Warm [██████] 35%  Cool [████] 30%|   |
|        |  | Cold [██] 15%   Dead [█] 5%                       |   |
|        |  +--------------------------------------------------+   |
+------------------------------------------------------------------+
```

**Components Needed:**
1. **Sidebar** - Navigation with icons
2. **Header** - Logo, search, profile
3. **HeroMetricsSection** - 2-column hero cards
4. **CampaignPriorityPanel** - Sliders + confirm
5. **ActivityFeed** - Recent activity list
6. **MeetingsWidget** - Upcoming meetings
7. **ALSDistributionChart** - Tier breakdown bars

---

### Page 2: Campaign List (`/dashboard/campaigns`)

**Layout:**
```
+------------------------------------------------------------------+
| CAMPAIGNS                               [ + New Campaign ]        |
+------------------------------------------------------------------+
| Filter: [All] [Active] [Paused] [Draft]     Sort: [Priority v]   |
+------------------------------------------------------------------+
|                                                                   |
| +--------------------------------------------------------------+ |
| | CAMPAIGN CARD                                                 | |
| | Tech Decision Makers (AI)                          ACTIVE     | |
| | ○━━━━━━━━━━━━━━━●━━━━━━━━━━━○  Priority: 40%                 | |
| |                                                               | |
| | 6 meetings  |  3.8% reply  |  85% show rate                   | |
| | Channels: Email, LinkedIn                                     | |
| +--------------------------------------------------------------+ |
|                                                                   |
| +--------------------------------------------------------------+ |
| | Series A Startups (AI)                             ACTIVE     | |
| | ...                                                           | |
| +--------------------------------------------------------------+ |
|                                                                   |
+------------------------------------------------------------------+
```

---

### Page 3: Campaign Detail (`/dashboard/campaigns/[id]`)

**Layout:**
```
+------------------------------------------------------------------+
| <- Back to Campaigns    Tech Decision Makers         [Edit] [...]|
+------------------------------------------------------------------+
| [Overview] [Leads] [Sequences] [Settings]                        |
+------------------------------------------------------------------+
|                                                                   |
| +------------------------+  +------------------------+            |
| | 6 Meetings Booked      |  | 3.8% Reply Rate        |            |
| | This campaign          |  | 45 replies             |            |
| +------------------------+  +------------------------+            |
|                                                                   |
| SEQUENCE STEPS                                                    |
| +--------------------------------------------------------------+ |
| | Day 1: Email - Introduction                       [Edit]      | |
| | Day 3: LinkedIn - Connection Request              [Edit]      | |
| | Day 5: Email - Follow-up                          [Edit]      | |
| | Day 8: Phone - Discovery Call                     [Edit]      | |
| +--------------------------------------------------------------+ |
|                                                                   |
| ACTIVE SEQUENCES (89)                                             |
| +--------------------------------------------------------------+ |
| | Sarah Chen, TechCorp          Step 2 of 4    Due tomorrow    | |
| | Mike Johnson, StartupXYZ      Step 3 of 4    Pending reply   | |
| +--------------------------------------------------------------+ |
|                                                                   |
+------------------------------------------------------------------+
```

---

### Page 4: Leads List (`/dashboard/leads`)

**Layout:**
```
+------------------------------------------------------------------+
| LEADS                                        [ Import ] [ Export ]|
+------------------------------------------------------------------+
| Filter: [All Tiers v]  [All Campaigns v]  Search: [___________]  |
+------------------------------------------------------------------+
|                                                                   |
| [Hot] [Warm] [Cool] [Cold] [Dead] - Tier filter tabs             |
|                                                                   |
| TABLE                                                             |
| +--------------------------------------------------------------+ |
| | Name           | Company    | ALS | Campaign    | Status      | |
| |----------------|------------|-----|-------------|-------------| |
| | Sarah Chen     | TechCorp   | 92  | Tech DM     | In Sequence | |
| | Mike Johnson   | StartupXYZ | 78  | Series A    | Replied     | |
| | Lisa Park      | Acme Inc   | 85  | Tech DM     | Meeting     | |
| +--------------------------------------------------------------+ |
|                                                                   |
+------------------------------------------------------------------+
```

---

### Page 5: Lead Detail (`/dashboard/leads/[id]`)

**Layout:**
```
+------------------------------------------------------------------+
| <- Back    Sarah Chen                    [Add Note] [Send Email] |
|            VP Engineering at TechCorp                             |
+------------------------------------------------------------------+
|                                                                   |
| +------------------------+  +----------------------------------+  |
| | ALS SCORE              |  | CONTACT INFO                    |  |
| |                        |  | sarah@techcorp.com              |  |
| |    92  HOT             |  | +1 (555) 123-4567               |  |
| |    [Radar Chart]       |  | linkedin.com/in/sarahchen       |  |
| +------------------------+  +----------------------------------+  |
|                                                                   |
| ACTIVITY TIMELINE                                                 |
| +--------------------------------------------------------------+ |
| | Jan 23  Email sent - Introduction                             | |
| | Jan 24  Email opened (3x)                                     | |
| | Jan 25  LinkedIn connected                                    | |
| | Jan 26  Email replied - "Interested, let's chat"              | |
| | Jan 27  Meeting scheduled - Discovery call                    | |
| +--------------------------------------------------------------+ |
|                                                                   |
| CO-PILOT (AI Assistant)                                          |
| +--------------------------------------------------------------+ |
| | [Generated email draft based on lead context]                 | |
| | [Regenerate] [Edit] [Send]                                    | |
| +--------------------------------------------------------------+ |
|                                                                   |
+------------------------------------------------------------------+
```

---

### Page 6: Reply Inbox (`/dashboard/replies`)

**Layout:**
```
+------------------------------------------------------------------+
| REPLIES                          [Mark All Read] [Filter: All v] |
+------------------------------------------------------------------+
|                                                                   |
| +------------------+  +--------------------------------------+   |
| | REPLY LIST       |  | REPLY DETAIL                         |   |
| |                  |  |                                      |   |
| | [*] Sarah Chen   |  | From: Sarah Chen <sarah@techcorp.com>|   |
| |     Re: Quick... |  | Subject: Re: Quick question about... |   |
| |     2h ago       |  |                                      |   |
| |                  |  | Hi,                                  |   |
| | [ ] Mike Johnson |  |                                      |   |
| |     Thanks for...|  | This looks interesting. Can we       |   |
| |     Yesterday    |  | schedule a call next week?           |   |
| |                  |  |                                      |   |
| | [ ] Lisa Park    |  | Best,                                |   |
| |     Not interes..|  | Sarah                                |   |
| |     2 days ago   |  |                                      |   |
| |                  |  | [Reply] [Archive] [Mark Interested]  |   |
| +------------------+  +--------------------------------------+   |
|                                                                   |
+------------------------------------------------------------------+
```

---

### Page 7: Reports (`/dashboard/reports`)

**Layout:**
```
+------------------------------------------------------------------+
| REPORTS                           Period: [This Month v] [Export]|
+------------------------------------------------------------------+
|                                                                   |
| +------------------------+  +------------------------+            |
| | MEETINGS TREND         |  | REPLY RATE TREND       |            |
| | [Line Chart]           |  | [Line Chart]           |            |
| | 12 this month (+3)     |  | 3.8% (+0.5%)           |            |
| +------------------------+  +------------------------+            |
|                                                                   |
| CAMPAIGN PERFORMANCE                                              |
| +--------------------------------------------------------------+ |
| | Campaign            | Meetings | Reply Rate | Show Rate       | |
| |---------------------|----------|------------|-----------------|  |
| | Tech Decision Makers| 6        | 3.8%       | 85%             | |
| | Series A Startups   | 4        | 2.9%       | 90%             | |
| | My Custom Campaign  | 2        | 1.8%       | 100%            | |
| +--------------------------------------------------------------+ |
|                                                                   |
| CHANNEL EFFECTIVENESS                                             |
| +--------------------------------------------------------------+ |
| | Email: 3.2% reply  |  LinkedIn: 4.1% reply  |  Phone: 8.5%   | |
| +--------------------------------------------------------------+ |
|                                                                   |
+------------------------------------------------------------------+
```

---

### Page 8: Settings (`/dashboard/settings`)

**Layout:**
```
+------------------------------------------------------------------+
| SETTINGS                                                          |
+------------------------------------------------------------------+
| [General] [ICP] [LinkedIn] [Webhooks] [Billing]                  |
+------------------------------------------------------------------+
|                                                                   |
| GENERAL                                                           |
| +--------------------------------------------------------------+ |
| | Company Name:    [Acme Agency               ]                 | |
| | Timezone:        [Australia/Sydney      v   ]                 | |
| | Business Hours:  [9:00 AM] to [6:00 PM]                       | |
| +--------------------------------------------------------------+ |
|                                                                   |
| EMERGENCY CONTROLS                                                |
| +--------------------------------------------------------------+ |
| | [!!! PAUSE ALL OUTREACH !!!]                                  | |
| | Immediately stops all email, SMS, LinkedIn, and voice calls   | |
| +--------------------------------------------------------------+ |
|                                                                   |
| NOTIFICATIONS                                                     |
| +--------------------------------------------------------------+ |
| | [x] Daily digest email                                        | |
| | [x] New meeting notifications                                 | |
| | [ ] Weekly performance report                                 | |
| +--------------------------------------------------------------+ |
|                                                                   |
+------------------------------------------------------------------+
```

---

## Shared Components for Plasmic

### 1. Sidebar Navigation
```
- Logo (Agency OS)
- Nav Items:
  - Dashboard (home icon)
  - Campaigns (target icon)
  - Leads (users icon)
  - Replies (message icon)
  - Reports (chart icon)
  - Settings (gear icon)
- Active state: Blue bg, white text
- Hover state: Light blue bg
- Mobile: Hamburger menu
```

### 2. Header Bar
```
- Breadcrumb (optional)
- Client selector dropdown
- Search input
- Notifications bell
- Profile avatar + dropdown
```

### 3. KPI Card
```
Props:
- title: string
- value: number | string
- change: number (optional)
- icon: IconComponent
- variant: "default" | "success" | "warning" | "error"

Design:
+------------------------+
| [Icon] Title           |
|                        |
| 123 Large Value        |
| +5% vs last month      |
+------------------------+
```

### 4. Campaign Card
```
Props:
- name: string
- isAI: boolean
- priority: number (0-100)
- meetings: number
- replyRate: number
- status: "active" | "paused" | "draft"
- channels: string[]
```

### 5. Activity Item
```
Props:
- channel: "email" | "sms" | "linkedin" | "voice" | "meeting"
- leadName: string
- company: string
- action: string
- timestamp: Date
```

### 6. Meeting Item
```
Props:
- leadName: string
- company: string
- scheduledAt: Date
- type: "discovery" | "demo" | "follow_up"
- duration: number
```

### 7. ALS Badge
```
Props:
- score: number
- tier: "hot" | "warm" | "cool" | "cold" | "dead"
- size: "sm" | "md" | "lg"
```

---

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| `xl` (1280px+) | Sidebar visible, 3-column content |
| `lg` (1024px) | Sidebar visible, 2-column content |
| `md` (768px) | Sidebar collapsible, 2-column content |
| `sm` (< 768px) | Sidebar hidden (hamburger), single column |

---

## Typography Scale

| Element | Size | Weight | Line Height |
|---------|------|--------|-------------|
| H1 (Page title) | 30px / 1.875rem | Bold (700) | 1.2 |
| H2 (Section) | 24px / 1.5rem | Semibold (600) | 1.3 |
| H3 (Card title) | 18px / 1.125rem | Semibold (600) | 1.4 |
| Body | 14px / 0.875rem | Regular (400) | 1.5 |
| Small | 12px / 0.75rem | Regular (400) | 1.5 |
| Hero number | 36px / 2.25rem | Bold (700) | 1.1 |

---

## Spacing Scale

| Name | Value | Usage |
|------|-------|-------|
| xs | 4px | Icon gaps, tight spacing |
| sm | 8px | Inside buttons, form inputs |
| md | 16px | Card padding, section gaps |
| lg | 24px | Section spacing |
| xl | 32px | Page sections |
| 2xl | 48px | Major sections |

---

## Shadow & Border

| Element | Shadow | Border |
|---------|--------|--------|
| Card (light) | `0 1px 3px rgba(0,0,0,0.1)` | `1px solid #E5E7EB` |
| Card (dark) | None | `1px solid rgba(255,255,255,0.1)` |
| Hover card | `0 4px 6px rgba(0,0,0,0.1)` | - |
| Modal | `0 25px 50px rgba(0,0,0,0.25)` | - |

---

## Build Order for Plasmic

### Phase 1: Foundation
1. Create color tokens
2. Create typography scale
3. Build Sidebar component
4. Build Header component

### Phase 2: Shared Components
5. Build KPI Card
6. Build ALS Badge
7. Build Activity Item
8. Build Meeting Item
9. Build Campaign Card (with slider)

### Phase 3: Dashboard Home
10. Compose Dashboard Home page
11. Wire HeroMetricsSection
12. Wire CampaignPriorityPanel
13. Wire Activity + Meetings widgets

### Phase 4: Remaining Pages
14. Campaign List page
15. Campaign Detail page
16. Leads List page
17. Lead Detail page
18. Reply Inbox page
19. Reports page
20. Settings page

---

## Next Steps

1. Open Plasmic Studio: https://studio.plasmic.app/projects/sTVtoZDhkmD2Edyr9vqjyS
2. Import color tokens from this document
3. Start building Sidebar + Header
4. Proceed with Phase 2 components
5. Compose pages from components
