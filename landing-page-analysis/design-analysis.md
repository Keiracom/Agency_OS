# Landing Page Design Analysis - EQTY Lab Reference

## Overview
Analysis of EQTY Lab's landing page design for replication as Agency OS landing page.

---

## 1. Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| Deep Black | `#0a0a0a` | Hero background, dark sections |
| Emerald Green | `#10b981` | Accents, CTAs, gradient text |
| Light Emerald | `#34d399` | Glow effects, secondary accents |
| Mint Cream | `#ecfdf5` | Light section backgrounds |
| White | `#ffffff` | Text, cards, light sections |
| Gray | `#9ca3af` | Muted text, secondary copy |

## 2. Typography

- **Headlines:** Large (48-72px), bold weight (700-800), serif or modern sans
- **Subheadlines:** Medium (18-24px), regular weight, gray color
- **Body:** 16px, regular weight, good line height (1.6)
- **Special Effect:** Gradient/colored text for emphasis words ("New Threats", "AI with")

## 3. Layout Structure

### Hero Section (Frames 1-2)
- Full-screen dark background
- Centered content alignment
- 3D chip/product visualization
- Floating UI elements (small chips) for depth
- Circuit board line decorations
- Aurora/wave effect at bottom
- Navigation: Logo left, links center, CTA right

### Features Section (Frames 3-4)
- Horizontal icon row with connecting lines
- Three feature icons with descriptions
- Clean spacing, centered layout

### Problem Section (Frame 5)
- White background transition
- Section badge/tag ("The Problem")
- Two-column split layout
- Dark card with visual on left
- Light mint card with bullet points on right

### Solutions Section (Frames 6-8)
- Floating animated dots background
- Section badge ("Solutions")
- Animated text reveal
- Dark green feature cards
- Vertical list with dot indicators

## 4. Visual Effects & Animations (Detailed from Video Analysis)

### Page Load Sequence (0-2s)
1. **Background aurora** fades in first (0.3s delay)
2. **Logo/Chip** materializes with glitch effect - blur reducing + scale growing
3. **Headline text** reveals progressively with fade + slide up (left-to-right character reveal implied)
4. **Nav** fades in (0.5s delay)
5. **Wave lines** draw themselves (0.5-0.9s staggered delays)
6. **Circuit lines** grow outward from chip (1.0-1.2s)
7. **Floating chips** fade in sequentially (1.5-2.1s staggered)
8. **Platform cards** slide up with stagger (1.5-1.7s)

### Continuous Animations
1. **Aurora Wave Effect:** Gentle pulse (8s cycle), scale 1.0-1.1, opacity 0.6-1.0
2. **Chip Float:** Subtle vertical bobbing (6s cycle, 10px range)
3. **Glow Pulse:** Behind chip (3s cycle, scale + opacity)
4. **Wave Lines:** Horizontal drift with rotation (-3deg to 3deg, 20s cycle)
5. **Floating Chips:** Drift with slight rotation (7-10s cycles, different per chip)

### Scroll-Triggered Animations
1. **Section Tags/Badges:** Fade in + slide up (0.6s ease-out)
2. **Headlines:** Fade in + slide up, then underline draws left-to-right
3. **Feature Icons:** Sequential reveal with pulse glow effect (0.4s stagger)
4. **Connecting Line:** Grows from center outward (1.5s)
5. **Diamond Connectors:** Scale in (0.5s delay after line)
6. **Problem Cards:** Slide in from sides (left card from left, right from right)
7. **Problem List Items:** Sequential fade + slide (150ms stagger)
8. **Solutions Card:** Slide up from below (0.8s)
9. **Solution Items:** Sequential slide from left (0.2s stagger)

### Text Cycling Animations
1. **Feature Highlight:** Cycles through "Automates" → "Orchestrates" → "Accelerates" (3s interval)
2. **Solutions Highlight:** Cycles through "Intelligent Automation" → "AI Orchestration" → "Verified Results"
3. **Animation:** Fade out + translateY(10px), text swap, fade in + translateY(0)

### Solutions Section Special Effects
1. **Floating Dots:** 25 dots with varying sizes (4-16px), random positions, parallax on scroll
2. **Active Solution Indicator:** 
   - Dot enlarges (12px → 16px)
   - Vertical accent bar grows (height: 0 → 100%)
   - 2.5s rotation cycle through items

### Hover Effects
1. **Nav Links:** Background opacity + color change
2. **Buttons:** translateY(-2px) + box-shadow glow
3. **Platform Cards:** Border color change + lift + glow shadow
4. **Feature Icons:** translateY(-5px) + box-shadow + gradient border glow

## 5. Component Inventory

### Navigation
- Logo (left)
- Links with dropdown (center pill container)
- Log In / Get Started buttons (right)

### Hero Elements
- 3D product graphic
- Headline with large typography
- Subtitle text
- Primary CTA button (Schedule Demo)
- Secondary options (Dell, Cloud, Accenture cards)

### Feature Icons
- Rounded square icons with glow
- Short description text
- Connecting line decoration

### Section Cards
- Rounded corners (16-24px)
- Subtle shadows
- Dark/light variants

### Badges/Tags
- Pill-shaped
- Border style
- Section labels

## 6. Responsive Considerations

- Hero scales down to single column on mobile
- Feature icons stack vertically
- Problem section becomes single column
- Navigation collapses to hamburger menu

## 7. Copy Style

- **Tone:** Technical but accessible, confident
- **Headlines:** Short, punchy, action-oriented
- **Subheadlines:** Explain the value proposition
- **Features:** Benefit-focused, brief descriptions

---

## Adaptation for Agency OS

### Brand Translation
- EQTY Lab → Agency OS
- "Verify to Trust AI" → "AI Agents That Actually Work"
- Chip graphic → Agent/workflow visualization
- Verifiable Compute → AI-Powered Agency Automation

### Content Mapping
| EQTY Section | Agency OS Section |
|--------------|-------------------|
| Verifiable Compute | Agent Orchestration |
| New Threats | Agency Challenges |
| Solutions | How Agency OS Helps |
| Training/Privacy/Safeguards | Lead Gen/Outreach/Automation |

### Visual Adjustments
- Keep dark hero aesthetic
- Maintain green accent color scheme
- Replace chip with agent/node visualization
- Keep aurora effect and floating dots
