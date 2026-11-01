"""
InkLoop Canvas Generation Engine (E2) - Two-Panel Dramatic Spread Template.
Features two panoramic horizontal landscape panels for monumental establishing vistas or before/after duality.
"""
from typing import List, Optional, Any
from app.contracts.geometry import Rect, snap_to_pixel_grid
from app.canvas.models import (
    CanvasSpec,
    PageSpec,
    PanelSlot,
    CanvasLayoutResult,
    LayoutTemplateId,
)
from app.canvas.errors import ImpossibleLayoutError
from app.canvas.templates.base import BaseLayoutTemplate


class TwoPanelDramaticSpreadTemplate(BaseLayoutTemplate):
    """
    2-panel panoramic horizontal layout:
    - Tier 1 (top): Wide landscape vista (50% usable height)
    - Tier 2 (bottom): Wide landscape vista (50% usable height)
    """
    template_id = LayoutTemplateId.TWO_PANEL_DRAMATIC_SPREAD
    version = "1.0.0"
    description = "Two panoramic horizontal landscape panels (50/50 split) for monumental vistas."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        top_ratio: float = 0.50,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        v_gutter = gutters.vertical
        net_h = usable_box.height - v_gutter
        if net_h <= 0:
            raise ImpossibleLayoutError("Vertical gutter exceeds usable height")

        h_top = net_h * top_ratio
        h_bot = net_h * (1.0 - top_ratio)

        p1_id = panel_ids[0] if panel_ids and len(panel_ids) > 0 else "panel_01"
        p2_id = panel_ids[1] if panel_ids and len(panel_ids) > 1 else "panel_02"

        slot_p1 = PanelSlot(
            panel_id=p1_id,
            reading_order=1,
            rect=snap_to_pixel_grid(Rect(
                x=usable_box.x,
                y=usable_box.y,
                width=usable_box.width,
                height=h_top,
            )),
            is_full_bleed=False,
            is_intentional_overlap=False,
            z_index=0,
        )

        slot_p2 = PanelSlot(
            panel_id=p2_id,
            reading_order=2,
            rect=snap_to_pixel_grid(Rect(
                x=usable_box.x,
                y=usable_box.y + h_top + v_gutter,
                width=usable_box.width,
                height=h_bot,
            )),
            is_full_bleed=False,
            is_intentional_overlap=False,
            z_index=0,
        )

        import uuid
        panels = [slot_p1, slot_p2]
        order_ids = [p.panel_id for p in panels]
        result = CanvasLayoutResult(
            canvas_id=f"canvas_spread_{uuid.uuid4().hex[:8]}",
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
