# Session Learning Report Template

This template is used by the application tracker to generate session reports.

---

## Session Learning Report

**Generated:** {{ timestamp }}
**Session:** {{ session_id }}

---

### Summary

| Metric | Value |
|--------|-------|
| Total Knowledge | {{ stats.total_knowledge }} |
| Applied | {{ stats.applied_count }} |
| Pending | {{ stats.unapplied_count }} |
| Recently Added (24h) | {{ stats.recently_added }} |
| Recently Applied (24h) | {{ stats.recently_applied }} |
| Avg Decay Score | {{ stats.avg_decay_score }} |
| At Risk (< 0.5) | {{ stats.at_risk_count }} |

---

### New Knowledge Added

{% for item in recently_added %}
- [{{ item.source_type }}] {{ item.summary or item.content[:60] }} - *{{ item.category }}*
{% endfor %}

---

### Knowledge Applied This Session

{% for item in recently_applied %}
- {{ item.summary or item.content[:40] }} → **Applied to:** {{ item.applied_context }}
{% endfor %}

---

### Pending Application (will decay if not used)

{% for item in pending_application %}
- {{ item.summary or item.content[:50] }} - decay score: {{ item.decay_score }} ({{ item.days_old }}d old)
{% endfor %}

---

## The Contract

**"I add a tool, I tell you how I applied it."**

Every piece of knowledge added to the system must eventually be applied to a real task.
Unapplied knowledge decays by 0.1 per day. Below 0.3, it gets pruned.

This ensures:
1. We don't just collect - we **apply**
2. Stale, unused knowledge doesn't clutter the system
3. Learning is tied to **action**

---

## Application Examples

Good application context examples:
- "Used HN insight about vector DBs to recommend Pinecone for client project"
- "Applied GitHub trending repo to speed up image processing pipeline"
- "Referenced ProductHunt tool in Dave's workflow optimization discussion"

Bad application context:
- "Read it" ❌
- "Noted" ❌
- "Will use later" ❌

Be specific. What task? What outcome?
