# Plasmic Studio Build Specs

**Project URL:** https://studio.plasmic.app/projects/sTVtoZDhkmD2Edyr9vqjyS

Build these components in Plasmic Studio, then run `npx @plasmicapp/cli sync --yes`

---

## Design Tokens (Create First)

Go to **Project Settings > Design Tokens**

### Colors
```
sidebar-bg:      #1E3A5F (navy blue from mockup)
sidebar-active:  #2563EB (bright blue)
page-bg:         #F8FAFC (light gray)
card-bg:         #FFFFFF (white)
card-border:     #E2E8F0 (light border)
text-primary:    #1E293B (dark text)
text-secondary:  #64748B (gray text)
text-muted:      #94A3B8 (light gray)
accent-blue:     #3B82F6 (blue)
success:         #10B981 (green)
warning:         #F59E0B (orange)
error:           #EF4444 (red)
```

---

## Component 1: Sidebar

**Name:** `Sidebar`

### Structure
```
Frame (vertical, 256px width, 100vh height)
├── fill: sidebar-bg (#1E3A5F)
├── padding: 16px
│
├── Logo Section (height: 64px)
│   └── Text "AGENCY OS" (white, bold, 18px)
│
├── Nav Items (vertical stack, gap: 4px)
│   ├── NavItem "Dashboard" (icon: grid, ACTIVE)
│   ├── NavItem "Campaigns" (icon: target)
│   ├── NavItem "Leads" (icon: users)
│   ├── NavItem "Replies" (icon: message)
│   ├── NavItem "Reports" (icon: chart)
│   └── NavItem "Settings" (icon: cog)
```

### NavItem Specs
- Height: 44px
- Padding: 12px 16px
- Border-radius: 8px
- Default: text white/60, bg transparent
- Hover: text white, bg white/10
- Active: text white, bg sidebar-active, left border 3px blue

---

## Component 2: Header

**Name:** `Header`

### Structure
```
Frame (horizontal, height: 64px, width: 100%)
├── fill: card-bg (#FFFFFF)
├── border-bottom: 1px card-border
├── padding: 0 24px
├── align: center
│
├── Left: Page Title
│   └── Text "Dashboard" (text-primary, semibold, 20px)
│
├── Center: Search (optional)
│   └── Input with search icon
│
└── Right: Actions (horizontal, gap: 16px)
    ├── Bell icon (notifications)
    └── Profile dropdown
        ├── Avatar circle (32px, blue bg)
        └── Name + chevron
```

---

## Component 3: KPICard

**Name:** `KPICard`

### Structure
```
Frame (vertical, padding: 24px)
├── fill: card-bg (#FFFFFF)
├── border: 1px card-border
├── border-radius: 12px
├── shadow: sm
│
├── Header Row (horizontal, space-between)
│   ├── Label (text-secondary, 14px) "Meetings Booked"
│   └── Icon (text-muted, 20px)
│
├── Value (text-primary, bold, 36px) "12"
│
└── Trend Row (horizontal, gap: 4px)
    ├── Arrow icon (green or red)
    ├── Change value "+3"
    └── Label (text-muted) "vs last month"
```

### Variants
- **trendUp:** Arrow up, green color
- **trendDown:** Arrow down, orange color
- **neutral:** Dash, gray color

---

## Component 4: CampaignCard

**Name:** `CampaignCard`

### Structure
```
Frame (vertical, padding: 20px)
├── fill: card-bg
├── border: 1px card-border
├── border-radius: 12px
│
├── Header (horizontal, space-between)
│   ├── Left (horizontal, gap: 8px)
│   │   ├── Icon (robot or pen)
│   │   └── Name (text-primary, semibold, 16px)
│   └── Badge "AI SUGGESTED" or "CUSTOM"
│
├── Slider Section (margin-top: 16px)
│   ├── Labels "Low" --- "High"
│   ├── Slider track + thumb
│   └── Percentage "40%" (center, bold, 24px)
│
├── Stats Row (horizontal, gap: 16px)
│   ├── "6 meetings"
│   ├── "|"
│   └── "3.8% reply rate"
│
└── Footer (horizontal, space-between)
    ├── Channel badges (Email, LinkedIn)
    └── Status dot + "Active"
```

---

## Component 5: ActivityItem

**Name:** `ActivityItem`

### Structure
```
Frame (horizontal, padding: 12px, gap: 12px)
├── border-radius: 8px
├── hover: bg gray/5
│
├── Icon Circle (40x40, colored by channel)
│   └── Channel icon (white)
│
├── Content (vertical, flex: 1)
│   ├── Name + Company (14px)
│   └── Action text (text-muted, 12px)
│
└── Timestamp (text-muted, 12px) "2m ago"
```

### Channel Colors
- email: #3B82F6 (blue)
- linkedin: #0A66C2
- sms: #10B981 (green)
- voice: #8B5CF6 (purple)
- meeting: #F59E0B (amber)

---

## Component 6: MeetingItem

**Name:** `MeetingItem`

### Structure
```
Frame (horizontal, padding: 12px, gap: 12px)
│
├── DateTime (width: 80px)
│   ├── Day (text-muted, 12px) "Today"
│   └── Time (text-primary, 14px) "2:00 PM"
│
├── Divider (1px vertical line)
│
├── Content (flex: 1)
│   ├── Name (text-primary, semibold)
│   └── Company (text-muted, 12px)
│
└── Right
    ├── Type badge (Discovery/Demo/Follow-up)
    └── Duration "30 min"
```

---

## Page: DashboardHome

**Name:** `DashboardHome`

### Layout
```
Frame (horizontal, 100vw, 100vh)
│
├── Sidebar (fixed left, 256px)
│
└── Main Content (margin-left: 256px, flex: 1)
    │
    ├── Header (sticky top)
    │
    └── Content Area (padding: 24px, bg: page-bg)
        │
        ├── Hero Section (grid 2 cols, gap: 24px)
        │   ├── KPICard "Meetings Booked"
        │   └── KPICard "Show Rate"
        │
        ├── Campaigns Section (margin-top: 32px)
        │   ├── Section Header "YOUR CAMPAIGNS" + "Add Campaign" btn
        │   ├── CampaignCard (repeat)
        │   └── Footer: Total 100% + "Confirm & Activate" btn
        │
        ├── Bottom Grid (2 cols, margin-top: 32px)
        │   ├── Activity Section (col-span: 2/3)
        │   │   ├── Header "RECENT ACTIVITY" + Live badge
        │   │   └── ActivityItem (repeat)
        │   │
        │   └── Meetings Section (col-span: 1/3)
        │       ├── Header "UPCOMING MEETINGS"
        │       └── MeetingItem (repeat)
        │
        └── ALS Section (margin-top: 32px)
            ├── Header "LEAD QUALITY"
            └── Tier bars (5 columns)
```

---

## After Building

1. Save all components in Plasmic Studio
2. Run in terminal:
   ```bash
   cd frontend
   npx @plasmicapp/cli sync --yes
   ```
3. Tell me "synced" and I'll wire up the logic

---

## Element Naming Convention

Name elements so I can wire them up:

| Element | Name in Plasmic |
|---------|-----------------|
| Meetings KPI value | `meetingsValue` |
| Show rate KPI value | `showRateValue` |
| Campaign cards container | `campaignsList` |
| Confirm button | `confirmBtn` |
| Activity items container | `activityList` |
| Meetings items container | `meetingsList` |
| Add campaign button | `addCampaignBtn` |
| Emergency pause button | `pauseBtn` |

This lets me override props like:
```tsx
<PlasmicDashboardHome
  meetingsValue={{ children: data.meetings }}
  confirmBtn={{ onClick: handleConfirm }}
/>
```
