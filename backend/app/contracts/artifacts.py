"""
InkLoop Shared Artifact and Asset Manifest Contracts.
Standardizes metadata, content hashing, lineage tracking, and physical storage references.
"""
import hashlib
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.contracts.geometry import Size

class AssetType(str, Enum):
    """Categorical types of artifacts produced and consumed by InkLoop engines."""
    IMAGE_REFERENCE = "image_reference"       # Approved canonical character/style reference
    IMAGE_GENERATED = "image_generated"       # Raw generated artwork from E1 Image Engine
    CANVAS_SPEC = "canvas_spec"               # Page/layout geometry description from E2 Canvas Engine
    PANEL_LAYER = "panel_layer"               # Fitted/cropped panel layer from E3 Integration Engine
    TEXT_BLOCK = "text_block"                 # Dialogue/script text blocks from E4 Text Engine
    FONT_FILE = "font_file"                   # TTF/OTF/WOFF2 font asset from E5 Typography Engine
    LETTERING_LAYER = "lettering_layer"       # Rendered text SVG/PNG layer from E5 Typography Engine
    BUBBLE_LAYER = "bubble_layer"             # Speech bubble vector/raster layer from E6 Bubble Engine
    EFFECT_LAYER = "effect_layer"             # Independent motion/visual effect layer from E7 Effects Engine
    COMPOSITE_PAGE = "composite_page"         # Fully assembled page bitmap/vector from S6 Compositor
    QA_REPORT = "qa_report"                   # Quality assurance verdict and evidence log from S7 QA
    EXPORT_PDF = "export_pdf"                 # Final published book/page PDF from S8 Export Engine
    EXPORT_PNG = "export_png"                 # High-resolution raster export from S8 Export Engine

class LifecycleStatus(str, Enum):
    """Lifecycle and approval state of an artifact."""
    DRAFT = "draft"               # Initial unapproved generation
    APPROVED = "approved"         # Approved for inclusion in downstream composites
    REJECTED = "rejected"         # Rejected by QA gate or user
    ARCHIVED = "archived"         # Superseded by newer version
    DELETED = "deleted"           # Marked for tombstoning/purge

class StorageRef(BaseModel):
    """Location reference for a stored binary or document artifact."""
    backend: str = Field(default="local_filesystem", description="Storage backend ('local_filesystem')")
    relative_path: str = Field(..., description="Repository-relative path to the stored file")
    uri: Optional[str] = Field(default=None, description="Optional URI representation (e.g. 'file:///...')")

class ArtifactManifest(BaseModel):
    """
    Immutable manifest record for a concrete binary or serialized asset.
    Stores content SHA-256, lineage parents, and validation status without embedding large raw bytes.
    """
    artifact_id: str = Field(..., description="Unique artifact identifier (e.g. 'art_nour_ref_01')")
    asset_type: AssetType = Field(..., description="Categorical asset type")
    version: int = Field(default=1, description="Version sequence number")
    mime_type: str = Field(..., description="MIME content type (e.g. 'image/png', 'application/json')")
    file_path: str = Field(..., description="Relative storage path from project root")
    content_sha256: str = Field(..., description="Cryptographic SHA-256 digest of file content")
    byte_size: int = Field(..., description="Size in bytes on disk")
    dimensions: Optional[Size] = Field(default=None, description="Pixel dimensions if applicable")
    dpi: Optional[float] = Field(default=300.0, description="Declared resolution in dots per inch")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 UTC timestamp")
    run_id: str = Field(..., description="Run execution identifier that generated this artifact")
    parent_artifact_ids: List[str] = Field(default_factory=list, description="Immediate predecessor artifact IDs for lineage tracking")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Engine-specific provenance or parameter metadata")
    lifecycle_status: LifecycleStatus = Field(default=LifecycleStatus.DRAFT, description="Approval and lifecycle state")

def compute_file_sha256(path: Path) -> str:
    """Computes hexadecimal SHA-256 checksum for a file on disk."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def build_artifact_manifest(
    file_path: Path,
    project_root: Path,
    artifact_id: str,
    asset_type: AssetType,
    run_id: str,
    mime_type: str,
    version: int = 1,
    dimensions: Optional[Size] = None,
    dpi: Optional[float] = 300.0,
    parent_artifact_ids: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    lifecycle_status: LifecycleStatus = LifecycleStatus.DRAFT
) -> ArtifactManifest:
    """Helper to construct an ArtifactManifest directly from a generated file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Cannot build artifact manifest: file does not exist at {file_path}")

    sha256 = compute_file_sha256(file_path)
    byte_size = file_path.stat().st_size
    rel_path = str(file_path.relative_to(project_root))

    return ArtifactManifest(
        artifact_id=artifact_id,
        asset_type=asset_type,
        version=version,
        mime_type=mime_type,
        file_path=rel_path,
        content_sha256=sha256,
        byte_size=byte_size,
        dimensions=dimensions,
        dpi=dpi,
        run_id=run_id,
        parent_artifact_ids=parent_artifact_ids or [],
        metadata=metadata or {},
        lifecycle_status=lifecycle_status
    )
