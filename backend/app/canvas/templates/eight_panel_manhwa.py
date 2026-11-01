"""
InkLoop Canvas Generation Engine (E2) - Eight-Panel Manhwa Template.
Modern manhwa print adaptation grid: 4 balanced tiers of 2 panels each (8 panels total).
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


class EightPanelManhwaTemplate(BaseLayoutTemplate):
    """
    8-panel episodic manhwa print layout:
    - 4 vertical tiers of 2 panels each
    - Rhythmically tuned for dialogue, reactions, and continuous episodic beats
    """
    template_id = LayoutTemplateId.EIGHT_PANEL_MANHWA
    version = "1.0.0"
    description = "8-panel episodic manhwa layout: 4 tiers of 2 panels each with narrative pacing."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        tier_ratios: Optional[List[float]] = None,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        v_gutter = gutters.vertical
        h_gutter = gutters.horizontal

        total_v_space = usable_box.height - (3 * v_gutter)
        if total_v_space <= 0:
            raise ImpossibleLayoutError("Vertical gutters exceed usable height")

        ratios = tier_ratios or [0.22, 0.28, 0.28, 0.22]
        sum_r = sum(ratios)
        norm_r = [r / sum_r for r in ratios]

        net_w = usable_box.width - h_gutter
        if net_w <= 0:
            raise ImpossibleLayoutError("Horizontal gutter exceeds usable width")
        col_w = net_w / 2.0

        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)
        p_ids = [
            (panel_ids[i] if panel_ids and len(panel_ids) > i else f"panel_{i+1:02d}")
            for i in range(8)
        ]

        panels = []
        curr_y = usable_box.y
        panel_idx = 0
        for t_idx, r in enumerate(norm_r):
            h_tier = total_v_space * r
            cols = [1, 0] if is_rtl else [0, 1]
            for col_idx in cols:
                x_pos = usable_box.x + (col_idx * (col_w + h_gutter))
                panels.append(PanelSlot(
                    panel_id=p_ids[panel_idx],
                    reading_order=panel_idx + 1,
                    rect=snap_to_pixel_grid(Rect(
                        x=x_pos,
                        y=curr_y,
                        width=col_w,
                        height=h_tier,
                    )),
                    is_full_bleed=False,
                    is_intentional_overlap=False,
                    z_index=0,
                ))
                panel_idx += 1
            curr_y += h_tier + v_gutter

        import uuid
        order_ids = [p.panel_id for p in panels]
        result = CanvasLayoutResult(
            canvas_id=f"canvas_manhwa_{uuid.uuid4().hex[:8]}",
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
