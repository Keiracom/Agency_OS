# Leadmagic Trial Report - AU Mobile/Email Discovery

**Date:** 2026-02-22  
**Status:** ⚠️ BLOCKED - Insufficient API Credits

---

## Executive Summary

Testing was **blocked** due to the Leadmagic API key having **0 credits**. The API requires credits upfront before attempting lookups (contrary to docs suggesting "no charge for not_found results" - that policy only applies once you have credits).

**Key Finding:** Cannot proceed with testing without purchasing a credit package.

---

## What Was Accomplished

### ✅ LinkedIn Profile Collection (30 of 50)

Successfully identified 30 Australian marketing agency decision-maker LinkedIn profiles:

| # | Name | Company | Title | LinkedIn |
|---|------|---------|-------|----------|
| 1 | Simon Gould | Sydney Digital Marketing | Founder | au.linkedin.com/in/speaktosimon |
| 2 | Ben Kinnaird | Sydney Digital Marketing | CEO | au.linkedin.com/in/ben-kinnaird |
| 3 | Benjamin Smolenaers | Digital Marketing Agency | CEO | au.linkedin.com/in/benjamin-smolenaers |
| 4 | Harry Sazos | Top SEO Sydney | Founder & CEO | au.linkedin.com/in/harry-sazos-8888aa2a |
| 5 | Dominique Ho | Digital Marketing Agency | CEO | au.linkedin.com/in/dominique-ho-58092959 |
| 6 | Ian Creaser | Rehab SEO | CEO & Founder | au.linkedin.com/in/ian-creaser-8082771a |
| 7 | Robert Tadros | Impressive Digital | Founder | au.linkedin.com/in/roberttadros |
| 8 | James Lawrence | Rocket Agency | Co-Founder | au.linkedin.com/in/jameslawrenceoz |
| 9 | Dain Walker | Rivyl | Founder & CEO | au.linkedin.com/in/dainwalker |
| 10 | Eric Stephens | True Sydney | Founder & CEO | au.linkedin.com/in/ericstephens1 |
| 11 | Sabri Suby | King Kong | Founder | au.linkedin.com/in/ssuby |
| 12 | Andy Merritt | Megaphone | Marketing | au.linkedin.com/in/andrew-marketing |
| 13 | James Lattouf | Megaphone Media | Founder | au.linkedin.com/in/jameslattouf |
| 14 | Sean Hewitt | Reload Media | EMEA | au.linkedin.com/in/seanhewittemea |
| 15 | Jamie Kritharas | Defiant Digital | CEO & Founder | au.linkedin.com/in/jamie-kritharas |
| 16 | Dim Apostolovski | Clearwater Agency | GM | au.linkedin.com/in/dim-apostolovski-8a47b0a8 |
| 17 | Nick Kritharas | Defiant Digital | GM | au.linkedin.com/in/nickkritharas |
| 18 | Glenn Lockwood | Clearwater Agency | Founder | au.linkedin.com/in/glennlockwood |
| 19 | Alex C | SEO Partners | Founder | au.linkedin.com/in/seo-consultant-brisbane |
| 20 | John Bucalo | Aussie SEO | Co-Founder | au.linkedin.com/in/adelaide-seo-consultant |
| 21 | Mike Haydon | Intelliwolf | Founder & CEO | au.linkedin.com/in/mikehaydon |
| 22 | Liam Ridings | Safari Digital SEO | Founder | au.linkedin.com/in/liamridings |
| 23 | Tom Galland | SEO Growth | MD | au.linkedin.com/in/tom-galland |
| 24 | Mike Hall | Rise SEO | Co-Founder | au.linkedin.com/in/mikehalldev |
| 25 | Claire Stevens | Crunchy Digital | Founder | linkedin.com/in/claire-stevens/ |
| 26 | Ruth Heenan | Strategic Communications | Founder | au.linkedin.com/in/ruth-heenan-bb63194 |
| 27 | Molly Hyndman | Swell Communications | Founder | au.linkedin.com/in/molly-hyndman |
| 28 | Maree Hopgood | GAT Agency | Founder/Director | au.linkedin.com/in/maree-hopgood-31a93128 |
| 29 | Marcus Torrisi | Vero Digital | Founder + Director | au.linkedin.com/in/marcustorrisi |
| 30 | Caroline Green | Spry PR & Communications | Founder | au.linkedin.com/in/caroline-green-2676b057 |

### ✅ API Documentation Reviewed

**Endpoints confirmed:**
- `POST https://api.leadmagic.io/v1/people/profile-search` (1 credit)
- `POST https://api.leadmagic.io/v1/people/email-finder` (1 credit)
- `POST https://api.leadmagic.io/v1/people/mobile-finder` (5 credits)

**Mobile Finder Input:**
```json
{
  "profile_url": "linkedin.com/in/johndoe"  // Works directly with LinkedIn URLs!
}
```

**Email Finder Input:**
```json
{
  "first_name": "John",
  "last_name": "Doe", 
  "domain": "company.com"
}
```

### ❌ API Testing Blocked

```json
{
  "error": "insufficient_credits",
  "detail": "This request requires 1 credit(s) but your account only has 0.00 credits remaining."
}
```

### ❌ Hunter Comparison Not Possible

Database has only 31 leads total, with 1 having a LinkedIn URL. No existing Hunter email data to compare against.

---

## Cost Analysis (Projected)

### For 50 Leads (Trial)

| Service | Credits/Lookup | 50 Lookups | Cost @ Essential ($0.01/credit) |
|---------|----------------|------------|--------------------------------|
| Profile Search | 1 | 50 | $0.50 |
| Email Finder | 1 | 50 | $0.50 |
| Mobile Finder | 5 | 250 | $2.50 |
| **Total** | | **350 credits** | **$3.50 AUD** |

### Full T5 Mobile Discovery (Assuming 500 leads/month)

| Service | Credits/Lead | Monthly Credits | Monthly Cost |
|---------|-------------|-----------------|--------------|
| Mobile Finder | 5 | 2,500 | $25.00 (Essential @ $0.01) |
| **Annual** | | 30,000 | **$300 AUD** |

### Kaspr Comparison

| Provider | Mobile/Month | Cost Estimate |
|----------|--------------|---------------|
| Kaspr | 500 | ~$99/mo USD (~$150 AUD) |
| Leadmagic | 500 | ~$25/mo AUD (Essential plan) |
| **Savings** | | **~$125 AUD/month** |

---

## Leadmagic Pricing Tiers

| Plan | Credits/Mo | $/Credit | Monthly | Good For |
|------|------------|----------|---------|----------|
| Basic | 2,500 | $0.024 | $59.99 | Light usage |
| Essential | 10,000 | $0.010 | $99.99 | **Recommended for trial** |
| Growth | 20,000 | $0.009 | $179.99 | Scaling ops |
| Advanced | 30,000 | $0.0087 | $259.99 | High volume |
| Professional | 50,000 | $0.0085 | $424.99 | Enterprise |
| Ultimate | 100,000 | $0.008 | $799.99 | Enterprise |

---

## API Features Confirmed

### Pros:
- ✅ Direct LinkedIn URL input for mobile finder
- ✅ Real-time validation
- ✅ Only charged when data found (after you have credits)
- ✅ Comprehensive profile enrichment included
- ✅ Good documentation, MCP integration available
- ✅ Significantly cheaper than Kaspr for mobiles

### Cons:
- ❌ No free trial credits (despite marketing claims)
- ❌ Requires upfront credit purchase to test
- ❌ Email finder needs domain (no LinkedIn → email directly)
- ❓ AU mobile hit rate unknown (needs testing)

---

## Recommendations

### Immediate Action Required

**Purchase Essential Plan ($99.99 USD) to proceed with testing:**
- 10,000 credits = ~2,000 mobile lookups or ~10,000 email lookups
- Enough for full validation + 1 month of operations

### Test Plan (Once Credits Available)

1. **Profile Search** (50 lookups, 50 credits): Extract names/domains from LinkedIn URLs
2. **Email Finder** (50 lookups, 50 credits): Compare with Hunter results
3. **Mobile Finder** (50 lookups, 250 credits): Validate AU mobile hit rate

**Total trial cost: 350 credits (~$3.50 of Essential plan)**

### Decision Framework

| Scenario | Recommendation |
|----------|----------------|
| AU mobile hit rate > 30% | ✅ Adopt for T5 (replace Kaspr) |
| AU mobile hit rate > 50% | ✅ Strong confirm |
| Email match rate > 80% vs Hunter | ✅ Consider replacing Hunter T3 |
| Email match rate < 60% vs Hunter | ❌ Keep Hunter for email |

---

## Next Steps

1. **Main agent decision needed:** Purchase Essential Plan ($99.99)?
2. Once credits available, re-run this trial
3. Full 50-lead validation with actual API calls
4. Compare results with any existing Hunter data
5. Generate final recommendation

---

## Files Generated

- `linkedin_profiles.json` - 30 AU marketing agency LinkedIn profiles ready for testing
- `TRIAL_REPORT.md` - This report

---

*Report generated by subagent. Credits required to complete API testing.*
