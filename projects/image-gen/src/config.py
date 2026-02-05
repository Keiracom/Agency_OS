"""
Configuration for NSFW Image Generation Service
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # RunPod
    runpod_api_key: str = os.getenv("RUNPOD_API_KEY", "")
    
    # Supabase (reuse existing)
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # Storage bucket for generated images
    storage_bucket: str = "generated-images"
    
    # Generation defaults
    default_model: str = "sdxl"  # sdxl, realistic-vision, etc.
    default_steps: int = 30
    default_cfg_scale: float = 7.0
    default_width: int = 1024
    default_height: int = 1024
    
    # Rate limiting
    max_concurrent_jobs: int = 5
    
    class Config:
        env_file = ".env"


settings = Settings()
