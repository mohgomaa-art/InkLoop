"""
Asset Reference interface and integrity validation for InkLoop Story Bible.
Ensures references point to existing files within project bounds with matching SHA-256 hashes.
Never embeds binary bytes or base64 strings in Bible metadata.
"""
from pathlib import Path
import hashlib
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class AssetIntegrityError(Exception):
    """Base exception for asset integrity violations."""
    pass

class PathTraversalError(AssetIntegrityError):
    """Raised when an asset path attempts directory traversal outside allowed project root."""
    pass

class AssetNotFoundError(AssetIntegrityError):
    """Raised when a referenced asset file does not exist on disk."""
    pass

class AssetHashMismatchError(AssetIntegrityError):
    """Raised when actual file SHA-256 does not match expected hash in AssetRef."""
    pass

class InvalidAssetTypeError(AssetIntegrityError):
    """Raised when an asset has an unsupported file extension or MIME type."""
    pass

ALLOWED_IMAGE_EXTENSIONS = {".png", ".webp", ".jpg", ".jpeg"}
ALLOWED_MIME_TYPES = {"image/png", "image/webp", "image/jpeg"}

class AssetRef(BaseModel):
    """
    Reference to a static asset stored in the project workspace or artifact store.
    Stores metadata and content hash only; never stores binary payloads.
    """
    asset_id: str = Field(..., description="Unique asset identifier")
    path: str = Field(..., description="Path relative to project root")
    asset_type: Literal["character_sheet", "style_reference", "location_ref", "prop_ref", "generic_image"] = Field(
        ..., description="Semantic type of the asset"
    )
    expected_hash: str = Field(..., description="Hex-encoded SHA-256 digest of the asset file")
    mime_type: str = Field(default="image/png", description="MIME type of the asset")
    file_size_bytes: Optional[int] = Field(default=None, description="Optional recorded file size in bytes")
    provenance: Optional[Dict[str, Any]] = Field(default=None, description="Generation metadata or author provenance")

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(self, "expected_hash", self.expected_hash.lower().strip())

def compute_file_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """Computes SHA-256 checksum of a file in streaming chunks."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest().lower()

def validate_asset_ref(
    ref: AssetRef,
    project_root: Path,
    verify_hash: bool = True
) -> Path:
    """
    Validates that:
    1. Asset path does not escape project_root (Path traversal protection).
    2. Asset exists on disk.
    3. Asset file extension and mime type are allowed.
    4. Expected SHA-256 hash matches actual file contents.
    
    Returns the resolved absolute Path if valid.
    """
    project_root = project_root.resolve()
    target_path = (project_root / ref.path).resolve()
    
    # Path traversal protection
    try:
        target_path.relative_to(project_root)
    except ValueError:
        raise PathTraversalError(
            f"Asset path traversal detected: '{ref.path}' escapes project root '{project_root}'"
        )
    
    if not target_path.is_file():
        raise AssetNotFoundError(
            f"Referenced asset file not found at '{target_path}' (asset_id='{ref.asset_id}')"
        )
    
    ext = target_path.suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise InvalidAssetTypeError(
            f"Unsupported asset extension '{ext}' for asset '{ref.asset_id}'. Allowed: {ALLOWED_IMAGE_EXTENSIONS}"
        )
    
    if ref.mime_type not in ALLOWED_MIME_TYPES:
        raise InvalidAssetTypeError(
            f"Unsupported MIME type '{ref.mime_type}' for asset '{ref.asset_id}'. Allowed: {ALLOWED_MIME_TYPES}"
        )

    if verify_hash:
        actual_hash = compute_file_sha256(target_path)
        if actual_hash != ref.expected_hash:
            raise AssetHashMismatchError(
                f"Asset hash mismatch for '{ref.asset_id}' at '{ref.path}': "
                f"expected {ref.expected_hash}, computed {actual_hash}"
            )

    return target_path
