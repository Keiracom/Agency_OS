# EQTY Lab Landing Page - Design Specification

## Overview
A premium SaaS landing page for EQTY Lab's "Verifiable Compute" product for AI trust and security.

---

## Color Palette

### Primary Colors
| Name | Hex | Usage |
|------|-----|-------|
| **Primary Green** | `#4ADE80` | Headlines accent, buttons, highlights |
| **Light Green** | `#86EFAC` | Secondary accents, dots |
| **Mint Green** | `#D1FAE5` | Light backgrounds, cards |
| **Dark Green (Solutions)** | `#064E3B` | Dark section backgrounds |
| **Muted Green** | `#6B8E85` | Decorative dots (muted) |

### Background Colors
| Name | Hex | Usage |
|------|-----|-------|
| **Black** | `#0A0A0A` or `#000000` | Hero section background |
| **White** | `#FFFFFF` | Light sections |
| **Gray (outer)** | `#A3A3A3` | Browser frame mock |

### Text Colors
| Name | Hex | Usage |
|------|-----|-------|
| **White** | `#FFFFFF` | Text on dark backgrounds |
| **Black/Dark** | `#1F2937` | Headlines on light bg |
| **Gray Text** | `#6B7280` | Subtitle/body text |
| **Light Gray** | `#9CA3AF` | Muted descriptions |

---

## Typography

### Font Family
- **Primary**: Inter or SF Pro Display (sans-serif system stack)
- **Fallback**: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`

### Font Sizes
| Element | Size | Weight | Line Height |
|---------|------|--------|-------------|
| Logo "EQTY" | 20px | 700 (Bold) | 1.2 |
| Logo "LAB" | 20px | 400 (Regular) | 1.2 |
| Nav Links | 14px | 500 | 1.5 |
| Hero Headline | 72px | 300-400 (Light) | 1.1 |
| Hero Subhead | 16px | 400 | 1.5 |
| Section Tag ("The Problem") | 14px | 500 | 1.5 |
| Section Headline | 48px | 600 | 1.2 |
| Card Title | 24px | 600 | 1.3 |
| Body Text | 14-16px | 400 | 1.6 |
| Button Text | 14px | 500 | 1 |
| Small Labels | 12px | 500 | 1.4 |

---

## Layout & Spacing

### Container
- Max width: 1200px
- Padding: 0 40px (desktop)
- Border radius (main card): 24px

### Sections
| Section | Height/Padding |
|---------|----------------|
| Navigation | 80px height |
| Hero | 100vh (full viewport) |
| Features | 100px padding top/bottom |
| Problem Section | 80px padding |
| Solutions Section | 100px padding |

### Component Spacing
- Section gap: 120px
- Card gap: 24px
- Button padding: 16px 24px
- Nav item spacing: 24px

---

## Components

### Navigation Bar
- **Background**: Transparent (dark mode: rgba(0,0,0,0.5))
- **Pill container**: Semi-transparent with subtle border
- **Border radius**: 40px (full pill)
- **Items**: Overview | Technology | Testimonials ▾ | Resources
- **Right CTA**: "Log In" (text) + "Get Started" (outlined button)

### Hero Chip Icon
- **Size**: ~100px × 100px
- **Background**: Dark with green border (#1a472a + #4ADE80 border)
- **Inner**: EQTY text with circuit board pattern
- **Glow**: Green radial glow behind

### CTA Button (Primary)
- **Background**: White
- **Text**: Black
- **Border radius**: 40px (full pill)
- **Icon**: Green sparkle/arrow icon on left
- **Padding**: 12px 24px
- **Shadow**: 0 4px 12px rgba(0,0,0,0.1)

### Deployment Cards (Dell, Cloud, Accenture)
- **Background**: rgba(255,255,255,0.05)
- **Border**: 1px solid rgba(255,255,255,0.1)
- **Border radius**: 16px
- **Padding**: 20px 32px
- **Icon**: External link ↗

### Feature Icons (Verifiable Compute section)
- **Size**: 64px × 64px
- **Background**: rgba(74,222,128,0.1)
- **Border**: 1px solid #4ADE80
- **Border radius**: 16px
- **Icon color**: #4ADE80

### Problem Section Card
- **Left panel**: Dark gradient with green glow curves
- **Right panel**: Light mint green (#D1FAE5)
- **Border radius**: 16px
- **Content**: Two-column bullet list

### Solutions Section
- **Top**: White with floating dots animation
- **Bottom**: Dark green (#064E3B) with "Verifiable" text
- **Dots**: Various sizes (4px-12px), green shades

---

## Animations

### 1. Page Load Sequence (0-2s)
1. **0-0.3s**: Fade in from black
2. **0.3-0.6s**: Logo and nav appear
3. **0.5-1s**: Chip icon scales in with glow
4. **0.8-1.2s**: Headline text reveal (left to right)
5. **1-1.5s**: Subtitle and CTA fade up
6. **1.3-2s**: Flowing gradient lines animate

### 2. Hero Background
- **Gradient lines**: Flowing teal/green aurora-like waves
- **Animation**: Continuous subtle movement (10-15s loop)
- **Style**: CSS gradient animation or canvas

### 3. Chip Icon
- **Pulse glow**: Scale 1 → 1.02 → 1, opacity 0.8 → 1 → 0.8 (3s loop)
- **Circuit lines**: Subtle flicker animation

### 4. Floating Icons (cards around hero)
- **Movement**: Float up/down 10px (4-6s loop, staggered)
- **Opacity**: Slight fade in/out

### 5. Section Transitions (on scroll)
- **Fade up**: translateY(30px) → 0, opacity 0 → 1
- **Timing**: 0.6s ease-out
- **Stagger**: 0.1s between elements

### 6. Floating Dots (Solutions section)
- **Pattern**: Random floating animation
- **Sizes**: 4px, 8px, 12px variants
- **Colors**: Mix of #4ADE80 (bright) and #6B8E85 (muted)
- **Movement**: Float randomly, 6-12s loops

### 7. "Verifiable" Text Animation
- **Entry**: Scale from 0.9 → 1, fade in
- **Accompanying dots**: Sequential appearance

---

## Responsive Breakpoints

| Breakpoint | Width | Changes |
|------------|-------|---------|
| Desktop XL | 1440px+ | Max-width container |
| Desktop | 1024-1439px | Default layout |
| Tablet | 768-1023px | Stacked sections, smaller fonts |
| Mobile | <768px | Single column, hamburger nav |

---

## Assets Required

### SVG Icons
1. EQTY Logo (text-based)
2. External link arrow (↗)
3. Sparkle/magic icon (for CTA)
4. Database/cylinder icon
5. Chip/processor icon
6. Fingerprint/shield icon
7. Play triangle icon
8. Chevron down (dropdown)

### Images/Graphics
1. Chip icon with circuit board pattern (can be SVG)
2. Aurora/gradient background (CSS or canvas)
3. Green glowing curves (CSS gradients)

---

## Interaction States

### Buttons
- **Hover**: Scale 1.02, brighten background
- **Active**: Scale 0.98
- **Transition**: 0.2s ease

### Links
- **Hover**: Color brighten, underline
- **Transition**: 0.15s ease

### Cards
- **Hover**: Subtle lift (translateY -4px), shadow increase
- **Transition**: 0.3s ease

---

## Accessibility

- Color contrast ratio: 4.5:1 minimum
- Focus states: Green outline ring
- Reduced motion: Disable complex animations
- Screen reader labels for icons
