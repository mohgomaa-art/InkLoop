import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Resolve project root relative to this file: backend/app/config.py -> parent.parent.parent
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOTENV_PATH = PROJECT_ROOT / ".env"

# Explicitly load project-root .env if it exists
if DOTENV_PATH.exists():
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    load_dotenv()

class InkLoopConfig(BaseModel):
    """Central configuration for InkLoop with fail-safe bounds."""
    model_api_key: Optional[str] = Field(
        default_factory=lambda: (os.getenv("MODEL_API_KEY") or os.getenv("META_API_KEY") or "").strip() or None,
        description="Meta Model API Bearer token (MODEL_API_KEY)"
    )
    meta_base_url: str = Field(
        default_factory=lambda: os.getenv("META_BASE_URL", "https://api.meta.ai/v1"),
        description="Base URL for Meta Model API"
    )
    muse_image_model: str = Field(
        default_factory=lambda: os.getenv("MUSE_IMAGE_MODEL", "muse-image-1.0"),
        description="Image generation model"
    )
    muse_spark_model: str = Field(
        default_factory=lambda: os.getenv("MUSE_SPARK_MODEL", "muse-spark-1.3"),
        description="Director and judge model"
    )
    sam_model: str = Field(
        default_factory=lambda: os.getenv("SAM_MODEL", "sam-3.1"),
        description="Segmentation model"
    )
    global_spend_cap_usd: float = Field(
        default_factory=lambda: float(os.getenv("GLOBAL_SPEND_CAP_USD", "25.0")),
        description="Global spending cap in USD"
    )
    max_retries_per_panel: int = Field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES_PER_PANEL", "2")),
        description="Maximum targeted retries per panel"
    )
    max_concurrent_requests: int = Field(
        default_factory=lambda: int(os.getenv("MAX_CONCURRENT_REQUESTS", "2")),
        description="Maximum parallel calls to Meta API"
    )
    host: str = Field(
        default_factory=lambda: os.getenv("HOST", "127.0.0.1"),
        description="Server bind host"
    )
    port: int = Field(
        default_factory=lambda: int(os.getenv("PORT", "8000")),
        description="Server bind port"
    )
    data_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data"))).resolve(),
        description="Configurable directory for runtime data and outputs"
    )

    @classmethod
    def load(cls) -> "InkLoopConfig":
        cfg = cls()
        cfg.data_dir.mkdir(parents=True, exist_ok=True)
        return cfg

    @property
    def base_url(self) -> str:
        return self.meta_base_url

    @property
    def api_key(self) -> Optional[str]:
        return self.model_api_key

    @property
    def has_credentials(self) -> bool:
        return bool(self.model_api_key and len(self.model_api_key) > 5)

    def mask_key(self) -> str:
        """Returns safe status without revealing any portion of the secret value."""
        if not self.has_credentials:
            return "[NOT SET]"
        return "[SET - REDACTED]"
