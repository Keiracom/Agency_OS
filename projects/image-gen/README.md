# NSFW Image Generation Service

Unfiltered image generation using RunPod Serverless + Stable Diffusion.

## Setup

1. **Get RunPod API Key:**
   - Sign up at https://runpod.io
   - Add credits ($10-25 to start)
   - Go to Settings → API Keys → Create

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your keys
   ```

3. **Create Supabase table:**
   ```sql
   CREATE TABLE generated_images (
     id UUID PRIMARY KEY,
     path TEXT NOT NULL,
     url TEXT NOT NULL,
     prompt TEXT,
     metadata JSONB DEFAULT '{}',
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   
   -- Create storage bucket (run in Supabase dashboard)
   -- Bucket name: generated-images
   -- Public: Yes
   ```

4. **Run locally:**
   ```bash
   pip install -r requirements.txt
   uvicorn src.api:app --reload --port 8000
   ```

5. **Deploy to Railway:**
   ```bash
   railway login
   railway init
   railway up
   ```

## Usage

### Generate an image:
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "your prompt here",
    "width": 1024,
    "height": 1024,
    "steps": 30
  }'
```

### Response:
```json
{
  "success": true,
  "image_url": "https://...",
  "image_id": "uuid",
  "seed": 12345,
  "generation_time": 5.2,
  "cost_estimate": 0.0013
}
```

## Cost Estimate

- ~$0.001-0.003 per image (RunPod serverless)
- 1,000 images = ~$1-3
- No monthly minimums

## Models Available

Using RunPod's serverless SDXL by default. For more control, deploy your own endpoint with:
- SDXL Base
- Realistic Vision
- Any CivitAI model
