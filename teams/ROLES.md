# Agent Roles

Elliot (main) orchestrates all work. Sub-agents are spawned for specific tasks and report back.

## 🔧 Linter
**Purpose:** Fix CI failures, code style, type errors

**Triggers:**
- CI pipeline fails
- New code needs formatting
- TypeScript/Python errors detected

**SOP:** `workflows/ci-fix.md`

**Outputs:**
- Clean code that passes all checks
- Summary of changes made

---

## 🧪 Tester
**Purpose:** Write tests, run E2E flows, validate functionality

**Triggers:**
- New feature completed
- Bug fix needs verification
- E2E journey needs testing (J0-J6)

**SOP:** `workflows/e2e-testing.md`

**Outputs:**
- Test files
- Pass/fail report with evidence
- Bug reports if issues found

---

## 👁️ Reviewer
**Purpose:** Code review, security checks, quality gates

**Triggers:**
- PR ready for review
- New integration added
- Security-sensitive changes

**SOP:** `workflows/code-review.md`

**Outputs:**
- Review comments
- Approval or rejection with reasons
- Security findings if any

---

## 🏗️ Builder
**Purpose:** Implement features, fix bugs, write code

**Triggers:**
- Task assigned from backlog
- Bug report needs fixing
- Feature request approved

**SOP:** `workflows/build.md`

**Outputs:**
- Working code
- PR ready for review
- Documentation updates if needed

---

## 📝 Documenter
**Purpose:** Update docs, SOPs, memory files

**Triggers:**
- New workflow created
- Process changed
- Knowledge needs capturing

**SOP:** `workflows/documentation.md`

**Outputs:**
- Updated markdown files
- Clear, actionable documentation

---

## Spawning Agents

Use `sessions_spawn` with a clear task description:

```
Task: [ROLE] - [Specific objective]
Context: [Relevant files/info]
Output: [Expected deliverable]
Report to: main session when complete
```

All agents follow the same core principles:
1. Read relevant SOPs before starting
2. Document what you do
3. Report back with clear outcomes
4. Don't push to main — PRs only
