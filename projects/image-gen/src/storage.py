"""
Image storage using Supabase Storage
"""
import base64
import uuid
from datetime import datetime
import httpx
from supabase import create_client, Client


class ImageStorage:
    """
    Store generated images in Supabase Storage.
    """
    
    def __init__(self, supabase_url: str, supabase_key: str, bucket: str = "generated-images"):
        self.client: Client = create_client(supabase_url, supabase_key)
        self.bucket = bucket
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Create bucket if it doesn't exist."""
        try:
            self.client.storage.create_bucket(
                self.bucket,
                options={"public": True}  # Public access for serving
            )
        except Exception:
            pass  # Bucket likely already exists
    
    async def save_image(
        self,
        image_data: str,
        prompt: str,
        metadata: dict = None
    ) -> dict:
        """
        Save an image to storage.
        
        Args:
            image_data: Base64 image data or URL
            prompt: The prompt used to generate
            metadata: Additional metadata
            
        Returns:
            Dict with image_id and public_url
        """
        image_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")
        path = f"{timestamp}/{image_id}.png"
        
        # Handle base64 or URL
        if image_data.startswith("data:"):
            # Extract base64 from data URL
            image_bytes = base64.b64decode(image_data.split(",")[1])
        elif image_data.startswith("http"):
            # Download from URL
            async with httpx.AsyncClient() as client:
                response = await client.get(image_data)
                image_bytes = response.content
        else:
            # Assume raw base64
            image_bytes = base64.b64decode(image_data)
        
        # Upload to Supabase Storage
        self.client.storage.from_(self.bucket).upload(
            path,
            image_bytes,
            {"content-type": "image/png"}
        )
        
        # Get public URL
        public_url = self.client.storage.from_(self.bucket).get_public_url(path)
        
        # Store metadata in database
        record = {
            "id": image_id,
            "path": path,
            "url": public_url,
            "prompt": prompt[:1000],  # Truncate long prompts
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.client.table("generated_images").insert(record).execute()
        
        return {
            "image_id": image_id,
            "url": public_url,
            "path": path
        }
    
    def get_image(self, image_id: str) -> dict | None:
        """Get image metadata by ID."""
        result = self.client.table("generated_images").select("*").eq("id", image_id).execute()
        return result.data[0] if result.data else None
    
    def list_images(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """List recent images."""
        result = (
            self.client.table("generated_images")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data
