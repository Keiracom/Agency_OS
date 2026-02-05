"""
FastAPI service for image generation
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
import os

from .config import settings
from .runpod_client import RunPodClient, GenerationRequest
from .storage import ImageStorage

app = FastAPI(
    title="Image Generation API",
    description="NSFW-capable image generation service",
    version="1.0.0"
)

# Initialize clients
runpod = RunPodClient(
    api_key=settings.runpod_api_key,
    endpoint_id=os.getenv("RUNPOD_ENDPOINT_ID")
)

storage = ImageStorage(
    supabase_url=settings.supabase_url,
    supabase_key=settings.supabase_key,
    bucket=settings.storage_bucket
)


class GenerateRequest(BaseModel):
    """API request for image generation."""
    prompt: str = Field(..., description="Image prompt")
    negative_prompt: str = Field(
        default="low quality, blurry, distorted, deformed, ugly",
        description="What to avoid"
    )
    width: int = Field(default=1024, ge=512, le=2048)
    height: int = Field(default=1024, ge=512, le=2048)
    steps: int = Field(default=30, ge=10, le=50)
    cfg_scale: float = Field(default=7.0, ge=1.0, le=20.0)
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    save: bool = Field(default=True, description="Save to storage")


class GenerateResponse(BaseModel):
    """API response for image generation."""
    success: bool
    image_url: str
    image_id: Optional[str] = None
    seed: int
    generation_time: float
    cost_estimate: float


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "image-gen"}


@app.post("/generate", response_model=GenerateResponse)
async def generate_image(request: GenerateRequest):
    """
    Generate an image from a text prompt.
    
    No content filtering - use responsibly.
    """
    if not settings.runpod_api_key:
        raise HTTPException(500, "RunPod API key not configured")
    
    try:
        # Generate with RunPod
        gen_request = GenerationRequest(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            steps=request.steps,
            cfg_scale=request.cfg_scale,
            seed=request.seed
        )
        
        result = await runpod.generate(gen_request)
        
        # Optionally save to storage
        image_id = None
        final_url = result.image_url
        
        if request.save:
            saved = await storage.save_image(
                image_data=result.image_url,
                prompt=request.prompt,
                metadata={
                    "negative_prompt": request.negative_prompt,
                    "width": request.width,
                    "height": request.height,
                    "steps": request.steps,
                    "cfg_scale": request.cfg_scale,
                    "seed": result.seed
                }
            )
            image_id = saved["image_id"]
            final_url = saved["url"]
        
        return GenerateResponse(
            success=True,
            image_url=final_url,
            image_id=image_id,
            seed=result.seed,
            generation_time=result.generation_time,
            cost_estimate=result.cost_estimate
        )
        
    except Exception as e:
        raise HTTPException(500, f"Generation failed: {str(e)}")


@app.get("/images")
async def list_images(limit: int = 50, offset: int = 0):
    """List recent generated images."""
    images = storage.list_images(limit=limit, offset=offset)
    return {"images": images, "count": len(images)}


@app.get("/images/{image_id}")
async def get_image(image_id: str):
    """Get a specific image by ID."""
    image = storage.get_image(image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    return image


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    await runpod.close()
