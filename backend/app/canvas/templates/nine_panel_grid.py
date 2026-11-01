"""
InkLoop Canvas Generation Engine (E2) - Nine-Panel Grid Template.
Classic uniform 3x3 layout for high-density psychological pacing and rhythmic beats.
"""
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
from app.canvas.errors import ImpossibleLayoutError
from app.canvas.templates.base import BaseLayoutTemplate


class NinePanelGridTemplate(BaseLayoutTemplate):
    """
    Classic 3x3 uniform grid (9 panels).
    Provides strict cadence for psychological tension, rhythmic dialogue, and suspense.
    """
    template_id = LayoutTemplateId.NINE_PANEL_GRID
    version = "1.0.0"
    description = "Classic uniform 3x3 grid (9 panels) for dense psychological storytelling."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        v_gutter = gutters.vertical
        h_gutter = gutters.horizontal

        net_w = usable_box.width - (2 * h_gutter)
        net_h = usable_box.height - (2 * v_gutter)
        if net_w <= 0 or net_h <= 0:
            raise ImpossibleLayoutError("Gutters exceed usable dimensions for 3x3 grid")

        col_w = net_w / 3.0
        row_h = net_h / 3.0
        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)

        p_ids = [
            (panel_ids[i] if panel_ids and len(panel_ids) > i else f"panel_{i+1:02d}")
            for i in range(9)
        ]

        panels = []
        panel_idx = 0
        for r in range(3):
            y_pos = usable_box.y + (r * (row_h + v_gutter))
            cols = [2, 1, 0] if is_rtl else [0, 1, 2]
            for c in cols:
                x_pos = usable_box.x + (c * (col_w + h_gutter))
                slot = PanelSlot(
                    panel_id=p_ids[panel_idx],
                    reading_order=panel_idx + 1,
                    rect=snap_to_pixel_grid(Rect(
                        x=x_pos,
                        y=y_pos,
                        width=col_w,
                        height=row_h,
                    )),
                    is_full_bleed=False,
                    is_intentional_overlap=False,
                    z_index=0,
                )
                panels.append(slot)
                panel_idx += 1

        import uuid
        order_ids = [p.panel_id for p in panels]
        result = CanvasLayoutResult(
            canvas_id=f"canvas_nine_{uuid.uuid4().hex[:8]}",
            canvas_spec=canvas_spec,
            page_spec=page_spec,
            template_id=self.template_id,
            template_version=self.version,
            reading_direction=page_spec.reading_direction,
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
