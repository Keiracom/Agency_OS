# Phase 22: Marketing Automation

**Status:** 📋 Planned (Post-Launch)
**Tasks:** 5
**Trigger:** After first paying customers, post-launch

---

## Purpose

Automated content pipeline for social media marketing using AI video generation and scheduled posting. Enables Agency OS to "dogfood" itself by generating marketing content automatically.

---

## Tasks

### 22A: Marketing Integrations (2 tasks)

| Task | Description | Files |
|------|-------------|-------|
| INT-013 | HeyGen integration | `src/integrations/heygen.py` |
| INT-014 | Buffer integration | `src/integrations/buffer.py` |

### 22B: Marketing Automation Setup (3 tasks)

| Task | Description | Files |
|------|-------------|-------|
| MKT-001 | HeyGen account + avatar setup | — |
| MKT-002 | Content automation flow (Prefect) | `src/orchestration/flows/marketing_automation_flow.py` |
| MKT-003 | Day 1 video script + post | — |

---

## Dependency Chain

```
INT-013 (HeyGen integration) ──┐
                               ├──► MKT-002 (Prefect flow) ──► Automated pipeline
INT-014 (Buffer integration) ──┘
```

---

## HeyGen Integration

### Purpose
Generate AI avatar videos for social media content from text scripts.

### API Usage
```python
# Create video from script
response = heygen.create_video(
    script="Agency OS just helped a client book 15 meetings in one week...",
    avatar_id="david_avatar",
    voice_id="male_professional"
)
```

### Key Features
- AI avatar creation
- Text-to-video generation
- Multiple avatar personas (David, Alex)
- Custom voice cloning

---

## Buffer Integration

### Purpose
Schedule and publish content across social media platforms.

### Platforms
- LinkedIn (primary)
- Twitter/X
- Instagram (optional)

### API Usage
```python
# Schedule post
response = buffer.create_post(
    text="Just closed 3 new clients this week using AI outreach...",
    media_ids=["video_123"],
    scheduled_at=datetime(2026, 1, 20, 9, 0)
)
```

---

## Content Pipeline Flow

```
1. Milestone Trigger (new client, meetings booked, etc.)
   ↓
2. Generate Script (Claude)
   ↓
3. Create Video (HeyGen)
   ↓
4. Schedule Post (Buffer)
   ↓
5. Track Engagement (Buffer analytics)
```

---

## Activation Criteria

- [ ] First 3 paying customers
- [ ] HeyGen account with avatar configured
- [ ] Buffer account connected to LinkedIn
- [ ] Content calendar defined

---

## Notes

- This phase is post-launch work
- Focus on dogfooding: Agency OS sells itself
- Start with 1 video/week cadence
- Scale based on engagement metrics
