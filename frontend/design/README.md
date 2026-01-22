# Agency OS Design System

**Purpose:** Design documentation, UI specifications, and visual guidelines for Agency OS frontend.

**Tool:** [Onlook](https://onlook.com) for visual React component editing.

---

## Folder Structure

```
frontend/design/
├── README.md              # This file
├── dashboard/             # Dashboard redesign (Q1 2026)
│   ├── OVERVIEW.md        # Goals, principles, terminology
│   ├── campaigns.md       # Campaign allocation UI
│   ├── metrics.md         # Metrics display decisions
│   └── mockups/           # Onlook exports, screenshots
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

1. **Spec** - Document in `design/` folder
2. **Visual Edit** - Use Onlook on `components/`
3. **Review** - Screenshot to `mockups/`
4. **Ship** - Commit component changes

---

## Related Architecture Docs

- `docs/architecture/frontend/DASHBOARD.md` - Technical specification
- `docs/architecture/frontend/TECHNICAL.md` - Frontend architecture
- `docs/architecture/frontend/ADMIN.md` - Admin panel spec
