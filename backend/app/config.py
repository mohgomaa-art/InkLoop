import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class InkLoopConfig(BaseModel):
    """Central configuration for InkLoop with fail-safe bounds."""
    meta_api_key: Optional[str] = Field(default=None, description="Meta Model API Bearer token")
    meta_base_url: str = Field(default="https://api.meta.ai/v1", description="Base URL for Meta Model API")
    muse_image_model: str = Field(default="muse-image-1.0", description="Image generation model")
    muse_spark_model: str = Field(default="muse-spark-1.3", description="Director and judge model")
    sam_model: str = Field(default="sam-3.1", description="Segmentation model")
    global_spend_cap_usd: float = Field(default=25.0, description="Global spending cap in USD")
    max_retries_per_panel: int = Field(default=2, description="Maximum targeted retries per panel")
    max_concurrent_requests: int = Field(default=2, description="Maximum parallel calls to Meta API")

    @classmethod
    def load(cls) -> "InkLoopConfig":
        return cls(
            meta_api_key=os.getenv("META_API_KEY") or os.getenv("MODEL_API_KEY"),
            meta_base_url=os.getenv("META_BASE_URL", "https://api.meta.ai/v1"),
            muse_image_model=os.getenv("MUSE_IMAGE_MODEL", "muse-image-1.0"),
            muse_spark_model=os.getenv("MUSE_SPARK_MODEL", "muse-spark-1.3"),
            sam_model=os.getenv("SAM_MODEL", "sam-3.1"),
            global_spend_cap_usd=float(os.getenv("GLOBAL_SPEND_CAP_USD", "25.0")),
            max_retries_per_panel=int(os.getenv("MAX_RETRIES_PER_PANEL", "2")),
            max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "2")),
        )

    @property
    def has_credentials(self) -> bool:
        return bool(self.meta_api_key and len(self.meta_api_key.strip()) > 5)

    def mask_key(self) -> str:
        if not self.has_credentials:
            return "[NOT SET]"
        return f"{self.meta_api_key[:4]}...{self.meta_api_key[-4:]}"
