# SKILL.md — v0.dev Integration

**Skill:** v0.dev API Integration  
**Author:** Dave + Claude  
**Version:** 1.0  
**Created:** January 5, 2026  
**Phase:** 21+

---

## Purpose

Enable Claude Code to use the v0.dev Platform API for generating high-quality React/Tailwind UI components. This skill covers SDK setup, prompt engineering for v0, iteration patterns, and integration of generated code into the Agency OS frontend.

---

## Prerequisites

- Node.js 18+
- pnpm installed
- V0_API_KEY in `config/.env`
- Next.js 14+ frontend (`frontend/`)
- Tailwind CSS configured
- Shadcn/ui initialized

---

## Installation

```bash
cd frontend
pnpm add v0-sdk
```

Verify environment variable:
```bash
# In config/.env
V0_API_KEY=REDACTED_V0_KEY
```

---

## SDK Usage Patterns

### Basic Generation

```typescript
import { v0 } from 'v0-sdk'

// Create a new chat with a prompt
const chat = await v0.chats.create({
  message: 'Create a dark mode dashboard card with...',
  system: 'You are an expert React/Tailwind developer. Use TypeScript.'
})

// Access generated files
chat.files?.forEach((file) => {
  console.log(`File: ${file.name}`)
  console.log(`Content: ${file.content}`)
})

// Get the demo URL for preview
console.log(`Preview: ${chat.demo}`)
```

### Iterating on Generated Code

```typescript
// Continue the conversation to refine
const response = await v0.chats.sendMessage({
  chatId: chat.id,
  message: 'Make the spacing more compact and add a gradient border'
})

// Access updated files
response.files?.forEach((file) => {
  console.log(`Updated: ${file.name}`)
})
```

### Project-Based Generation

```typescript
// Create a project for related components
const project = await v0.projects.create({
  name: 'Agency OS Dashboard'
})

// Initialize chat with existing files
const chat = await v0.chats.init({
  type: 'files',
  files: existingComponentFiles,
  projectId: project.id,
})
```

---

## Helper Script

Create `scripts/v0-generate.ts`:

```typescript
import { v0 } from 'v0-sdk'
import * as fs from 'fs'
import * as path from 'path'
import * as dotenv from 'dotenv'

// Load env from config/.env
dotenv.config({ path: path.resolve(__dirname, '../config/.env') })

interface GenerateOptions {
  prompt: string
  outputDir: string
  iterate?: string[]  // Follow-up prompts
}

async function generate(options: GenerateOptions): Promise<string> {
  const { prompt, outputDir, iterate = [] } = options
  
  // Ensure output directory exists
  fs.mkdirSync(outputDir, { recursive: true })
  
  // Create initial chat
  console.log('🚀 Generating with v0...')
  const chat = await v0.chats.create({
    message: prompt,
    system: `You are an expert React/TypeScript/Tailwind developer.
Follow these rules:
- Use TypeScript with proper types
- Use Tailwind CSS for all styling
- Dark theme default (#0a0a0f or #0f0f13 background)
- Compact spacing, high information density
- Glass morphism: backdrop-blur, white/10 borders
- Max border-radius: 8px
- Use lucide-react for icons
- Export components as default`
  })
  
  console.log(`📺 Preview: ${chat.demo}`)
  
  // Apply iterations
  let currentChat = chat
  for (const followUp of iterate) {
    console.log(`🔄 Iterating: ${followUp.substring(0, 50)}...`)
    currentChat = await v0.chats.sendMessage({
      chatId: chat.id,
      message: followUp
    })
  }
  
  // Write files
  currentChat.files?.forEach((file) => {
    const filePath = path.join(outputDir, file.name)
    fs.writeFileSync(filePath, file.content)
    console.log(`✅ Written: ${filePath}`)
  })
  
  return chat.id
}

// CLI interface
const args = process.argv.slice(2)
if (args.length < 2) {
  console.log('Usage: npx ts-node scripts/v0-generate.ts <prompt-file> <output-dir>')
  process.exit(1)
}

const promptFile = args[0]
const outputDir = args[1]
const prompt = fs.readFileSync(promptFile, 'utf-8')

generate({ prompt, outputDir })
  .then((chatId) => console.log(`\n✨ Done! Chat ID: ${chatId}`))
  .catch((err) => console.error('Error:', err))
```

### Usage

```bash
# Create a prompt file
echo "Create a dark mode stats card..." > prompts/stats-card.txt

# Generate
npx ts-node scripts/v0-generate.ts prompts/stats-card.txt frontend/components/generated/
```

---

## Prompt Engineering for v0

### Effective Prompt Structure

```
Create a [component type] for [product context].

Layout:
- [Describe visual structure]
- [Describe grid/flex arrangement]

Content:
- [List specific text, labels, values]
- [Describe data to display]

Requirements:
- [Technical requirement 1]
- [Technical requirement 2]
- [Style requirement 1]
- [Style requirement 2]

Use [framework], [library], [language].
```

### Good Prompt Example

```
Create a dark mode SaaS dashboard stats card for "Agency OS".

Layout:
- 4 cards in a horizontal row (CSS Grid, gap-4)
- Each card: icon top-left, value large center, label below, change indicator

Content:
1. Pipeline Value: "$284K" with "+23% this month" in green
2. Meetings Booked: "47" with "+12 this week" in green
3. Reply Rate: "12.4%" with "3x industry avg" in blue
4. Active Leads: "2,847" with "Across 5 channels" in purple

Requirements:
- Dark theme (#0f0f13 background)
- Glass morphism on cards (backdrop-blur, border white/10)
- Compact padding (p-4)
- Border radius max 8px
- Use lucide-react for icons
- Tailwind CSS, React, TypeScript
```

### Bad Prompt Example

```
Make me a dashboard with some stats cards that look good.
```

### Iteration Prompts

After initial generation, use follow-ups like:
- "Make the spacing more compact, reduce padding to p-3"
- "Add a subtle gradient border on hover"
- "Change the background to #0a0a0f"
- "Add a loading skeleton state"
- "Make it responsive - stack on mobile"
- "Add TypeScript interfaces for the props"

---

## File Organization

### Generated Components Directory

```
frontend/components/
├── generated/           # Raw v0 output (temporary)
│   ├── StatsCard.tsx
│   └── ActivityFeed.tsx
├── landing/             # Refined landing page components
│   ├── HeroSection.tsx
│   ├── ActivityFeed.tsx
│   ├── TypingDemo.tsx
│   └── HowItWorksTabs.tsx
├── dashboard/           # Refined dashboard components
│   ├── DashboardGrid.tsx
│   ├── StatsCards.tsx
│   ├── ActivityFeed.tsx
│   └── ALSDistribution.tsx
└── admin/               # Refined admin components
    ├── AdminGrid.tsx
    ├── ClientTable.tsx
    └── RevenueChart.tsx
```

### Integration Workflow

1. **Generate** → Output to `components/generated/`
2. **Review** → Check preview URL, iterate if needed
3. **Refine** → Copy to appropriate directory, add real data connections
4. **Connect** → Wire up to API hooks, add loading states
5. **Clean up** → Remove from `generated/` once integrated

---

## Common v0 Issues & Fixes

### Issue: Components don't match existing styles

**Fix:** Include existing design tokens in the prompt:
```
Use these exact colors:
- Background: #0a0a0f
- Card: rgba(255,255,255,0.05)
- Border: rgba(255,255,255,0.1)
- Primary gradient: from-blue-500 to-purple-600
- Text primary: white
- Text secondary: rgba(255,255,255,0.6)
```

### Issue: Missing TypeScript types

**Fix:** Add to iteration:
```
Add TypeScript interfaces for all props. Export them from the file.
```

### Issue: Hardcoded data

**Fix:** Add to iteration:
```
Make all data come from props. Add sensible default values.
```

### Issue: Not responsive

**Fix:** Add to iteration:
```
Add responsive breakpoints:
- Mobile (< 640px): Stack vertically
- Tablet (640-1024px): 2 columns
- Desktop (> 1024px): Original layout
```

### Issue: Missing loading states

**Fix:** Add to iteration:
```
Add a loading prop. When true, show skeleton placeholders using animate-pulse.
```

---

## Integration with Existing Components

### Using with Shadcn/ui

v0 generates standalone components. To integrate with existing Shadcn:

```typescript
// Generated component might have its own Card
// Replace with Shadcn Card for consistency

// Before (v0 generated)
<div className="rounded-lg border bg-card p-4">

// After (using Shadcn)
import { Card, CardContent, CardHeader } from '@/components/ui/card'

<Card>
  <CardHeader>...</CardHeader>
  <CardContent>...</CardContent>
</Card>
```

### Using with Tremor

For charts, v0 may generate basic implementations. Replace with Tremor:

```typescript
// Before (v0 generated basic chart)
<div className="h-40 bg-gradient-to-r from-blue-500...">

// After (using Tremor)
import { BarChart } from '@tremor/react'

<BarChart
  data={data}
  index="name"
  categories={["value"]}
  colors={["blue"]}
/>
```

---

## Rate Limits & Best Practices

### API Limits
- Check v0.dev dashboard for current limits
- Cache generated components (don't regenerate same prompt)
- Use projects to organize related components

### Cost Optimization
- Write detailed prompts to reduce iterations
- Batch related components in single project
- Review preview before iterating

### Quality Assurance
1. Always check the demo URL before accepting
2. Test in actual Next.js app (not just preview)
3. Verify responsive behavior
4. Check for accessibility (aria labels, focus states)
5. Ensure no console errors

---

## Success Criteria

v0 integration is working correctly when:

- [ ] v0-sdk installed and configured
- [ ] Helper script can generate components
- [ ] Generated code compiles without errors
- [ ] Components render correctly in Next.js
- [ ] Iteration workflow produces refinements
- [ ] Generated components match design system

---

## Quick Reference

### Commands

```bash
# Install SDK
pnpm add v0-sdk

# Generate component
npx ts-node scripts/v0-generate.ts prompts/my-component.txt frontend/components/generated/

# Preview in browser
# (Use the demo URL from generation output)
```

### Environment

```
V0_API_KEY=v1:...  # In config/.env
```

### Key Imports

```typescript
import { v0 } from 'v0-sdk'
```

---
