#!/usr/bin/env python3
"""
CLI tool for image generation.

Usage:
    python generate.py "your prompt here" --output image.png
    python generate.py "your prompt" --width 1024 --height 768 --steps 40
"""
import asyncio
import argparse
import os
import base64
import httpx
from pathlib import Path

# Load env
from dotenv import load_dotenv
load_dotenv()


async def generate_image(
    prompt: str,
    negative_prompt: str = "low quality, blurry, distorted",
    width: int = 1024,
    height: int = 1024,
    steps: int = 30,
    cfg_scale: float = 7.0,
    seed: int = -1,
    output_path: str = None
) -> dict:
    """
    Generate an image using RunPod serverless.
    
    Returns dict with image data or saves to file.
    """
    api_key = os.getenv("RUNPOD_API_KEY")
    if not api_key:
        raise ValueError("RUNPOD_API_KEY not set in environment")
    
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID", "sdxl-base")
    url = f"https://api.runpod.ai/v2/{endpoint_id}/runsync"
    
    payload = {
        "input": {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": cfg_scale,
            "seed": seed,
        }
    }
    
    print(f"🎨 Generating: {prompt[:50]}...")
    print(f"   Size: {width}x{height}, Steps: {steps}")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Handle async polling if needed
        if data.get("status") in ["IN_QUEUE", "IN_PROGRESS"]:
            job_id = data["id"]
            print(f"   Job queued: {job_id}")
            
            for i in range(120):  # 4 min timeout
                await asyncio.sleep(2)
                status_response = await client.get(
                    f"https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                data = status_response.json()
                
                if data.get("status") == "COMPLETED":
                    print(f"   ✅ Complete!")
                    break
                elif data.get("status") == "FAILED":
                    raise Exception(f"Failed: {data.get('error')}")
                
                if i % 5 == 0:
                    print(f"   ⏳ Waiting... ({i*2}s)")
        
        # Extract image
        output = data.get("output", {})
        image_data = output.get("image") or output.get("images", [None])[0]
        
        if not image_data:
            raise Exception("No image in response")
        
        # Save if output path specified
        if output_path:
            if image_data.startswith("http"):
                # Download from URL
                img_response = await client.get(image_data)
                img_bytes = img_response.content
            else:
                # Decode base64
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                img_bytes = base64.b64decode(image_data)
            
            Path(output_path).write_bytes(img_bytes)
            print(f"   💾 Saved to: {output_path}")
        
        exec_time = data.get("executionTime", 0) / 1000
        cost = exec_time * 0.00025
        
        print(f"   ⏱️  Time: {exec_time:.1f}s")
        print(f"   💰 Cost: ${cost:.4f}")
        
        return {
            "image_url": image_data if image_data.startswith("http") else None,
            "image_base64": image_data if not image_data.startswith("http") else None,
            "seed": output.get("seed", 0),
            "execution_time": exec_time,
            "cost": cost,
            "output_path": output_path
        }


def main():
    parser = argparse.ArgumentParser(description="Generate images with Stable Diffusion")
    parser.add_argument("prompt", help="Image generation prompt")
    parser.add_argument("--negative", "-n", default="low quality, blurry, distorted", help="Negative prompt")
    parser.add_argument("--width", "-W", type=int, default=1024, help="Image width")
    parser.add_argument("--height", "-H", type=int, default=1024, help="Image height")
    parser.add_argument("--steps", "-s", type=int, default=30, help="Inference steps")
    parser.add_argument("--cfg", type=float, default=7.0, help="CFG scale")
    parser.add_argument("--seed", type=int, default=-1, help="Random seed")
    parser.add_argument("--output", "-o", help="Output file path")
    
    args = parser.parse_args()
    
    # Default output path
    if not args.output:
        args.output = "generated_image.png"
    
    result = asyncio.run(generate_image(
        prompt=args.prompt,
        negative_prompt=args.negative,
        width=args.width,
        height=args.height,
        steps=args.steps,
        cfg_scale=args.cfg,
        seed=args.seed,
        output_path=args.output
    ))
    
    print(f"\n✨ Done! Seed: {result['seed']}")


if __name__ == "__main__":
    main()
