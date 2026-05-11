# Deprecated Rule: R# / NAME

**Retired:** YYYY-MM-DD via PR #NNN
**Replaced by:** <deterministic mechanism file path / "structural prevention" / "merged into R#">

## Incident that created this rule

Brief paragraph describing the original failure mode this rule guarded against, the session/date it surfaced, and the immediate consequence (what broke, what Dave had to fix).

## Original RULES_PROMPT text (verbatim)

```
<exact lines from src/bot_common/enforcer_rules.py RULES_PROMPT for this rule before retirement>
```

## Why this is safe to retire

Concrete reason the rule is no longer load-bearing. Examples:
- Replaced by a deterministic mechanism (link to function + tests)
- Underlying failure mode no longer possible due to architectural change
- Zero fires in N sessions + supporting evidence the original incident class is gone

## Verification

Commands or queries a future agent can run to confirm the rule is genuinely unneeded.

## What to watch for

If you see X behaviour return, re-instate this rule (or its successor). Specific symptoms or log patterns.

---

*This file is institutional memory. Do not delete. If the deprecation turns out to be wrong, revive the rule and link the new incident here.*
