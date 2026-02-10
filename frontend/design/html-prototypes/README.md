# HTML Prototypes — Design SSOT

These HTML files are the **Single Source of Truth** for Agency OS UI design.

All React ports **must visually match** these prototypes.

## Sprint 2 Primary References

| File | Purpose | Priority |
|------|---------|----------|
| `dashboard-v3.html` | Command Center dashboard | **PRIMARY** |
| `leads-v2.html` | Leads list with ALS tiers | **PRIMARY** |
| `lead-detail-v2.html` | Individual lead view | Sprint 2 |

## Secondary References

| File | Purpose |
|------|---------|
| `dashboard-v2.html` | Previous dashboard iteration |
| `dashboard-v4-customer.html` | Customer-facing variant |
| `dashboard-campaigns.html` | Campaign management view |
| `dashboard-inbox.html` | Unified inbox view |
| `dashboard-prospects.html` | Prospect pipeline view |

## Usage

Before porting any component:
1. `cat` the relevant HTML file
2. Extract the exact structure, classes, and content
3. Map HTML classes to theme tokens (bg-void, bg-surface, accent-primary, etc.)
4. Build React component matching the prototype exactly

## Theme Token Mapping

| Prototype Class | Theme Token |
|-----------------|-------------|
| Dark backgrounds | `bg-void`, `bg-base` |
| Card surfaces | `bg-surface` |
| Accent colors | `accent-primary`, `accent-secondary` |
| Text | `text-primary`, `text-muted` |
| Borders | `border-subtle` |

---

*Last updated: 2026-02-10*
