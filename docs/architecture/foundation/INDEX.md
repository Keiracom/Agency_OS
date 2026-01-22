# Foundation — Agency OS

**Purpose:** Core architectural rules, API layer, and database schema.
**Status:** LOCKED (changes require CEO approval)

---

## Documents

| Doc | Purpose | Status |
|-----|---------|--------|
| [DECISIONS.md](DECISIONS.md) | Technology stack choices | ✅ Locked |
| [IMPORT_HIERARCHY.md](IMPORT_HIERARCHY.md) | Layer import rules | ✅ Locked |
| [RULES.md](RULES.md) | Claude Code development protocol | ✅ Locked |
| [FILE_STRUCTURE.md](FILE_STRUCTURE.md) | Project directory layout | ✅ Locked |
| [API_LAYER.md](API_LAYER.md) | FastAPI routes, auth, multi-tenancy | ✅ Complete |
| [DATABASE.md](DATABASE.md) | SQLAlchemy models, migrations | ✅ Complete |

---

## Key Principles

1. **Architecture First** — Update docs before code
2. **Single Source of Truth** — Each topic has ONE doc
3. **Import Hierarchy Enforced** — models → integrations → engines → orchestration
4. **Soft Deletes Only** — Never hard delete records

---

## Cross-References

- [Master Index](../ARCHITECTURE_INDEX.md)
- [TODO.md](../TODO.md) — Gaps and priorities
