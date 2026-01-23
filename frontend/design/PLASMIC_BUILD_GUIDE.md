# Plasmic Dashboard Build Guide

**Project:** https://studio.plasmic.app/projects/sTVtoZDhkmD2Edyr9vqjyS
**Page:** Dashboard Home
**Last Updated:** 2026-01-23

---

## Setup Complete

- [x] Plasmic loader installed: `@plasmicapp/loader-nextjs`
- [x] Config created: `frontend/plasmic-init.ts`
- [x] Code components registered for use in Plasmic

---

## Step 1: Create Design Tokens in Plasmic Studio

Open Plasmic Studio and go to **Project Settings > Tokens**.

### Colors (Create These)

| Token Name | Value | Category |
|------------|-------|----------|
| `--color-sidebar-bg` | `#1a2744` | Backgrounds |
| `--color-card-dark` | `#1a1a1f` | Backgrounds |
| `--color-card-light` | `#FFFFFF` | Backgrounds |
| `--color-page-bg` | `#F5F7FA` | Backgrounds |
| `--color-primary` | `#2196F3` | Brand |
| `--color-success` | `#10B981` | Status |
| `--color-warning` | `#F59E0B` | Status |
| `--color-error` | `#EF4444` | Status |
| `--color-text-primary` | `#1F2937` | Text |
| `--color-text-secondary` | `#6B7280` | Text |
| `--color-text-muted` | `#9CA3AF` | Text |
| `--color-text-white` | `#FFFFFF` | Text |
| `--color-border` | `#E5E7EB` | Borders |
| `--color-border-dark` | `rgba(255,255,255,0.1)` | Borders |

### Typography (Create These)

| Token Name | Font | Size | Weight |
|------------|------|------|--------|
| `--font-heading-1` | Inter | 30px | 700 |
| `--font-heading-2` | Inter | 24px | 600 |
| `--font-heading-3` | Inter | 18px | 600 |
| `--font-body` | Inter | 14px | 400 |
| `--font-small` | Inter | 12px | 400 |
| `--font-hero-number` | Inter | 36px | 700 |

### Spacing

| Token Name | Value |
|------------|-------|
| `--space-xs` | 4px |
| `--space-sm` | 8px |
| `--space-md` | 16px |
| `--space-lg` | 24px |
| `--space-xl` | 32px |
| `--space-2xl` | 48px |

---

## Step 2: Build Sidebar Component

**Create new component:** `Sidebar`

### Structure
```
Sidebar (Box - vertical stack)
├── Logo (Box)
│   └── Text: "AGENCY OS"
├── NavList (Box - vertical stack, gap: 4px)
│   ├── NavItem: Dashboard (active)
│   ├── NavItem: Campaigns
│   ├── NavItem: Leads
│   ├── NavItem: Replies
│   ├── NavItem: Reports
│   └── NavItem: Settings
└── Spacer (flex: 1)
```

### Sidebar Styles
```
Width: 256px
Height: 100vh
Background: #1a2744
Padding: 24px 16px
Position: fixed
Left: 0
Top: 0
```

### NavItem Component (Create)
```
Box (horizontal stack)
├── Icon (24x24)
└── Text (14px, white)

States:
- Default: opacity 0.7, hover: opacity 1, bg: transparent
- Active: opacity 1, bg: rgba(255,255,255,0.1), border-left: 3px #2196F3
```

### NavItem Props
| Prop | Type | Default |
|------|------|---------|
| `icon` | slot | - |
| `label` | string | "Item" |
| `href` | string | "/" |
| `isActive` | boolean | false |

---

## Step 3: Build Header Component

**Create new component:** `Header`

### Structure
```
Header (Box - horizontal, justify: space-between)
├── Left (Box)
│   └── Breadcrumb or Page Title
├── Center (Box) [optional]
│   └── Search Input
└── Right (Box - horizontal, gap: 16px)
    ├── NotificationBell (Icon button)
    └── ProfileDropdown
        ├── Avatar (32x32 circle)
        └── ChevronDown
```

### Header Styles
```
Height: 64px
Background: white
Border-bottom: 1px solid #E5E7EB
Padding: 0 24px
Display: flex
Align-items: center
```

---

## Step 4: Build KPI Card Component

**Create new component:** `KPICard`

### Structure
```
KPICard (Box - vertical)
├── Header (Box - horizontal, justify: space-between)
│   ├── Label (Text - 14px, muted)
│   └── Icon (16x16, muted)
├── Value (Text - 36px, bold)
└── Footer (Box - horizontal)
    ├── TrendIcon (arrow up/down)
    └── TrendText ("+3 vs last month")
```

### KPICard Styles
```
Background: #1a1a1f (dark) or white (light)
Border: 1px solid rgba(255,255,255,0.1)
Border-radius: 12px
Padding: 24px
```

### KPICard Props
| Prop | Type | Options |
|------|------|---------|
| `label` | string | "Meetings Booked" |
| `value` | string | "12" |
| `trend` | number | 3 |
| `trendLabel` | string | "vs last month" |
| `icon` | slot | Calendar icon |
| `variant` | choice | "dark", "light" |

### Variants
- **Positive trend:** Green arrow up, green text
- **Negative trend:** Red arrow down, red text
- **Neutral:** Gray dash, gray text

---

## Step 5: Build Activity Item Component

**Create new component:** `ActivityItem`

### Structure
```
ActivityItem (Box - horizontal, gap: 12px)
├── ChannelIcon (Box - 40x40 circle, centered)
│   └── Icon (20x20)
├── Content (Box - vertical, flex: 1)
│   ├── Title (Text - 14px)
│   │   ├── Name (bold)
│   │   └── " at " + Company
│   └── Action (Text - 12px, muted)
└── Timestamp (Text - 12px, muted, right-aligned)
```

### Channel Icons & Colors
| Channel | Icon | Background |
|---------|------|------------|
| email | Mail | `#3B82F6` (blue) |
| linkedin | Linkedin | `#0A66C2` (linkedin blue) |
| sms | MessageSquare | `#10B981` (green) |
| voice | Phone | `#8B5CF6` (purple) |
| meeting | Calendar | `#F59E0B` (amber) |

### ActivityItem Props
| Prop | Type |
|------|------|
| `channel` | choice: email, linkedin, sms, voice, meeting |
| `name` | string |
| `company` | string |
| `action` | string |
| `timestamp` | string |

---

## Step 6: Build Meeting Item Component

**Create new component:** `MeetingItem`

### Structure
```
MeetingItem (Box - horizontal, gap: 12px, padding: 12px)
├── DateTime (Box - vertical, width: 80px)
│   ├── Day (Text - 12px, muted) "Today"
│   └── Time (Text - 14px, bold) "2:00 PM"
├── Divider (Box - 1px width, bg: border color)
├── Content (Box - vertical, flex: 1)
│   ├── Name (Text - 14px, bold)
│   ├── Company (Text - 12px, muted)
│   └── Type Badge (Text - 10px, pill badge)
└── Duration (Text - 12px, muted) "30 min"
```

### Type Badge Colors
| Type | Background | Text |
|------|------------|------|
| Discovery | `#DBEAFE` | `#1D4ED8` |
| Demo | `#D1FAE5` | `#047857` |
| Follow-up | `#FEF3C7` | `#B45309` |

---

## Step 7: Build Campaign Priority Card

**Create new component:** `CampaignCard`

### Structure
```
CampaignCard (Box - vertical, padding: 20px)
├── Header (Box - horizontal, justify: space-between)
│   ├── Title (Box - horizontal, gap: 8px)
│   │   ├── Icon (robot or pencil)
│   │   └── Name (Text - 16px, semibold)
│   └── Badge (AI SUGGESTED or CUSTOM)
├── Slider Section (Box - vertical, margin-top: 16px)
│   ├── Labels (Box - horizontal, justify: space-between)
│   │   ├── "Low" (12px, muted)
│   │   └── "High" (12px, muted)
│   ├── Slider Track (Box - horizontal, relative)
│   │   ├── Track BG (Box - full width, 8px height, rounded, gray)
│   │   ├── Track Fill (Box - width: {priority}%, 8px, rounded, blue)
│   │   └── Thumb (Box - 20x20 circle, white, shadow, position: {priority}%)
│   └── Percentage (Text - 24px, bold, center) "40%"
├── Stats Row (Box - horizontal, gap: 16px, margin-top: 16px)
│   ├── Stat: "6 meetings"
│   ├── Divider (Text: "|")
│   └── Stat: "3.8% reply rate"
└── Footer (Box - horizontal, gap: 8px, margin-top: 12px)
    ├── Channel Badge: "Email"
    ├── Channel Badge: "LinkedIn"
    └── Status: "Active" (green dot)
```

### CampaignCard Props
| Prop | Type |
|------|------|
| `name` | string |
| `isAI` | boolean |
| `priority` | number (0-100) |
| `meetings` | number |
| `replyRate` | number |
| `channels` | string[] |
| `status` | choice: active, paused, draft |

---

## Step 8: Compose Dashboard Home Page

**Create new page:** `DashboardHome`

### Page Layout
```
DashboardHome (Box - horizontal)
├── Sidebar (Component)
└── MainContent (Box - vertical, margin-left: 256px, flex: 1)
    ├── Header (Component)
    └── Content (Box - vertical, padding: 24px)
        ├── PageTitle (Text - 30px) "Dashboard"
        ├── PageSubtitle (Text - 14px, muted) "Welcome back! Here's..."
        │
        ├── HeroSection (Box - horizontal, gap: 24px, margin-top: 24px)
        │   ├── KPICard: Meetings Booked
        │   └── KPICard: Show Rate
        │
        ├── CampaignsSection (Box - vertical, margin-top: 32px)
        │   ├── SectionHeader (Box - horizontal)
        │   │   ├── Title: "YOUR CAMPAIGNS"
        │   │   └── Button: "+ Add Campaign"
        │   ├── CampaignCard (repeat for each)
        │   └── Footer (Box)
        │       ├── Total: "100%"
        │       └── Button: "Confirm & Activate"
        │
        ├── BottomSection (Box - horizontal, gap: 24px, margin-top: 32px)
        │   ├── ActivitySection (Box - flex: 2)
        │   │   ├── SectionHeader: "RECENT ACTIVITY" + Live badge
        │   │   └── ActivityList (repeat ActivityItem)
        │   └── MeetingsSection (Box - flex: 1)
        │       ├── SectionHeader: "UPCOMING MEETINGS"
        │       └── MeetingsList (repeat MeetingItem)
        │
        └── ALSSection (Box - margin-top: 32px)
            ├── SectionHeader: "ALS DISTRIBUTION"
            └── TierBars (Box - horizontal, gap: 16px)
                ├── TierBar: Hot (15%)
                ├── TierBar: Warm (35%)
                ├── TierBar: Cool (30%)
                ├── TierBar: Cold (15%)
                └── TierBar: Dead (5%)
```

---

## Step 9: Add Responsive Variants

### Breakpoints
| Name | Width | Changes |
|------|-------|---------|
| Desktop | 1280px+ | Full layout |
| Tablet | 768-1279px | Sidebar collapsible, 2-col grid |
| Mobile | <768px | Sidebar hidden, single column |

### Mobile Changes
- Sidebar: Hidden by default, hamburger menu
- Hero KPIs: Stack vertically
- Campaign cards: Full width
- Bottom section: Stack vertically
- Activity/Meetings: Full width each

---

## Step 10: Connect Code Components

In Plasmic Studio, you can drag in our registered code components:

1. Go to **Insert > Code Components**
2. Available components:
   - `HeroMetricsCard` - Pre-built hero metrics
   - `LiveActivityFeed` - Real-time activity
   - `MeetingsWidget` - Upcoming meetings
   - `CampaignPriorityPanel` - Full campaign sliders
   - `EmergencyPauseButton` - Pause button
   - `ALSScorecard` - ALS display

These components are fully functional with data hooks.

---

## Preview URLs

After building, access via:
- **Studio Preview:** Click "Preview" in Plasmic Studio
- **Local Dev:** `http://localhost:3000/api/preview?secret=agency-os-plasmic-preview-2026&slug=/dashboard`
- **Exit Preview:** `http://localhost:3000/api/exit-preview`

---

## Files Created

| File | Purpose |
|------|---------|
| `frontend/plasmic-init.ts` | Plasmic loader + component registration |
| `frontend/design/PLASMIC_BUILD_GUIDE.md` | This file |

---

## Next: Open Plasmic Studio

1. Go to: https://studio.plasmic.app/projects/sTVtoZDhkmD2Edyr9vqjyS
2. Start with Step 1 (Design Tokens)
3. Build components in order (Steps 2-7)
4. Compose the page (Step 8)
5. Add responsive variants (Step 9)
6. Connect code components (Step 10)
