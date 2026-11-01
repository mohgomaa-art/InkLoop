"""
InkLoop Image-Canvas Integration Engine (E3).
Provides deterministic fitting, aspect-ratio preservation, anchor-directed cropping,
anti-aliased polygonal clipping, and lineage tracking for comic panel artwork.
"""
from app.image_canvas.models import (
    PlacementSpec,
    PlacedPanelLayer,
    PageIntegrationResult,
    ResamplingFilter,
)
from app.image_canvas.errors import (
    PlacementError,
    InvalidPlacementGeometryError,
    AssetResolutionError,
    UnsupportedImageFormatError,
    AllocationLimitExceededError,
    AspectRatioDistortionError,
)
from app.image_canvas.engine import ImageCanvasIntegrationEngine
from app.image_canvas.fitter import (
    compute_placement_transform,
    compute_source_crop_rect,
)
from app.image_canvas.raster_ops import (
    load_source_image,
    apply_placement_raster,
    apply_polygon_mask,
    encode_png_bytes,
)

__all__ = [
    "ImageCanvasIntegrationEngine",
    "PlacementSpec",
    "PlacedPanelLayer",
    "PageIntegrationResult",
    "ResamplingFilter",
    "PlacementError",
    "InvalidPlacementGeometryError",
    "AssetResolutionError",
    "UnsupportedImageFormatError",
    "AllocationLimitExceededError",
    "AspectRatioDistortionError",
    "compute_placement_transform",
    "compute_source_crop_rect",
    "load_source_image",
    "apply_placement_raster",
    "apply_polygon_mask",
    "encode_png_bytes",
]
