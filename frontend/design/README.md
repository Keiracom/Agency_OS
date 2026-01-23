# Agency OS Design System

**Purpose:** Design documentation, UI specifications, and visual guidelines for Agency OS frontend.

**Tool:** [v0.dev](https://v0.dev) for AI-powered UI generation + Claude Code for integration.

---

## Folder Structure

```
frontend/design/
├── README.md              # This file
├── dashboard/             # Dashboard redesign (Q1 2026)
│   ├── OVERVIEW.md        # Goals, principles, terminology
│   ├── campaigns.md       # Campaign allocation UI
│   ├── metrics.md         # Metrics display decisions
│   └── mockups/           # Screenshots, v0 exports
└── tokens/                # Design tokens (future)
    ├── colors.md
    ├── typography.md
    └── spacing.md
```

---

## Current Focus: Dashboard Redesign

See `dashboard/OVERVIEW.md` for the active redesign initiative.

**Key Principles:**
1. **Outcome-focused** - Show meetings booked, not lead counts
2. **Transparency** - Activity data as proof of work
3. **No commodity language** - We're not selling leads

---

## Design-to-Code Workflow

1. **Spec** - Document requirements in `design/` folder
2. **Generate** - Use v0.dev API to create visual mockups
3. **Integrate** - Claude Code wires up APIs, auth, data
4. **Review** - Run locally, screenshot feedback
5. **Iterate** - Adjust until vision matches
6. **Ship** - Commit component changes

---

## Related Architecture Docs

- `docs/architecture/frontend/DASHBOARD.md` - Technical specification
- `docs/architecture/frontend/TECHNICAL.md` - Frontend architecture
- `docs/architecture/frontend/ADMIN.md` - Admin panel spec
