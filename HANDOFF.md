# Session Handoff — 2026-02-27

## Next Action
Run E2E Test #31 after Railway redeploys. Both PRs just merged — wait 90 seconds.

## PRs Merged This Session
- PR #116: website→organization_website column fix
- PR #117: T1.5b reads "link" not "url" key
- PR #118: T2 populates lead.website from LinkedIn
- PR #119: CLOSED (superseded by #120)
- PR #120: Full v2.2 waterfall alignment (T1.25 built, tier reorder, trading_name fixes)
- PR #121: T1.25 self.abn → self.abn_client fix
- PR #122: DM discovery chain fix (T2 stores employees, T2.5 scrapes profiles, ALS authority scoring fixed)

## Test #31 Expected Results
- T1.25 runs for ABN leads → trading names
- T1.5b/T1.5a use trading names → 80%+ hit rate
- T2.5 scrapes employee profiles → real DM titles
- Authority score populated (was always 0)
- ALS ceiling now 85+ (was 60)
- Target: 40+ leads, avg ALS 55+

## Test #31 Campaign
campaign_id: d97208cb-65e9-4356-822f-36681c6fc441
client_id: 87554553-e691-40c9-9307-eab684d20183

## Known State
- LEADMAGIC_MOCK=true (emails are synthetic)
- target_industries: ["marketing_agency"]
- ALS gate: 20
- All other mocks: MOCK_CRM, MOCK_UNIPILE = true

## Next Directive Number
#127
