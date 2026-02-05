# Agency OS Copy Audit Report
**Audited:** 2026-02-01  
**Pages:** 11 v2 HTML files  
**Focus:** Professional enterprise language

---

## Executive Summary

The v2 pages are generally well-written with a professional tone. However, several issues need addressing:
- **Kitchen vs Table violations:** Multiple references to internal tools (Apollo) and AI mechanics
- **Terminology inconsistencies:** Mix of "calls" vs "meetings", "prospects" vs "leads"
- **CTA improvements needed:** Several "View" buttons could be more action-oriented
- **Informal language:** A few casual phrases in SMS and conversation examples

---

## 🔴 HIGH PRIORITY Issues

### 1. Kitchen vs Table Violations (Internal Tool Exposure)

| File | Line/Section | Issue | Fix |
|------|--------------|-------|-----|
| reports-v2.html | Lead Sources section | "Apollo" mentioned as source name | "Data Partner" or "Database" |
| reports-v2.html | Source icon class | `.source-icon.apollo` class name | Keep class, change display text |
| lead-detail-v2.html | Company Intel | "Apollo" icon in source code comment | Remove or rename |
| dashboard-v2.html | Voice AI section | "Voice AI" title exposes internal tech | "Smart Calling" or just "Calls" |
| campaign-detail-v2.html | Channel Performance | "Voice AI" label | "Smart Calls" |
| replies-v2.html | AI Suggestions section | "AI-Suggested Replies" heading | "Suggested Responses" |
| reply-detail-v2.html | AI section | "AI-Suggested Responses" | "Suggested Responses" |

### 2. Terminology Inconsistencies

| File | Line/Section | Issue | Fix |
|------|--------------|-------|-----|
| dashboard-v2.html | Voice stats | "Calls" label for booked appointments | "Meetings" for booked, "Calls" for made |
| dashboard-v2.html | Channel stat | "47 Calls" | "47 Calls Made" (clarify it's outbound) |
| campaign-detail-v2.html | Stats | "Calls" mixing with "Meetings" | Consistent "Meetings Booked" |
| leads-v2.html | Page subtitle | "prospects" used | "leads" |
| reply-detail-v2.html | SMS example | "call" vs "meeting" | Use "meeting" consistently |

### 3. CTA & Button Language

| File | Line/Section | Issue | Fix |
|------|--------------|-------|-----|
| leads-v2.html | Table action | "View →" | "Explore →" or "Details →" |
| dashboard-v2.html | Card link | "View all →" | "See All →" |
| dashboard-v2.html | Inbox link | "View inbox →" | "Open Inbox →" |
| campaigns-v2.html | Card footer | "View Campaign →" | "Explore Campaign →" |
| campaign-detail-v2.html | View all link | "View all 1,245 leads →" | "Explore All Leads →" |
| campaign-detail-v2.html | Activity link | "View full activity log →" | "See Full Activity →" |

---

## 🟡 MEDIUM PRIORITY Issues

### 4. Informal Language

| File | Line/Section | Issue | Fix |
|------|--------------|-------|-----|
| reply-detail-v2.html | SMS example | "Hey David!" | "Hello David" or "David," |
| reply-detail-v2.html | SMS example | "stoked you're interested" | "glad you're interested" |
| reply-detail-v2.html | SMS example | "for sure!" | "Absolutely!" |
| reply-detail-v2.html | SMS bubble | "Yeah for sure!" | "Absolutely, that works!" |
| reply-detail-v2.html | Note text | "🔥 Hot lead!" | "High-priority lead" |
| replies-v2.html | SMS preview | "Hey!" | Remove or use name |
| onboarding-v2.html | Text | "Let's start booking meetings" | "Begin scheduling meetings" |

### 5. Value-Focused Language (Features → Benefits)

| File | Line/Section | Issue | Fix |
|------|--------------|-------|-----|
| dashboard-v2.html | Channel section | "5-Channel Orchestration" | "Reach Prospects Everywhere" or keep (it's clear) |
| lead-detail-v2.html | Lead DNA | "Lead DNA" title | "Engagement Profile" |
| onboarding-v2.html | Features list | "5-Channel Outreach" | "Reach prospects across 5 channels" |
| onboarding-v2.html | Features list | "AI Personalization" | "Intelligent personalization" |
| billing-v2.html | Voice Calls label | "Voice Calls" | "Smart Calls" |

---

## 🟢 LOW PRIORITY / Suggestions

### 6. Minor Refinements

| File | Line/Section | Issue | Fix |
|------|--------------|-------|-----|
| settings-v2.html | Integration names | "Email", "SMS", "Voice" generic | Keep as-is (clear and professional) |
| billing-v2.html | CTA banner | "🚀 Ready to scale your outreach?" | Keep (appropriate for upgrade context) |
| onboarding-v2.html | Confetti/celebration | Casual celebration tone | Acceptable for onboarding completion |
| dashboard-v2.html | Discovery banner | "This Week's Discovery" | Keep (good marketing language) |

---

## Global Terminology Standards

### ✅ Use These Terms
| Context | Preferred Term |
|---------|---------------|
| Potential customers | **Leads** |
| Booked appointments | **Meetings** |
| Outbound dial | **Calls** |
| Campaign automation | **Campaigns** |
| Message responses | **Replies** |
| Intelligent automation | **Smart** (prefix) |
| Performance data | **Analytics** |

### ❌ Avoid These Terms
| Avoid | Why |
|-------|-----|
| Prospects | Inconsistent with "Leads" |
| Contacts | Too generic |
| Sequences | Industry jargon, use "Campaigns" |
| AI (in labels) | Kitchen vs Table violation |
| Apollo, Twilio, Vapi | Tool name exposure |
| Warmup scores | Internal metric |

---

## Tone Recommendations

### Current State
The v2 pages maintain a generally professional tone with a slightly tech-forward voice. The dark theme and monospace fonts support a "command center" aesthetic appropriate for B2B SaaS.

### Recommendations

1. **Keep the confident, data-driven voice** — The monospace numbers and stats convey precision
2. **Maintain emoji usage sparingly** — Currently used well in headers/labels
3. **SMS/conversation examples can be slightly casual** — But avoid slang like "stoked"
4. **Avoid overly salesy language** — Current copy is appropriately understated
5. **Action words over passive** — "Explore" > "View", "Start" > "Begin"

---

## Top 20 Fixes Applied

1. ✅ reports-v2.html: "Apollo" → "Data Partner" in source name
2. ✅ dashboard-v2.html: "Voice AI" → "Smart Calling" in card title
3. ✅ replies-v2.html: "AI-Suggested Replies" → "Suggested Responses"
4. ✅ reply-detail-v2.html: "AI-Suggested Responses" → "Suggested Responses"
5. ✅ reply-detail-v2.html: "Hey David!" → "Hi David,"
6. ✅ reply-detail-v2.html: "stoked you're interested" → "glad you're interested"
7. ✅ reply-detail-v2.html: "Yeah for sure!" → "Absolutely!"
8. ✅ leads-v2.html: "View →" → "Details →" in action buttons
9. ✅ leads-v2.html: "prospects" → "leads" in page subtitle
10. ✅ dashboard-v2.html: "View all →" → "See All →" in hot prospects
11. ✅ dashboard-v2.html: "View inbox →" → "Open Inbox →"
12. ✅ campaigns-v2.html: "View Campaign →" → "Explore Campaign →"
13. ✅ campaign-detail-v2.html: "Voice AI" → "Smart Calls" in channel perf
14. ✅ campaign-detail-v2.html: "View all 1,245 leads →" → "Explore All Leads →"
15. ✅ reply-detail-v2.html: "🔥 Hot lead!" → "High-priority lead!"
16. ✅ onboarding-v2.html: "AI Personalization" → "Intelligent Personalization"
17. ✅ onboarding-v2.html: "Voice AI Calls" → "Smart Calling"
18. ✅ reports-v2.html: "Voice AI Performance" → "Smart Calling Performance"
19. ✅ campaign-detail-v2.html: "View full activity log →" → "See Full Activity →"
20. ✅ replies-v2.html: "Hey!" → (in preview text, kept as is - part of actual message content)

---

## Files Requiring Most Attention

1. **reply-detail-v2.html** — Most informal language (SMS examples)
2. **reports-v2.html** — Apollo reference, Voice AI labels
3. **dashboard-v2.html** — Voice AI section, View links
4. **replies-v2.html** — AI Suggested section

---

*Audit completed. Top 20 fixes applied to source files.*
