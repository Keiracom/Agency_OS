# Agency OS UI Design System

## Trigger
Use when building or updating Agency OS frontend UI, designing dashboard components, or needing premium visual effects.

## Component Library (148+ components)

### ✨ Premium Effects
| Component | Use Case |
|-----------|----------|
| `shine-border` | Animated border glow on cards |
| `border-beam` | Moving light border effect |
| `animated-beam` | Connection lines between elements |
| `spotlight` | Hover spotlight effect |
| `aurora-background` | Animated gradient backgrounds |
| `sparkles` | Particle sparkle effect |
| `meteors` | Falling meteor animation |
| `shooting-stars` | Star trail effect |
| `particles` | Particle system |
| `confetti` | Celebration confetti |

### 📊 Data Visualization
| Component | Use Case |
|-----------|----------|
| `number-ticker` | Animated counting numbers |
| `animated-circular-progress-bar` | Circular progress |
| `progress` | Linear progress bars |
| `globe` | 3D world map with arcs |
| `world-map` | Flat world map |
| `orbiting-circles` | Orbital animation |

### 🎴 Cards & Layouts
| Component | Use Case |
|-----------|----------|
| `bento-grid` | Masonry-style grid |
| `3d-card` | Perspective hover card |
| `magic-card` | Gradient hover card |
| `glare-card` | Light glare effect |
| `wobble-card` | Tilt on hover |
| `card-hover-effect` | Lift and shadow |
| `card-stack` | Stacked cards |
| `evervault-card` | Matrix hover effect |

### 📝 Text Effects
| Component | Use Case |
|-----------|----------|
| `typewriter-effect` | Typing animation |
| `typing-animation` | Simple typing |
| `text-generate-effect` | Word-by-word reveal |
| `flip-words` | Rotating words |
| `word-rotate` | Word carousel |
| `animated-shiny-text` | Shimmer text |
| `aurora-text` | Gradient animated text |
| `sparkles-text` | Text with sparkles |
| `hyper-text` | Scramble reveal |
| `morphing-text` | Morph between words |

### 🧭 Navigation
| Component | Use Case |
|-----------|----------|
| `floating-navbar` | Sticky nav with blur |
| `floating-dock` | macOS-style dock |
| `dock` | App dock |
| `navbar-menu` | Mega menu |
| `tabs` | Tab navigation |
| `sidebar` | Collapsible sidebar |

### 🎬 Animation
| Component | Use Case |
|-----------|----------|
| `blur-fade` | Fade with blur |
| `marquee` | Infinite scroll |
| `3d-marquee` | 3D carousel |
| `infinite-moving-cards` | Testimonial scroll |
| `parallax-scroll` | Scroll parallax |
| `sticky-scroll-reveal` | Scroll-triggered reveal |
| `container-scroll-animation` | Scroll zoom |
| `hero-parallax` | Hero section parallax |

### 🖼️ Image Effects
| Component | Use Case |
|-----------|----------|
| `lens` | Magnifying glass |
| `compare` | Before/after slider |
| `images-slider` | Image carousel |
| `focus-cards` | Focus on hover |
| `apple-cards-carousel` | Apple-style cards |
| `hero-video-dialog` | Video modal |

### 🎨 Backgrounds
| Component | Use Case |
|-----------|----------|
| `dot-pattern` | Dotted background |
| `grid-pattern` | Grid lines |
| `retro-grid` | Perspective grid |
| `background-beams` | Laser beams |
| `background-boxes` | Floating boxes |
| `flickering-grid` | Animated grid |
| `wavy-background` | Wave animation |
| `vortex` | Spiral effect |
| `warp-background` | Speed lines |

## Color Palette (Mint Theme)
```css
--primary: 157 85% 39%;        /* #0eb77a mint-500 */
--background: 150 20% 98%;     /* Off-white with mint tint */
--accent: 157 60% 91%;         /* #ccfce8 mint-100 */
```

```js
mint: {
  50: '#f0fdf8',
  100: '#ccfce8',
  200: '#99f6d4',
  300: '#5eebb8',
  400: '#2dd498',
  500: '#0eb77a',
  600: '#059562',
  700: '#047652',
  800: '#065d43',
  900: '#054d38',
}
```

## Dashboard V4 Components
Located in `components/dashboard-v4/`:
- `QuickStatsRow` - KPI summary row
- `HeroMeetingsCard` - Primary meetings display
- `HotProspectsCard` - Hot lead highlights
- `WeekAheadCard` - Upcoming week preview
- `WarmRepliesCard` - Recent reply inbox
- `InsightCard` - AI insight callouts
- `CelebrationBanner` - Success celebrations

## Design Patterns

### Card Pattern
```tsx
<Card className="p-6 bg-white border border-neutral-200 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
  <CardHeader className="pb-2">
    <CardTitle className="text-lg font-semibold text-foreground">Title</CardTitle>
  </CardHeader>
  <CardContent>
    {/* Content */}
  </CardContent>
</Card>
```

### Stat Card with Animation
```tsx
<div className="p-4 rounded-xl bg-card border">
  <span className="text-muted-foreground text-xs uppercase tracking-wider">Label</span>
  <NumberTicker value={1234} className="text-3xl font-bold" />
</div>
```

### Premium Border Effect
```tsx
<div className="relative rounded-xl p-6 bg-card">
  <ShineBorder shineColor={["#2dd498", "#0eb77a"]} />
  {/* Content */}
</div>
```

## Landing Page Components
Located in `components/landing/`:
- `HeroSection` - Main hero with animations
- `DashboardDemo` - Live dashboard preview
- `TypingDemo` - AI typing demonstration
- `ActivityFeed` - Real-time activity simulation
- `SocialProofBar` - Testimonials/logos
- `HowItWorksCarousel` - Feature showcase

## Import Pattern
```tsx
import { ShineBorder } from "@/components/ui/shine-border";
import { NumberTicker } from "@/components/ui/number-ticker";
import { Marquee } from "@/components/ui/marquee";
import { BentoGrid, BentoGridItem } from "@/components/ui/bento-grid";
```

## Source
Most components from:
- Magic UI (magicui.design)
- Aceternity UI (ui.aceternity.com)
- shadcn/ui (ui.shadcn.com)
