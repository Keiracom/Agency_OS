# Plasmic Navigation & Access Skill

**Purpose:** Quick reference for accessing and navigating Plasmic Studio for Agency OS design work.
**Last Updated:** 2026-01-23

---

## Quick Access

### Plasmic Studio
- **URL:** https://studio.plasmic.app/
- **Login:** Use Google OAuth or email associated with the project

### Environment Variables
```bash
# Already configured in frontend/.env.local and config/.env
NEXT_PUBLIC_PLASMIC_PROJECT_API_TOKEN=G7yBb...9RA
PLASMIC_PREVIEW_SECRET=agency-os-plasmic-preview-2026
```

---

## Navigation Guide

### 1. Opening a Project

1. Go to https://studio.plasmic.app/
2. Select "Agency OS" project from dashboard
3. Project ID is in URL: `https://studio.plasmic.app/projects/PROJECTID`

### 2. Finding Components

| Location in Studio | What You'll Find |
|-------------------|------------------|
| **Pages** panel (left) | All page layouts |
| **Components** panel | Reusable component library |
| **Assets** panel | Images, icons, fonts |
| **Data** panel | Data queries & bindings |

### 3. Getting API Token

1. Open project in Plasmic Studio
2. Click **"Code"** button in top toolbar
3. Copy the public API token shown

### 4. Preview Mode

Access live preview while designing:
```
http://localhost:3000/api/preview?secret=agency-os-plasmic-preview-2026&slug=/dashboard
```

Exit preview:
```
http://localhost:3000/api/exit-preview
```

---

## Common Tasks

### Export Component Code

1. Select component in Plasmic Studio
2. Click **"Code"** → **"Export"**
3. Choose export format (React/Next.js)
4. Copy generated code

### Connect to Codebase

```typescript
// In plasmic-init.ts
import { initPlasmicLoader } from "@plasmicapp/loader-nextjs";

export const PLASMIC = initPlasmicLoader({
  projects: [
    {
      id: process.env.NEXT_PUBLIC_PLASMIC_PROJECT_ID!,
      token: process.env.NEXT_PUBLIC_PLASMIC_PROJECT_API_TOKEN!,
    },
  ],
  preview: true,
});
```

### Fetch Component Data (SSR/SSG)

```typescript
import { PLASMIC } from "@/plasmic-init";

export async function getStaticProps() {
  const plasmicData = await PLASMIC.fetchComponentData("ComponentName");
  return { props: { plasmicData } };
}
```

### Render Plasmic Component

```typescript
import { PlasmicComponent } from "@plasmicapp/loader-nextjs";

export default function Page() {
  return <PlasmicComponent component="ComponentName" />;
}
```

---

## Keyboard Shortcuts (Plasmic Studio)

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + K` | Quick search |
| `Cmd/Ctrl + S` | Save |
| `Cmd/Ctrl + Z` | Undo |
| `Cmd/Ctrl + Shift + Z` | Redo |
| `Cmd/Ctrl + D` | Duplicate |
| `Delete` | Remove element |
| `Cmd/Ctrl + G` | Group elements |
| `Cmd/Ctrl + Shift + G` | Ungroup |
| `Space + Drag` | Pan canvas |
| `Cmd/Ctrl + +/-` | Zoom in/out |
| `Cmd/Ctrl + 0` | Zoom to fit |
| `Cmd/Ctrl + 1` | Zoom to 100% |

---

## Workflow Integration

### Design → Code Flow

```
1. CEO designs in Plasmic Studio
   ↓
2. Claude fetches via API or exports code
   ↓
3. Claude implements in codebase
   ↓
4. Test with preview mode
   ↓
5. Deploy
```

### When to Use Plasmic vs Code

| Use Plasmic | Use Code |
|-------------|----------|
| Layout changes | Complex state logic |
| Visual prototypes | Performance-critical |
| Rapid iteration | Custom animations |
| Non-technical design | TypeScript integrations |

---

## Troubleshooting

### "Component not found"
- Ensure component is published in Plasmic Studio
- Check project ID and API token are correct
- Verify component name matches exactly

### "Preview not working"
- Check `PLASMIC_PREVIEW_SECRET` matches in URL and .env
- Ensure dev server is running on localhost:3000
- Try exiting and re-entering preview mode

### "Changes not appearing"
- Plasmic caches aggressively - wait or force refresh
- Check you're viewing the correct project version
- For SSG, rebuild may be required

---

## Resources

| Resource | URL |
|----------|-----|
| Plasmic Docs | https://docs.plasmic.app/ |
| Next.js Guide | https://docs.plasmic.app/learn/nextjs-quickstart/ |
| Community Forum | https://forum.plasmic.app/ |
| GitHub Starter | https://github.com/plasmicapp/nextjs-starter |

---

## Related Files

| File | Purpose |
|------|---------|
| `PLASMIC_WORKFLOW.md` | Full collaboration workflow |
| `INDEX.md` | Design navigation hub |
| `frontend/.env.local` | Environment variables |
| `plasmic-init.ts` | Plasmic loader config (to create) |
