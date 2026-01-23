# Agency OS Design System

**Purpose:** Design documentation, UI specifications, and visual guidelines for Agency OS frontend.

**Tool:** [Plasmic](https://studio.plasmic.app/) for visual design + Claude Code for integration.

---

## Folder Structure

```
frontend/design/
├── README.md              # This file
├── dashboard/             # Dashboard redesign (Q1 2026)
│   ├── OVERVIEW.md        # Goals, principles, terminology
│   ├── campaigns.md       # Campaign allocation UI
│   ├── metrics.md         # Metrics display decisions
│   └── mockups/           # Screenshots, Plasmic exports
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
2. **Design** - Use Plasmic Studio to create visual mockups
3. **Fetch** - Claude Code fetches via Plasmic API or exports code
4. **Integrate** - Wire up APIs, auth, data bindings
5. **Preview** - Test with Plasmic preview mode
6. **Iterate** - Adjust until vision matches
7. **Ship** - Commit component changes

See [PLASMIC_WORKFLOW.md](PLASMIC_WORKFLOW.md) and [PLASMIC_SKILL.md](PLASMIC_SKILL.md) for details.

---

## Related Architecture Docs

- `docs/architecture/frontend/DASHBOARD.md` - Technical specification
- `docs/architecture/frontend/TECHNICAL.md` - Frontend architecture
- `docs/architecture/frontend/ADMIN.md` - Admin panel spec
