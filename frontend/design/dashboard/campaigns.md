# Campaign Allocation UI Specification

**Status:** Planning
**Component:** `CampaignAllocationManager`

---

## Overview

Clients allocate their monthly capacity across campaigns using **priority sliders**. This replaces showing raw lead counts with a focus-based mental model.

---

## User Mental Model

**What client thinks:**
> "I want to put more focus on my Tech Decision Makers campaign this month"

**What actually happens:**
> System calculates: 50% of 1,250 = 625 leads → sources & enriches immediately

**Client never sees:** "625 leads allocated"

---

## Component: Campaign Priority Card

```
┌─────────────────────────────────────────────────────────────┐
│ 🤖 Tech Decision Makers                      AI SUGGESTED   │
│                                                             │
│ Priority                                                    │
│ Low ○━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━○ High             │
│                     40%                                     │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ This Month                                              │ │
│ │ 6 meetings booked  •  3.8% reply rate  •  85% show rate │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Channels: Email, LinkedIn  •  Status: Active                │
└─────────────────────────────────────────────────────────────┘
```

### Elements

| Element | Description |
|---------|-------------|
| Campaign name | With icon (🤖 AI, 📝 Custom) |
| Badge | "AI SUGGESTED" or "CUSTOM" |
| Priority slider | Draggable, shows % |
| Results row | Meetings, reply rate, show rate |
| Channels | Active channels for this campaign |
| Status | Active, Paused, Draft |

---

## Slider Behavior

### Auto-Balance Rule
All campaign percentages must sum to 100%.

When user drags one slider:
1. Other sliders adjust proportionally
2. Minimum per campaign: 10%
3. Maximum per campaign: 80%

**Example:**
- Campaign A: 40% → user drags to 50%
- Campaign B: 35% → auto-adjusts to 29%
- Campaign C: 25% → auto-adjusts to 21%
- Total: 100% ✓

### Visual Feedback

```
Priority
Low ○━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━○ High
                   40%
                    ↑
              Draggable thumb
```

While dragging:
- Show percentage updating in real-time
- Other sliders animate to new positions
- Yellow highlight on "pending changes" state

---

## Campaign List Layout

```
┌─────────────────────────────────────────────────────────────┐
│ YOUR CAMPAIGNS                           [ + Add Campaign ] │
│ 3 of 3 slots used                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Campaign Card 1                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Campaign Card 2                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Campaign Card 3                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ⚠️  Changes pending                                        │
│                                                             │
│  [ Cancel ]                    [ Confirm & Activate ]       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## States

### Initial State (No Changes)
- Sliders at current allocation
- No action buttons visible
- "Confirm & Activate" hidden

### Pending Changes State
- Yellow border on changed campaigns
- "⚠️ Changes pending" message
- "Cancel" and "Confirm & Activate" buttons visible

### Processing State
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│     ◐  Preparing your campaigns...                          │
│                                                             │
│        Finding ideal prospects                              │
│        Researching & qualifying                             │
│        Setting up outreach sequences                        │
│                                                             │
│     This usually takes 30-60 seconds                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Success State
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│     ✓  Campaigns ready!                                     │
│                                                             │
│        Your priorities have been updated.                   │
│        Outreach will begin during business hours.           │
│                                                             │
│                              [ View Campaigns ]             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Error State
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│     ✗  Something went wrong                                 │
│                                                             │
│        We couldn't update your campaigns.                   │
│        Your previous settings are still active.             │
│                                                             │
│     [ Try Again ]              [ Contact Support ]          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## API Contract

### Request
```
POST /api/v1/clients/{client_id}/campaigns/allocate

{
  "allocations": [
    { "campaign_id": "uuid-1", "priority_pct": 40 },
    { "campaign_id": "uuid-2", "priority_pct": 35 },
    { "campaign_id": "uuid-3", "priority_pct": 25 }
  ]
}
```

### Response (Success)
```json
{
  "status": "processing",
  "message": "Campaigns are being prepared",
  "estimated_seconds": 45
}
```

Then poll or websocket for completion.

### Backend Flow
1. Validate percentages sum to 100
2. Update `lead_allocation_pct` on each campaign
3. Calculate `lead_count` from client's tier quota
4. Trigger `pool_population_flow` immediately
5. Enrich leads (no batching)
6. Assign to campaigns
7. Return success

---

## Tier Limits

| Tier | Max Campaigns | Monthly Capacity |
|------|---------------|------------------|
| Starter | 2 | ~5-10 meetings |
| Growth | 3 | ~15-25 meetings |
| Scale | 5 | ~30-50 meetings |
| Enterprise | Unlimited | ~50+ meetings |

**Note:** We show meeting targets, not lead counts.

---

## Slot Management

When client has fewer campaigns than their limit:
```
┌─────────────────────────────────────────────────────────────┐
│ YOUR CAMPAIGNS                           [ + Add Campaign ] │
│ 2 of 3 slots used                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Campaign Card 1 (50%)                                   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Campaign Card 2 (50%)                                   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ │
│   + Add another campaign                                    │
│ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Mobile Considerations

- Sliders should be touch-friendly (larger hit area)
- Cards stack vertically
- Percentage shown above slider on mobile
- "Confirm" button sticky at bottom

---

## Accessibility

- Slider keyboard accessible (arrow keys)
- ARIA labels: "Campaign priority for Tech Decision Makers, currently 40%"
- Focus indicators on interactive elements
- Screen reader announces percentage changes

---

## Related Files

| File | Purpose |
|------|---------|
| `frontend/components/campaigns/CampaignAllocationManager.tsx` | Main component |
| `frontend/components/campaigns/PrioritySlider.tsx` | Slider component |
| `frontend/components/campaigns/CampaignPriorityCard.tsx` | Card component |
| `frontend/lib/api/campaigns.ts` | Add `allocateCampaigns()` |
| `frontend/hooks/use-campaign-allocation.ts` | State management |
