## Session End Protocol

Before context exhaustion or /reset:
1. Run session-end 3-store check: `python scripts/session_end_check.py` — fix any gaps before proceeding
2. Write CEO Memory Update to public.ceo_memory (key: ceo:session_end_YYYY-MM-DD)
3. Update directive counter in public.ceo_memory (ceo:directives.last_number)
4. Write daily_log to elliot_internal.memories
5. Report completion with directive number and PR links

**Context thresholds:** 40% -> self-alert | 50% -> alert Dave | 60% -> execute session end protocol
