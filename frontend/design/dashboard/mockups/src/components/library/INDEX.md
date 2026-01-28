# Component Library Registry - "The Glass Stack"

**RULE for AI:** Always check this list before creating new UI. Import from here.

---

## 1. Shadcn UI - The Logic Layer
**Path:** `@/components/ui`
**Vibe:** Clean, functional, accessible

| Component | Use For |
|-----------|---------|
| `Button` | Standard actions, form submissions |
| `Input` | Form fields, search bars |
| `Table` | Data density (20+ API listings) |
| `Sheet` | Slide-over panels (Edit User, View Details) |
| `Dialog` | Modal confirmations, forms |
| `Card` | Content containers |
| `Badge` | Status indicators (Active/Pending) |
| `Avatar` | User profile images |
| `Tabs` | Content switching |
| `Progress` | Loading indicators |
| `Slider` | Range inputs |
| `Switch` | Toggle settings |
| `Separator` | Visual dividers |
| `Tooltip` | Hover hints |
| `Select` | Dropdowns |
| `Label` | Form labels |
| `Textarea` | Multi-line inputs |

---

## 2. Aceternity UI - The Glass Layer
**Path:** `@/components/ui`
**Vibe:** Apple-style, dark mode, glowing borders

| Component | Use For |
|-----------|---------|
| `CardContainer`, `CardBody`, `CardItem` (3d-card) | Featured content with 3D hover effect |
| `MovingBorder` (moving-border) | Premium CTAs, "Upgrade" buttons |
| `SparklesCore` (sparkles) | Hero sections, celebration effects |
| `BackgroundBeams` | Page backgrounds, hero sections |
| `HeroHighlight`, `Highlight` | Emphasized text in hero sections |
| `TextGenerateEffect` | Typewriter-style text reveals |

---

## 3. Magic UI - The Motion Layer
**Path:** `@/components/ui`
**Vibe:** High-speed SaaS, animated numbers, marquees

| Component | Use For |
|-----------|---------|
| `NumberTicker` | Animated counting numbers (revenue, users) |
| `BentoGrid`, `BentoCard` | Main dashboard container layout |
| `Marquee` | Scrolling testimonials, logos |
| `AnimatedList` | Live notification feeds |
| `BorderBeam` | Animated border highlight |
| `ShineBorder` | Shimmering card borders |
| `Dock`, `DockIcon` | macOS-style bottom navigation |
| `BlurFade` | Fade-in with blur effect |
| `Ripple` | Background ripple animations |
| `Particles` | Particle background effects |

---

## 4. Tremor - The Data Layer
**Path:** `@tremor/react`
**Vibe:** Dashboard-native charts

| Component | Use For |
|-----------|---------|
| `AreaChart` | Revenue history, trends over time |
| `BarChart` | Comparisons, monthly stats |
| `DonutChart` | User demographics, distribution |
| `LineChart` | Time series data |
| `Badge` (Tremor) | KPI delta indicators (+12%, -3%) |
| `Card` (Tremor) | Metric containers |
| `Metric` | Big numbers with labels |
| `ProgressBar` | Goal progress |

---

## 5. Cult UI - The Edge Layer
**Path:** `@/components/ui`
**Vibe:** Aggressive, futuristic design

| Component | Use For |
|-----------|---------|
| `GradientHeading` | Hero titles with gradient text |

---

## 6. Tabler Icons
**Import:** `@tabler/icons-react`
**Vibe:** Clean dashboard icons

```tsx
import { IconBell, IconCreditCard, IconChartBar } from "@tabler/icons-react";
```

**Best icons for dashboards:**
- `IconBell` - Notifications
- `IconCreditCard` - Billing
- `IconChartBar` - Analytics
- `IconUsers` - Team/Customers
- `IconSettings` - Configuration
- `IconCloud` - Integrations
- `IconCalendar` - Scheduling
- `IconMail` - Email
- `IconPhone` - Voice/SMS
- `IconBrandLinkedin` - LinkedIn

---

## Import Examples

### Shadcn Core
```tsx
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
```

### Aceternity Glass
```tsx
import { CardContainer, CardBody, CardItem } from "@/components/ui/3d-card";
import { Button as MovingBorderButton } from "@/components/ui/moving-border";
import { SparklesCore } from "@/components/ui/sparkles";
```

### Magic UI Motion
```tsx
import { NumberTicker } from "@/components/ui/number-ticker";
import { BentoGrid, BentoCard } from "@/components/ui/bento-grid";
import { BorderBeam } from "@/components/ui/border-beam";
```

### Tremor Charts
```tsx
import { AreaChart, DonutChart, BarChart } from "@tremor/react";
```

---

## Full Component Count: 43

| Library | Count | Category |
|---------|-------|----------|
| Shadcn UI | 26 | Core |
| Aceternity UI | 6 | Glass |
| Magic UI | 10 | Motion |
| Tremor | Built-in | Charts |
| Cult UI | 1 | Edge |
| Tabler Icons | 3,000+ | Icons |

---

## Gallery Preview

View all components at: **http://localhost:3000/gallery**
