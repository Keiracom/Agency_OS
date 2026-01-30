# Tool Evaluation: screenshot-to-code

**Evaluated:** 2026-01-30
**Source:** https://github.com/abi/screenshot-to-code

## What It Does
AI tool to convert screenshots, mockups, and Figma designs into working code:
- Supports: HTML+Tailwind, React+Tailwind, Vue+Tailwind, Bootstrap, SVG
- AI Models: Gemini 3, Claude Opus 4.5, GPT-5.2
- Video-to-prototype: Record a website and generate functional code
- FastAPI backend + React/Vite frontend

## Pricing
- **Open Source** (MIT)
- Hosted version: screenshottocode.com (paid)
- Self-hosted: Free (bring your own API keys)

## Integration Complexity with Our Stack
| Factor | Assessment |
|--------|------------|
| Stack | FastAPI + React - matches our stack ✓ |
| Use Case | Development tool, not runtime service |
| Value | Could speed up UI development |

**Complexity: LOW** - Docker-compose deployment, simple to try

## Competitors/Alternatives
- **v0.dev** (Vercel) - AI UI generation
- **Galileo AI** - Design to code
- **Locofy** - Figma to code
- **Builder.io** - Visual development

## Analysis
This is a development productivity tool, not a runtime service for Agency OS:

**Potential uses:**
1. Quickly mock up new dashboard components
2. Recreate competitor UIs for analysis
3. Speed up frontend development iteration

**Limitations:**
- Requires API keys (cost)
- Generated code needs cleanup
- Not a production service

## Recommendation: **WATCH**

**Reasoning:**
1. Could be useful for development velocity
2. Not core to Agency OS functionality
3. Open source - can self-host when needed
4. FastAPI backend aligns with our stack

**Action:** Bookmark for development use. Try when need to quickly prototype UI components. Not a priority for Agency OS integration.
