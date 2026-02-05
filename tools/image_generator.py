#!/usr/bin/env python3
"""
Image Generator Tool for Clawdbot/Elliot
Uses Replicate API for Stable Diffusion / Flux models

Usage:
    python tools/image_generator.py generate "your prompt" --output /path/to/image.png
    python tools/image_generator.py generate "prompt" --width 1024 --height 768
    
Environment:
    REPLICATE_API_TOKEN - Required (get from replicate.com)
"""
import asyncio
import argparse
import os
import sys
import httpx
from pathlib import Path
from datetime import datetime


async def generate(
    prompt: str,
    negative_prompt: str = "low quality, blurry, distorted, deformed, ugly, nsfw",
    width: int = 1024,
    height: int = 1024,
    steps: int = 28,
    guidance: float = 3.5,
    output: str = None,
    model: str = "flux-schnell",  # flux-schnell (fast), flux-dev, sdxl
    nsfw: bool = False
) -> dict:
    """
    Generate an image using Replicate API.
    """
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        print("ERROR: REPLICATE_API_TOKEN environment variable not set")
        print("Get your token at: https://replicate.com/account/api-tokens")
        sys.exit(1)
    
    # Model selection
    models = {
        "flux-schnell": "black-forest-labs/flux-schnell",  # Fast, good quality
        "flux-dev": "black-forest-labs/flux-dev",          # Better quality, slower
        "flux-pro": "black-forest-labs/flux-1.1-pro",      # Best quality
        "sdxl": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
    }
    
    model_id = models.get(model, models["flux-schnell"])
    
    print(f"Generating image...")
    print(f"  Model: {model}")
    print(f"  Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
    print(f"  Size: {width}x{height}")
    
    # Build input based on model
    if "flux" in model:
        input_data = {
            "prompt": prompt,
            "aspect_ratio": "1:1" if width == height else f"{width}:{height}",
            "output_format": "png",
            "output_quality": 90,
        }
        if model != "flux-schnell":
            input_data["num_inference_steps"] = steps
            input_data["guidance_scale"] = guidance
        if nsfw:
            input_data["disable_safety_checker"] = True
    else:
        # SDXL format
        input_data = {
            "prompt": prompt,
            "negative_prompt": negative_prompt if not nsfw else "",
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        }
        if nsfw:
            input_data["disable_safety_checker"] = True
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Start prediction
        response = await client.post(
            "https://api.replicate.com/v1/predictions",
            headers={
                "Authorization": f"Token {api_token}",
                "Content-Type": "application/json"
            },
            json={
                "version": model_id.split(":")[-1] if ":" in model_id else None,
                "model": model_id.split(":")[0] if ":" in model_id else model_id,
                "input": input_data
            }
        )
        
        if response.status_code not in [200, 201]:
            print(f"ERROR: API returned {response.status_code}")
            print(response.text)
            sys.exit(1)
        
        data = response.json()
        prediction_id = data.get("id")
        
        if not prediction_id:
            # Might be a direct response for some models
            if data.get("output"):
                image_url = data["output"][0] if isinstance(data["output"], list) else data["output"]
            else:
                print(f"ERROR: Unexpected response: {data}")
                sys.exit(1)
        else:
            # Poll for completion
            print(f"  Prediction ID: {prediction_id}")
            get_url = data.get("urls", {}).get("get") or f"https://api.replicate.com/v1/predictions/{prediction_id}"
            
            for i in range(120):
                await asyncio.sleep(1)
                status_resp = await client.get(
                    get_url,
                    headers={"Authorization": f"Token {api_token}"}
                )
                data = status_resp.json()
                status = data.get("status")
                
                if status == "succeeded":
                    output_data = data.get("output")
                    image_url = output_data[0] if isinstance(output_data, list) else output_data
                    break
                elif status == "failed":
                    print(f"ERROR: Generation failed: {data.get('error')}")
                    sys.exit(1)
                
                if i % 5 == 0 and i > 0:
                    print(f"  ⏳ Waiting... ({i}s)")
            else:
                print("ERROR: Timeout waiting for generation")
                sys.exit(1)
        
        # Determine output path
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"/home/elliotbot/clawd/.cache/generated_{timestamp}.png"
        
        # Download and save image
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        
        img_resp = await client.get(image_url)
        Path(output).write_bytes(img_resp.content)
        
        metrics = data.get("metrics", {})
        predict_time = metrics.get("predict_time", 0)
        
        print(f"\n✅ Image generated successfully!")
        print(f"  Output: {output}")
        print(f"  Time: {predict_time:.1f}s")
        
        return {
            "success": True,
            "output_path": output,
            "predict_time": predict_time,
            "image_url": image_url
        }


def main():
    parser = argparse.ArgumentParser(description="Generate images with AI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate an image")
    gen_parser.add_argument("prompt", help="Image prompt")
    gen_parser.add_argument("--negative", "-n", default="low quality, blurry, distorted, deformed, ugly")
    gen_parser.add_argument("--width", "-W", type=int, default=1024)
    gen_parser.add_argument("--height", "-H", type=int, default=1024)
    gen_parser.add_argument("--steps", "-s", type=int, default=28)
    gen_parser.add_argument("--guidance", "-g", type=float, default=3.5)
    gen_parser.add_argument("--output", "-o", help="Output file path")
    gen_parser.add_argument("--model", "-m", default="flux-schnell", 
                          choices=["flux-schnell", "flux-dev", "flux-pro", "sdxl"])
    gen_parser.add_argument("--nsfw", action="store_true", help="Disable safety filters")
    
    args = parser.parse_args()
    
    if args.command == "generate":
        asyncio.run(generate(
            prompt=args.prompt,
            negative_prompt=args.negative,
            width=args.width,
            height=args.height,
            steps=args.steps,
            guidance=args.guidance,
            output=args.output,
            model=args.model,
            nsfw=args.nsfw
        ))


if __name__ == "__main__":
    main()
