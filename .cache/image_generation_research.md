# Image Generation API Research for Clawdbot Integration

**Research Date:** February 2026  
**Purpose:** Find the best image generation service to add as a Clawdbot tool

---

## Executive Summary

**Recommended Provider: FAL.ai with Flux 2 Pro/Turbo**

For Agency OS use cases (marketing, diagrams, memes), FAL.ai offers the best balance of:
- **Cost:** $0.008–$0.03/image (7–10x cheaper than DALL-E 3)
- **Quality:** Flux models excel at text rendering and photorealism
- **Speed:** 2–10 seconds per image
- **Integration:** Simple REST API, no SDK required

**Runner-up:** Replicate (same models, slightly higher cost, excellent developer experience)

---

## Provider Comparison Table

| Provider | API Available | Cost/Image (Standard) | Cost/Image (Premium) | Speed | Text Rendering | Ease of Integration |
|----------|--------------|----------------------|---------------------|-------|----------------|---------------------|
| **FAL.ai** | ✅ Yes | $0.008 (Turbo) | $0.03–$0.06 (Pro/Ultra) | 2–10s | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Replicate** | ✅ Yes | $0.003 (Schnell) | $0.04–$0.06 (Pro) | 2–15s | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **OpenAI DALL-E 3** | ✅ Yes | $0.04 (1024x1024) | $0.08–$0.12 (HD) | 10–20s | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **OpenAI GPT Image 1** | ✅ Yes | $0.011 (Low) | $0.042–$0.167 (Med/High) | 5–15s | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Stability AI** | ✅ Yes | $0.03 (Core) | $0.08 (Ultra) | 5–15s | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Ideogram** | ✅ Yes | $0.04 (Standard) | $0.08 (v2/v3) | 10–20s | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Leonardo.ai** | ✅ Yes | Token-based (~$0.02) | Variable | 5–15s | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Midjourney** | ❌ No official API | N/A | N/A | N/A | ⭐⭐⭐⭐ | ❌ Not viable |

---

## Detailed Provider Analysis

### 1. FAL.ai (⭐ RECOMMENDED)

**API:** REST API with simple authentication  
**Models:** Flux 2 Pro, Flux 2 Turbo, Flux 1.1 Pro, SDXL, SD3.5

**Pricing (per megapixel-based, roughly per 1MP image):**
- Flux 2 Turbo: **$0.008/image** (best value)
- Flux 2 Dev: $0.012/image
- Flux 2 Pro: **$0.03/image** (production quality)
- Flux 2 Flex: $0.06/image

**Pros:**
- Extremely cost-effective (7x cheaper than DALL-E 3)
- Excellent text rendering in images
- Fast generation (2–10 seconds)
- Simple REST API
- Megapixel-based pricing = predictable costs
- Supports latest Flux 2 models

**Cons:**
- Newer platform (less established than OpenAI)
- Documentation could be better

**Best for:** High-volume production, marketing assets, anything needing text in images

---

### 2. Replicate

**API:** REST API + Python SDK  
**Models:** Flux Schnell, Flux 1.1 Pro, Flux Pro Ultra, SDXL, SD3.5

**Pricing:**
- Flux Schnell: **$0.003/image** (fastest, lowest quality)
- Flux 1.1 Pro: **$0.04/image**
- Flux 1.1 Pro Ultra (4MP): **$0.06/image**

**Pros:**
- Excellent developer experience
- Pay-per-use (no minimums)
- Huge model library
- Great documentation
- Python SDK available

**Cons:**
- Slightly higher than FAL.ai for same models
- Cold starts on less popular models

**Best for:** Developers who value DX, need model variety

---

### 3. OpenAI (DALL-E 3 / GPT Image 1)

**API:** REST API + Python SDK  
**Models:** DALL-E 2, DALL-E 3, GPT Image 1, GPT Image 1 Mini

**Pricing (per image):**
| Model | Quality | 1024x1024 | 1536x1024 |
|-------|---------|-----------|-----------|
| DALL-E 3 | Standard | $0.04 | $0.08 |
| DALL-E 3 | HD | $0.08 | $0.12 |
| GPT Image 1 | Low | $0.011 | $0.016 |
| GPT Image 1 | Medium | $0.042 | $0.063 |
| GPT Image 1 | High | $0.167 | $0.25 |
| GPT Image 1 Mini | Low | $0.005 | $0.006 |
| GPT Image 1 Mini | Medium | $0.011 | $0.015 |

**Pros:**
- Most established provider
- Good safety/content moderation
- Easy integration (same API as GPT)
- GPT Image 1 Mini is very cost-effective for simple uses

**Cons:**
- Text rendering often garbled/incorrect
- More expensive than Flux alternatives
- Strict content policies may reject valid prompts

**Best for:** Simple integrations where you already use OpenAI, need content moderation

---

### 4. Stability AI

**API:** REST API  
**Models:** Stable Image Core, Stable Image Ultra, SDXL, SD 3.5

**Pricing (credit-based, $0.01/credit):**
- Stable Image Core: **3 credits = $0.03/image**
- Stable Image Ultra: **8 credits = $0.08/image**
- SDXL: 3 credits = $0.03/image

**Pros:**
- Strong open-source ecosystem
- Good for customization (fine-tuning)
- Self-hosting option available

**Cons:**
- Pricing increased August 2025
- Less impressive than Flux for text
- API deprecating older models

**Best for:** Teams wanting self-hosting option, existing SD workflows

---

### 5. Ideogram

**API:** REST API  
**Models:** Ideogram 2.0, Ideogram 3.0

**Pricing:**
- Standard: ~$0.04/image
- Ideogram v2/v3: **$0.08/image**
- Turbo variants available cheaper

**Pros:**
- **Best-in-class text/typography rendering**
- Excellent for logos and designs
- Style consistency features
- Good for marketing materials

**Cons:**
- Higher cost for premium quality
- API documentation less mature
- Inconsistent faces (reported issue)

**Best for:** Logos, designs with text, typography-heavy graphics

---

### 6. Leonardo.ai

**API:** REST API (token-based)  
**Models:** Leonardo Phoenix, various fine-tuned models

**Pricing:**
- Token-based (complex calculation)
- Roughly $0.02–$0.05/image depending on settings
- Subscription tiers available

**Pros:**
- Many style-specific models
- Good UI for prompt iteration
- LoRA training supported

**Cons:**
- Complex pricing model
- Token system confusing
- API less documented than competitors

**Best for:** Creative exploration, style-specific outputs

---

### 7. Midjourney

**Status: ❌ NO OFFICIAL API**

Midjourney still operates exclusively through Discord. No official API exists as of Feb 2026. Third-party wrappers exist but violate ToS and are unreliable.

**Skip for programmatic integration.**

---

## Use Case Recommendations

### Marketing Assets (Social Posts, Ads)
**Best:** FAL.ai Flux 2 Pro ($0.03/image)
- Photorealistic
- Great text rendering for copy overlay
- Fast turnaround

### Diagrams & Architecture Visuals
**Best:** OpenAI GPT Image 1 Mini (Low) ($0.005/image)
- Simple, clean outputs
- Cheaper for simpler graphics
- Good for technical diagrams

### Presentation Graphics
**Best:** FAL.ai Flux 2 Turbo ($0.008/image)
- Fast iteration
- Cheap enough to generate variations
- Professional quality

### Memes/Viral Content
**Best:** Replicate Flux Schnell ($0.003/image)
- Cheapest option
- Fast generation
- Acceptable quality for memes

### Logos & Typography
**Best:** Ideogram 3.0 ($0.08/image)
- Unmatched text rendering
- Style consistency
- Worth the premium for brand assets

---

## Monthly Cost Analysis (~100 images/month)

| Provider | Budget Tier | Standard Tier | Premium Tier |
|----------|-------------|---------------|--------------|
| **FAL.ai** | $0.80 (Turbo) | **$3.00 (Pro)** | $6.00 (Ultra) |
| **Replicate** | $0.30 (Schnell) | $4.00 (1.1 Pro) | $6.00 (Ultra) |
| **OpenAI** | $0.50 (Mini Low) | $4.00 (DALL-E 3 Std) | $16.70 (GPT Image High) |
| **Stability AI** | - | $3.00 (Core) | $8.00 (Ultra) |
| **Ideogram** | - | $4.00 (Standard) | $8.00 (v3) |

**Recommended budget: $5–10/month** covers all Agency OS use cases with FAL.ai/Replicate.

---

## Integration Approach

### Recommended Architecture

```
User Request → Clawdbot → image_generator.py → FAL.ai API → Image URL
                              ↓
                         Local Storage (.cache/images/)
```

### File Structure
```
/home/elliotbot/clawd/
├── tools/
│   └── image_generator.py    # Main image generation tool
├── .cache/
│   └── images/               # Generated image storage
└── .env                      # API keys (FAL_KEY)
```

### Python Integration Code

```python
#!/usr/bin/env python3
"""
Image Generation Tool for Clawdbot
Uses FAL.ai Flux models for cost-effective, high-quality generation
"""

import os
import httpx
import base64
from pathlib import Path
from datetime import datetime

# Configuration
FAL_API_KEY = os.getenv("FAL_KEY")
FAL_BASE_URL = "https://queue.fal.run"
IMAGE_CACHE_DIR = Path("/home/elliotbot/clawd/.cache/images")

# Model options (cost per image at 1MP)
MODELS = {
    "turbo": {  # Fastest, cheapest - good for drafts
        "endpoint": "fal-ai/flux/dev/turbo",
        "cost": 0.008
    },
    "pro": {  # Production quality - marketing assets
        "endpoint": "fal-ai/flux-pro/v1.1",
        "cost": 0.04
    },
    "ultra": {  # Highest quality, 4MP resolution
        "endpoint": "fal-ai/flux-pro/v1.1-ultra",
        "cost": 0.06
    },
    "schnell": {  # Replicate fallback - cheapest
        "endpoint": "fal-ai/flux/schnell",
        "cost": 0.003
    }
}


async def generate_image(
    prompt: str,
    model: str = "pro",
    width: int = 1024,
    height: int = 1024,
    num_images: int = 1,
    save_local: bool = True
) -> dict:
    """
    Generate an image using FAL.ai Flux models.
    
    Args:
        prompt: Text description of desired image
        model: "turbo" (fast/cheap), "pro" (production), "ultra" (highest quality)
        width: Image width (default 1024)
        height: Image height (default 1024)
        num_images: Number of images to generate
        save_local: Whether to save to local cache
    
    Returns:
        dict with 'images' (list of URLs/paths), 'cost', 'model', 'prompt'
    """
    if model not in MODELS:
        model = "pro"
    
    model_config = MODELS[model]
    
    headers = {
        "Authorization": f"Key {FAL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": prompt,
        "image_size": {"width": width, "height": height},
        "num_images": num_images,
        "enable_safety_checker": True
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Submit request
        response = await client.post(
            f"{FAL_BASE_URL}/{model_config['endpoint']}",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        result = response.json()
    
    images = []
    for idx, img_data in enumerate(result.get("images", [])):
        img_url = img_data.get("url")
        
        if save_local and img_url:
            # Download and save locally
            local_path = await _save_image(img_url, prompt, model, idx)
            images.append({"url": img_url, "local_path": str(local_path)})
        else:
            images.append({"url": img_url})
    
    return {
        "images": images,
        "cost": model_config["cost"] * num_images,
        "model": model,
        "prompt": prompt
    }


async def _save_image(url: str, prompt: str, model: str, idx: int) -> Path:
    """Download and save image to local cache."""
    IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize prompt for filename
    safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in " -_").strip()
    safe_prompt = safe_prompt.replace(" ", "_")
    
    filename = f"{timestamp}_{model}_{safe_prompt}_{idx}.png"
    filepath = IMAGE_CACHE_DIR / filename
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        filepath.write_bytes(response.content)
    
    return filepath


# Sync wrapper for non-async contexts
def generate_image_sync(prompt: str, **kwargs) -> dict:
    """Synchronous wrapper for generate_image."""
    import asyncio
    return asyncio.run(generate_image(prompt, **kwargs))


# CLI interface
if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python image_generator.py <prompt> [model]")
        print("Models: turbo, pro, ultra, schnell")
        sys.exit(1)
    
    prompt = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "pro"
    
    result = generate_image_sync(prompt, model=model)
    print(json.dumps(result, indent=2))
```

### Alternative: Replicate Integration

```python
"""
Alternative Replicate integration (if FAL.ai unavailable)
"""
import os
import replicate

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

def generate_with_replicate(prompt: str, model: str = "pro") -> dict:
    """Generate image using Replicate's Flux models."""
    
    models = {
        "schnell": "black-forest-labs/flux-schnell",
        "pro": "black-forest-labs/flux-1.1-pro",
        "ultra": "black-forest-labs/flux-1.1-pro-ultra"
    }
    
    output = replicate.run(
        models.get(model, models["pro"]),
        input={
            "prompt": prompt,
            "aspect_ratio": "1:1",
            "output_format": "png"
        }
    )
    
    # Returns list of URLs
    return {"images": [{"url": url} for url in output]}
```

---

## Setup Checklist

1. **Get API Key:**
   - FAL.ai: https://fal.ai/dashboard/keys
   - Or Replicate: https://replicate.com/account/api-tokens

2. **Add to environment:**
   ```bash
   echo 'FAL_KEY=your_key_here' >> ~/.config/agency-os/.env
   # Or for Replicate:
   echo 'REPLICATE_API_TOKEN=your_token' >> ~/.config/agency-os/.env
   ```

3. **Create cache directory:**
   ```bash
   mkdir -p /home/elliotbot/clawd/.cache/images
   ```

4. **Install dependencies:**
   ```bash
   pip install httpx  # For FAL.ai
   # Or: pip install replicate  # For Replicate
   ```

5. **Test generation:**
   ```bash
   python tools/image_generator.py "A modern office dashboard, clean UI, data visualization" pro
   ```

---

## Final Recommendation

**Primary: FAL.ai with Flux 2 Pro**
- Best cost-quality ratio
- Excellent for Agency OS use cases
- $3–5/month at expected usage

**Fallback: Replicate**
- Same models, slightly more expensive
- Better documentation/SDK
- Good alternative if FAL.ai has issues

**For text-heavy designs: Ideogram 3.0**
- Worth the premium ($0.08/image) for logos/branding
- Use sparingly for typography-critical assets

---

*Research compiled for Agency OS integration. Last updated: February 2026*
