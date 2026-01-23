# Plasmic Design Collaboration Workflow

**Purpose:** Document the design-to-code workflow using Plasmic as a shared visual design platform.
**Last Updated:** 2026-01-23

---

## Overview

Plasmic serves as the shared visual design canvas between CEO (design) and Claude (implementation). This creates a live design-to-code loop with real-time sync capabilities.

```
┌─────────────┐    Plasmic API    ┌─────────────┐
│   Claude    │ ◄───────────────► │   Plasmic   │
│   (Code)    │   fetch/sync      │  (Design)   │
└─────────────┘                   └─────────────┘
       │                                ▲
       │ implement                      │ design
       ▼                                │
┌─────────────┐                   ┌─────────────┐
│  Codebase   │                   │     CEO     │
│ Agency OS   │                   │  (Visual)   │
└─────────────┘                   └─────────────┘
```

---

## Workflow Steps

### 1. Design in Plasmic Studio

CEO designs components visually:
- Open Plasmic Studio: https://studio.plasmic.app/
- Create/edit components visually
- Plasmic generates React code automatically

### 2. Claude Fetches via API

Claude can fetch components using the Plasmic loader:

```typescript
import { initPlasmicLoader } from "@plasmicapp/loader-nextjs";

export const PLASMIC = initPlasmicLoader({
  projects: [
    {
      id: process.env.NEXT_PUBLIC_PLASMIC_PROJECT_ID!,
      token: process.env.NEXT_PUBLIC_PLASMIC_PROJECT_API_TOKEN!,
    },
  ],
  preview: true, // Enable preview mode for live updates
});
```

### 3. Preview Mode

Access live preview during development:
```
http://localhost:3000/api/preview?secret=PLASMIC_PREVIEW_SECRET&slug=PATH
```

Exit preview: `http://localhost:3000/api/exit-preview`

### 4. Claude Implements

- Fetch design changes from Plasmic
- Add backend endpoints if new data needed
- Update types, hooks, API functions
- Sync documentation

### 5. Iterate

Repeat steps 1-4 until design is finalized.

---

## When Backend Changes Needed

If a design requires new data:

| Design Change | Backend Action |
|---------------|----------------|
| New metric displayed | Add field to API response |
| New filter/sort | Add query parameter to endpoint |
| New action button | Create new endpoint |
| New page section | May need new hook + endpoint |

**Process:**
1. CEO adds element in Plasmic
2. Claude sees it needs data we don't have
3. Claude proposes backend addition
4. CEO approves
5. Claude implements backend + frontend together

---

## Environment Variables

**Location:** `config/.env` and `frontend/.env.local`

```bash
# --- PLASMIC (Visual Design & Code Generation) ---
# Project ID from Plasmic Studio URL
NEXT_PUBLIC_PLASMIC_PROJECT_ID=<your-project-id>
# Project API Token (from Code button in Plasmic Studio)
NEXT_PUBLIC_PLASMIC_PROJECT_API_TOKEN=<your-api-token>
# Preview secret (any random string)
PLASMIC_PREVIEW_SECRET=agency-os-plasmic-preview-2026
```

### Getting Your Credentials

1. **Project ID:** Found in Plasmic Studio URL: `https://studio.plasmic.app/projects/PROJECTID`
2. **API Token:** Click "Code" button in Plasmic Studio toolbar
3. **Preview Secret:** Any random string (avoid spaces)

---

## Plasmic Integration Files

| File | Purpose |
|------|---------|
| `plasmic-init.ts` | Initialize Plasmic loader with credentials |
| `app/[[...catchall]]/page.tsx` | Catch-all route for Plasmic pages |
| `components/plasmic/` | Plasmic-generated components |

---

## File Mapping

| Plasmic Component | Codebase Location |
|-------------------|-------------------|
| Dashboard Home | `app/dashboard/page.tsx` |
| Campaign Detail | `app/dashboard/campaigns/[id]/page.tsx` |
| Campaign Cards | `components/campaigns/*.tsx` |
| Dashboard Widgets | `components/dashboard/*.tsx` |
| Shared UI | `components/ui/*.tsx` |

---

## Best Practices

1. **Small iterations** - Design one component at a time
2. **Name clearly** - Use same component names in Plasmic as codebase
3. **Flag data needs** - CEO notes when new data is needed
4. **Keep synced** - Claude updates SPEC_ALIGNMENT.md after each sync
5. **Use preview mode** - Test changes live before committing

---

## Plasmic vs Code-First

| Approach | Use When |
|----------|----------|
| **Plasmic-first** | New pages, major layout changes, rapid prototyping |
| **Code-first** | Complex logic, animations, performance-critical UI |
| **Hybrid** | Plasmic for layout, code for interactions |

---

## API Reference

### Fetching Components

```typescript
import { PlasmicComponent } from "@plasmicapp/loader-nextjs";

// In a page component
export default function Page() {
  return <PlasmicComponent component="ComponentName" />;
}
```

### Server-Side Data

```typescript
import { PLASMIC } from "@/plasmic-init";

export async function getStaticProps() {
  const plasmicData = await PLASMIC.fetchComponentData("ComponentName");
  return { props: { plasmicData } };
}
```

### Authentication Headers (CMS API)

For CMS operations, use header:
```
x-plasmic-api-cms-tokens: <CMS_ID>:<TOKEN>
```

---

## Cross-References

| Need | Location |
|------|----------|
| Component specs | `docs/architecture/frontend/CAMPAIGNS.md` |
| Design philosophy | `frontend/design/dashboard/OVERVIEW.md` |
| Implementation status | `docs/architecture/frontend/SPEC_ALIGNMENT.md` |

---

## Resources

- [Plasmic Documentation](https://docs.plasmic.app/)
- [Next.js Quickstart](https://docs.plasmic.app/learn/nextjs-quickstart/)
- [Auth Integration](https://docs.plasmic.app/learn/auth-integration/)
- [CMS API Reference](https://docs.plasmic.app/learn/plasmic-cms-api-reference/)
- [GitHub Starter](https://github.com/plasmicapp/nextjs-starter)
