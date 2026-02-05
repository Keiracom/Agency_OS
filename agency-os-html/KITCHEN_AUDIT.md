# Kitchen vs Table Audit Report

**Date:** 2026-02-03  
**Auditor:** Elliot (Subagent)  
**Scope:** All HTML prototypes in ~/clawd/agency-os-html/

---

## 1. Kitchen vs Table Principle Summary

From MEMORY.md and daily logs:

> **"Kitchen vs Table: Never show internal metrics (warmup, AI costs) to customers. Only outcomes."**

### What is "Kitchen" (Don't Show)
- Internal metrics we control (send times, volume decisions)
- Technical details (API sources, automation mentions)  
- System internals (warmup, ALS scoring mechanics)
- Provider names (Twilio, Vapi, Salesforce, etc.)
- Campaign naming conventions
- How the sausage is made

### What is "Table" (Show)
- Outcomes only: meetings booked, replies received, pipeline value
- Clean labels: "Lead Score" not "ALS Score"
- "Matched your target criteria" not "Source: Apollo enrichment"
- "Multi-Channel Sequence" not internal campaign names

### Historical Cleanups (2026-02-01)
| Before (Kitchen) | After (Table) |
|------------------|---------------|
| "ALS Score" | "Lead Score" |
| "Via Unipile automation" | (removed) |
| "Campaign: Q1 Agency Outreach — Step 1" | (removed) |
| "Source: Apollo enrichment" | "Matched your target criteria" |
| Campaign names exposed | "Multi-Channel Sequence" |

---

## 2. Violations Found Per Page

### ✅ dashboard.html — 1 Violation

| Line/Section | Violation | Severity |
|--------------|-----------|----------|
| Insight Card | `"Tuesday emails are crushing it"` + `"Your Tuesday morning sends have a 42% open rate — double your average. Consider shifting more volume to Tuesdays."` | **MEDIUM** |

**Issue:** Exposes internal send timing decisions. Client shouldn't know we control *when* emails go out.

**Fix:** Change to outcome-focused:
```html
<!-- Before -->
<div class="insight-headline">Tuesday emails are crushing it</div>
<div class="insight-detail">Your Tuesday morning sends have a 42% open rate — double your average. Consider shifting more volume to Tuesdays.</div>

<!-- After -->
<div class="insight-headline">Tuesday is your best day</div>
<div class="insight-detail">Your prospects are most engaged on Tuesdays — 42% open rate vs 21% average. Expect higher activity mid-week.</div>
```

---

### ✅ leads.html — CLEAN ✓

No violations found. Score shown without "ALS" prefix, tiers are outcome-based.

---

### ⚠️ lead-detail.html — 2 Violations

| Line/Section | Violation | Severity |
|--------------|-----------|----------|
| Score Breakdown | Shows component breakdown (Engagement 36/40, Fit 35/40, Timing 18/20, Recency +5) | **LOW** |
| AI Call Transcript | `"AI Agent"` label visible to client | **HIGH** |

**Issue 1 - Score Breakdown:** Exposes internal scoring mechanics. Clients might ask "why is my Fit Score only 35?" and expect to change it.

**Fix:** Either remove breakdown OR use vaguer labels:
```html
<!-- Before -->
<span class="score-row-label">Engagement</span>
<span class="score-row-label">Fit Score</span>
<span class="score-row-label">Timing</span>
<span class="score-row-label">Recency Boost</span>

<!-- After (if keeping) -->
<span class="score-row-label">Activity Level</span>
<span class="score-row-label">Profile Match</span>
<span class="score-row-label">Momentum</span>
<span class="score-row-label">Recent Activity</span>
```

**Issue 2 - AI Agent:** Call transcript shows `"AI Agent"` as speaker. This explicitly exposes automation.

**Fix:** Use ambiguous label:
```html
<!-- Before -->
<div class="speaker-name">AI Agent <span class="timestamp">0:00</span></div>

<!-- After -->
<div class="speaker-name">Emma (Agent) <span class="timestamp">0:00</span></div>
<!-- or simply -->
<div class="speaker-name">Your Team <span class="timestamp">0:00</span></div>
```

---

### ⚠️ campaigns.html — 2 Violations

| Line/Section | Violation | Severity |
|--------------|-----------|----------|
| All campaign cards | Internal naming conventions exposed: "Q1 Agency Outreach", "SaaS Founders Campaign", "December Warm-Up", "LinkedIn Only Test" | **LOW** |
| Start dates | "Started Jan 15, 2026" — exposes internal scheduling | **LOW** |

**Note:** These are borderline. Agencies managing campaigns *do* need to name them. But if this UI is ever client-facing (white-label), these would be violations.

**Fix (if needed):**
```html
<!-- Before -->
<h3>Q1 Agency Outreach</h3>
<span class="start-date">Started Jan 15, 2026</span>

<!-- After -->
<h3>Agency Growth Sequence</h3>
<span class="start-date">Running for 16 days</span>
```

---

### ⚠️ campaign-detail.html — 1 Violation

| Line/Section | Violation | Severity |
|--------------|-----------|----------|
| Metrics grid | "1,842 Emails Sent" — exposes volume control | **LOW** |

**Note:** Borderline. Agencies may want to see volume metrics. But "Sent" count implies we control cadence.

**Fix (if needed):**
```html
<!-- Before -->
<div class="metric-label">Emails Sent</div>

<!-- After -->
<div class="metric-label">Touches</div>
```

---

### ✅ replies.html — CLEAN ✓

No violations. Shows replies and email content only.

---

### ⚠️ reply-detail.html — 1 Violation

| Line/Section | Violation | Severity |
|--------------|-----------|----------|
| Lead Details Panel | `<span class="lead-detail-value">Q1 Agency Outreach</span>` | **MEDIUM** |

**Issue:** This was explicitly called out in 2026-02-01 log as kitchen content! Campaign names shouldn't be exposed.

**Fix:**
```html
<!-- Before -->
<div class="lead-detail-row">
  <span class="lead-detail-label">Campaign</span>
  <span class="lead-detail-value">Q1 Agency Outreach</span>
</div>

<!-- After -->
<div class="lead-detail-row">
  <span class="lead-detail-label">Sequence</span>
  <span class="lead-detail-value">Multi-Channel Outreach</span>
</div>
```

---

### ✅ reports.html — 1 Minor Violation

| Line/Section | Violation | Severity |
|--------------|-----------|----------|
| Channel Performance | "Sent" column shows exact send counts per channel | **LOW** |

**Note:** Borderline. Agencies need channel analytics. The "Sent" metric does expose volume decisions.

---

### ⚠️ settings.html — 1 Violation

| Line/Section | Violation | Severity |
|--------------|-----------|----------|
| Integrations section | Provider names exposed: "Gmail", "LinkedIn", "Twilio SMS", "Vapi Voice", "Salesforce" | **MEDIUM** |

**Issue:** Exposes the tech stack. Client doesn't need to know we use "Twilio" or "Vapi".

**Fix:**
```html
<!-- Before -->
<div class="integration-name">Twilio SMS</div>
<div class="integration-name">Vapi Voice</div>

<!-- After -->
<div class="integration-name">SMS</div>
<div class="integration-name">Voice Calling</div>
```

---

### ⚠️ billing.html — 1 Violation

| Line/Section | Violation | Severity |
|--------------|-----------|----------|
| Usage Meters | Shows "Leads", "Emails Sent", "AI Calls" as separate metered resources | **LOW** |

**Note:** Borderline. These ARE what they're paying for. But "AI Calls" explicitly mentions AI.

**Fix:**
```html
<!-- Before -->
<span class="meter-label">AI Calls</span>

<!-- After -->
<span class="meter-label">Voice Calls</span>
```

---

### ✅ onboarding.html — CLEAN ✓

No violations. User-facing onboarding flow with clean labels.

---

## 3. Summary

| Page | Violations | Severity |
|------|------------|----------|
| dashboard.html | 1 | MEDIUM |
| leads.html | 0 | — |
| lead-detail.html | 2 | HIGH, LOW |
| campaigns.html | 2 | LOW |
| campaign-detail.html | 1 | LOW |
| replies.html | 0 | — |
| reply-detail.html | 1 | MEDIUM |
| reports.html | 1 | LOW |
| settings.html | 1 | MEDIUM |
| billing.html | 1 | LOW |
| onboarding.html | 0 | — |

**Total:** 10 violations across 8 pages

### Priority Fixes
1. **HIGH:** lead-detail.html — Remove "AI Agent" label from call transcript
2. **MEDIUM:** reply-detail.html — Replace campaign name with generic "Multi-Channel Sequence"
3. **MEDIUM:** settings.html — Replace provider names with generic labels
4. **MEDIUM:** dashboard.html — Reframe insight to be outcome-focused

---

## 4. Recommended Next Steps

1. **Immediate:** Fix the 4 MEDIUM/HIGH priority items
2. **Review:** Decide if campaigns.html will ever be white-labeled/client-facing
3. **Policy:** Document which pages are "internal" vs "client-facing" so future violations are caught
4. **Pattern:** Consider a CSS class `.kitchen-only` for elements that should be hidden in client-facing mode

---

*"Client sees outcomes, not how the sausage is made."*
