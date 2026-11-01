"""
InkLoop Image-Canvas Integration Engine (E3) - Domain Models and Contracts.
Defines typed models for image placement specifications, placed layer artifacts,
resampling filters, and whole-page integration results.
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator

from app.contracts.geometry import (
    Rect,
    Point,
    Size,
    FitMode,
    Transform2D,
)
from app.contracts.engine import ImageCanvasIntegrationOutput
from app.canvas.models import PanelSlot, CanvasLayoutResult
from app.image_canvas.errors import InvalidPlacementGeometryError

class ResamplingFilter(str, Enum):
    """Interpolation algorithms for image scaling and transformation."""
    LANCZOS = "lanczos"     # High-quality anti-aliasing sinc filter (default for comic artwork)
    BICUBIC = "bicubic"     # Smooth cubic spline interpolation
    BILINEAR = "bilinear"   # Fast linear interpolation
    NEAREST = "nearest"     # Nearest-neighbor pixelated filter (for screentones/pixel art)

class PlacementSpec(BaseModel):
    """
    Specification for placing a single source artwork into a target panel slot.
    Governs fit mode, anchor alignment, resampling filter, and clipping behavior.
    """
    target_panel_id: str = Field(..., description="Target panel slot identifier from CanvasLayoutResult")
    source_artifact_id: Optional[str] = Field(default=None, description="Registered asset ID in AssetRegistry")
    source_image_bytes: Optional[bytes] = Field(default=None, description="Direct in-memory image bytes")
    source_file_path: Optional[str] = Field(default=None, description="Direct filesystem path to source image")
    fit_mode: FitMode = Field(default=FitMode.COVER, description="Fit policy: COVER, CONTAIN, or STRETCH")
    anchor: Point = Field(default_factory=lambda: Point(x=0.5, y=0.5), description="Normalized anchor: (0.5, 0.5) = center")
    manual_transform: Transform2D = Field(default_factory=Transform2D, description="Non-destructive user transform applied inside the fixed panel mask")
    resampling: ResamplingFilter = Field(default=ResamplingFilter.LANCZOS)
    allow_upscaling: bool = Field(default=True, description="Whether to allow scaling image beyond its native dimensions")
    allow_bleed: bool = Field(default=False, description="Whether placement can expand to outer page bleed envelope")
    background_color: Optional[str] = Field(default=None, description="Letterbox background hex (None = transparent RGBA)")
    clip_to_polygon: bool = Field(default=True, description="Whether to apply polygonal mask if target slot is non-rectangular")

    @field_validator("anchor")
    @classmethod
    def validate_anchor_range(cls, v: Point) -> Point:
        if v.x < 0.0 or v.x > 1.0 or v.y < 0.0 or v.y > 1.0:
            raise InvalidPlacementGeometryError(
                f"Anchor coordinates must be normalized within [0.0, 1.0], received ({v.x}, {v.y})"
            )
        return v

    @field_validator("fit_mode")
    @classmethod
    def require_aspect_preserving_fit(cls, v: FitMode) -> FitMode:
        if v not in (FitMode.COVER, FitMode.CONTAIN):
            raise InvalidPlacementGeometryError(
                "Panel artwork must preserve its source aspect ratio; choose COVER (crop to the panel mask) or CONTAIN (show the full image)."
            )
        return v

    @field_validator("manual_transform")
    @classmethod
    def preserve_uniform_manual_scale(cls, v: Transform2D) -> Transform2D:
        if abs(v.scale_x - v.scale_y) > 1e-6:
            raise InvalidPlacementGeometryError(
                "Manual panel-image scaling must preserve aspect ratio (scale_x must equal scale_y)."
            )
        return v

class PlacedPanelLayer(BaseModel):
    """
    Resulting placed raster layer artifact produced by E3 for a single panel slot.
    Maintains complete transformation provenance, coordinates in both local and page space,
    and cryptographic checksums.
    """
    layer_id: str = Field(..., description="Unique placed layer identifier, e.g., 'layer_panel_01_...'")
    panel_id: str = Field(..., description="Target panel slot identifier")
    source_artifact_id: Optional[str] = Field(default=None, description="Lineage reference to source asset")
    source_content_hash: str = Field(..., description="SHA-256 of source image input")
    output_content_hash: str = Field(..., description="SHA-256 of resulting placed PNG raster")
    source_dimensions: Size = Field(..., description="Native dimensions of source image")
    target_slot_rect: Rect = Field(..., description="Target panel boundary in PAGE coordinate space")
    placed_rect: Rect = Field(..., description="Effective bounding box of placed artwork in PAGE space")
    local_rect: Rect = Field(..., description="Local coordinate frame: [0, 0, width, height)")
    transform_applied: Transform2D = Field(..., description="Exact affine transform applied to map source to target")
    manual_transform_applied: Transform2D = Field(default_factory=Transform2D, description="Additional user transform applied after fit and before clipping")
    fit_mode_applied: FitMode = Field(..., description="Fit mode applied")
    anchor_applied: Point = Field(..., description="Normalized anchor used")
    is_clipped: bool = Field(default=False, description="Whether content was cropped/clipped during placement")
    has_polygon_mask: bool = Field(default=False, description="Whether an anti-aliased polygonal mask was applied")
    output_image_bytes: Optional[bytes] = Field(default=None, description="Placed PNG image bytes")
    output_png_path: Optional[str] = Field(default=None, description="Filesystem path if written to disk")

    def to_engine_output(self) -> ImageCanvasIntegrationOutput:
        """Adapts this placed panel layer to the shared contract ImageCanvasIntegrationOutput."""
        return ImageCanvasIntegrationOutput(
            panel_layer_artifact_id=self.layer_id,
            placed_rect=self.placed_rect,
            transform_applied=self.transform_applied,
            fit_mode_applied=self.fit_mode_applied,
            clipped=self.is_clipped,
        )

class PageIntegrationResult(BaseModel):
    """
    Aggregate result representing a completed page integration where source artworks
    have been placed into all defined panel slots of a CanvasLayoutResult.
    """
    integration_id: str = Field(..., description="Unique page integration operation identifier")
    canvas_id: str = Field(..., description="Associated canvas layout identifier")
    page_id: str = Field(..., description="Associated page identifier")
    placed_layers: Dict[str, PlacedPanelLayer] = Field(default_factory=dict, description="Placed layers keyed by panel_id")
    total_panels: int = Field(default=0)
    placed_panels: int = Field(default=0)
    unplaced_panels: List[str] = Field(default_factory=list)
    diagnostics: List[Dict[str, Any]] = Field(default_factory=list)

    @property
    def is_fully_placed(self) -> bool:
        return self.placed_panels == self.total_panels and len(self.unplaced_panels) == 0

    def get_layer(self, panel_id: str) -> Optional[PlacedPanelLayer]:
        return self.placed_layers.get(panel_id)
