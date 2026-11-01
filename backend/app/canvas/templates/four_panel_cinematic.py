"""
InkLoop Canvas Generation Engine (E2) - Four-Panel Cinematic Template.
Features a panoramic 16:9 widescreen establishing header with 3 vertical rhythm panels below.
"""
from typing import List, Optional, Any
from app.contracts.geometry import Rect, Point, snap_to_pixel_grid
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


class FourPanelCinematicTemplate(BaseLayoutTemplate):
    """
    4-panel cinematic sequence layout:
    - Tier 1 (top): Wide letterbox panoramic establishing panel (45% height)
    - Tier 2 (bottom): 3 vertical panels for emotional cadence and sequential beats
    """
    template_id = LayoutTemplateId.FOUR_PANEL_CINEMATIC
    version = "1.0.0"
    description = "Cinematic 16:9 widescreen header with 3 vertical cadence panels below."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        header_ratio: float = 0.45,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        v_gutter = gutters.vertical
        h_gutter = gutters.horizontal

        net_h = usable_box.height - v_gutter
        if net_h <= 0:
            raise ImpossibleLayoutError("Vertical gutter exceeds usable height")

        h_top = net_h * header_ratio
        h_bot = net_h * (1.0 - header_ratio)

        # Tier 1: Wide panoramic header
        p1_id = panel_ids[0] if panel_ids and len(panel_ids) > 0 else "panel_01"
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

        # Tier 2: 3 vertical rhythm panels
        net_w = usable_box.width - (2 * h_gutter)
        if net_w <= 0:
            raise ImpossibleLayoutError("Horizontal gutters exceed usable width")

        col_w = net_w / 3.0
        y_bot = usable_box.y + h_top + v_gutter
        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)

        p2_id = panel_ids[1] if panel_ids and len(panel_ids) > 1 else "panel_02"
        p3_id = panel_ids[2] if panel_ids and len(panel_ids) > 2 else "panel_03"
        p4_id = panel_ids[3] if panel_ids and len(panel_ids) > 3 else "panel_04"

        slots_bot = []
        for i, pid in enumerate([p2_id, p3_id, p4_id]):
            col_idx = (2 - i) if is_rtl else i
            x_pos = usable_box.x + (col_idx * (col_w + h_gutter))
            slots_bot.append(PanelSlot(
                panel_id=pid,
                reading_order=i + 2,
                rect=snap_to_pixel_grid(Rect(
                    x=x_pos,
                    y=y_bot,
                    width=col_w,
                    height=h_bot,
                )),
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            ))

        import uuid
        panels = [slot_p1] + slots_bot
        order_ids = [p.panel_id for p in panels]
        result = CanvasLayoutResult(
            canvas_id=f"canvas_cinematic_{uuid.uuid4().hex[:8]}",
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
