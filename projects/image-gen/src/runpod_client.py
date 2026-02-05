"""
RunPod Serverless Client for Stable Diffusion
"""
import asyncio
import httpx
from typing import Optional
from pydantic import BaseModel


class GenerationRequest(BaseModel):
    """Image generation request."""
    prompt: str
    negative_prompt: str = "low quality, blurry, distorted, deformed"
    width: int = 1024
    height: int = 1024
    steps: int = 30
    cfg_scale: float = 7.0
    seed: Optional[int] = None
    

class GenerationResult(BaseModel):
    """Image generation result."""
    image_url: str
    seed: int
    generation_time: float
    cost_estimate: float


class RunPodClient:
    """
    Client for RunPod Serverless Stable Diffusion.
    
    Uses AUTOMATIC1111-compatible endpoints.
    """
    
    # Public SDXL endpoint (no filters)
    # You can also deploy your own for more control
    ENDPOINT_URL = "https://api.runpod.ai/v2/{endpoint_id}/runsync"
    
    def __init__(self, api_key: str, endpoint_id: str = None):
        """
        Initialize RunPod client.
        
        Args:
            api_key: RunPod API key
            endpoint_id: Your deployed endpoint ID (or use community endpoint)
        """
        self.api_key = api_key
        self.endpoint_id = endpoint_id or "sdxl-base"  # Default community endpoint
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=300.0,  # 5 min timeout for generation
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._client
    
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """
        Generate an image.
        
        Args:
            request: Generation parameters
            
        Returns:
            GenerationResult with image URL
        """
        client = await self._get_client()
        
        payload = {
            "input": {
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "width": request.width,
                "height": request.height,
                "num_inference_steps": request.steps,
                "guidance_scale": request.cfg_scale,
                "seed": request.seed or -1,  # -1 = random
            }
        }
        
        url = self.ENDPOINT_URL.format(endpoint_id=self.endpoint_id)
        
        response = await client.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle async job
        if data.get("status") == "IN_QUEUE" or data.get("status") == "IN_PROGRESS":
            # Poll for completion
            job_id = data["id"]
            result = await self._poll_job(job_id)
        else:
            result = data
        
        # Extract image from result
        output = result.get("output", {})
        image_data = output.get("image") or output.get("images", [None])[0]
        
        return GenerationResult(
            image_url=image_data if image_data.startswith("http") else f"data:image/png;base64,{image_data}",
            seed=output.get("seed", 0),
            generation_time=result.get("executionTime", 0) / 1000,  # ms to seconds
            cost_estimate=self._estimate_cost(result.get("executionTime", 0))
        )
    
    async def _poll_job(self, job_id: str, max_attempts: int = 60) -> dict:
        """Poll for job completion."""
        client = await self._get_client()
        status_url = f"https://api.runpod.ai/v2/{self.endpoint_id}/status/{job_id}"
        
        for _ in range(max_attempts):
            response = await client.get(status_url)
            data = response.json()
            
            if data.get("status") == "COMPLETED":
                return data
            elif data.get("status") == "FAILED":
                raise Exception(f"Generation failed: {data.get('error')}")
            
            await asyncio.sleep(2)  # Poll every 2 seconds
        
        raise TimeoutError("Generation timed out")
    
    def _estimate_cost(self, execution_time_ms: int) -> float:
        """Estimate cost based on execution time."""
        # RunPod serverless: ~$0.00025/second for GPU
        seconds = execution_time_ms / 1000
        return round(seconds * 0.00025, 4)
    
    async def close(self):
        """Close the client."""
        if self._client:
            await self._client.aclose()
            self._client = None
