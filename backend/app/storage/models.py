"""
InkLoop Asset Registry & Artifact Store - Metadata Contracts and Models.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, ConfigDict

from app.contracts.artifacts import AssetType, LifecycleStatus, ArtifactManifest
from app.contracts.geometry import Size
from app.project.asset_refs import AssetRef


def utc_now_iso() -> str:
    """Returns current UTC time formatted as standard ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


class AssetMetadata(BaseModel):
    """
    Complete, validated metadata record for an artifact stored in the managed store.
    Separates searchable metadata and lineage from binary bytes.
    """
    asset_id: str = Field(..., description="Stable unique asset identifier (e.g. 'art_nour_01_a9f8')")
    project_id: str = Field(..., description="Project owning this artifact")
    run_id: Optional[str] = Field(default=None, description="Execution run ID if produced during a pipeline run")
    asset_type: AssetType = Field(..., description="Categorical asset family")
    name: str = Field(..., description="Logical or display name of the asset")
    original_filename: str = Field(..., description="Original filename of the imported or generated artifact")
    managed_path: str = Field(..., description="Relative path within the managed artifact store")
    mime_type: str = Field(..., description="Verified MIME content type (e.g. 'image/png', 'font/ttf')")
    extension: str = Field(..., description="Normalized file extension with leading dot (e.g. '.png')")
    byte_size: int = Field(..., description="Actual byte size on disk")
    content_sha256: str = Field(..., description="Cryptographic SHA-256 digest of the actual file bytes")
    width: Optional[int] = Field(default=None, description="Pixel width if raster image or canvas")
    height: Optional[int] = Field(default=None, description="Pixel height if raster image or canvas")
    dpi: Optional[float] = Field(default=300.0, description="Declared resolution in dots per inch")
    page_count: Optional[int] = Field(default=None, description="Total pages if PDF or document export")
    font_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Font metrics, glyph count, format family")
    created_at: str = Field(default_factory=utc_now_iso, description="ISO 8601 creation timestamp")
    source_origin: Optional[str] = Field(default=None, description="Human/provenance note (e.g. 'E1 prompt: Nour in alley')")
    license_info: Optional[str] = Field(default=None, description="License terms (e.g. 'SIL OFL 1.1', 'Original Proprietary')")
    engine_id: Optional[str] = Field(default=None, description="Producing engine identifier (e.g. 'E1_IMAGE_GEN')")
    engine_version: Optional[str] = Field(default=None, description="Producing engine semantic version")
    config_hash: Optional[str] = Field(default=None, description="Engine configuration content hash")
    parent_asset_ids: List[str] = Field(default_factory=list, description="Direct predecessor asset IDs in lineage graph")
    lineage_operation: Optional[str] = Field(default=None, description="Transformation operation (e.g. 'crop', 'compose', 'render_text')")
    lineage_params: Dict[str, Any] = Field(default_factory=dict, description="Audit parameters of the transformation")
    schema_version: str = Field(default="1.0.0", description="Asset metadata schema version")
    validation_state: Literal["valid", "invalid", "pending"] = Field(default="valid", description="Format validation outcome")
    validation_errors: List[str] = Field(default_factory=list, description="Validation issues if any")
    lifecycle_status: LifecycleStatus = Field(default=LifecycleStatus.APPROVED, description="Lifecycle and approval state")
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary engine-specific metadata")

    model_config = ConfigDict(frozen=True)

    def to_asset_ref(self) -> AssetRef:
        """
        Bridges to the Story Bible AssetRef interface used by character, style, and location definitions.
        Maps AssetType to the expected AssetRef semantic category.
        """
        asset_type_map = {
            AssetType.IMAGE_REFERENCE: "character_sheet",
            AssetType.IMAGE_GENERATED: "generic_image",
            AssetType.COMPOSITE_PAGE: "generic_image",
            AssetType.EXPORT_PNG: "generic_image",
            AssetType.PAGE_PREVIEW: "generic_image",
            AssetType.PANEL_LAYER: "generic_image",
        }
        ref_type = asset_type_map.get(self.asset_type, "generic_image")
        return AssetRef(
            asset_id=self.asset_id,
            path=self.managed_path.replace("\\", "/"),
            asset_type=ref_type,
            expected_hash=self.content_sha256,
            mime_type=self.mime_type,
            file_size_bytes=self.byte_size,
            provenance={
                "engine_id": self.engine_id,
                "engine_version": self.engine_version,
                "project_id": self.project_id,
                "run_id": self.run_id,
                "source_origin": self.source_origin,
                "license_info": self.license_info,
            }
        )

    def to_artifact_manifest(self) -> ArtifactManifest:
        """Bridges to the shared contracts ArtifactManifest model."""
        dims = None
        if self.width is not None and self.height is not None:
            dims = Size(width=float(self.width), height=float(self.height))

        return ArtifactManifest(
            artifact_id=self.asset_id,
            asset_type=self.asset_type,
            version=1,
            mime_type=self.mime_type,
            file_path=self.managed_path.replace("\\", "/"),
            content_sha256=self.content_sha256,
            byte_size=self.byte_size,
            dimensions=dims,
            dpi=self.dpi,
            created_at=self.created_at,
            run_id=self.run_id or "run_unassigned",
            parent_artifact_ids=self.parent_asset_ids,
            metadata={
                **self.extra_metadata,
                "engine_id": self.engine_id,
                "engine_version": self.engine_version,
                "config_hash": self.config_hash,
                "lineage_operation": self.lineage_operation,
                "lineage_params": self.lineage_params,
            },
            lifecycle_status=self.lifecycle_status
        )


class ResolvedAsset(BaseModel):
    """
    An asset resolved from the registry with verified local filesystem path.
    """
    metadata: AssetMetadata
    absolute_path: Path
    is_verified: bool = Field(..., description="True if content SHA-256 was checked and matched disk file")

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)


class AssetFilter(BaseModel):
    """Query filters for listing registered assets."""
    project_id: Optional[str] = None
    run_id: Optional[str] = None
    asset_type: Optional[Union[AssetType, List[AssetType]]] = None
    parent_id: Optional[str] = None
    lifecycle_status: Optional[LifecycleStatus] = None
    validation_state: Optional[Literal["valid", "invalid", "pending"]] = None
    engine_id: Optional[str] = None
    extension: Optional[str] = None


class AssetManifestDocument(BaseModel):
    """
    Machine-readable export manifest capturing all registered artifacts,
    reproducible hashes, and lineage relationships for a project or run.
    Contains zero binary data or secrets.
    """
    manifest_id: str = Field(..., description="Unique manifest identifier")
    project_id: str
    run_id: Optional[str] = None
    schema_version: str = "1.0.0"
    generated_at: str = Field(default_factory=utc_now_iso)
    asset_count: int
    assets: List[AssetMetadata]
    lineage_graph: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Graph mapping parent_asset_id -> [child_asset_ids]"
    )
    manifest_sha256: str = Field(..., description="Deterministic SHA-256 digest of the manifest content")
