# Claude Code Advanced Techniques Analysis
> Extracted from 6 video transcripts on AI agent training and automation

---

## Table of Contents
1. [Skills Architecture](#1-skills-architecture)
2. [Training Workflows](#2-training-workflows)
3. [Browser/Chrome Integration](#3-browserchrome-integration)
4. [Video Understanding Pipeline](#4-video-understanding-pipeline)
5. [Cron/Scheduled Jobs](#5-cronscheduled-jobs)
6. [Multi-Skill Combinations](#6-multi-skill-combinations)
7. [X/Twitter Automation](#7-xtwitter-automation)
8. [YouTube/Video Automation](#8-youtubevideo-automation)
9. [Ralph Loop Architecture](#9-ralph-loop-architecture)
10. [Implementation Recommendations](#10-implementation-recommendations)

---

## 1. Skills Architecture

### Key Technique #1: Skill.md File Structure

Skills are stored as markdown files in a dedicated directory (e.g., `claude/skills/`). Each skill contains:

```
skills/
├── x/
│   └── skill.md          # X/Twitter navigation
├── linkedin/
│   └── skill.md          # LinkedIn automation
├── youtube/
│   └── skill.md          # YouTube uploading
├── video-research/
│   └── skill.md          # Research pipeline
├── video-edit/
│   └── skill.md          # Remotion editing
├── gmail/
│   └── skill.md          # Email handling
├── thumbnail/
│   └── skill.md          # Image generation
└── github/
    └── skill.md          # Repo management
```

### Key Technique #2: Skill.md Content Pattern

A skill.md file should contain:

```markdown
# [Platform] Skill

## Overview
Brief description of what this skill enables

## Prerequisites
- Logged into [platform] in Chrome
- Required API keys/tools

## Workflows

### [Action 1]: [e.g., Creating a Post]
1. Navigate to [URL]
2. JavaScript injection pattern:
   ```javascript
   // Exact selector/injection code that worked
   document.querySelector('[selector]').value = 'text';
   ```
3. Expected result

### [Action 2]: [e.g., Searching Users]
1. Steps...
2. Code patterns...

## Common Issues & Fixes
- Issue: [description]
- Fix: [solution]

## Last Updated
[Date] - [What was learned]
```

### Key Technique #3: Project-Scoped vs Global Skills

From the Skills.sh video:
- **Global skills**: Agent-wide capabilities (X, Gmail, etc.)
- **Project skills**: Installed per-project via `npx skills add [repo]`

```bash
# Install project-specific skills
npx skills add vercel/react-best-practices
npx skills add remotion/best-practices

# Check installed skills
/skills  # Lists all available skills
```

---

## 2. Training Workflows

### Key Technique #4: Iterative Skill Training Process

```
┌─────────────────────────────────────────────────────────────┐
│                    SKILL TRAINING LOOP                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. CREATE EMPTY SKILL.MD                                    │
│     └─> "Create skills/linkedin/skill.md empty for now"      │
│                                                              │
│  2. READ BROWSER CONTROL DOCS                                │
│     └─> "Read browser.js to understand Chrome connection"    │
│                                                              │
│  3. SET A GOAL                                               │
│     └─> "Make a draft post on LinkedIn"                      │
│                                                              │
│  4. LET AGENT ITERATE (accept failures)                      │
│     └─> Agent tries different approaches                     │
│     └─> ~6 minutes of exploration                            │
│                                                              │
│  5. CAPTURE SUCCESS                                          │
│     └─> "Update skill.md with the workflow that worked"      │
│                                                              │
│  6. TEST WITH FRESH CONTEXT                                  │
│     └─> Exit Claude, restart                                 │
│     └─> Same task now takes ~40 seconds (vs 6 min)           │
│                                                              │
│  7. ADD MORE SKILLS TO SAME FILE                             │
│     └─> Search users, send messages, etc.                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Technique #5: Training Prompts That Work

**Initial Setup:**
```
Read the [platform] skill.md. Let's train some more on [platform].
Please try to [specific action].
```

**After Success:**
```
Great job. Now update this [platform] skill.md with the workflow 
that led to success. For next time to save time.
```

**Testing Learned Skill:**
```
Read the [platform] skill. Please [do action]. 
[Agent should now execute immediately without exploration]
```

### Key Technique #6: Time Savings Metrics

| Scenario | Without Skill | With Skill | Savings |
|----------|---------------|------------|---------|
| LinkedIn post | 6 minutes | 40 seconds | 89% |
| LinkedIn DM | 10-15 minutes | ~30 seconds | 96% |
| X meme post | Variable | Immediate | Significant |

---

## 3. Browser/Chrome Integration

### Key Technique #7: Chrome CDP Connection

The agent connects to a running Chrome instance via Chrome DevTools Protocol (CDP):

```javascript
// browser.js pattern - connects to Chrome
// Claude uses JavaScript injection via CDP to:
// 1. Navigate pages
// 2. Fill forms
// 3. Click buttons
// 4. Read DOM content
```

### Key Technique #8: Element Interaction Pattern

```javascript
// Typical injection pattern for form filling
document.querySelector('[data-testid="post-editor"]').innerText = 'content';

// For clicking
document.querySelector('button[aria-label="Post"]').click();

// For reading
const posts = document.querySelectorAll('[data-testid="tweet"]');
```

### Key Technique #9: Login State Advantage

**Critical insight**: Use a dedicated machine (Mac Mini) where the agent is permanently logged into all services:
- No API key management for X, LinkedIn, Gmail, YouTube
- More secure (credentials stay in browser)
- Avoids rate limits on official APIs
- Can access features not in APIs

```
┌──────────────────────────────────────────────┐
│           DEDICATED AGENT MACHINE            │
├──────────────────────────────────────────────┤
│                                              │
│  Chrome Browser (always running)             │
│  ├── Logged into X (@agent_account)          │
│  ├── Logged into LinkedIn                    │
│  ├── Logged into Gmail                       │
│  ├── Logged into YouTube                     │
│  └── Logged into GitHub                      │
│                                              │
│  Claude Code connects via CDP                │
│  └── Can control any logged-in service       │
│                                              │
└──────────────────────────────────────────────┘
```

---

## 4. Video Understanding Pipeline

### Key Technique #10: Video Without Audio (Frame Analysis)

```bash
# Step 1: Download video from X/Twitter
yt-dlp "https://x.com/user/status/123456"

# Step 2: Check if video has audio
ffprobe -i video.mp4 -show_streams -select_streams a

# Step 3: If no audio, extract frames
ffmpeg -i video.mp4 -vf "fps=1/3" frame_%03d.png
# (1 frame every 3 seconds)

# Step 4: Analyze frames with vision model
# Claude reads each frame image and summarizes
```

### Key Technique #11: Video With Audio (Whisper Pipeline)

```bash
# Step 1: Download video
yt-dlp "https://x.com/user/status/123456"

# Step 2: Extract audio
ffmpeg -i video.mp4 -vn -acodec libmp3lame audio.mp3

# Step 3: Transcribe with local Whisper
whisper audio.mp3 --model base --output_format txt
# Or: whisper audio.mp3 --model small --output_format srt

# Step 4: Claude now has full text context
# Can summarize, extract key points, answer questions

# Step 5: Clean up
rm audio.mp3  # Keep transcription, delete audio
```

### Key Technique #12: Video Understanding Decision Flow

```
VIDEO FOUND
    │
    ▼
┌─────────────────┐
│ Has Audio?      │
├─────────────────┤
│ ffprobe check   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    ▼         ▼
┌────────┐ ┌────────────┐
│Extract │ │Extract     │
│Audio   │ │Frames      │
│(FFmpeg)│ │(FFmpeg)    │
└───┬────┘ └─────┬──────┘
    │            │
    ▼            ▼
┌────────┐ ┌────────────┐
│Whisper │ │Vision      │
│Transcr.│ │Analysis    │
└───┬────┘ └─────┬──────┘
    │            │
    └─────┬──────┘
          │
          ▼
    ┌───────────┐
    │ Full      │
    │ Context   │
    │ Available │
    └───────────┘
```

---

## 5. Cron/Scheduled Jobs

### Key Technique #13: Simple Cron System

```bash
# Schedule a job via Claude Code
"Schedule a job at 15:46 that opens Hacker News, 
checks the top post, writes a summary"

# Job gets added to cron list
# Runs daily at that time unless removed
```

### Key Technique #14: Cron Job Examples

```
┌────────────────────────────────────────────────────────────┐
│                    EXAMPLE CRON JOBS                        │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Nighttime (while sleeping):                                │
│  ├── Go to X, find new posts on [topic]                     │
│  ├── Make thoughtful comments on trending posts             │
│  ├── Check Gmail for important emails                       │
│  ├── Generate daily summary report                          │
│  ├── Research competitors                                   │
│  └── Post scheduled content                                 │
│                                                             │
│  Management:                                                │
│  ├── "Schedule job at [time]: [task]"                       │
│  ├── "Remove job [id]"                                      │
│  └── "List all scheduled jobs"                              │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### Key Technique #15: Autonomous Night Mode

Run 6+ tasks overnight:
1. X engagement (comments, likes)
2. Research gathering
3. Content drafting
4. Email triage
5. Analytics checking
6. Report generation

---

## 6. Multi-Skill Combinations

### Key Technique #16: Skill Chaining Pattern

```
USER: "Do video research and create a video, 
       publish it on YouTube, 
       go to X and post about it"

AGENT SKILL CHAIN:
┌──────────────┐
│ video-research│ ──→ Gather info, download clips
└──────┬───────┘
       ▼
┌──────────────┐
│ video-edit   │ ──→ Create video with Remotion
└──────┬───────┘
       ▼
┌──────────────┐
│ thumbnail    │ ──→ Generate thumbnail image
└──────┬───────┘
       ▼
┌──────────────┐
│ youtube      │ ──→ Upload video + metadata
└──────┬───────┘
       ▼
┌──────────────┐
│ x            │ ──→ Post announcement with link
└──────────────┘
```

### Key Technique #17: Real-World Multi-Skill Example

From transcript - complete autonomous workflow:
```
1. Spotted trending topic (Project Genie from Google)
2. video-research skill: Downloaded article + videos
3. video-edit skill: Created script, voiceover, B-roll
4. Used Remotion to stitch video with animations
5. youtube skill: Uploaded to agent's channel
6. x skill: Posted about new video

Result: 87 subscribers, 5000+ views on agent's channel
```

---

## 7. X/Twitter Automation

### Key Technique #18: X Skill Capabilities

```markdown
## X.skill.md Contents

### Posting
- Navigate to compose
- Inject text via JavaScript
- Upload images (from local path)
- Click post button

### Research
- Search keywords (top/latest)
- Open individual tweets
- Scroll and gather context
- Read comments for sentiment

### Engagement
- Like posts
- Reply with generated content
- Retweet

### Video Understanding
- Download videos with yt-dlp
- Transcribe with Whisper
- Generate contextual responses
```

### Key Technique #19: X Meme Generation Workflow

```
PROMPT: "Research top posts on Claude Code from last 24h,
         create a meme about this, post it"

WORKFLOW:
1. Open X.com (already logged in)
2. Search "Claude Code" → Latest
3. Read top posts, analyze sentiment
4. Open posts with high engagement
5. Read comments to understand vibe
6. Generate meme with image model (Nano Banana Pro)
7. Open compose, upload image
8. Add witty caption
9. Post
```

### Key Technique #20: X Research Pattern

```python
# Pseudocode for X research skill
async def research_x(topic, timeframe="24h"):
    # 1. Navigate and search
    await browser.goto("x.com")
    await browser.search(topic)
    await browser.click("Latest")  # Switch to latest
    
    # 2. Gather posts
    posts = []
    for i in range(10):
        post = await browser.get_post_content()
        posts.append(post)
        await browser.scroll_down()
    
    # 3. Analyze top post
    top_post = max(posts, key=lambda p: p.engagement)
    await browser.click(top_post)
    comments = await browser.get_comments()
    
    # 4. Return context
    return {
        "posts": posts,
        "top_post": top_post,
        "sentiment": analyze_sentiment(comments)
    }
```

---

## 8. YouTube/Video Automation

### Key Technique #21: Video Generation Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                  VIDEO GENERATION PIPELINE                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  INPUT: Topic URL or description                             │
│                                                              │
│  STEP 1: RESEARCH (video-research.skill.md)                  │
│  ├── Scrape article/source                                   │
│  ├── Download existing videos (yt-dlp)                       │
│  └── Extract key points for script                           │
│                                                              │
│  STEP 2: SCRIPT GENERATION                                   │
│  ├── Create story structure                                  │
│  ├── Write voiceover script                                  │
│  └── Plan B-roll insertions                                  │
│                                                              │
│  STEP 3: ASSET CREATION                                      │
│  ├── Generate voiceover (TTS)                                │
│  ├── Create/select background clips                          │
│  └── Generate thumbnail                                      │
│                                                              │
│  STEP 4: VIDEO EDITING (Remotion)                            │
│  ├── Stitch clips with transitions                           │
│  ├── Add captions (from Whisper SRT)                         │
│  ├── Overlay voiceover                                       │
│  └── Add sound effects                                       │
│                                                              │
│  STEP 5: EXPORT & PUBLISH                                    │
│  ├── Render final video                                      │
│  ├── Upload to YouTube                                       │
│  └── Post announcement on X                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Technique #22: Remotion Integration

```javascript
// Remotion project structure
remotion-project/
├── src/
│   ├── Video.tsx       // Main composition
│   ├── Captions.tsx    // Caption overlay component
│   ├── transitions/    // Transition effects
│   └── audio/          // Sound effects
├── public/
│   ├── clips/          // Downloaded B-roll
│   └── voiceover.mp3   // Generated audio
└── package.json

// Claude Code uses Remotion CLI
npm run dev      // Preview in browser
npm run build    // Render final video
```

### Key Technique #23: Caption Generation Flow

```bash
# 1. Extract audio from video
ffmpeg -i input.mp4 -vn -acodec libmp3lame audio.mp3

# 2. Generate SRT with timestamps
whisper audio.mp3 --model small --output_format srt

# 3. SRT file format
1
00:00:00,000 --> 00:00:03,500
Today we are taking a look at Vercel skills.sh

2
00:00:03,500 --> 00:00:07,200
This is where you can level up your agents

# 4. Import SRT into Remotion for caption overlay
```

---

## 9. Ralph Loop Architecture

### Key Technique #24: PRD-Driven Autonomous Loop

```json
// prd.json structure
{
  "project": "VR Cinema Room",
  "tasks": [
    {
      "id": 1,
      "description": "Set up Next.js with Three.js",
      "priority": 1,
      "dependencies": [],
      "passes": false
    },
    {
      "id": 2,
      "description": "Create 180-degree spherical screen",
      "priority": 2,
      "dependencies": [1],
      "passes": false
    }
    // ... up to 22 tasks
  ]
}
```

### Key Technique #25: Ralph Loop Script

```bash
#!/bin/bash
# ralph.sh

MAX_ITERATIONS=$1
ITERATION=0

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    echo "=== Iteration $ITERATION of $MAX_ITERATIONS ==="
    
    # Launch Claude Code with autonomous permissions
    claude --dangerously-skip-permissions --print << 'EOF'
    
    Read prd.json. Find highest priority task where passes=false.
    Consider dependencies and logical order.
    
    Implement that SINGLE feature.
    Run tests to verify.
    Update prd.json: set passes=true when complete.
    Append progress to progress.txt.
    Commit your changes.
    
    Only work on ONE feature per iteration.
    
EOF
    
    ITERATION=$((ITERATION + 1))
    
    # Check if all tasks complete
    if grep -q '"passes": false' prd.json; then
        continue
    else
        echo "RALPH COMPLETE"
        break
    fi
done
```

### Key Technique #26: Ralph Loop Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      RALPH LOOP FLOW                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│           ┌──────────────┐                                   │
│           │   PRD.json   │ ◄─── Memory between iterations    │
│           │   (tasks)    │                                   │
│           └──────┬───────┘                                   │
│                  │                                           │
│                  ▼                                           │
│           ┌──────────────┐                                   │
│           │ Find next    │                                   │
│           │ unpassed task│                                   │
│           └──────┬───────┘                                   │
│                  │                                           │
│                  ▼                                           │
│           ┌──────────────┐                                   │
│           │ Execute task │ ◄─── Fresh context window         │
│           │ (Claude Code)│                                   │
│           └──────┬───────┘                                   │
│                  │                                           │
│                  ▼                                           │
│           ┌──────────────┐                                   │
│           │ Run tests    │                                   │
│           │ Verify work  │                                   │
│           └──────┬───────┘                                   │
│                  │                                           │
│                  ▼                                           │
│           ┌──────────────┐                                   │
│           │ Update PRD   │                                   │
│           │ passes=true  │                                   │
│           └──────┬───────┘                                   │
│                  │                                           │
│                  ▼                                           │
│           ┌──────────────┐                                   │
│           │ Git commit   │                                   │
│           └──────┬───────┘                                   │
│                  │                                           │
│                  ▼                                           │
│           ┌──────────────┐                                   │
│           │ WIPE CONTEXT │ ◄─── Reset Claude Code            │
│           │ Loop back    │                                   │
│           └──────────────┘                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Technique #27: Ralph Loop Results

| Project | Tasks | Time | Human Intervention |
|---------|-------|------|-------------------|
| VR Cinema Room | 22 | ~1 hour | Minimal (WiFi issue) |
| Music Slot Machine | 20 | ~25 min | Minor text fix |

---

## 10. Implementation Recommendations

### What We Should Implement in Clawdbot

#### Priority 1: Skills System
```bash
# Create skills directory structure
mkdir -p skills/{x,youtube,browser,video}

# Initialize skill template
cat > skills/TEMPLATE.md << 'EOF'
# [Platform] Skill

## Workflows

### [Action Name]
Steps and code patterns...

## Last Updated
[Date]
EOF
```

#### Priority 2: Video Understanding Integration
```python
# Add to tools/
tools/
├── video_processor.py    # FFmpeg wrapper
├── whisper_transcribe.py # Local Whisper
└── frame_extractor.py    # For silent videos
```

#### Priority 3: Browser Automation Enhancement
- Leverage existing browser tool with skill patterns
- Store successful element selectors in skill files
- Build selector library for common sites

#### Priority 4: Cron/Scheduled Tasks
```python
# Simple cron system
scheduled_tasks = [
    {"time": "09:00", "task": "Check X mentions"},
    {"time": "21:00", "task": "Generate daily summary"},
]
```

#### Priority 5: Ralph Loop for Large Projects
- Implement PRD-driven task execution
- Fresh context per task (token savings)
- Progress tracking in JSON

### Specific Prompts That Work Well

**For Training New Skills:**
```
"Read [skill].md. Let's train more on [platform].
Please try to [specific action]. 
When you figure it out, update the skill.md with the workflow."
```

**For Multi-Skill Tasks:**
```
"Do video research on [topic], create a video about it,
upload to YouTube, then post about it on X."
```

**For Autonomous Mode:**
```
"[Read skills]. [Task description]. 
Don't give up until complete. 
Update skill.md with any new workflows discovered."
```

**For Ralph Loop:**
```
"Read prd.json. Find highest priority task where passes=false.
Implement SINGLE feature. Run tests. Update PRD. Commit.
Only ONE feature per iteration."
```

---

## Summary: Key Insights

1. **Skills are learned, not coded** - Let agent explore, then capture what works
2. **Time savings compound** - 6 min → 40 sec after training
3. **Browser > API** - Logged-in Chrome bypasses rate limits, accesses more features
4. **Video = FFmpeg + Whisper** - Simple pipeline for full video understanding
5. **Cron enables autonomy** - Night mode for engagement/research
6. **Ralph Loop scales** - Fresh context per task = cleaner code, less confusion
7. **Skills chain naturally** - research → create → publish → promote

---

*Analysis complete. Ready for implementation.*
