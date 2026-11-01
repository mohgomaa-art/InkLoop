"""
InkLoop Canvas Generation Engine (E2) - Vertical Webtoon Strip Template.
Generates continuous vertical scroll layouts with deterministic panel heights,
pacing gaps, margin padding, and optional dynamic canvas height derivation.
"""
import uuid
from typing import List, Optional, Any

from app.contracts.geometry import Rect, snap_to_pixel_grid
from app.canvas.models import (
    CanvasSpec,
    PageSpec,
    PanelSlot,
    CanvasLayoutResult,
    LayoutTemplateId,
    ReadingDirection,
)
from app.canvas.errors import ImpossibleLayoutError, InvalidDimensionError
from app.canvas.templates.base import BaseLayoutTemplate

class WebtoonVerticalTemplate(BaseLayoutTemplate):
    """
    Vertical continuous scroll webtoon template.
    Arranges panels in a single vertical column with cinematic pacing gaps between scenes.
    """
    template_id = LayoutTemplateId.WEBTOON_VERTICAL
    version = "1.0.0"
    description = "Vertical continuous scroll webtoon layout with cinematic pacing gaps."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        panel_count: int = 4,
        panel_heights: Optional[List[float]] = None,
        vertical_gaps: Optional[List[float]] = None,
        panel_width_ratio: float = 1.0,
        derive_canvas_height: bool = True,
        **params: Any
    ) -> CanvasLayoutResult:
        if panel_count < 1:
            raise InvalidDimensionError(f"panel_count must be >= 1, got {panel_count}")

        if panel_count > 50:
            raise ImpossibleLayoutError(f"panel_count ({panel_count}) exceeds single strip allocation ceiling (max 50)")

        if panel_width_ratio <= 0.0 or panel_width_ratio > 1.0:
            raise InvalidDimensionError(f"panel_width_ratio must be in (0.0, 1.0], got {panel_width_ratio}")

        # Resolve panel heights (default 600 px per panel if unspecified)
        if panel_heights is None:
            resolved_heights = [600.0] * panel_count
        else:
            if len(panel_heights) != panel_count:
                raise InvalidDimensionError(f"panel_heights length ({len(panel_heights)}) must match panel_count ({panel_count})")
            for h in panel_heights:
                if h <= 0:
                    raise InvalidDimensionError(f"Panel height must be strictly positive, got {h}")
            resolved_heights = [float(h) for h in panel_heights]

        # Resolve vertical gaps (default to canvas_spec.gutters.vertical or 80.0 px)
        default_gap = canvas_spec.gutters.vertical if canvas_spec.gutters.vertical > 0 else 80.0
        if vertical_gaps is None:
            resolved_gaps = [default_gap] * (panel_count - 1)
        else:
            if len(vertical_gaps) != (panel_count - 1):
                raise InvalidDimensionError(f"vertical_gaps length ({len(vertical_gaps)}) must be panel_count - 1 ({panel_count - 1})")
            for g in vertical_gaps:
                if g < 0:
                    raise InvalidDimensionError(f"Vertical gap must be non-negative, got {g}")
            resolved_gaps = [float(g) for g in vertical_gaps]

        # Calculate total content height required
        m = canvas_spec.margins
        content_height = sum(resolved_heights) + sum(resolved_gaps)
        required_total_height = m.top + content_height + m.bottom

        # Derive or validate canvas height
        effective_canvas_spec = canvas_spec
        if derive_canvas_height:
            if required_total_height != canvas_spec.height_px:
                effective_canvas_spec = canvas_spec.model_copy(update={"height_px": required_total_height})
        else:
            if required_total_height > canvas_spec.height_px:
                raise ImpossibleLayoutError(
                    f"Webtoon panels and gaps require {required_total_height} px, which exceeds canvas height ({canvas_spec.height_px} px)",
                    details={"required_height": required_total_height, "canvas_height": canvas_spec.height_px}
                )

        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(effective_canvas_spec)

        # Panel width calculation
        panel_w = usable_box.width * panel_width_ratio
        # Center panel horizontally within usable box
        panel_x = usable_box.x + ((usable_box.width - panel_w) / 2.0)

        # Build panels top-to-bottom
        panels: List[PanelSlot] = []
        cur_y = usable_box.y

        for i in range(panel_count):
            h_i = resolved_heights[i]
            raw_rect = Rect(x=panel_x, y=cur_y, width=panel_w, height=h_i)
            snapped = snap_to_pixel_grid(raw_rect)

            slot = PanelSlot(
                panel_id=f"panel_{i + 1:02d}",
                reading_order=i + 1,
                rect=snapped,
                is_full_bleed=(panel_width_ratio >= 1.0 and m.left == 0 and m.right == 0),
                is_intentional_overlap=False,
                z_index=0,
            )
            panels.append(slot)

            cur_y += h_i
            if i < len(resolved_gaps):
                cur_y += resolved_gaps[i]

        order_ids = [p.panel_id for p in panels]

        result = CanvasLayoutResult(
            canvas_id=f"canvas_webtoon_{uuid.uuid4().hex[:8]}",
            canvas_spec=effective_canvas_spec,
            page_spec=page_spec,
            template_id=self.template_id,
            template_version=self.version,
            reading_direction=ReadingDirection.LTR,  # Webtoons are conventionally scrolled top-to-bottom
            panel_slots=panels,
            trim_box=trim_box,
            bleed_box=bleed_box,
            safe_area_box=safe_area_box,
            usable_box=usable_box,
            reading_order_panel_ids=order_ids,
        )

        diags = self.validate_layout(result, strict=True)
        result.diagnostics = diags
        return result
