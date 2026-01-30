# Video/Screenshot to Code Tools

> Last updated: 2026-01-30
> Purpose: Convert visual designs, screenshots, and video recordings into working code

---

## 🏆 Top Recommended Tools

### 1. screenshot-to-code (Open Source) ⭐ BEST FOR SELF-HOSTING

**What it does:** Converts screenshots, mockups, Figma designs, AND video recordings into clean code.

| Attribute | Value |
|-----------|-------|
| **GitHub** | https://github.com/abi/screenshot-to-code |
| **Hosted Version** | https://screenshottocode.com (paid) |
| **Pricing** | Free (self-hosted) / Paid (hosted) |
| **Quality** | Excellent - near pixel-perfect for simple UIs |
| **Video Support** | ✅ Yes (experimental) |

**Supported Stacks:**
- HTML + Tailwind
- HTML + CSS
- React + Tailwind
- Vue + Tailwind
- Bootstrap
- Ionic + Tailwind
- SVG

**Supported AI Models:**
- Gemini 3 Flash/Pro (Google) - Recommended
- Claude Opus 4.5 (Anthropic) - Recommended
- GPT-5.2, GPT-4.1 (OpenAI)

**Installation:**
```bash
# Clone repository
git clone https://github.com/abi/screenshot-to-code.git
cd screenshot-to-code

# Backend setup
cd backend
echo "OPENAI_API_KEY=sk-your-key" > .env
echo "ANTHROPIC_API_KEY=your-key" >> .env
echo "GEMINI_API_KEY=your-key" >> .env
pip install poetry
poetry install
poetry run uvicorn main:app --reload --port 7001

# Frontend setup (new terminal)
cd frontend
yarn install
yarn dev
```

**Docker Setup:**
```bash
echo "OPENAI_API_KEY=sk-your-key" > .env
docker-compose up -d --build
# Access at http://localhost:5173
```

**Video-to-Code Usage:**
- Record screen (max 30 seconds recommended)
- AI extracts 20 frames from video
- Generates functional prototype with interactions
- Requires ANTHROPIC_API_KEY (uses Claude)

**Integration with our stack:**
- Can run as local service on our infrastructure
- API keys we already have (Anthropic, OpenAI)
- Output compatible with our React/Tailwind stack

---

### 2. v0 by Vercel ⭐ BEST FOR QUICK PROTOTYPES

**What it does:** AI-powered UI generation from text prompts and screenshots.

| Attribute | Value |
|-----------|-------|
| **Website** | https://v0.dev |
| **Pricing** | Free ($5/mo credits) / Premium $20/mo / Team $30/user/mo |
| **Quality** | Excellent for React/Next.js components |
| **Video Support** | ❌ No |
| **API Access** | ✅ Yes (Premium+) |

**Supported Stacks:**
- React + Tailwind
- Next.js
- shadcn/ui components

**API Usage:**
```bash
# REST API
curl https://api.v0.dev/v1/chat/completions \
  -H "Authorization: Bearer $V0_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "v0-1.5-md",
    "messages": [
      {"role": "user", "content": "Create a pricing page with 3 tiers"}
    ]
  }'

# AI SDK Integration
npm install @ai-sdk/vercel

# Usage
import { generateText } from 'ai'
import { vercel } from '@ai-sdk/vercel'

const { text } = await generateText({
  model: vercel('v0-1.5-md'),
  prompt: 'Create a Next.js dashboard with charts'
})
```

**Models:**
- `v0-1.5-md` - Everyday tasks, UI generation
- `v0-1.5-lg` - Advanced thinking/reasoning
- `v0-1.0-md` - Legacy

**Token Pricing (per 1M tokens):**
| Model | Input | Output |
|-------|-------|--------|
| v0 Mini | $1 | $5 |
| v0 Pro | $3 | $15 |
| v0 Max | $5 | $25 |

---

### 3. Bolt.new ⭐ BEST FOR FULL-STACK

**What it does:** AI-powered full-stack web development in browser with instant deployment.

| Attribute | Value |
|-----------|-------|
| **Website** | https://bolt.new |
| **GitHub** | https://github.com/stackblitz/bolt.new (open source) |
| **Pricing** | Free tier / Paid plans available |
| **Quality** | Excellent for full-stack apps |
| **Video Support** | ❌ No |

**Key Features:**
- Full-stack in browser (WebContainers)
- Install npm packages
- Run Node.js servers
- Deploy to production from chat
- AI controls entire environment

**Supported Frameworks:**
- Vite, Next.js, Astro
- React, Vue, Svelte
- Any JavaScript framework

**Self-Hosting:**
```bash
git clone https://github.com/stackblitz/bolt.new.git
cd bolt.new
# Follow CONTRIBUTING.md for setup
```

---

### 4. Lovable.dev ⭐ BEST FOR NON-DEVELOPERS

**What it does:** AI app builder that converts prompts and screenshots to working apps.

| Attribute | Value |
|-----------|-------|
| **Website** | https://lovable.dev |
| **Pricing** | Free / Pro $25/mo / Business $50/mo |
| **Quality** | Good for MVPs and prototypes |
| **Screenshot Support** | ✅ Yes |

**Features:**
- Natural language to app
- Screenshot/Figma upload for inspiration
- One-click deployment
- GitHub integration

---

## 🔌 Figma Plugins

### Builder.io
| Attribute | Value |
|-----------|-------|
| **Plugin** | https://www.figma.com/community/plugin/747985167520967365 |
| **Pricing** | Free tier / Growth $404/mo (8 users) |
| **Output** | React, Next.js, Vue, Svelte, HTML |

**Features:**
- AI-powered Figma to code
- No special design prep needed
- CMS integration

### Locofy.ai
| Attribute | Value |
|-----------|-------|
| **Plugin** | https://www.figma.com/community/plugin/1056467900248561542 |
| **Pricing** | Free (beta) |
| **Output** | React, React Native, HTML/CSS, Flutter, Vue, Angular, Next.js |

**Features:**
- Semantic tagging for better output
- Live preview before export
- Team collaboration

### Anima
| Attribute | Value |
|-----------|-------|
| **Website** | https://www.animaapp.com |
| **Pricing** | Pro $39/user/mo / Business $150/mo |
| **Output** | HTML, React, Vue |

**Features:**
- Accurate code generation
- Preserves Figma prototype features
- Supports transitions and effects

### TeleportHQ
| Attribute | Value |
|-----------|-------|
| **Website** | https://teleporthq.io |
| **Pricing** | €15/user/mo (~$17) |
| **Output** | HTML, CSS, React, Vue, WordPress |

**Features:**
- Visual builder
- Easy export process
- CMS integration

### CodeParrot.ai
| Attribute | Value |
|-----------|-------|
| **Website** | https://codeparrot.ai |
| **Pricing** | Free trial (10 sessions) / $19/seat/mo |
| **Output** | React Native (TypeScript/JavaScript) |

**Features:**
- AI-powered conversion
- Auto-testing and documentation
- React Native focused

---

## 🛠️ CLI/API Tools for Programmatic Use

### Direct Vision API Integration (DIY)

Use Claude or GPT-4V directly for screenshot-to-code:

```python
# Using Claude Vision API
import anthropic
import base64

client = anthropic.Anthropic()

# Read screenshot
with open("screenshot.png", "rb") as f:
    image_data = base64.standard_b64encode(f.read()).decode("utf-8")

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_data,
                },
            },
            {
                "type": "text",
                "text": "Convert this UI screenshot to React + Tailwind code. Output only the code."
            }
        ],
    }],
)

print(message.content[0].text)
```

```bash
# Using OpenAI GPT-4V
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4-vision-preview",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "Convert this to React + Tailwind"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
      ]
    }],
    "max_tokens": 4096
  }'
```

---

## 📊 Tool Comparison Matrix

| Tool | Screenshot | Video | Self-Host | API | Free Tier | Best For |
|------|------------|-------|-----------|-----|-----------|----------|
| screenshot-to-code | ✅ | ✅ | ✅ | Local | ✅ | Self-hosted, full control |
| v0.dev | ✅ | ❌ | ❌ | ✅ | ✅ | Quick React/Next.js |
| Bolt.new | ✅ | ❌ | ✅ | ❌ | ✅ | Full-stack apps |
| Lovable | ✅ | ❌ | ❌ | ❌ | ✅ | Non-developers |
| Builder.io | Figma | ❌ | ❌ | ✅ | ✅ | Figma workflows |
| Locofy | Figma | ❌ | ❌ | ❌ | ✅ | Multi-framework |

---

## 🚀 Recommended Setup for Elliot

### Primary: screenshot-to-code (Self-Hosted)

Best option for our stack:
1. Full control over the tool
2. Uses APIs we already have (Anthropic, OpenAI)
3. Supports video recordings
4. React + Tailwind output matches our tech

```bash
# Add to our infrastructure
cd /home/elliotbot
git clone https://github.com/abi/screenshot-to-code.git
cd screenshot-to-code

# Create .env with our existing keys
cat > backend/.env << EOF
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}
GEMINI_API_KEY=${GEMINI_API_KEY}
EOF

# Run with Docker
docker-compose up -d
```

### Secondary: v0 API for Quick Generations

Use v0 API when we need quick component generation:

```bash
# Add to .env
V0_API_KEY=your-key-here

# Quick generation script
curl -X POST https://api.v0.dev/v1/chat/completions \
  -H "Authorization: Bearer $V0_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"v0-1.5-md","messages":[{"role":"user","content":"..."}]}'
```

### For Figma Workflows: Builder.io Plugin

Free tier available, integrates with our React/Tailwind stack.

---

## 📝 Usage Examples

### Convert Website Screenshot to Code
```bash
# Using screenshot-to-code locally
# 1. Start the service
cd screenshot-to-code && docker-compose up -d

# 2. Open http://localhost:5173
# 3. Upload screenshot or paste URL
# 4. Select stack (React + Tailwind)
# 5. Get generated code
```

### Convert Video Recording to Prototype
```bash
# Using screenshot-to-code video feature
# 1. Record 30-second video of the target UI
# 2. Upload to screenshot-to-code
# 3. AI extracts frames and generates interactive prototype
```

### Programmatic Screenshot to Code (Python)
```python
import anthropic
import base64

def screenshot_to_code(image_path: str, stack: str = "react-tailwind") -> str:
    client = anthropic.Anthropic()
    
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    prompts = {
        "react-tailwind": "Convert to React component with Tailwind CSS",
        "vue-tailwind": "Convert to Vue 3 component with Tailwind CSS",
        "html-tailwind": "Convert to HTML with Tailwind CSS",
    }
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}},
                {"type": "text", "text": f"{prompts.get(stack, prompts['react-tailwind'])}. Output clean, production-ready code only."}
            ],
        }],
    )
    return message.content[0].text

# Usage
code = screenshot_to_code("ui-mockup.png", "react-tailwind")
print(code)
```

---

## 🔗 Quick Links

| Tool | URL |
|------|-----|
| screenshot-to-code | https://github.com/abi/screenshot-to-code |
| v0.dev | https://v0.dev |
| Bolt.new | https://bolt.new |
| Lovable | https://lovable.dev |
| Builder.io | https://builder.io |
| Locofy | https://locofy.ai |
| Anima | https://animaapp.com |
