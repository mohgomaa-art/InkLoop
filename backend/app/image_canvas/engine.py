"""
InkLoop Image-Canvas Integration Engine (E3) - Primary Engine Service.
Orchestrates placing source artwork into E2-generated panel slots with exact aspect-ratio
preservation, anchor-directed cropping, anti-aliased polygonal clipping, and lineage tracking.
"""
import uuid
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

from app.contracts.geometry import Rect, Size, Point, FitMode
from app.contracts.engine import ImageCanvasIntegrationParams, ImageCanvasIntegrationOutput
from app.contracts.identity import IdPrefix, generate_id
from app.canvas.models import PanelSlot, CanvasLayoutResult, CanvasSpec
from app.image_canvas.models import (
    PlacementSpec,
    PlacedPanelLayer,
    PageIntegrationResult,
    ResamplingFilter,
)
from app.image_canvas.errors import (
    PlacementError,
    AssetResolutionError,
    InvalidPlacementGeometryError,
)
from app.image_canvas.fitter import compute_placement_transform
from app.image_canvas.raster_ops import (
    load_source_image,
    apply_fit_manual_transform,
    apply_polygon_mask,
    encode_png_bytes,
)

class ImageCanvasIntegrationEngine:
    """
    Specialist Production Engine E3: Image-Canvas Integration Engine.
    Places source artwork into E2 canvas panel slots deterministically without
    altering canvas geometry, compositing dialogue, or generating final export books.
    """

    @classmethod
    def place_artwork_in_slot(
        cls,
        panel_slot: PanelSlot,
        spec: PlacementSpec,
        canvas_spec: Optional[CanvasSpec] = None,
        asset_registry: Optional[Any] = None
    ) -> PlacedPanelLayer:
        """
        Integrates a single source artwork into the target panel slot.
        """
        # 1. Resolve source image bytes
        source_bytes: Optional[bytes] = None
        source_path: Optional[str] = None
        artifact_id = spec.source_artifact_id

        if spec.source_image_bytes is not None:
            source_bytes = spec.source_image_bytes
        elif spec.source_file_path is not None:
            source_path = str(spec.source_file_path)
            p = Path(source_path)
            if not p.is_file():
                raise AssetResolutionError(f"Source file not found at path: {source_path}")
            source_bytes = p.read_bytes()
        elif artifact_id is not None and asset_registry is not None:
            try:
                resolved = asset_registry.resolve_asset(artifact_id)
                source_path = str(resolved.absolute_path)
                source_bytes = resolved.absolute_path.read_bytes()
            except Exception as e:
                raise AssetResolutionError(f"Failed to resolve artifact '{artifact_id}' from registry: {e}")
        else:
            raise AssetResolutionError(
                f"No source artwork provided for panel '{panel_slot.panel_id}'. Specify source_image_bytes, source_file_path, or source_artifact_id."
            )

        # 2. Load and inspect native image
        source_img, src_hash, src_size = load_source_image(source_bytes)

        # 3. Determine effective target rectangle
        target_rect = panel_slot.rect
        if panel_slot.is_full_bleed and spec.allow_bleed and canvas_spec is not None:
            b = canvas_spec.bleed
            # Expand target rect to outer bleed edges
            target_rect = Rect(
                x=target_rect.x - b.left,
                y=target_rect.y - b.top,
                width=target_rect.width + b.left + b.right,
                height=target_rect.height + b.top + b.bottom
            )

        # 4. Compute exact placement transform
        transform, placed_rect, is_clipped = compute_placement_transform(
            source_size=src_size,
            target_rect=target_rect,
            mode=spec.fit_mode,
            anchor=spec.anchor
        )

        # 5. Fit and transform the complete source, then crop it to the fixed panel canvas.
        target_size = Size(width=target_rect.width, height=target_rect.height)
        placed_img = apply_fit_manual_transform(
            source_img=source_img,
            target_size=target_size,
            mode=spec.fit_mode,
            anchor=spec.anchor,
            transform=spec.manual_transform,
            resampling=spec.resampling,
            background_color=spec.background_color
        )

        # 6. Apply polygon alpha mask if slot is dynamic/non-rectangular
        has_poly = False
        if panel_slot.has_polygon and panel_slot.polygon and spec.clip_to_polygon:
            placed_img = apply_polygon_mask(
                img=placed_img,
                polygon_points=panel_slot.polygon,
                target_slot_rect=target_rect
            )
            has_poly = True
            is_clipped = True

        # 7. Encode output PNG bytes
        out_bytes, out_hash = encode_png_bytes(placed_img)

        # Optional registration in asset registry
        layer_id = generate_id(IdPrefix.ARTIFACT, f"layer_{panel_slot.panel_id}")
        if asset_registry is not None and hasattr(asset_registry, "register_bytes"):
            try:
                from app.contracts.artifacts import AssetType
                parent_ids = [artifact_id] if artifact_id else []
                asset_registry.register_bytes(
                    data=out_bytes,
                    filename=f"{layer_id}.png",
                    asset_type=AssetType.PANEL_IMAGE,
                    project_id="proj_default",
                    parent_ids=parent_ids,
                    tags=["placed_layer", panel_slot.panel_id]
                )
            except Exception:
                pass  # Non-fatal if in standalone test mode

        local_rect = Rect(x=0.0, y=0.0, width=target_rect.width, height=target_rect.height)

        return PlacedPanelLayer(
            layer_id=layer_id,
            panel_id=panel_slot.panel_id,
            source_artifact_id=artifact_id,
            source_content_hash=src_hash,
            output_content_hash=out_hash,
            source_dimensions=src_size,
            target_slot_rect=target_rect,
            placed_rect=placed_rect,
            local_rect=local_rect,
            transform_applied=transform,
            manual_transform_applied=spec.manual_transform,
            fit_mode_applied=spec.fit_mode,
            anchor_applied=spec.anchor,
            is_clipped=is_clipped,
            has_polygon_mask=has_poly,
            output_image_bytes=out_bytes,
        )

    @classmethod
    def integrate_page(
        cls,
        layout_result: CanvasLayoutResult,
        placements: Dict[str, PlacementSpec],
        asset_registry: Optional[Any] = None
    ) -> PageIntegrationResult:
        """
        Integrates source artworks across all defined panels of a page layout.
        """
        placed_layers: Dict[str, PlacedPanelLayer] = {}
        unplaced: List[str] = []
        diagnostics: List[Dict[str, Any]] = []

        for slot in layout_result.panel_slots:
            spec = placements.get(slot.panel_id)
            if spec is None:
                unplaced.append(slot.panel_id)
                continue

            try:
                layer = cls.place_artwork_in_slot(
                    panel_slot=slot,
                    spec=spec,
                    canvas_spec=layout_result.canvas_spec,
                    asset_registry=asset_registry
                )
                placed_layers[slot.panel_id] = layer
            except Exception as e:
                unplaced.append(slot.panel_id)
                diagnostics.append({
                    "panel_id": slot.panel_id,
                    "error": str(e),
                })

        return PageIntegrationResult(
            integration_id=f"page_int_{uuid.uuid4().hex[:8]}",
            canvas_id=layout_result.canvas_id,
            page_id=layout_result.page_spec.page_id,
            placed_layers=placed_layers,
            total_panels=layout_result.panel_count,
            placed_panels=len(placed_layers),
            unplaced_panels=unplaced,
            diagnostics=diagnostics,
        )

    @classmethod
    def integrate_from_engine_params(
        cls,
        params: ImageCanvasIntegrationParams,
        asset_registry: Optional[Any] = None
    ) -> ImageCanvasIntegrationOutput:
        """
        Implements the shared specialist contract ImageCanvasIntegrationParams -> ImageCanvasIntegrationOutput.
        """
        # Create a synthetic PanelSlot matching target_slot_rect
        slot = PanelSlot(
            panel_id=params.target_panel_id,
            reading_order=1,
            rect=params.target_slot_rect,
            is_full_bleed=params.allow_bleed,
        )

        spec = PlacementSpec(
            target_panel_id=params.target_panel_id,
            source_artifact_id=params.source_image_artifact_id,
            fit_mode=params.fit_mode,
            anchor=params.anchor,
            allow_bleed=params.allow_bleed,
        )

        layer = cls.place_artwork_in_slot(
            panel_slot=slot,
            spec=spec,
            asset_registry=asset_registry
        )
        return layer.to_engine_output()
